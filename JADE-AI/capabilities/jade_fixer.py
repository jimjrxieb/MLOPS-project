"""jade_fixer.py — JADE Fixer Engine: Mini Claude CLI for C-Rank Autonomous Fixes.

3-phase pipeline:
  1. INVESTIGATE — Read files, search code, query RAG for context
  2. DIAGNOSE   — LLM-powered root cause analysis with domain-specific prompt
  3. GENERATE   — LLM-powered fix generation with code_before/code_after

JADE Fixer has deterministic investigation tools (read, search, list) and
uses LLM only for diagnosis + fix generation. Max 5 LLM calls per finding
as a cost safety limit.

Dependencies are injected (LLM query function, RAG query function) so the
engine is testable without live services.
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from jade_domains import detect_domain, get_domain_config, DomainConfig

logger = logging.getLogger(__name__)

# Safety limit: max LLM calls per finding
MAX_LLM_CALLS = 5


@dataclass
class InvestigationContext:
    """Context gathered during the investigation phase."""
    domain: str = "general"
    domain_config: Optional[DomainConfig] = None
    file_content: str = ""
    file_path: str = ""
    surrounding_code: str = ""
    related_files: List[str] = field(default_factory=list)
    related_code: List[str] = field(default_factory=list)
    rag_context: str = ""
    search_results: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Diagnosis:
    """Structured diagnosis from LLM analysis."""
    root_cause: str = ""
    fix_location: str = ""
    fix_strategy: str = ""
    confidence: float = 0.0


@dataclass
class FixResult:
    """Result of the fix generation phase."""
    success: bool = False
    code_before: str = ""
    code_after: str = ""
    fix_type: str = ""
    description: str = ""
    confidence: float = 0.0
    domain: str = "general"
    error: str = ""
    llm_calls_used: int = 0


class JADEFixer:
    """JADE Fixer Engine — investigates, diagnoses, and generates fixes for C-rank findings.

    Args:
        llm_query_fn: Callable(prompt, system_prompt=None, max_tokens=None) -> Optional[str]
            Function to query the LLM. Returns response text or None.
        rag_query_fn: Callable(query, top_k=5) -> str
            Function to query RAG knowledge base. Returns context string.
        max_llm_calls: Safety limit on LLM calls per finding.
    """

    def __init__(
        self,
        llm_query_fn: Callable,
        rag_query_fn: Callable,
        max_llm_calls: int = MAX_LLM_CALLS,
    ):
        self._llm = llm_query_fn
        self._rag = rag_query_fn
        self._max_llm_calls = max_llm_calls
        self._llm_calls = 0

    def fix(self, finding: Dict[str, Any], target_path: str) -> FixResult:
        """Run the full 3-phase pipeline for a single finding.

        Args:
            finding: Finding dict (rule_id, scanner, file, line, message, severity, etc.)
            target_path: Root path of the project being scanned.

        Returns:
            FixResult with code_before/code_after if successful.
        """
        self._llm_calls = 0
        result = FixResult()

        try:
            # Phase 1: Investigate
            context = self._investigate(finding, target_path)
            result.domain = context.domain

            if not context.file_content:
                result.error = "Could not read target file for investigation"
                return result

            # Phase 2: Diagnose
            diagnosis = self._diagnose(finding, context)
            if not diagnosis.root_cause:
                result.error = "Diagnosis failed: no root cause identified"
                return result

            if diagnosis.confidence < 0.3:
                result.error = f"Diagnosis confidence too low: {diagnosis.confidence:.2f}"
                return result

            # Phase 3: Generate fix
            result = self._generate_fix(finding, context, diagnosis)
            result.domain = context.domain

        except Exception as e:
            logger.error("JADEFixer pipeline error: %s", e)
            result.error = f"Pipeline error: {e}"

        result.llm_calls_used = self._llm_calls
        return result

    # =========================================================================
    # PHASE 1: INVESTIGATE
    # =========================================================================

    def _investigate(self, finding: Dict[str, Any], target_path: str) -> InvestigationContext:
        """Gather context about the finding: read file, detect domain, search related code, query RAG."""
        ctx = InvestigationContext()

        # Detect domain
        ctx.domain = detect_domain(finding)
        ctx.domain_config = get_domain_config(ctx.domain)

        # Read the target file
        file_path = finding.get("file") or finding.get("file_path", "")
        line = finding.get("line")

        if file_path:
            if line:
                ctx.surrounding_code = self._read_context(file_path, line, target_path, window=30)
            ctx.file_content = self._read_file(file_path, target_path)
            ctx.file_path = file_path

        # Search for related patterns
        rule_id = finding.get("rule_id", "")
        message = finding.get("message", "")

        # Search for imports/references to the problematic code
        if ctx.domain_config and ctx.domain_config.search_terms:
            for term in ctx.domain_config.search_terms[:3]:
                results = self._search_code(term, target_path, max_results=3)
                ctx.search_results.extend(results)

        # List related files by domain patterns
        if ctx.domain_config and ctx.domain_config.file_patterns:
            for pattern in ctx.domain_config.file_patterns[:2]:
                files = self._list_files(target_path, pattern)
                ctx.related_files.extend(files[:5])

        # Query RAG for domain knowledge
        rag_query = f"fix {rule_id} {message} {ctx.domain} security"
        ctx.rag_context = self._rag(rag_query, top_k=3) if self._rag else ""

        return ctx

    # =========================================================================
    # PHASE 2: DIAGNOSE
    # =========================================================================

    def _diagnose(self, finding: Dict[str, Any], context: InvestigationContext) -> Diagnosis:
        """Use LLM to analyze root cause and determine fix strategy."""
        if self._llm_calls >= self._max_llm_calls:
            return Diagnosis()

        domain_config = context.domain_config or get_domain_config("general")
        system_prompt = domain_config.system_prompt

        # Build diagnosis prompt
        rule_id = finding.get("rule_id", "unknown")
        severity = finding.get("severity", "MEDIUM")
        message = finding.get("message") or finding.get("title") or finding.get("description", "")
        line = finding.get("line", "N/A")

        # Use surrounding code (focused) if available, else full file (truncated)
        code_section = context.surrounding_code or context.file_content[:3000]

        rag_section = ""
        if context.rag_context:
            rag_section = f"\n--- Platform Knowledge ---\n{context.rag_context}\n"

        related_section = ""
        if context.search_results:
            snippets = []
            for r in context.search_results[:5]:
                snippets.append(f"  [{r.get('file', '?')}:{r.get('line', '?')}] {r.get('content', '')[:200]}")
            related_section = f"\n--- Related Code ---\n" + "\n".join(snippets) + "\n"

        prompt = f"""Diagnose this security finding and determine the fix strategy.

Rule: {rule_id}
Severity: {severity}
File: {context.file_path}
Line: {line}
Issue: {message}

--- File Content ---
{code_section}
{rag_section}{related_section}
Respond with ONLY valid JSON:
{{"root_cause": "what causes this vulnerability", "fix_location": "file:line or area to fix", "fix_strategy": "specific steps to fix", "confidence": 0.0-1.0}}"""

        self._llm_calls += 1
        response = self._llm(prompt, system_prompt=system_prompt, max_tokens=500)
        if not response:
            return Diagnosis()

        return self._parse_diagnosis(response)

    def _parse_diagnosis(self, response: str) -> Diagnosis:
        """Parse LLM diagnosis response into Diagnosis dataclass."""
        try:
            cleaned = self._extract_json(response)
            if not cleaned:
                return Diagnosis()

            data = json.loads(cleaned)
            confidence = data.get("confidence", 0.0)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except ValueError:
                    confidence = 0.5

            return Diagnosis(
                root_cause=data.get("root_cause", ""),
                fix_location=data.get("fix_location", ""),
                fix_strategy=data.get("fix_strategy", ""),
                confidence=min(max(confidence, 0.0), 1.0),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug("Failed to parse diagnosis: %s", e)
            return Diagnosis()

    # =========================================================================
    # PHASE 3: GENERATE FIX
    # =========================================================================

    def _generate_fix(
        self,
        finding: Dict[str, Any],
        context: InvestigationContext,
        diagnosis: Diagnosis,
    ) -> FixResult:
        """Use LLM to generate code_before/code_after fix."""
        if self._llm_calls >= self._max_llm_calls:
            return FixResult(error="LLM call limit reached")

        domain_config = context.domain_config or get_domain_config("general")
        system_prompt = domain_config.system_prompt

        rule_id = finding.get("rule_id", "unknown")
        severity = finding.get("severity", "MEDIUM")
        message = finding.get("message") or finding.get("title") or ""

        # Use surrounding code for precise matching, fall back to full file
        code_section = context.surrounding_code or context.file_content[:4000]

        prompt = f"""Generate a fix for this security vulnerability.

Rule: {rule_id}
Severity: {severity}
File: {context.file_path}
Issue: {message}

Diagnosis:
- Root cause: {diagnosis.root_cause}
- Fix strategy: {diagnosis.fix_strategy}
- Fix location: {diagnosis.fix_location}

--- Current Code ---
{code_section}

IMPORTANT RULES:
1. code_before MUST be an EXACT substring of the current code above (copy-paste, preserve whitespace)
2. code_after is the replacement with the security fix applied
3. Make the MINIMAL change needed to fix the vulnerability
4. Do NOT change unrelated code

Respond with ONLY valid JSON:
{{"fix_type": "direct", "description": "what this fix does", "code_before": "exact vulnerable code", "code_after": "fixed code", "confidence": 0.0-1.0}}"""

        self._llm_calls += 1
        response = self._llm(prompt, system_prompt=system_prompt, max_tokens=1500)
        if not response:
            return FixResult(error="LLM returned no response for fix generation")

        result = self._parse_fix_response(response)

        # Validate code_before exists in the actual file
        if result.success and result.code_before:
            if not self._validate_code_before(result.code_before, context.file_content):
                # Retry with relaxed matching hint
                retry_result = self._retry_fix_generation(
                    finding, context, diagnosis, result.code_before
                )
                if retry_result.success:
                    return retry_result
                result.success = False
                result.error = "code_before not found in file (validation failed)"

        return result

    def _retry_fix_generation(
        self,
        finding: Dict[str, Any],
        context: InvestigationContext,
        diagnosis: Diagnosis,
        failed_code_before: str,
    ) -> FixResult:
        """Retry fix generation when code_before didn't match."""
        if self._llm_calls >= self._max_llm_calls:
            return FixResult(error="LLM call limit reached on retry")

        domain_config = context.domain_config or get_domain_config("general")
        code_section = context.surrounding_code or context.file_content[:4000]

        prompt = f"""Your previous fix attempt had a code_before that didn't match the file exactly.

Previous code_before (WRONG — not found in file):
{failed_code_before}

--- Actual File Content (copy from THIS exactly) ---
{code_section}

Rule: {finding.get('rule_id', 'unknown')}
Fix strategy: {diagnosis.fix_strategy}

Generate the fix again. code_before MUST be copied EXACTLY from the file content above.
Preserve all whitespace, indentation, and line breaks exactly.

Respond with ONLY valid JSON:
{{"fix_type": "direct", "description": "what this fix does", "code_before": "exact code from file", "code_after": "fixed code", "confidence": 0.0-1.0}}"""

        self._llm_calls += 1
        response = self._llm(prompt, system_prompt=domain_config.system_prompt, max_tokens=1500)
        if not response:
            return FixResult(error="LLM returned no response on retry")

        result = self._parse_fix_response(response)

        if result.success and result.code_before:
            if not self._validate_code_before(result.code_before, context.file_content):
                result.success = False
                result.error = "code_before still not found in file after retry"

        return result

    def _parse_fix_response(self, response: str) -> FixResult:
        """Parse LLM fix response into FixResult."""
        try:
            cleaned = self._extract_json(response)
            if not cleaned:
                return FixResult(error="No JSON found in LLM response")

            data = json.loads(cleaned)
            code_before = data.get("code_before", "")
            code_after = data.get("code_after", "")

            if not code_before or not code_after:
                return FixResult(
                    error="Missing code_before or code_after",
                    description=data.get("description", ""),
                )

            if code_before == code_after:
                return FixResult(error="code_before equals code_after — no change")

            confidence = data.get("confidence", 0.7)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except ValueError:
                    confidence = 0.7

            return FixResult(
                success=True,
                code_before=code_before,
                code_after=code_after,
                fix_type=data.get("fix_type", "direct"),
                description=data.get("description", ""),
                confidence=min(max(confidence, 0.0), 1.0),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug("Failed to parse fix response: %s", e)
            return FixResult(error=f"JSON parse error: {e}")

    def _validate_code_before(self, code_before: str, file_content: str) -> bool:
        """Check if code_before exists in file_content.

        Tries exact match first, then whitespace-normalized match.
        """
        if not code_before or not file_content:
            return False

        # Exact match
        if code_before in file_content:
            return True

        # Whitespace-normalized match
        normalized_before = " ".join(code_before.split())
        normalized_content = " ".join(file_content.split())
        return normalized_before in normalized_content

    # =========================================================================
    # TOOL METHODS (deterministic, no LLM)
    # =========================================================================

    def _read_file(self, path: str, target_path: str, start: int = None, end: int = None) -> str:
        """Read a file's contents, optionally a line range.

        Args:
            path: File path (relative or absolute).
            target_path: Project root for resolving relative paths.
            start: Start line (1-indexed, inclusive). None = from beginning.
            end: End line (1-indexed, inclusive). None = to end.

        Returns:
            File content string, or empty string on error.
        """
        fp = Path(path)
        if not fp.is_absolute():
            fp = Path(target_path) / fp

        if not fp.exists() or not fp.is_file():
            return ""

        try:
            content = fp.read_text(encoding="utf-8", errors="replace")

            if start is not None or end is not None:
                lines = content.splitlines(keepends=True)
                s = (start - 1) if start and start > 0 else 0
                e = end if end else len(lines)
                return "".join(lines[s:e])

            # Truncate very large files
            if len(content) > 50000:
                return content[:50000] + "\n... (truncated)"

            return content
        except Exception as e:
            logger.debug("Failed to read %s: %s", fp, e)
            return ""

    def _read_context(self, file_path: str, line: int, target_path: str, window: int = 30) -> str:
        """Read lines around a specific line number.

        Args:
            file_path: File to read.
            line: Center line number (1-indexed).
            target_path: Project root.
            window: Number of lines above and below to include.

        Returns:
            Code context string with line numbers.
        """
        start = max(1, line - window)
        end = line + window

        fp = Path(file_path)
        if not fp.is_absolute():
            fp = Path(target_path) / fp

        if not fp.exists():
            return ""

        try:
            all_lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
            s = max(0, start - 1)
            e = min(len(all_lines), end)
            numbered = []
            for i, l in enumerate(all_lines[s:e], start=s + 1):
                marker = " >>> " if i == line else "     "
                numbered.append(f"{marker}{i:4d} | {l}")
            return "\n".join(numbered)
        except Exception as e:
            logger.debug("Failed to read context from %s: %s", fp, e)
            return ""

    # Directories to skip during code search — these are large, generated,
    # or irrelevant and cause grep to time out on real projects.
    _SEARCH_EXCLUDE_DIRS = [
        "node_modules", ".git", "__pycache__", "dist", "build",
        ".next", ".nuxt", "vendor", "venv", ".venv", "env",
        ".tox", ".mypy_cache", ".pytest_cache", "coverage",
        ".terraform", ".gradle", "target",
        ".jsa", "localstack-data",  # JSA scan artifacts + localstack cache
    ]

    def _search_code(self, pattern: str, target_path: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search for a pattern in the project using grep.

        Uses find -prune | xargs grep so excluded directories are never
        entered at the filesystem level. Plain --exclude-dir still stat()s
        every entry in huge dirs like node_modules, causing timeouts.

        Args:
            pattern: Search pattern (literal string or simple regex).
            target_path: Project root to search in.
            max_results: Maximum number of results.

        Returns:
            List of dicts with file, line, content keys.
        """
        try:
            # Build find with -prune to skip excluded dirs entirely
            find_cmd = ["find", target_path]
            # ( -name dir1 -o -name dir2 ... ) -prune -o -type f -print0
            find_cmd.append("(")
            for i, d in enumerate(self._SEARCH_EXCLUDE_DIRS):
                if i > 0:
                    find_cmd.append("-o")
                find_cmd.extend(["-name", d])
            find_cmd.extend([")", "-prune", "-o", "-type", "f", "-print0"])

            find_proc = subprocess.Popen(
                find_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            grep_proc = subprocess.Popen(
                ["xargs", "-0", "-r", "grep", "-n", "-m", str(max_results), "--", pattern],
                stdin=find_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            find_proc.stdout.close()  # allow find to receive SIGPIPE

            stdout, _ = grep_proc.communicate(timeout=10)
            find_proc.wait(timeout=2)

            results = []
            for match_line in stdout.strip().splitlines()[:max_results]:
                parts = match_line.split(":", 2)
                if len(parts) >= 3:
                    results.append({
                        "file": parts[0],
                        "line": parts[1],
                        "content": parts[2].strip()[:200],
                    })
            return results
        except Exception as e:
            logger.debug("Search failed for pattern '%s': %s", pattern, e)
            return []

    def _list_files(self, target_path: str, glob_pattern: str) -> List[str]:
        """List files matching a glob pattern under target_path.

        Args:
            target_path: Project root.
            glob_pattern: Glob pattern (e.g. "*.yaml", "templates/*.yaml").

        Returns:
            List of relative file paths.
        """
        try:
            root = Path(target_path)
            matches = sorted(root.rglob(glob_pattern))
            return [str(m.relative_to(root)) for m in matches[:20]]
        except Exception as e:
            logger.debug("File listing failed for '%s': %s", glob_pattern, e)
            return []

    # =========================================================================
    # UTILITY
    # =========================================================================

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Extract JSON object from LLM response text.

        Uses balanced-brace tracking to find the correct JSON boundaries,
        handling nested braces inside string values, code examples, and
        markdown that jade:v1.0 frequently includes in responses.
        """
        if not text:
            return None

        cleaned = text.strip()

        # Remove markdown code fences
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1]
        if "```" in cleaned:
            cleaned = cleaned.split("```")[0]
        cleaned = cleaned.strip()

        # Try balanced-brace extraction: find the first '{' and walk
        # forward tracking brace depth, respecting JSON string literals.
        start = cleaned.find("{")
        if start < 0:
            return None

        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                if in_string:
                    escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start:i + 1]
                    # Validate it actually parses
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        # This balanced block didn't parse — keep scanning
                        # for a later '{' that might work
                        next_start = cleaned.find("{", start + 1)
                        if next_start >= 0 and next_start < i:
                            # Reset and try from the next '{' (recursive-ish)
                            pass
                        else:
                            # No more candidates, return best effort
                            return candidate

        # Fallback: first '{' to last '}' (original behaviour)
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            return cleaned[start:end]

        return None
