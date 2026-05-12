#!/usr/bin/env python3
"""
JADE - C-Rank DevSecOps Supervisor
GP-Copilot's orchestrator for the Iron Legion

Receives escalations from JSA agents (jsa-devsec, jsa-infrasec),
provides fix solutions, and routes work back to agents.
Commands fleet operations via Commander interface.
"""

import sys
import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "core"))
sys.path.insert(0, str(Path(__file__).parent / "capabilities"))
sys.path.insert(0, str(Path(__file__).parent.parent / "GP-INFRA" / "platform" / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent / "GP-INFRA" / "platform" / "tasks"))
sys.path.insert(0, str(Path(__file__).parent.parent / "GP-INFRA" / "core"))

from llm_provider import create_provider
from chat_handler import ChatHandler
from intent_router import IntentRouter

# Agentic Engine
try:
    from agentic_engine import (
        AgenticEngine,
        Tool,
        create_scan_tool,
        create_fix_tool,
        create_query_rag_tool,
        create_run_command_tool,
        create_read_file_tool,
        create_list_files_tool,
        create_grep_tool,
        create_kubectl_tool,
        create_list_tasks_tool,
        create_process_task_file_tool,
        create_answer_task_tool,
    )
    AGENTIC_AVAILABLE = True
except ImportError:
    AGENTIC_AVAILABLE = False

# Task Processor
try:
    from task_processor import TaskProcessor, get_task_processor
    TASK_PROCESSOR_AVAILABLE = True
except ImportError:
    TASK_PROCESSOR_AVAILABLE = False

# RAG Integration
try:
    from raggraph_engine import get_raggraph_engine
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Chat logging - readable JSON format in GP-CLOUDWATCH
GP_ROOT = Path(__file__).parent.parent
CHAT_LOGS_DIR = GP_ROOT / "GP-CLOUDWATCH" / "jade-chat"

# Try importing tools - gracefully handle missing
try:
    from jsa_deployer import JSADeployer
    JSA_AVAILABLE = True
except ImportError:
    JSA_AVAILABLE = False

try:
    from log_reader import LogReader
    LOGS_AVAILABLE = True
except ImportError:
    LOGS_AVAILABLE = False

try:
    from cluster_manager import ClusterManager
    CLUSTER_AVAILABLE = True
except ImportError:
    CLUSTER_AVAILABLE = False

try:
    from orchestrator import GPCopilotOrchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

try:
    from git_guardian import GitGuardianNPC
    from git_monitor import GitMonitorNPC
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

# Commander - JADE's interface for commanding JSA agents
try:
    from commander.commander import JADECommander
    from commander.models import CommandType, AgentType, CommandStatus
    COMMANDER_AVAILABLE = True
except ImportError:
    COMMANDER_AVAILABLE = False

# Fixer NPCs for actual code fixes
# Both GP-CONSULTING paths have 'npcs' packages, so we need to import carefully
_scan_path = Path(__file__).parent.parent / "GP-CONSULTING" / "1-Security-Assessment"
_fix_path = Path(__file__).parent.parent / "GP-CONSULTING" / "2-App-Sec-Fixes"

# Import fixers FIRST with fixer path at position 0
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    try:
        # Clear any cached npcs module first
        if 'npcs' in sys.modules:
            del sys.modules['npcs']

        # Add fixer path at position 0 to import fixers
        sys.path.insert(0, str(_fix_path))
        from npcs.sast.code_fixer_npc import CodeFixerNPC
        from npcs.secrets.secrets_fixer_npc import SecretsFixerNPC
        from npcs.dependencies.dependency_fixer_npc import DependencyFixerNPC
        FIXERS_AVAILABLE = True

        # Clear npcs modules and reset path for scanners
        for m in list(sys.modules.keys()):
            if m == 'npcs' or m.startswith('npcs.'):
                del sys.modules[m]

        # Remove fixer path and add scanner path at position 0
        sys.path.remove(str(_fix_path))
        sys.path.insert(0, str(_scan_path))
        # Add fixer path back at the end (for any later fixer usage)
        sys.path.append(str(_fix_path))

    except Exception as e:
        FIXERS_AVAILABLE = False
        # Ensure scanner path is still set up for scans
        if str(_scan_path) not in sys.path:
            sys.path.insert(0, str(_scan_path))


class JADE:
    """
    C-Rank DevSecOps Supervisor — GP-Copilot's Iron Legion orchestrator.

    Responsibilities:
    - Receives escalations from JSA agents (jsa-devsec, jsa-infrasec)
    - Provides fix solutions for findings JSA can't resolve (C-rank)
    - Escalates B-S rank findings to human (Jimmie)
    - Commands JSA fleet via Commander interface
    - Answers DevSecOps knowledge queries via RAG
    """

    def __init__(self, quiet: bool = False):
        import os
        if not quiet:
            print("Starting JADE...", flush=True)

        # LLM Provider - Plug & Play via env vars or jade_config.yaml
        # Env vars override config: JADE_PROVIDER, JADE_MODEL
        # Config default: jade_config.yaml llm.provider (anthropic)
        provider_name = os.environ.get("JADE_PROVIDER") or None  # None = read from config
        model_name = os.environ.get("JADE_MODEL") or None        # None = read from config

        self.llm = create_provider(
            provider_name=provider_name,
            model_name=model_name
        )
        provider_info = self.llm.get_model_info()
        actual_provider = provider_info.get("provider", "unknown")
        actual_model = provider_info.get("model", "unknown")
        if not quiet:
            print(f"  Provider: {actual_provider} ({actual_model})")

        if not self.llm.is_available():
            if actual_provider == "ollama":
                print("\nOllama not running or model not found.")
                print("Quick setup:")
                print("  1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
                print("  2. Start Ollama: ollama serve")
                print(f"  3. Pull model: ollama pull {actual_model}")
                print("\nThen run: jade .")
            else:
                print(f"\n{actual_provider} provider not available.")
                print(f"Check your API key: {actual_provider.upper()}_API_KEY")
            sys.exit(1)

        # RAG Engine (29,000+ security knowledge vectors)
        self.rag = None
        if RAG_AVAILABLE:
            try:
                # Let RAG engine print its own status (quiet=False when JADE is not quiet)
                self.rag = get_raggraph_engine(quiet=quiet)
            except Exception as e:
                if not quiet:
                    print(f"⚠️  RAG unavailable: {e}")

        # Tools
        self.orchestrator = GPCopilotOrchestrator() if ORCHESTRATOR_AVAILABLE else None
        self.jsa = JSADeployer() if JSA_AVAILABLE else None
        self.logs = LogReader() if LOGS_AVAILABLE else None
        self.cluster = ClusterManager() if CLUSTER_AVAILABLE else None
        self.git_guardian = GitGuardianNPC() if GIT_AVAILABLE else None
        self.git_monitor = GitMonitorNPC() if GIT_AVAILABLE else None
        self.task_processor = get_task_processor() if TASK_PROCESSOR_AVAILABLE else None

        # Commander - JADE's interface for commanding JSA fleet
        self.commander = JADECommander() if COMMANDER_AVAILABLE else None
        if self.commander and not quiet:
            print(f"  Commander: JSA fleet management ready")

        # Fixer classes for intent router
        self.fixer_classes = None
        if FIXERS_AVAILABLE:
            self.fixer_classes = {
                'code': CodeFixerNPC,
                'secrets': SecretsFixerNPC,
                'dependency': DependencyFixerNPC,
            }

        # Conversation persistence
        self.context_file = Path.home() / ".jade_context.json"
        self.max_history = 50  # Keep last 50 exchanges

        # Core modules (extracted from monolith)
        self.chat_handler = ChatHandler(self)
        self.intent_router = IntentRouter(self)

        # Load context via chat handler
        self.history, self.context = self.chat_handler.load_context()

        # Chat logging - readable JSON format
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        CHAT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.log_file = CHAT_LOGS_DIR / f"jade_session_{self.session_id}.json"
        self.chat_handler.init_log_file()

        # Agentic mode - the core upgrade that makes JADE like Claude Code
        self.agentic_mode = AGENTIC_AVAILABLE
        self.agentic_engine = None
        if self.agentic_mode:
            self._init_agentic_engine()
            if not quiet:
                tool_count = len(self.agentic_engine.tools) if self.agentic_engine else 0
                print(f"✅ Agentic engine: {tool_count} tools registered")

        if not quiet:
            ctx_count = len(self.history) // 2 if self.history else 0
            if ctx_count > 0:
                print(f"📝 Loaded {ctx_count} prior exchanges from context")
            print(f"\n🤖 JADE [C-rank] ready. Type 'help' for commands.\n")

    @staticmethod
    def _get_scanner(finding: dict) -> str:
        """
        Get scanner name from finding, checking both 'scanner' and 'source_scanner' fields.

        Some findings (especially CVE/GHSA from trivy) use 'source_scanner' instead of 'scanner'.
        """
        if not isinstance(finding, dict):
            return "unknown"
        # Check scanner first, then source_scanner as fallback
        scanner = finding.get("scanner", "") or finding.get("source_scanner", "") or "unknown"
        return scanner.lower() if isinstance(scanner, str) else "unknown"

    # =========================================================================
    # AGENTIC ENGINE - This is what makes JADE act like Claude Code
    # =========================================================================

    def _init_agentic_engine(self):
        """Initialize the agentic engine with all available tools."""
        self.agentic_engine = AgenticEngine(
            llm=self.llm,
            context=self.context,
            max_iterations=10
        )

        # Register tools with their implementations
        self.agentic_engine.register_tool(create_scan_tool(self._tool_scan))
        self.agentic_engine.register_tool(create_fix_tool(self._tool_fix))
        self.agentic_engine.register_tool(create_read_file_tool(self._tool_read_file))
        self.agentic_engine.register_tool(create_list_files_tool(self._tool_list_files))
        self.agentic_engine.register_tool(create_grep_tool(self._tool_grep))
        self.agentic_engine.register_tool(create_run_command_tool(self._tool_run_command))
        self.agentic_engine.register_tool(create_kubectl_tool(self._tool_kubectl))

        if self.rag:
            self.agentic_engine.register_tool(create_query_rag_tool(self._tool_query_rag))

        # Task processing tools - core JSA orchestration
        if self.task_processor:
            self.agentic_engine.register_tool(create_list_tasks_tool(self._tool_list_tasks))
            self.agentic_engine.register_tool(create_process_task_file_tool(self._tool_process_task_file))
            self.agentic_engine.register_tool(create_answer_task_tool(self._tool_answer_task))

        # Commander tools - JSA fleet management
        if self.commander:
            self.agentic_engine.register_tool(Tool(
                name="agent_status",
                description="Get status of a JSA agent deployed to a slot (findings, fixes, escalations)",
                parameters={
                    "instance": {"type": "string", "description": "Instance ID (e.g., '01-instance', '02-instance')"},
                    "slot": {"type": "string", "description": "Slot ID (e.g., 'slot-1', 'slot-2')"},
                },
                execute=self._tool_agent_status
            ))
            self.agentic_engine.register_tool(Tool(
                name="escalate",
                description="Escalate a security finding that exceeds C-rank to human review",
                parameters={
                    "instance": {"type": "string", "description": "Instance ID"},
                    "slot": {"type": "string", "description": "Slot ID"},
                    "finding": {"type": "string", "description": "Description of the finding to escalate"},
                    "rank": {"type": "string", "description": "Finding rank (B, A, or S)"},
                },
                execute=self._tool_escalate
            ))
            self.agentic_engine.register_tool(Tool(
                name="list_agents",
                description="List all deployed JSA agents across all instances",
                parameters={
                    "instance": {"type": "string", "description": "Optional: filter by instance ID"},
                },
                execute=self._tool_list_agents
            ))

        # Add new tool for project summarization
        self.agentic_engine.register_tool(Tool(
            name="summarize_project",
            description="Summarize a project by inspecting its files and using RAG to understand its purpose, deployment, and technologies.",
            parameters={
                "project_path": {"type": "string", "description": "The absolute path to the project directory to summarize."}
            },
            execute=self._tool_summarize_project
        ))

    # =========================================================================
    # TASK PROCESSING TOOLS - JSA Orchestration
    # =========================================================================

    def _tool_list_tasks(self) -> Dict[str, Any]:
        """Tool implementation: List available task files."""
        if not self.task_processor:
            return {"success": False, "error": "Task processor not available"}

        task_files = self.task_processor.list_task_files()
        return {
            "success": True,
            "task_files": [f.name for f in task_files],
            "count": len(task_files),
            "path": str(self.task_processor.tasks_dir)
        }

    def _tool_process_task_file(self, file: str) -> Dict[str, Any]:
        """Tool implementation: Parse and route a task file."""
        if not self.task_processor:
            return {"success": False, "error": "Task processor not available"}

        # Find the file
        task_path = self.task_processor.tasks_dir / file
        if not task_path.exists():
            return {"success": False, "error": f"Task file not found: {file}"}

        # Parse the task file
        parsed = self.task_processor.parse_task_file(task_path)
        routing = self.task_processor.get_routing_summary(parsed)

        # Build task summaries
        tasks_summary = []
        for task in parsed.tasks:
            emoji = "🤖" if task.is_jsa_task() else "💎" if task.is_jade_task() else "👤"
            tasks_summary.append({
                "id": task.id,
                "title": task.title,
                "rank": task.rank.value,
                "type": task.task_type.value,
                "routing": task.get_routing(),
                "emoji": emoji,
                "deliverables_count": len(task.deliverables),
                "estimated_minutes": self.task_processor.estimate_time(task)
            })

        return {
            "success": True,
            "file": file,
            "total_tasks": parsed.task_count,
            "routing": routing,
            "tasks": tasks_summary,
            "message": f"Parsed {parsed.task_count} tasks: {routing['jsa_tasks']['count']} for JSA, {routing['jade_tasks']['count']} for JADE, {routing['human_tasks']['count']} require human"
        }

    def _tool_answer_task(self, task_id: str, file: str) -> Dict[str, Any]:
        """Tool implementation: Answer a specific task using RAG knowledge."""
        if not self.task_processor:
            return {"success": False, "error": "Task processor not available"}

        # Find and parse the file
        task_path = self.task_processor.tasks_dir / file
        if not task_path.exists():
            return {"success": False, "error": f"Task file not found: {file}"}

        parsed = self.task_processor.parse_task_file(task_path)

        # Find the specific task
        task = None
        for t in parsed.tasks:
            if t.id == task_id:
                task = t
                break

        if not task:
            return {"success": False, "error": f"Task not found: {task_id}"}

        # Check if this is something JADE can handle
        if task.is_human_task():
            return {
                "success": False,
                "escalate": True,
                "reason": f"Task {task_id} is {task.rank.value}-rank - requires human decision",
                "task_summary": f"{task.title}: {task.description[:200]}..."
            }

        # Format task for RAG query
        rag_query = self.task_processor.format_task_for_rag(task)

        # Query RAG if available
        rag_context = ""
        if self.rag:
            try:
                results = self.rag.query(rag_query, n_results=5)
                if results:
                    rag_context = "\n\nRelevant knowledge:\n"
                    for r in results[:3]:
                        rag_context += f"- {r.get('content', r.get('text', ''))[:500]}\n"
            except Exception as e:
                rag_context = f"\n(RAG query failed: {e})"

        return {
            "success": True,
            "task_id": task_id,
            "rank": task.rank.value,
            "routing": task.get_routing(),
            "task_prompt": rag_query,
            "rag_context": rag_context,
            "deliverables": task.deliverables,
            "message": f"Task {task_id} ({task.rank.value}-rank) ready for answering. Use RAG context and your knowledge."
        }

    # =========================================================================
    # COMMANDER TOOLS - JSA Fleet Management
    # =========================================================================

    def _tool_agent_status(self, instance: str, slot: str) -> Dict[str, Any]:
        """Tool implementation: Get JSA agent status via Commander."""
        if not self.commander:
            return {"success": False, "error": "Commander not available"}

        try:
            # Try each agent type to find what's deployed
            results = {}
            for agent_type in AgentType:
                result = self.commander.command(
                    agent=agent_type,
                    action=CommandType.STATUS,
                    instance=instance,
                    slot=slot
                )
                if result.status == CommandStatus.SUCCESS:
                    results[agent_type.value] = result.data

            if not results:
                return {
                    "success": True,
                    "message": f"No agents found in {instance}/{slot}",
                    "agents": {}
                }

            return {
                "success": True,
                "instance": instance,
                "slot": slot,
                "agents": results,
                "agent_count": len(results)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_escalate(self, instance: str, slot: str, finding: str, rank: str = "B") -> Dict[str, Any]:
        """Tool implementation: Escalate a finding beyond C-rank to human review."""
        if not self.commander:
            return {"success": False, "error": "Commander not available"}

        try:
            result = self.commander.command(
                agent=AgentType.JSA_DEVSECOPS,
                action=CommandType.ESCALATE,
                instance=instance,
                slot=slot,
                params={
                    "finding": finding,
                    "rank": rank,
                    "escalated_by": "jade",
                    "reason": f"Finding exceeds C-rank authority (rank: {rank})"
                }
            )

            return {
                "success": result.status == CommandStatus.SUCCESS,
                "message": result.message,
                "escalation_id": result.request_id,
                "rank": rank,
                "error": result.error
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_list_agents(self, instance: str = None) -> Dict[str, Any]:
        """Tool implementation: List all deployed JSA agents."""
        if not self.commander:
            return {"success": False, "error": "Commander not available"}

        try:
            agents = self.commander.list_agents(instance=instance)
            agent_list = [a.to_dict() for a in agents]

            return {
                "success": True,
                "agents": agent_list,
                "count": len(agent_list),
                "message": f"Found {len(agent_list)} deployed agent(s)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # DIRECT TOOLS - Scan/Fix (path-based, runs scanners directly)
    # =========================================================================

    def _tool_scan(self, target: str) -> Dict[str, Any]:
        """Tool implementation: Run security scans."""
        target_path = Path(target).resolve()
        if not target_path.exists():
            return {"success": False, "error": f"Target not found: {target}"}

        try:
            # Import ScanOrchestrator
            scan_path = Path(__file__).parent.parent / "GP-CONSULTING" / "1-Security-Assessment"
            if str(scan_path) not in sys.path:
                sys.path.insert(0, str(scan_path))
            from orchestrator.scan_orchestrator import ScanOrchestrator

            # Create output directory
            output_dir = target_path / ".jsa" / "scans"
            output_dir.mkdir(parents=True, exist_ok=True)

            print(f"  [scan] Scanning {target_path.name}...")

            orchestrator = ScanOrchestrator(
                target=str(target_path),
                output_dir=str(output_dir),
                parallel=True,
                verbose=False
            )
            result = orchestrator.standard_scan()

            # Save results
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

            # Update context
            self.context["last_cycle"] = {
                "file": str(cycle_file),
                "instance": "jade-scan",
                "data": cycle_data
            }
            self.chat_handler.save_context()

            print(f"  [scan] Found {result.total_findings} findings")

            return {
                "success": True,
                "total_findings": result.total_findings,
                "findings_by_severity": result.findings_by_severity,
                "findings_by_category": result.findings_by_category,
                "scanners_run": result.scanners_run,
                "duration_seconds": result.duration_seconds,
                "output_file": str(cycle_file),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_fix(self, severity_filter: str = None, scanner_filter: str = None) -> Dict[str, Any]:
        """Tool implementation: Apply fixes to findings."""
        if not FIXERS_AVAILABLE:
            return {"success": False, "error": "Fixer NPCs not available"}

        if not self.context.get("last_cycle"):
            return {"success": False, "error": "No scan results to fix. Run scan first."}

        cycle_data = self.context["last_cycle"]
        data = cycle_data.get("data", {})
        findings = data.get("findings", [])
        target = data.get("target", "")

        if not findings:
            return {"success": True, "message": "No findings to fix", "fixed_count": 0}

        # Apply filters
        filtered = []
        for f in findings:
            if not isinstance(f, dict):
                continue
            severity = (f.get("severity", "") or "").lower()
            scanner = self._get_scanner(f)

            if severity_filter and severity != severity_filter.lower():
                continue
            if scanner_filter and scanner != scanner_filter.lower():
                continue
            filtered.append(f)

        if not filtered:
            return {"success": True, "message": "No findings match filters", "fixed_count": 0}

        print(f"  [fix] Fixing {len(filtered)} findings...")

        # Group findings by type
        sast_findings = []
        secrets_findings = []
        dependency_findings = []

        for f in filtered:
            scanner = self._get_scanner(f)
            rule_id = f.get("rule_id", "")

            if scanner in ["bandit", "semgrep"] or rule_id.startswith("B"):
                sast_findings.append(f)
            elif "gitleaks" in scanner or "secret" in scanner:
                secrets_findings.append(f)
            elif scanner in ["trivy", "grype"] or rule_id.startswith("CVE-") or rule_id.startswith("GHSA-"):
                dependency_findings.append(f)

        fixed_count = 0
        skipped_count = 0
        results = []

        # Fix SAST
        if sast_findings:
            try:
                fixer = CodeFixerNPC(dry_run=False)
                for finding in sast_findings[:10]:
                    rule_id = finding.get("rule_id", "")
                    if rule_id in fixer.FIX_PATTERNS:
                        result = fixer.apply_fix(finding, target)
                        if result.get("success"):
                            fixed_count += 1
                            results.append(f"Fixed {rule_id}")
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
            except Exception as e:
                results.append(f"SAST error: {e}")

        # Fix secrets
        if secrets_findings:
            try:
                fixer = SecretsFixerNPC(dry_run=False)
                result = fixer.run(target, findings=secrets_findings)
                if result.get("success"):
                    fixed = result.get("fixed_count", 0)
                    fixed_count += fixed
                    results.append(f"Fixed {fixed} secrets")
            except Exception as e:
                results.append(f"Secrets error: {e}")

        # Fix dependencies
        if dependency_findings:
            try:
                fixer = DependencyFixerNPC(dry_run=False)
                by_package = {}
                for f in dependency_findings:
                    pkg = f.get("package", f.get("pkg_name", "unknown"))
                    if pkg not in by_package:
                        by_package[pkg] = f

                for pkg, finding in list(by_package.items())[:15]:
                    normalized = {
                        "package": pkg,
                        "pkg_name": pkg,
                        "version": finding.get("version", ""),
                        "fixed_version": finding.get("fixed_in", finding.get("fixed_version", "")),
                        "pkg_type": finding.get("pkg_type", ""),
                    }
                    result = fixer.apply_fix(normalized, target)
                    if result.get("success"):
                        fixed_count += 1
                        results.append(f"Updated {pkg}")
                    else:
                        skipped_count += 1
            except Exception as e:
                results.append(f"Dependency error: {e}")

        # Update context
        self.context["last_fix_results"] = {
            "fixed_count": fixed_count,
            "skipped_count": skipped_count,
            "target": target
        }
        self.chat_handler.save_context()

        print(f"  [fix] Fixed {fixed_count}, skipped {skipped_count}")

        return {
            "success": True,
            "fixed_count": fixed_count,
            "skipped_count": skipped_count,
            "details": results,
        }

    def _tool_read_file(self, path: str, lines: int = 100) -> Dict[str, Any]:
        """Tool implementation: Read file contents."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()[:lines]

            return {
                "success": True,
                "path": str(file_path),
                "lines": len(content),
                "content": "".join(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_list_files(self, path: str, pattern: str = "*") -> Dict[str, Any]:
        """Tool implementation: List files in directory."""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return {"success": False, "error": f"Directory not found: {path}"}

            if dir_path.is_file():
                return {"success": True, "files": [str(dir_path)], "count": 1}

            files = list(dir_path.glob(pattern))[:100]  # Limit to 100
            return {
                "success": True,
                "path": str(dir_path),
                "pattern": pattern,
                "count": len(files),
                "files": [str(f.relative_to(dir_path)) for f in files[:50]]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_grep(self, pattern: str, path: str, file_type: str = None) -> Dict[str, Any]:
        """Tool implementation: Search for patterns in files."""
        import subprocess

        try:
            cmd = ["grep", "-r", "-n", "-I", pattern, path]
            if file_type:
                cmd.extend(["--include", f"*.{file_type}"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            matches = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return {
                "success": True,
                "pattern": pattern,
                "match_count": len(matches),
                "matches": matches[:30]  # Limit output
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Search timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Tool implementation: Run shell command (allowlisted DevSecOps tools only)."""
        import subprocess
        import shlex

        # Allowlist: only DevSecOps tools JADE should invoke
        ALLOWED_COMMANDS = [
            "kubectl", "helm", "git", "docker",
            "trivy", "bandit", "semgrep", "checkov", "conftest", "grype",
            "gitleaks", "hadolint", "kubescape", "polaris",
            "python", "python3", "pip", "pip3",
            "ls", "cat", "head", "tail", "grep", "find", "wc",
        ]

        # Parse command and validate first token against allowlist
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return {"success": False, "error": f"Invalid command syntax: {e}"}

        if not parts:
            return {"success": False, "error": "Empty command"}

        # Extract base command name (strip path)
        base_cmd = Path(parts[0]).name
        if base_cmd not in ALLOWED_COMMANDS:
            return {
                "success": False,
                "error": f"Command '{base_cmd}' not in allowlist. "
                         f"Allowed: {', '.join(ALLOWED_COMMANDS)}"
            }

        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout[:3000] if result.stdout else "",
                "stderr": result.stderr[:1000] if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except FileNotFoundError:
            return {"success": False, "error": "Command '{base_cmd}' not found on system"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_kubectl(self, command: str) -> Dict[str, Any]:
        """Tool implementation: Run kubectl commands."""
        import subprocess

        # Ensure it starts with kubectl subcommand (not full path)
        if command.startswith("kubectl "):
            command = command[8:]  # Remove "kubectl " prefix

        try:
            cmd = ["kubectl"] + command.split()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            return {
                "success": result.returncode == 0,
                "command": f"kubectl {command}",
                "output": result.stdout[:3000] if result.stdout else "",
                "error": result.stderr[:500] if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "kubectl timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "kubectl not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_query_rag(self, question: str) -> Dict[str, Any]:
        """Tool implementation: Query the RAG knowledge base."""
        if not self.rag:
            return {"success": False, "error": "RAG not available"}

        try:
            results = self.rag.query(question, top_k=5)
            if not results:
                return {"success": True, "results": [], "message": "No relevant documents found"}

            formatted = []
            for r in results:
                formatted.append({
                    "content": r.content[:500],
                    "source": r.metadata.get('file', r.collection) if hasattr(r, 'metadata') else r.collection,
                    "score": getattr(r, 'score', None)
                })

            return {
                "success": True,
                "question": question,
                "result_count": len(results),
                "results": formatted
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_summarize_project(self, project_path: str) -> Dict[str, Any]:
        """Tool implementation: Summarize a project by inspecting files and using RAG."""
        try:
            from pathlib import Path
            import os

            project_dir = Path(project_path)
            if not project_dir.exists() or not project_dir.is_dir():
                return {"success": False, "error": f"Directory not found: {project_path}"}

            # Gather project info
            info = {
                "path": str(project_dir),
                "name": project_dir.name,
                "files": [],
                "structure": {}
            }

            # List key files
            key_files = ["README.md", "package.json", "requirements.txt", "Dockerfile",
                        "docker-compose.yml", "Chart.yaml", "values.yaml", "Makefile"]

            for f in key_files:
                file_path = project_dir / f
                if file_path.exists():
                    info["files"].append(f)

            # Count file types
            extensions = {}
            for root, dirs, files in os.walk(project_dir):
                # Skip common directories
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]
                for file in files:
                    ext = Path(file).suffix or 'no-extension'
                    extensions[ext] = extensions.get(ext, 0) + 1

            info["structure"] = dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10])

            # Query RAG for context if available
            rag_context = ""
            if self.rag:
                rag_query = f"project {project_dir.name} structure deployment"
                results = self.rag.query(rag_query, top_k=3)
                if results:
                    rag_context = f"\nKnowledge base context: {results[0].content[:200]}..." if results else ""

            return {
                "success": True,
                "project": info,
                "summary": f"Project: {info['name']}, Key files: {', '.join(info['files'][:5])}, Main file types: {', '.join(list(info['structure'].keys())[:5])}{rag_context}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def chat(self, message: str) -> str:
        """
        Main conversation interface.
        Now uses agentic reasoning - JADE thinks and acts, not just responds.
        """
        # Handle special commands
        msg_lower = message.lower().strip()
        if msg_lower in ["clear", "forget", "clear context", "start fresh", "reset"]:
            return self.chat_handler.clear_context()

        if msg_lower == "classic":
            self.agentic_mode = False
            return "Switched to classic mode (intent classification)."

        if msg_lower == "agentic":
            if AGENTIC_AVAILABLE:
                self.agentic_mode = True
                if not self.agentic_engine:
                    self._init_agentic_engine()
                return "Switched to agentic mode (LLM reasoning with tools)."
            else:
                return "Agentic engine not available."

        # Use agentic mode if available and enabled
        if self.agentic_mode and self.agentic_engine:
            return self.chat_handler.agentic_chat(message)

        # Fallback to classic intent-based routing
        return self.chat_handler.classic_chat(message)

    def interactive(self):
        """Chat mode"""
        # Enable readline for arrow keys, history, and line editing
        try:
            import readline
            # Set up history file
            history_file = Path.home() / ".jade_history"
            try:
                readline.read_history_file(history_file)
            except FileNotFoundError:
                pass
            readline.set_history_length(1000)
            import atexit
            atexit.register(readline.write_history_file, history_file)
        except ImportError:
            pass  # readline not available on some platforms

        print("\n" + "=" * 56)
        print("  JADE [C-rank] — DevSecOps Supervisor")
        print("  Iron Legion Orchestrator | GP-Copilot")
        print("=" * 56)
        print("  Commands: scan, fix, status, escalate, help")
        print("  Modes:    agentic (default) | classic")
        print("  Type 'exit' to quit")
        print("=" * 56 + "\n")

        while True:
            try:
                user = input("\033[1;36mYou:\033[0m ").strip()
                if not user:
                    continue
                if user.lower() in ['exit', 'quit', 'q']:
                    print("\nBye!")
                    break

                response = self.chat(user)
                print(f"\n\033[1;32mJADE:\033[0m {response}\n")

            except KeyboardInterrupt:
                print("\n\nBye!")
                break
            except Exception as e:
                print(f"\n\033[31mError: {e}\033[0m\n")


def main():
    jade = JADE(quiet=len(sys.argv) > 1)

    if len(sys.argv) == 1 or sys.argv[1] == ".":
        jade.interactive()
    else:
        query = " ".join(sys.argv[1:])
        response = jade.chat(query)
        print(f"\n\033[1;32mJADE:\033[0m {response}\n")


if __name__ == "__main__":
    main()