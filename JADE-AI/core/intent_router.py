"""
JADE Intent Router
Classifies user intent via LLM and routes to appropriate handler.

Extracted from jade.py monolith — handles:
- Intent classification (_understand) via LLM with keyword fallback
- Intent routing (_act) to 19 handler types
- All classic-mode handlers (projects, scan, fix, cluster, git, etc.)
"""

import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def _get_scanner(finding: dict) -> str:
    """Get scanner name from finding, checking both 'scanner' and 'source_scanner' fields."""
    if not isinstance(finding, dict):
        return "unknown"
    scanner = finding.get("scanner", "") or finding.get("source_scanner", "") or "unknown"
    return scanner.lower() if isinstance(scanner, str) else "unknown"


class IntentRouter:
    """Classifies user intent and routes to appropriate handler."""

    def __init__(self, jade):
        """
        Args:
            jade: JADE instance (provides llm, rag, context, tools, fixer_classes, etc.)
        """
        self.jade = jade

    # =========================================================================
    # INTENT CLASSIFICATION
    # =========================================================================

    def understand(self, message: str) -> Dict[str, Any]:
        """Use LLM to understand what the user wants."""
        intent = {
            "type": None,
            "target": None,
            "details": {}
        }

        classify_prompt = f"""Classify this user message into ONE of these categories:

Message: "{message}"

Categories:
- "projects" = asking about GP-PROJECTS, instances, project counts, project names
- "scanners" = asking about NPCs, scanners, fixers, tools we have
- "cluster" = ACTION requests to show/list/get cluster resources (show pods, list nodes, get deployments, cluster status)
- "scan" = requesting a security scan on something
- "deploy_jsa" = deploying a JSA agent
- "jsa_status" = checking JSA status (is it running, deployed)
- "jsa_logs" = asking about JSA findings, fixes, what was fixed, what's left, fix history, pending reviews, summarize cycle, latest findings
- "followup" = FOLLOW-UP questions OR ACTIONS about previous results: dive deeper, more details, show me the X findings, expand on Y, what about Z from before, how to fix these, fix these please, please fix, fix them, apply fixes, filter by scanner/severity
- "training" = asking about model training
- "generate" = asking to create/generate code (gatekeeper, policy, manifest)
- "platform" = asking about GP-Copilot platform, capabilities, structure
- "git_check" = check for git changes, updates, what teammate changed, repo sync status
- "git_reject" = reject changes, deny bad code, push correct code, force push, revert remote
- "git_diff" = show diff, what changed, show changes
- "greeting" = hello, hi, hey
- "help" = asking for help or capabilities
- "question" = KNOWLEDGE questions (what is X, explain Y, how does Z work, best practices) - use this for conceptual questions about kubernetes, security, policies, etc.

IMPORTANT: If user asks "what is a network policy" or "explain kubernetes RBAC", that's a "question" NOT "cluster".
Only use "cluster" for ACTION requests like "show pods", "get nodes", "list deployments".
Use "followup" when user references previous results (unknown scanner, these findings, the HIGH severity ones, etc).

Also extract any target (project name, instance number, etc).

Respond with ONLY valid JSON:
{{"intent": "category_name", "target": "extracted_target_or_null", "needs_rag": true/false}}"""

        try:
            response = self.jade.llm.generate(
                prompt=classify_prompt,
                system_prompt="You are an intent classifier. Return ONLY JSON, no other text.",
                temperature=0.1,
                max_tokens=100
            )

            # Parse JSON from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()

            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                intent["type"] = parsed.get("intent", "question")
                intent["target"] = parsed.get("target")
                intent["needs_rag"] = parsed.get("needs_rag", True)
            else:
                intent["type"] = "question"
                intent["needs_rag"] = True

            # Post-LLM override: If context exists and user wants to fix, force followup
            msg = message.lower()
            if self.jade.context.get("last_cycle") and any(kw in msg for kw in [
                "fix these", "please fix", "fix them", "apply fix", "go ahead", "do it"
            ]):
                intent["type"] = "followup"
                intent["needs_rag"] = False

        except Exception:
            # Fallback to simple keywords if LLM fails
            msg = message.lower()
            if any(w in msg for w in ["hello", "hi", "hey"]):
                intent["type"] = "greeting"
            elif "scan" in msg and any(w in msg for w in ["run", "start", "perform", "do"]):
                intent["type"] = "scan"
            elif any(w in msg for w in [
                "dive deeper", "more details", "expand on", "these findings",
                "how to fix", "fix these", "please fix", "fix them", "apply fix"
            ]) or \
                 (any(w in msg for w in ["unknown", "scanner", "severity", "findings"]) and
                  self.jade.context.get("last_cycle")) or \
                 (any(w in msg for w in ["fix", "these", "them"]) and
                  self.jade.context.get("last_cycle")):
                intent["type"] = "followup"
            elif any(action in msg for action in ["show", "list", "get", "status"]) and \
                 any(resource in msg for resource in ["pod", "node", "deploy", "service", "namespace"]):
                intent["type"] = "cluster"
            elif "kubectl" in msg:
                intent["type"] = "cluster"
            else:
                intent["type"] = "question"
                intent["needs_rag"] = True

        return intent

    # =========================================================================
    # INTENT ROUTING
    # =========================================================================

    def act(self, message: str, intent: Dict[str, Any]) -> str:
        """Take action based on understood intent."""
        itype = intent["type"]

        if itype == "projects":
            return self._handle_projects(intent)
        elif itype == "scanners":
            return self._handle_scanners(message)
        elif itype == "platform":
            return self._handle_platform(message)
        elif itype == "generate":
            return self.jade.chat_handler.handle_generate(message)
        elif itype == "deploy_jsa":
            return self._handle_deploy_jsa(intent)
        elif itype == "jsa_status":
            return self._handle_jsa_status()
        elif itype == "jsa_logs":
            return self._handle_jsa_logs(message)
        elif itype == "followup":
            return self._handle_followup(message)
        elif itype == "training":
            return self._handle_training()
        elif itype == "logs":
            return self._handle_logs(message)
        elif itype == "cluster":
            return self._handle_cluster_real(message)
        elif itype == "scan":
            return self._handle_scan(intent)
        elif itype == "git_check":
            return self._handle_git_check(intent)
        elif itype == "git_reject":
            return self._handle_git_reject(intent)
        elif itype == "git_diff":
            return self._handle_git_diff(intent)
        elif itype == "greeting":
            return self.jade.chat_handler.greeting()
        elif itype == "help":
            return self.jade.chat_handler.help_text()
        else:
            return self.jade.chat_handler.answer_with_rag(message)

    # =========================================================================
    # HANDLERS
    # =========================================================================

    def _handle_projects(self, intent: Dict) -> str:
        """Handle project/instance queries by reading actual GP-PROJECTS directory."""
        gp_projects = Path(__file__).parent.parent.parent / "GP-PROJECTS"
        if not gp_projects.exists():
            return "GP-PROJECTS directory not found."

        target = intent.get("target")

        instances = {}
        for item in sorted(gp_projects.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                if "instance" in item.name.lower():
                    projects = sorted([p.name for p in item.iterdir()
                                       if p.is_dir() and not p.name.startswith('.')])
                    instances[item.name] = projects
                else:
                    if "standalone" not in instances:
                        instances["standalone"] = []
                    instances["standalone"].append(item.name)

        if target:
            target_normalized = target.lower().replace("-", "").replace("_", "")
            for inst_name, projects in instances.items():
                inst_normalized = inst_name.lower().replace("-", "").replace("_", "")
                if target_normalized in inst_normalized or inst_normalized in target_normalized:
                    if not projects:
                        return f"{inst_name} has no projects."
                    resp = f"**{inst_name}** has {len(projects)} project(s):\n"
                    for i, proj in enumerate(projects, 1):
                        marker = " (first)" if i == 1 else ""
                        resp += f"\n  {i}. **{proj}**{marker}"
                    resp += f"\n\nFirst project: **{projects[0]}**"
                    return resp
            return f"Instance '{target}' not found. Available: {', '.join(instances.keys())}"

        else:
            total_projects = sum(len(p) for p in instances.values())
            resp = f"**GP-PROJECTS Structure** ({total_projects} projects total):\n"
            for inst_name, projects in instances.items():
                if inst_name == "standalone":
                    resp += f"\n**Standalone Projects:** {', '.join(projects)}"
                else:
                    resp += f"\n**{inst_name}** ({len(projects)} projects):"
                    for proj in projects[:5]:
                        resp += f"\n  - {proj}"
                    if len(projects) > 5:
                        resp += f"\n  ... and {len(projects) - 5} more"
            return resp

    def _handle_deploy_jsa(self, intent: Dict) -> str:
        """Deploy JSA."""
        if not self.jade.jsa:
            return "JSA deployer not available."

        name = intent.get("target", "shadow")
        result = self.jade.jsa.deploy(name, dry_run=True)

        if result.get("error"):
            return f"Can't deploy JSA: {result['error']}"

        ctx = result.get("context", "unknown")
        ns = result.get("namespace", "jsa-system")

        return f"""**JSA '{name}' deployment ready**

Cluster: {ctx}
Namespace: {ns}
Model: scdao:v0.3
Permissions: D-rank (read-only)

This is a dry-run. Say "confirm deploy jsa {name}" to actually deploy it."""

    def _handle_jsa_status(self) -> str:
        """JSA status."""
        if not self.jade.jsa:
            return "JSA deployer not available."

        result = self.jade.jsa.list_instances()
        instances = result.get("instances", [])

        if not instances:
            return "No JSA instances deployed. Say 'deploy jsa called shadow' to create one."

        resp = f"**{len(instances)} JSA instance(s):**\n"
        for inst in instances:
            name = inst.get("name", "unknown")
            status = inst.get("status", "unknown")
            ns = inst.get("namespace", "")
            resp += f"\n  - **{name}**: {status} ({ns})"

        return resp

    def _handle_jsa_logs(self, message: str = "") -> str:
        """Show JSA fix history, findings, and pending reviews."""
        jsa_logs_base = Path(__file__).parent.parent.parent / "GP-BEDROCK-AGENTS" / "jadeSecureAgent" / "target-slot-logs"

        if not jsa_logs_base.exists():
            return f"JSA logs directory not found at:\n`{jsa_logs_base}`"

        instances = []
        for d in jsa_logs_base.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                if (d / "cycles").exists() or (d / "operations").exists() or (d / "state" / "pending").exists():
                    instances.append(d)

        if not instances:
            return "No JSA instance logs found. Run a JSA cycle first."

        msg = message.lower()
        if any(w in msg for w in ["summarize", "summary", "latest", "details", "show me"]):
            return self._summarize_latest_cycle(instances)

        resp = "**JSA Fix History & Findings**\n"

        for instance_dir in sorted(instances):
            instance_name = instance_dir.name
            has_content = False
            instance_resp = f"\n### {instance_name}\n"

            cycles_dir = instance_dir / "cycles"
            if cycles_dir.exists():
                cycle_files = sorted(cycles_dir.glob("*.json"), reverse=True)[:3]
                if cycle_files:
                    has_content = True
                    instance_resp += f"**Latest cycles:** {len(list(cycles_dir.glob('*.json')))} total\n"
                    for cf in cycle_files:
                        instance_resp += f"  - `{cf.name}`\n"

            fixes_dir = instance_dir / "operations" / "fixes"
            if fixes_dir.exists():
                fix_files = sorted(fixes_dir.glob("*.json"), reverse=True)[:3]
                if fix_files:
                    has_content = True
                    instance_resp += f"**Recent fixes:** {len(list(fixes_dir.glob('*.json')))} total\n"
                    for ff in fix_files:
                        instance_resp += f"  - `{ff.name}`\n"

            pending_dir = instance_dir / "state" / "pending"
            if pending_dir.exists():
                pending_files = list(pending_dir.glob("*.json"))
                if pending_files:
                    has_content = True
                    instance_resp += f"**Pending reviews:** {len(pending_files)}\n"
                    for pf in pending_files[:5]:
                        instance_resp += f"  - `{pf.name}`\n"
                elif has_content:
                    instance_resp += "**Pending reviews:** None\n"

            if has_content:
                resp += instance_resp

        resp += f"\n**Log locations:**\n"
        resp += f"- Cycles: `target-slot-logs/<instance>/cycles/`\n"
        resp += f"- Fixes: `target-slot-logs/<instance>/operations/fixes/`\n"
        resp += f"- Pending: `target-slot-logs/<instance>/state/pending/`\n"
        resp += f"\nSay **'summarize latest jsa findings'** to see details."

        return resp

    def _summarize_latest_cycle(self, instances: list) -> str:
        """Summarize the latest cycle file."""
        latest_file = None
        latest_time = None

        for instance_dir in instances:
            cycles_dir = instance_dir / "cycles"
            if cycles_dir.exists():
                for cf in cycles_dir.glob("*.json"):
                    mtime = cf.stat().st_mtime
                    if latest_time is None or mtime > latest_time:
                        latest_time = mtime
                        latest_file = cf

        if not latest_file:
            return "No cycle files found to summarize."

        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return f"Failed to read cycle file: {e}"

        # Store in context for follow-up queries
        self.jade.context["last_cycle"] = {
            "file": str(latest_file),
            "instance": latest_file.parent.parent.name,
            "data": data
        }

        resp = f"**Latest Cycle Summary**\n"
        resp += f"**File:** `{latest_file.name}`\n"
        resp += f"**Instance:** {latest_file.parent.parent.name}\n\n"

        if isinstance(data, dict):
            if "timestamp" in data:
                resp += f"**Time:** {data['timestamp']}\n"
            if "duration_seconds" in data:
                resp += f"**Duration:** {data['duration_seconds']:.1f}s\n"

            findings = data.get("findings", data.get("total_findings", []))
            if isinstance(findings, list):
                resp += f"**Total findings:** {len(findings)}\n"

                by_severity = {}
                for f in findings:
                    sev = f.get("severity", "unknown") if isinstance(f, dict) else "unknown"
                    sev = sev.lower() if sev else "unknown"
                    by_severity[sev] = by_severity.get(sev, 0) + 1

                if by_severity:
                    resp += "**By severity:**\n"
                    for sev in ["critical", "high", "medium", "low", "info", "unknown"]:
                        if sev in by_severity:
                            resp += f"  - {sev.upper()}: {by_severity[sev]}\n"

                by_scanner = {}
                for f in findings:
                    scanner = _get_scanner(f)
                    by_scanner[scanner] = by_scanner.get(scanner, 0) + 1

                if by_scanner:
                    resp += "**By scanner:**\n"
                    for scanner, count in sorted(by_scanner.items(), key=lambda x: -x[1])[:5]:
                        resp += f"  - {scanner}: {count}\n"

            elif isinstance(findings, int):
                resp += f"**Total findings:** {findings}\n"

            if "fixes_attempted" in data:
                resp += f"\n**Fixes attempted:** {data['fixes_attempted']}\n"
            if "fixes_successful" in data:
                resp += f"**Fixes successful:** {data['fixes_successful']}\n"
            if "fix_rate" in data:
                resp += f"**Fix rate:** {data['fix_rate']:.1%}\n"

            if "decision" in data:
                decision = data["decision"]
                if isinstance(decision, dict):
                    resp += f"\n**Decision:** {decision.get('action', 'N/A')}\n"
                    resp += f"**Confidence:** {decision.get('confidence', 'N/A')}\n"
                else:
                    resp += f"\n**Decision:** {decision}\n"

            resp += "\n**Drill down:**\n"
            resp += "- 'dive deeper into unknown scanner findings'\n"
            resp += "- 'show me the HIGH severity findings'\n"
            resp += "- 'how should we fix these?'\n"

        return resp

    def _handle_followup(self, message: str) -> str:
        """Handle follow-up questions about previous results."""
        msg = message.lower()

        # Check for "why were they skipped?" questions
        if any(phrase in msg for phrase in ["why", "skipped", "why not", "couldn't fix", "didn't fix"]):
            fix_results = self.jade.context.get("last_fix_results")
            if fix_results and fix_results.get("skipped_details"):
                skipped = fix_results["skipped_details"]
                resp = f"**Why {len(skipped)} findings were skipped:**\n\n"

                by_reason = {}
                for item in skipped:
                    reason_key = item["reason"].split(".")[0]
                    if reason_key not in by_reason:
                        by_reason[reason_key] = []
                    by_reason[reason_key].append(item)

                for reason, items in by_reason.items():
                    resp += f"**{reason}** ({len(items)} findings)\n"
                    for item in items[:3]:
                        resp += f"  - `{item['rule_id']}` in `{Path(item['file']).name if item['file'] != 'unknown' else 'unknown'}`\n"
                    if len(items) > 3:
                        resp += f"  - ... and {len(items) - 3} more\n"
                    resp += "\n"

                resp += "**To add support for these rules:**\n"
                resp += "1. Add fix patterns to `code_fixer_npc.py`\n"
                resp += "2. Or create a new Fixer NPC for the scanner type\n"
                return resp
            else:
                return "No skipped findings to explain. Run 'please fix these' first to see what can be fixed."

        if not self.jade.context.get("last_cycle"):
            return "No previous cycle data to follow up on. Try 'summarize latest jsa findings' first."

        cycle_data = self.jade.context["last_cycle"]
        data = cycle_data.get("data", {})
        findings = data.get("findings", data.get("total_findings", []))

        if not isinstance(findings, list):
            return "No detailed findings available in the last cycle."

        resp = f"**Follow-up on cycle:** `{Path(cycle_data['file']).name}`\n\n"

        # Determine filters
        filter_scanner = None
        filter_severity = None

        scanners = set()
        for f in findings:
            if isinstance(f, dict):
                scanners.add(_get_scanner(f))

        for scanner in scanners:
            if scanner in msg:
                filter_scanner = scanner
                break

        for sev in ["critical", "high", "medium", "low", "info", "unknown"]:
            if sev in msg:
                filter_severity = sev
                break

        # Filter findings
        filtered = []
        for f in findings:
            if not isinstance(f, dict):
                continue
            scanner = _get_scanner(f)
            severity = (f.get("severity", "unknown") or "unknown").lower()

            if filter_scanner and scanner != filter_scanner:
                continue
            if filter_severity and severity != filter_severity:
                continue
            filtered.append(f)

        if not filtered:
            if filter_scanner or filter_severity:
                return f"No findings match the filter (scanner={filter_scanner}, severity={filter_severity})."
            filtered = findings[:20]

        # Check if user wants to EXECUTE fixes
        execute_keywords = ["please fix", "fix them", "fix these now", "apply fix", "go ahead", "do it", "execute", "run the fix"]
        wants_execution = any(kw in msg for kw in execute_keywords) or (msg.startswith("fix") and "how" not in msg)

        if wants_execution:
            return self._execute_fixes(filtered, cycle_data)

        # Fix recommendations
        if any(w in msg for w in ["fix", "remediate", "how to", "what should"]):
            resp += f"**Fix recommendations for {len(filtered)} findings:**\n\n"

            by_type = {}
            for f in filtered:
                ftype = f.get("rule_id", f.get("type", f.get("scanner", "unknown")))
                if ftype not in by_type:
                    by_type[ftype] = []
                by_type[ftype].append(f)

            for ftype, items in list(by_type.items())[:5]:
                resp += f"**{ftype}** ({len(items)} findings)\n"
                sample = items[0]
                file_path = sample.get("file", sample.get("path", "N/A"))
                resp += f"  - Example: `{file_path}`\n"

                scanner = _get_scanner(sample)
                if "trivy" in scanner or "grype" in scanner:
                    resp += f"  - Fix: Update vulnerable package versions\n"
                elif "gitleaks" in scanner or "secret" in ftype.lower():
                    resp += f"  - Fix: Remove secrets, use env vars or secrets manager\n"
                elif "bandit" in scanner or "semgrep" in scanner:
                    resp += f"  - Fix: Apply SAST remediation patterns\n"
                elif "kubescape" in scanner or "kube" in scanner.lower():
                    resp += f"  - Fix: Add security context, resource limits, or network policies\n"
                else:
                    resp += f"  - Fix: Review and apply security best practices\n"
                resp += "\n"

            resp += "\n**Ready to fix?** Say 'please fix these' to execute fixes."
            return resp

        # Default: show detailed findings
        resp += f"**Showing {len(filtered)} findings"
        if filter_scanner:
            resp += f" from {filter_scanner}"
        if filter_severity:
            resp += f" with {filter_severity.upper()} severity"
        resp += ":**\n\n"

        for i, f in enumerate(filtered[:15], 1):
            file_path = f.get("file", f.get("path", "N/A"))
            rule = f.get("rule_id", f.get("type", f.get("message", "")[:30]))
            severity = (f.get("severity", "?") or "?").upper()
            scanner = _get_scanner(f) or "?"
            resp += f"{i}. [{severity}] `{file_path}`\n"
            resp += f"   Rule: {rule} (via {scanner})\n"

        if len(filtered) > 15:
            resp += f"\n... and {len(filtered) - 15} more. Filter by scanner or severity to narrow down."

        resp += f"\n\n**Tips:**\n"
        resp += f"- Say 'how to fix these' for remediation guidance\n"
        resp += f"- Filter: 'show me the HIGH severity findings'\n"
        resp += f"- Filter: 'dive into {list(scanners)[:2]} findings'\n"

        return resp

    def _execute_fixes(self, findings: List[Dict], cycle_data: Dict) -> str:
        """Actually execute fixes using Fixer NPCs."""
        if not self.jade.fixer_classes:
            return "**Error:** Fixer NPCs not available. Install from GP-CONSULTING/2-App-Sec-Fixes/"

        resp = "**Executing fixes...**\n\n"
        skipped_details = []

        # Group findings by type
        sast_findings = []
        secrets_findings = []
        dependency_findings = []
        other_findings = []

        for f in findings:
            scanner = _get_scanner(f)
            rule_id = f.get("rule_id", "")

            if scanner in ["bandit", "semgrep"] or rule_id.startswith("B"):
                sast_findings.append(f)
            elif "gitleaks" in scanner or "secret" in scanner:
                secrets_findings.append(f)
            elif scanner in ["trivy", "grype"] or rule_id.startswith("CVE-") or rule_id.startswith("GHSA-"):
                dependency_findings.append(f)
            else:
                other_findings.append(f)

        target = cycle_data.get("data", {}).get("target", "")
        if not target:
            return "**Error:** Cannot determine target directory from cycle data."

        fixed_count = 0
        skipped_count = 0
        failed_count = 0

        CodeFixerNPC = self.jade.fixer_classes.get('code')
        SecretsFixerNPC = self.jade.fixer_classes.get('secrets')
        DependencyFixerNPC = self.jade.fixer_classes.get('dependency')

        # Fix SAST findings
        if sast_findings and CodeFixerNPC:
            resp += f"**SAST findings:** {len(sast_findings)}\n"
            try:
                fixer = CodeFixerNPC(dry_run=False)
                for finding in sast_findings[:10]:
                    rule_id = finding.get("rule_id", "")
                    file_path = finding.get("file", "")

                    if rule_id in fixer.FIX_PATTERNS:
                        result = fixer.apply_fix(finding, target)
                        if result.get("success"):
                            fixed_count += 1
                            resp += f"  Fixed {rule_id} in `{Path(file_path).name}`\n"
                        else:
                            failed_count += 1
                            error = result.get("error", "Unknown error")
                            resp += f"  Failed {rule_id}: {error}\n"
                            skipped_details.append({
                                "rule_id": rule_id, "file": file_path,
                                "reason": f"Fix failed: {error}",
                                "scanner": finding.get("scanner", "bandit")
                            })
                    else:
                        skipped_count += 1
                        resp += f"  Skipped {rule_id} (no auto-fix pattern)\n"
                        skipped_details.append({
                            "rule_id": rule_id, "file": file_path,
                            "reason": f"No auto-fix pattern available for {rule_id}.",
                            "scanner": finding.get("scanner", "bandit")
                        })
            except Exception as e:
                resp += f"  SAST fixer error: {e}\n"

        # Fix secrets
        if secrets_findings and SecretsFixerNPC:
            resp += f"\n**Secrets findings:** {len(secrets_findings)}\n"
            try:
                fixer = SecretsFixerNPC(dry_run=False)
                result = fixer.run(target, findings=secrets_findings)
                if result.get("success"):
                    fixed = result.get("fixed_count", 0)
                    fixed_count += fixed
                    resp += f"  Fixed {fixed} secrets\n"
                else:
                    resp += f"  Secrets fixer failed: {result.get('error', 'Unknown')}\n"
            except Exception as e:
                resp += f"  Secrets fixer error: {e}\n"

        # Fix dependencies
        if dependency_findings and DependencyFixerNPC:
            resp += f"\n**Dependency findings (CVE/GHSA):** {len(dependency_findings)}\n"
            try:
                dep_fixer = DependencyFixerNPC(dry_run=False)

                by_package = {}
                for f in dependency_findings:
                    pkg = f.get("package", f.get("pkg_name", f.get("file", "unknown")))
                    if pkg not in by_package:
                        by_package[pkg] = f

                dep_fixed = 0

                for pkg, finding in list(by_package.items())[:15]:
                    fixed_in = finding.get("fixed_in", finding.get("fixed_version", ""))
                    rule_id = finding.get("rule_id", "")

                    normalized = {
                        "package": pkg,
                        "pkg_name": pkg,
                        "version": finding.get("version", finding.get("installed_version", "")),
                        "fixed_version": fixed_in,
                        "pkg_type": finding.get("pkg_type", ""),
                        "severity": finding.get("severity", "HIGH"),
                        "cve": rule_id,
                    }

                    result = dep_fixer.apply_fix(normalized, target)
                    if result.get("success"):
                        dep_fixed += 1
                        fixed_count += 1
                        changes = result.get("changes", [])
                        if changes:
                            old_v = changes[0].get("old_version", "?")
                            new_v = changes[0].get("new_version", fixed_in)
                            resp += f"  `{pkg}`: {old_v} -> {new_v}\n"
                        else:
                            resp += f"  Fixed `{pkg}`\n"
                    else:
                        skipped_count += 1
                        error = result.get("error", "Unknown error")
                        resp += f"  `{pkg}`: {error}\n"
                        skipped_details.append({
                            "rule_id": rule_id, "file": pkg,
                            "reason": f"Dependency fix failed: {error}",
                            "scanner": _get_scanner(finding), "fixed_in": fixed_in
                        })

                if len(by_package) > 15:
                    remaining = len(by_package) - 15
                    skipped_count += remaining
                    resp += f"  ... and {remaining} more packages (run again to continue)\n"

                if dep_fixed > 0:
                    resp += f"  Next: Run `npm install` / `pip install -r requirements.txt` / `go mod tidy` to update lockfiles\n"

            except Exception as e:
                resp += f"  Dependency fixer error: {e}\n"
                skipped_count += len(dependency_findings)
                for f in dependency_findings:
                    skipped_details.append({
                        "rule_id": f.get("rule_id", ""), "file": f.get("package", f.get("file", "unknown")),
                        "reason": f"Dependency fixer failed: {e}", "scanner": _get_scanner(f)
                    })

        if other_findings:
            skipped_count += len(other_findings)
            resp += f"\n**Other findings:** {len(other_findings)} (skipped - no auto-fix)\n"
            for f in other_findings:
                scanner = _get_scanner(f)
                skipped_details.append({
                    "rule_id": f.get("rule_id", "unknown"), "file": f.get("file", "unknown"),
                    "reason": f"No fixer NPC available for scanner '{scanner}'.",
                    "scanner": scanner
                })

        # Store fix results for follow-up
        self.jade.context["last_fix_results"] = {
            "fixed_count": fixed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "skipped_details": skipped_details,
            "target": target
        }

        resp += f"\n**Summary:**\n"
        resp += f"  - Fixed: {fixed_count}\n"
        resp += f"  - Skipped: {skipped_count}\n"
        resp += f"  - Failed: {failed_count}\n"

        if fixed_count > 0:
            resp += f"\n**Next:** Run `jade scan {target}` to verify fixes."
        if skipped_count > 0:
            resp += f"\n**Ask:** 'why were they skipped?' for details."

        return resp

    def _handle_training(self) -> str:
        """Training status."""
        if not self.jade.logs:
            return "Log reader not available."

        result = self.jade.logs.get_training_status()

        if result.get("status") == "no_logs":
            return "No training logs found. Training might not be running."

        loss = result.get("latest_loss")
        epoch = result.get("current_epoch")
        step = result.get("current_step")
        recent = result.get("recent_output", [])[-5:]

        resp = "**Training Status**\n"
        if loss:
            resp += f"Loss: {loss:.4f}\n"
        if epoch:
            resp += f"Epoch: {epoch}\n"
        if step:
            resp += f"Step: {step}\n"

        if recent:
            resp += "\n**Recent output:**\n```\n"
            resp += "\n".join(recent[-3:])
            resp += "\n```"

        return resp

    def _handle_logs(self, message: str) -> str:
        """Handle log queries."""
        if not self.jade.logs:
            return "Log reader not available."

        msg = message.lower()
        if "training" in msg:
            return self._handle_training()

        result = self.jade.logs.list_logs()

        resp = "**Available logs:**\n"
        for category, data in result.items():
            if isinstance(data, dict) and "files" in data:
                count = data.get("count", 0)
                resp += f"\n**{category}**: {count} file(s)"
                for f in data.get("files", [])[:3]:
                    resp += f"\n  - {f['name']} ({f['size_human']})"

        resp += "\n\nSay 'show training logs' or 'tail <filename>' for details."
        return resp

    def _handle_scan(self, intent: Dict) -> str:
        """Handle scan requests."""
        target = intent.get("target")

        if not target:
            if self.jade.orchestrator:
                projects = self.jade.orchestrator.list_projects()
                names = [p.get("name", pid) for pid, p in projects.get("projects", {}).items()]
                return f"Which project? Available: {', '.join(names)}\n\nSay 'scan DVWA' or 'scan portfolio'"
            return "Which project do you want to scan?"

        target_path = Path(target)
        if not target_path.exists():
            return f"**Error:** Target path not found: `{target}`"

        return self._execute_scan(str(target_path))

    def _execute_scan(self, target: str) -> str:
        """Actually run security scans on target."""
        target_path = Path(target).resolve()

        try:
            scan_path = Path(__file__).parent.parent.parent / "GP-CONSULTING" / "1-Security-Assessment"
            if str(scan_path) not in sys.path:
                sys.path.insert(0, str(scan_path))
            from orchestrator.scan_orchestrator import ScanOrchestrator

            output_dir = target_path / ".jsa" / "scans"
            output_dir.mkdir(parents=True, exist_ok=True)

            print(f"Scanning {target_path.name}...")
            print(f"   Profile: Standard (secrets, SAST, dependencies)")
            print(f"   Scanners: gitleaks, bandit, semgrep, trivy, grype")

            orchestrator = ScanOrchestrator(
                target=str(target_path),
                output_dir=str(output_dir),
                parallel=True,
                verbose=True
            )

            result = orchestrator.standard_scan()

            resp = f"**Scan Complete: {target_path.name}**\n\n"
            resp += f"**Duration:** {result.duration_seconds:.1f}s\n"
            resp += f"**Total findings:** {result.total_findings}\n\n"

            if result.findings_by_severity:
                resp += "**By severity:**\n"
                for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                    count = result.findings_by_severity.get(sev, 0)
                    if count > 0:
                        resp += f"  - {sev}: {count}\n"

            if result.findings_by_category:
                resp += "\n**By category:**\n"
                for cat, count in result.findings_by_category.items():
                    resp += f"  - {cat}: {count}\n"

            if result.scanners_run:
                resp += f"\n**Scanners run:** {', '.join(result.scanners_run)}\n"

            # Save results as cycle file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cycle_file = output_dir / f"scan_{timestamp}.json"

            cycle_data = {
                "timestamp": datetime.now().isoformat(),
                "target": str(target_path),
                "duration_seconds": result.duration_seconds,
                "findings": result.findings,
                "total_findings": result.total_findings,
                "findings_by_severity": result.findings_by_severity,
                "findings_by_category": result.findings_by_category,
                "scanners_run": result.scanners_run,
            }

            with open(cycle_file, 'w') as f:
                json.dump(cycle_data, f, indent=2)

            self.jade.context["last_cycle"] = {
                "file": str(cycle_file),
                "instance": "jade-scan",
                "data": cycle_data
            }
            self.jade.chat_handler.save_context()

            resp += f"\n**Results saved to:**\n`{cycle_file}`\n"
            resp += f"\n**Next steps:**\n"
            resp += f"- 'show me the HIGH severity findings'\n"
            resp += f"- 'how to fix these'\n"
            resp += f"- 'please fix these'\n"

            if result.errors:
                resp += f"\n**Errors:** {len(result.errors)} scanners had issues\n"
                for err in result.errors[:3]:
                    resp += f"  - {err}\n"

            return resp

        except ImportError as e:
            return f"**Error:** ScanOrchestrator not available: {e}\n\nTry running manually:\n```bash\ncd GP-CONSULTING/1-Security-Assessment\npython3 -m orchestrator.scan_orchestrator {target}\n```"
        except Exception as e:
            import traceback
            return f"**Error during scan:** {e}\n\n```\n{traceback.format_exc()}\n```"

    def _handle_git_check(self, intent: Dict) -> str:
        """Check for git changes in a project."""
        if not self.jade.git_guardian:
            return "Git tools not available. Check git_guardian.py installation."

        target = intent.get("target")
        repo_path = self._find_repo_path(target)
        if not repo_path:
            return f"Couldn't find repository for '{target}'. Try specifying the full path."

        try:
            report = self.jade.git_guardian.get_protection_report(repo_path)
            return report
        except Exception as e:
            return f"Error checking repository: {e}"

    def _handle_git_reject(self, intent: Dict) -> str:
        """Reject bad changes and push correct code back."""
        if not self.jade.git_guardian:
            return "Git tools not available. Check git_guardian.py installation."

        target = intent.get("target")
        repo_path = self._find_repo_path(target)
        if not repo_path:
            return f"Couldn't find repository for '{target}'. Try specifying the full path."

        try:
            result = self.jade.git_guardian.reject_and_restore(repo_path, dry_run=True)
            return result['message'] + "\n\nTo actually reject, say: 'force reject changes'"
        except Exception as e:
            return f"Error: {e}"

    def _handle_git_diff(self, intent: Dict) -> str:
        """Show diff of remote changes."""
        if not self.jade.git_monitor:
            return "Git tools not available. Check git_monitor.py installation."

        target = intent.get("target")
        repo_path = self._find_repo_path(target)
        if not repo_path:
            return f"Couldn't find repository for '{target}'. Try specifying the full path."

        try:
            diff = self.jade.git_monitor.get_diff(repo_path)
            if not diff:
                return "No differences found with remote."
            if len(diff) > 2000:
                diff = diff[:2000] + "\n\n... (truncated)"
            return f"**Changes from remote:**\n```diff\n{diff}\n```"
        except Exception as e:
            return f"Error getting diff: {e}"

    def _find_repo_path(self, target: str) -> str:
        """Find a repository path from target name."""
        gp_projects = Path(__file__).parent.parent.parent / "GP-PROJECTS"

        if not target:
            default = gp_projects / "01-instance" / "ai-powered-project"
            if default.exists():
                return str(default)
            return None

        target_lower = target.lower().replace("-", "").replace("_", "")
        for instance in gp_projects.iterdir():
            if instance.is_dir():
                for project in instance.iterdir():
                    if project.is_dir():
                        proj_lower = project.name.lower().replace("-", "").replace("_", "")
                        if target_lower in proj_lower or proj_lower in target_lower:
                            return str(project)

        if Path(target).exists():
            return target
        return None

    def _handle_scanners(self, message: str) -> str:
        """Handle queries about scanners/NPCs using RAG."""
        return self.jade.chat_handler.answer_with_rag(message, collection="jade-platform")

    def _handle_platform(self, message: str) -> str:
        """Handle platform info queries using RAG."""
        return self.jade.chat_handler.answer_with_rag(message, collection="jade-platform")

    def _handle_cluster_real(self, message: str) -> str:
        """Handle cluster queries with REAL kubectl execution."""
        msg = message.lower()

        if "pod" in msg:
            cmd = ["kubectl", "get", "pods", "-A", "--no-headers"]
            label = "Pods"
        elif "node" in msg:
            cmd = ["kubectl", "get", "nodes", "--no-headers"]
            label = "Nodes"
        elif "deploy" in msg:
            cmd = ["kubectl", "get", "deployments", "-A", "--no-headers"]
            label = "Deployments"
        elif "service" in msg or "svc" in msg:
            cmd = ["kubectl", "get", "services", "-A", "--no-headers"]
            label = "Services"
        elif "namespace" in msg or "ns" in msg:
            cmd = ["kubectl", "get", "namespaces", "--no-headers"]
            label = "Namespaces"
        else:
            cmd = ["kubectl", "get", "pods", "-A", "--no-headers"]
            label = "Pods"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                error = result.stderr.strip() or "kubectl command failed"
                return f"Kubectl error: {error}\n\nIs the cluster running? Try: minikube start"

            output = result.stdout.strip()
            if not output:
                return f"No {label.lower()} found in the cluster."

            lines = output.split('\n')
            count = len(lines)

            resp = f"**{label} in cluster: {count}**\n\n"

            for line in lines[:10]:
                parts = line.split()
                if label == "Pods" and len(parts) >= 4:
                    ns, name, ready, status = parts[0], parts[1], parts[2], parts[3]
                    resp += f"  {ns}/{name} - {status} ({ready})\n"
                elif label == "Nodes" and len(parts) >= 2:
                    name, status = parts[0], parts[1]
                    resp += f"  {name} - {status}\n"
                else:
                    resp += f"  {line}\n"

            if count > 10:
                resp += f"\n  ...and {count - 10} more"

            return resp

        except subprocess.TimeoutExpired:
            return "Kubectl timed out. Is the cluster responsive?"
        except FileNotFoundError:
            return "kubectl not found. Install it or check your PATH."
        except Exception as e:
            return f"Error running kubectl: {e}"
