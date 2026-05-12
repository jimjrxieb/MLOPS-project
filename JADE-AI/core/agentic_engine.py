"""
Agentic Engine for JADE
========================

This transforms JADE from a Q&A bot into an agentic AI that reasons and acts.

Instead of:
  User message → Intent classification → Fixed handler → Response

We now have:
  User message → LLM reasons about what to do → Executes tools → Continues reasoning → Response

Like Claude Code, JADE can now:
- Decide what tools to use based on the request
- Chain multiple actions (scan → fix → verify)
- Learn from tool results and adapt
- Handle complex multi-step workflows
"""

import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class Tool:
    """Definition of a tool JADE can use."""
    name: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable[..., Dict[str, Any]]

    def to_prompt_format(self) -> str:
        """Format tool for inclusion in system prompt."""
        params_desc = ", ".join(
            f"{k}: {v.get('description', v.get('type', 'any'))}"
            for k, v in self.parameters.items()
        )
        return f"- **{self.name}**({params_desc}): {self.description}"


@dataclass
class ToolCall:
    """A parsed tool call from LLM output."""
    tool_name: str
    arguments: Dict[str, Any]
    raw_text: str = ""


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None


class AgenticEngine:
    """
    The agentic reasoning engine for JADE.

    This engine:
    1. Takes user messages and context
    2. Lets the LLM reason about what tools to use
    3. Executes tool calls and returns results
    4. Continues reasoning until the task is complete
    """

    def __init__(self, llm, context: Dict = None, max_iterations: int = 10):
        """
        Initialize the agentic engine.

        Args:
            llm: The LLM engine to use for reasoning
            context: Shared context dict (scan results, fix history, etc.)
            max_iterations: Max reasoning iterations to prevent infinite loops
        """
        self.llm = llm
        self.context = context or {}
        self.max_iterations = max_iterations
        self.tools: Dict[str, Tool] = {}
        self.conversation_history: List[Dict[str, str]] = []

        # Register default tools
        self._register_default_tools()

    def register_tool(self, tool: Tool):
        """Register a tool that JADE can use."""
        self.tools[tool.name] = tool

    def _register_default_tools(self):
        """Register the default set of tools."""
        # These will be wired to actual implementations by JADE
        pass

    def _build_system_prompt(self) -> str:
        """Build the system prompt with available tools and context."""

        # Tool documentation
        tool_docs = "\n".join(t.to_prompt_format() for t in self.tools.values())

        # Context summary
        context_summary = ""
        if self.context.get("last_cycle"):
            cycle = self.context["last_cycle"]
            data = cycle.get("data", {})
            findings = data.get("total_findings", data.get("findings", []))
            count = len(findings) if isinstance(findings, list) else findings
            context_summary += f"\n- Last scan: {count} findings"
            if data.get("target"):
                context_summary += f" in {Path(data['target']).name}"

        if self.context.get("last_fix_results"):
            fix = self.context["last_fix_results"]
            context_summary += f"\n- Last fix: {fix.get('fixed_count', 0)} fixed, {fix.get('skipped_count', 0)} skipped"

        return f"""You are JADE, the C-rank DevSecOps supervisor of GP-Copilot's Iron Legion.

## CRITICAL: Act First, Talk Later
When the user asks you to DO something, USE A TOOL IMMEDIATELY.
Do NOT plan, do NOT explain what you would do — just do it.

- "how many services?" → use kubectl tool RIGHT NOW
- "scan this project" → use scan tool RIGHT NOW
- "show pods" → use kubectl tool RIGHT NOW
- "fix these findings" → use fix tool RIGHT NOW

Only explain AFTER you have results from a tool.

## Available Tools
{tool_docs}

## How to Use Tools
Output EXACTLY this format:
<tool_call>
{{"tool": "TOOL_NAME", "args": {{"param": "value"}}}}
</tool_call>

Examples:
<tool_call>
{{"tool": "kubectl", "args": {{"command": "get services -A"}}}}
</tool_call>

<tool_call>
{{"tool": "kubectl", "args": {{"command": "get pods -A"}}}}
</tool_call>

<tool_call>
{{"tool": "scan", "args": {{"target": "/path/to/project"}}}}
</tool_call>

<tool_call>
{{"tool": "query_knowledge", "args": {{"question": "how to fix OOMKilled pods"}}}}
</tool_call>

<tool_call>
{{"tool": "list_tasks", "args": {{}}}}
</tool_call>

## Current Context{context_summary if context_summary else " (no prior operations)"}

## Your Role
You orchestrate JSA agents and handle security findings:
1. **Operational queries** (pods, services, nodes) → kubectl tool
2. **Security scans** → scan tool
3. **Fix findings** → fix tool
4. **Knowledge questions** → query_knowledge tool or answer directly
5. **Task files** → list_tasks / process_task_file tools
6. **JSA fleet** → agent_status / list_agents / escalate tools

## Rank System
| Rank | Your Action |
|------|-------------|
| E-D | Answer directly or dispatch to JSA |
| C | YOU decide using RAG knowledge |
| B-S | ESCALATE to human (you cannot approve) |

## Rules
1. USE TOOLS for actions — don't describe what you would do
2. Be CONCISE — answer like a senior engineer
3. For cluster queries, run kubectl and summarize the output
4. For knowledge questions, answer directly or use RAG
5. Your ceiling is C-rank. ESCALATE B-S rank decisions to human."""

    def _parse_tool_calls(self, response: str) -> List[ToolCall]:
        """Extract tool calls from LLM response."""
        tool_calls = []

        # Method 1: Find formal <tool_call>...</tool_call> blocks
        pattern = r'<tool_call>\s*(\{[^}]+\})\s*</tool_call>'
        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                tool_name = data.get("tool", "")
                args = data.get("args", {})

                if tool_name and tool_name in self.tools:
                    tool_calls.append(ToolCall(
                        tool_name=tool_name,
                        arguments=args,
                        raw_text=match
                    ))
            except json.JSONDecodeError:
                try:
                    fixed = match.replace("'", '"')
                    data = json.loads(fixed)
                    tool_name = data.get("tool", "")
                    args = data.get("args", {})
                    if tool_name and tool_name in self.tools:
                        tool_calls.append(ToolCall(
                            tool_name=tool_name,
                            arguments=args,
                            raw_text=match
                        ))
                except:
                    pass

        return tool_calls

    def _detect_action_from_message(self, message: str) -> Optional[ToolCall]:
        """
        Detect intended action from natural language message.
        This makes JADE work even when the LLM doesn't output formal tool calls.
        """
        msg = message.lower()

        # Detect scan requests
        if any(w in msg for w in ["scan", "check for vulnerabilities", "security check", "run scanners"]):
            # Extract path
            path = self._extract_path(message)
            if path:
                return ToolCall(
                    tool_name="scan",
                    arguments={"target": path},
                    raw_text=f"detected: scan {path}"
                )

        # Detect fix requests
        if any(w in msg for w in ["fix", "apply fix", "remediate", "patch"]):
            args = {}
            if "high" in msg:
                args["severity_filter"] = "HIGH"
            elif "critical" in msg:
                args["severity_filter"] = "CRITICAL"
            return ToolCall(
                tool_name="fix",
                arguments=args,
                raw_text="detected: fix"
            )

        # Detect list files requests
        if any(w in msg for w in ["list", "show files", "show directories", "what files", "what's in"]):
            path = self._extract_path(message)
            if path:
                return ToolCall(
                    tool_name="list_files",
                    arguments={"path": path},
                    raw_text=f"detected: list_files {path}"
                )

        # Detect read file requests
        if any(w in msg for w in ["read", "show me", "cat", "view", "open"]) and "/" in message:
            path = self._extract_path(message)
            if path:
                return ToolCall(
                    tool_name="read_file",
                    arguments={"path": path},
                    raw_text=f"detected: read_file {path}"
                )

        # Detect investigation/debugging requests (must come before generic kubectl)
        investigate_triggers = ["investigate", "debug", "why is", "what's wrong", "what is wrong",
                                "crash", "crashing", "crashloopbackoff", "error", "failing", "failed"]
        if any(t in msg for t in investigate_triggers):
            # Extract pod name from message
            pod_name = self._extract_pod_name(message)
            namespace = self._extract_namespace(message)
            ns_flag = f"-n {namespace}" if namespace else ""

            if pod_name:
                # Return describe command - we'll chain logs in the response
                return ToolCall(
                    tool_name="kubectl",
                    arguments={"command": f"describe pod {pod_name} {ns_flag}".strip()},
                    raw_text=f"detected: kubectl describe pod {pod_name}"
                )

        # Detect kubectl requests — fuzzy match K8s resource types
        # Maps canonical resource names + common typos/abbreviations to kubectl resource
        k8s_resource_map = {
            "pods": "pods", "pod": "pods", "pds": "pods", "po": "pods",
            "deployments": "deployments", "deployment": "deployments", "deploy": "deployments",
            "deploymens": "deployments", "deploys": "deployments",
            "services": "services", "service": "services", "svc": "services",
            "sevices": "services", "servics": "services", "svcs": "services",
            "nodes": "nodes", "node": "nodes", "nods": "nodes",
            "namespaces": "namespaces", "namespace": "namespaces", "ns": "namespaces",
            "ingresses": "ingresses", "ingress": "ingresses", "ing": "ingresses",
            "configmaps": "configmaps", "configmap": "configmaps", "cm": "configmaps",
            "secrets": "secrets", "secret": "secrets",
            "statefulsets": "statefulsets", "statefulset": "statefulsets", "sts": "statefulsets",
            "daemonsets": "daemonsets", "daemonset": "daemonsets", "ds": "daemonsets",
            "cronjobs": "cronjobs", "cronjob": "cronjobs", "cj": "cronjobs",
            "jobs": "jobs", "job": "jobs",
            "pvc": "pvc", "pvcs": "pvc", "persistentvolumeclaims": "pvc",
            "networkpolicies": "networkpolicies", "networkpolicy": "networkpolicies", "netpol": "networkpolicies",
        }
        detected_resource = None
        for word in msg.split():
            clean = word.strip("?.,!\"'")
            if clean in k8s_resource_map:
                detected_resource = k8s_resource_map[clean]
                break

        if "kubectl" in msg or detected_resource:
            namespace = self._extract_namespace(message)
            # nodes are cluster-scoped, no namespace flag
            if detected_resource == "nodes":
                return ToolCall(
                    tool_name="kubectl",
                    arguments={"command": "get nodes"},
                    raw_text="detected: kubectl get nodes"
                )
            ns_flag = f"-n {namespace}" if namespace else "-A"
            resource = detected_resource or "pods"  # default to pods for bare "kubectl" mentions
            return ToolCall(
                tool_name="kubectl",
                arguments={"command": f"get {resource} {ns_flag}"},
                raw_text=f"detected: kubectl get {resource} {ns_flag}"
            )

        # Detect search/grep requests
        if any(w in msg for w in ["search for", "find", "grep", "look for"]):
            # Try to extract pattern and path
            path = self._extract_path(message)
            # Extract quoted string as pattern
            quoted = re.findall(r'["\']([^"\']+)["\']', message)
            if quoted and path:
                return ToolCall(
                    tool_name="search",
                    arguments={"pattern": quoted[0], "path": path},
                    raw_text=f"detected: search {quoted[0]} in {path}"
                )

        return None

    def _extract_path(self, message: str) -> Optional[str]:
        """Extract file path from message."""
        # Look for absolute paths
        path_pattern = r'(/[^\s"\']+)'
        matches = re.findall(path_pattern, message)
        if matches:
            # Return the longest match (most specific path)
            return max(matches, key=len)

        # Look for relative paths
        rel_pattern = r'(?:in|on|at|from)\s+([^\s"\']+)'
        matches = re.findall(rel_pattern, message, re.I)
        if matches:
            return matches[0]

        return None

    def _extract_namespace(self, message: str) -> Optional[str]:
        """Extract Kubernetes namespace from message."""
        msg_lower = message.lower()

        # Pattern: "in the X namespace" or "in X namespace"
        ns_pattern = r'(?:in|from|on)\s+(?:the\s+)?(\w+)\s+namespace'
        match = re.search(ns_pattern, msg_lower)
        if match:
            return match.group(1)

        # Pattern: "namespace X" or "-n X"
        ns_pattern2 = r'(?:namespace|ns|-n)\s+(\w+)'
        match = re.search(ns_pattern2, msg_lower)
        if match:
            return match.group(1)

        # Pattern: "X's pods" or "X pods"
        # Common namespaces to look for
        common_ns = ['portfolio', 'default', 'kube-system', 'ingress-nginx', 'monitoring', 'portainer']
        for ns in common_ns:
            if ns in msg_lower:
                return ns

        return None

    def _extract_pod_diagnostics(self, describe_output: str) -> str:
        """Extract key diagnostic info from kubectl describe pod output."""
        lines = describe_output.split('\n')
        diagnostics = []

        # Key fields to extract
        pod_name = ""
        status = ""
        restart_count = 0
        last_state = ""
        events = []

        in_events = False
        in_containers = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Pod name
            if line.startswith("Name:"):
                pod_name = line.split(":", 1)[1].strip()

            # Status
            if line.startswith("Status:"):
                status = line.split(":", 1)[1].strip()

            # Restart count
            if "Restart Count:" in line:
                try:
                    restart_count = int(line.split(":", 1)[1].strip())
                except:
                    pass

            # Last State (container crash info)
            if "Last State:" in line:
                last_state = line.split(":", 1)[1].strip()
                # Get next few lines for details
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith(("Ready:", "Restart", "State:")):
                        last_state += " " + lines[j].strip()
                    else:
                        break

            # Events section
            if line.startswith("Events:"):
                in_events = True
                continue

            if in_events and line_stripped:
                # Skip header line
                if not line_stripped.startswith(("Type", "----")):
                    events.append(line_stripped)

        # Build diagnostic summary
        diagnostics.append(f"**Pod:** {pod_name}")
        diagnostics.append(f"**Status:** {status}")

        if restart_count > 0:
            diagnostics.append(f"**Restarts:** {restart_count}")

        if last_state and last_state != "Terminated":
            diagnostics.append(f"**Last State:** {last_state}")

        if events:
            diagnostics.append("\n**Recent Events:**")
            # Show last 5 events (most recent usually at end)
            for event in events[-5:]:
                # Highlight warnings/errors
                if "Warning" in event or "Error" in event or "Failed" in event or "Back-off" in event:
                    diagnostics.append(f"⚠️  {event}")
                else:
                    diagnostics.append(f"   {event}")

        # Add recommendation based on findings
        if "CrashLoopBackOff" in status or "Back-off" in str(events):
            diagnostics.append("\n**Diagnosis:** Container is crash-looping. Check logs with:")
            diagnostics.append(f"```kubectl logs {pod_name} --previous```")
        elif restart_count > 3:
            diagnostics.append(f"\n**Diagnosis:** High restart count ({restart_count}). Container may be unstable.")

        return "\n".join(diagnostics)

    def _extract_pod_name(self, message: str) -> Optional[str]:
        """Extract Kubernetes pod name from message."""
        # Common pod name patterns:
        # - deployment-replicaset-pod: name-5d7c7474df-jj56p
        # - cronjob: name-29458560-wd77z
        # - statefulset: name-0, name-1

        # Look for pod name patterns (word with hyphens and alphanumeric suffixes)
        pod_pattern = r'\b([a-z][a-z0-9-]*-[a-z0-9]{4,}(?:-[a-z0-9]+)?)\b'
        matches = re.findall(pod_pattern, message.lower())
        if matches:
            # Return the longest match (most likely to be complete pod name)
            return max(matches, key=len)

        # Try to extract just the base name (e.g., "jsa-devsecops-log-sync")
        # Look for hyphenated names that look like K8s resources
        base_pattern = r'\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,5})\b'
        matches = re.findall(base_pattern, message.lower())
        if matches:
            # Filter out common non-pod words
            non_pods = ['crash', 'loop', 'back', 'off', 'log-sync', 'what-is', 'why-is']
            matches = [m for m in matches if m not in non_pods and len(m) > 5]
            if matches:
                return max(matches, key=len)

        return None

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool = self.tools.get(tool_call.tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                result=None,
                error=f"Unknown tool: {tool_call.tool_name}"
            )

        try:
            result = tool.execute(**tool_call.arguments)
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=True,
                result=result
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                result=None,
                error=str(e)
            )

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Format tool results for feeding back to LLM."""
        parts = []
        for result in results:
            if result.success:
                # Truncate very long results
                result_str = str(result.result)
                if len(result_str) > 3000:
                    result_str = result_str[:3000] + "\n... (truncated)"
                parts.append(f"<tool_result name=\"{result.tool_name}\">\n{result_str}\n</tool_result>")
            else:
                parts.append(f"<tool_result name=\"{result.tool_name}\" error=\"true\">\n{result.error}\n</tool_result>")
        return "\n\n".join(parts)

    def _strip_tool_calls(self, response: str) -> str:
        """Remove tool call blocks from response for final output."""
        # Remove <tool_call>...</tool_call> blocks
        cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
        # Clean up extra whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    def _clean_verbose_patterns(self, response: str) -> str:
        """Strip verbose boilerplate patterns from LLM responses."""
        # Remove common verbose patterns
        patterns_to_remove = [
            r'\*\*User Query:\*\*.*?\n',
            r'\*\*My Analysis:\*\*\s*',
            r'\*\*My Summary:\*\*\s*',
            r'\*\*Tool Response:\*\*.*?\n',
            r'\*\*Tool:\*\*.*?\n',
            r'\*\*Execution Time:\*\*.*?\n',
            r'\*\*Human Readable Output:\*\*\s*',
            r'Note: This answer provides.*?\n',
            r'Created Question/Answer.*?\n',
            r'Let me analyze.*?\n',
            r'Based on the.*?results?:?\s*',
        ]

        cleaned = response
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

        # Clean up extra whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'^\s+', '', cleaned)  # Leading whitespace

        return cleaned.strip()

    def _is_conversational(self, msg: str) -> bool:
        """Check if message is conversational (greeting, thanks, simple question)."""
        # Greetings
        greetings = ["hello", "hi", "hey", "yo", "sup", "good morning", "good afternoon", "good evening"]
        if any(msg.startswith(g) or msg == g for g in greetings):
            return True

        # Thanks
        thanks = ["thanks", "thank you", "thx", "ty"]
        if any(msg.startswith(t) or msg == t for t in thanks):
            return True

        # Farewells
        farewells = ["bye", "goodbye", "see you", "later", "cya"]
        if any(msg.startswith(f) or msg == f for f in farewells):
            return True

        # Simple questions that don't need tools
        simple_questions = ["who are you", "what are you", "what can you do", "help"]
        if any(q in msg for q in simple_questions):
            return True

        return False

    def _handle_conversational(self, message: str) -> str:
        """Handle conversational messages without tool reasoning."""
        msg = message.lower().strip()

        # Greetings
        if any(g in msg for g in ["hello", "hi", "hey", "yo", "sup"]):
            return """Hey! I'm JADE, the DevSecOps AI for GP-Copilot.

I can help you with:
- **Scanning**: "scan /path/to/project" - run security scanners
- **Fixing**: "fix these findings" - apply auto-fixes
- **Kubernetes**: "show pods", "get deployments"
- **Files**: "read /path/to/file", "list /directory"

What would you like me to do?"""

        # Thanks
        if any(t in msg for t in ["thanks", "thank you", "thx"]):
            return "You're welcome! Let me know if you need anything else."

        # Farewells
        if any(f in msg for f in ["bye", "goodbye", "see you"]):
            return "Bye! Stay secure 🔐"

        # Who are you / help
        if "who are you" in msg or "what are you" in msg:
            return """I'm **JADE** (Junior AI DevSecOps Engineer) - the AI brain of GP-Copilot.

I specialize in:
- Security scanning (gitleaks, bandit, trivy, semgrep)
- Vulnerability remediation
- Kubernetes security
- Policy as Code (OPA, Gatekeeper, Kyverno)

I can reason about tasks, execute tools, and help you secure your infrastructure."""

        if "help" in msg or "what can you do" in msg:
            tools_list = ", ".join(self.tools.keys()) if self.tools else "scan, fix, read_file, list_files, kubectl"
            return f"""**JADE Capabilities**

**Available Tools:** {tools_list}

**Examples:**
- "scan /path/to/project" - Run security scans
- "fix the HIGH severity findings" - Apply fixes
- "read /path/to/file.yaml" - View file contents
- "show pods" - List Kubernetes pods

Just tell me what you need!"""

        # Fallback - let LLM handle it
        try:
            response = self.llm.generate(
                prompt=message,
                system_prompt="You are JADE, C-rank DevSecOps supervisor. Be brief and direct. No verbose sections.",
                temperature=0.7,
                max_tokens=200
            )
            return self._clean_verbose_patterns(response)
        except:
            return "I'm here to help with security and DevOps tasks. What would you like to do?"

    def reason(self, user_message: str) -> str:
        """
        Main reasoning loop - this is where the magic happens.

        Takes a user message and:
        1. Detects intended action from message OR sends to LLM
        2. Parses any tool calls
        3. Executes tools
        4. Feeds results back to LLM for explanation
        5. Returns final response to user
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        all_tool_results = []

        # FAST PATH: Handle greetings and simple questions without tool reasoning
        msg_lower = user_message.lower().strip()
        if self._is_conversational(msg_lower):
            response = self._handle_conversational(user_message)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response

        # FIRST: Try to detect action directly from user message
        # This makes JADE work even when LLM doesn't output formal tool calls
        detected_action = self._detect_action_from_message(user_message)

        if detected_action:
            # Execute the detected action directly
            print(f"  [agentic] Detected: {detected_action.tool_name}({detected_action.arguments})")
            result = self._execute_tool(detected_action)
            all_tool_results.append(result)

            # If action was successful, let LLM summarize the results
            if result.success:
                # For kubectl, format the count directly without LLM
                if detected_action.tool_name == "kubectl":
                    output = result.result.get("output", "") if isinstance(result.result, dict) else str(result.result)
                    cmd = detected_action.arguments.get("command", "")

                    # Handle describe commands - extract key diagnostic info
                    if "describe" in cmd:
                        # Extract important sections from describe output
                        diag_info = self._extract_pod_diagnostics(output)
                        final_response = diag_info
                        self.conversation_history.append({"role": "assistant", "content": final_response})
                        return final_response

                    # Handle logs commands
                    if "logs" in cmd:
                        # Truncate long logs
                        if len(output) > 2000:
                            output = output[-2000:]  # Last 2000 chars (most recent)
                            final_response = f"**Pod logs** (last 2000 chars):\n```\n{output}\n```"
                        else:
                            final_response = f"**Pod logs**:\n```\n{output}\n```"
                        self.conversation_history.append({"role": "assistant", "content": final_response})
                        return final_response

                    # Handle get commands - count items
                    lines = [l for l in output.strip().split('\n') if l.strip()]
                    # Count data rows (skip header)
                    header = lines[0] if lines else ""
                    data_lines = lines[1:] if len(lines) > 1 else []
                    count = len(data_lines)

                    # Build concise response — extract resource type from command
                    resource_label = None
                    for token in cmd.split():
                        if token in ("pods", "deployments", "services", "nodes",
                                     "namespaces", "ingresses", "configmaps", "secrets",
                                     "statefulsets", "daemonsets", "cronjobs", "jobs",
                                     "pvc", "networkpolicies"):
                            resource_label = token
                            break
                    if resource_label:
                        final_response = f"**{count} {resource_label}**\n```\n{output}\n```"
                    else:
                        final_response = f"```\n{output}\n```"

                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response

                # For scan results - deterministic formatting
                elif detected_action.tool_name == "scan":
                    res = result.result if isinstance(result.result, dict) else {}
                    total = res.get("total_findings", 0)
                    by_scanner = res.get("by_scanner", {})
                    by_severity = res.get("by_severity", {})

                    parts = [f"**{total} findings**"]
                    if by_severity:
                        sev_str = ", ".join(f"{k}: {v}" for k, v in sorted(by_severity.items()))
                        parts.append(f"Severity: {sev_str}")
                    if by_scanner:
                        scan_str = ", ".join(f"{k}: {v}" for k, v in by_scanner.items())
                        parts.append(f"Scanners: {scan_str}")

                    final_response = "\n".join(parts)
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response

                # For list_files - deterministic formatting
                elif detected_action.tool_name == "list_files":
                    res = result.result if isinstance(result.result, dict) else {}
                    files = res.get("files", [])
                    path = res.get("path", "")
                    count = len(files)

                    if count <= 20:
                        file_list = "\n".join(f"  {f}" for f in files)
                        final_response = f"**{count} files** in {path}:\n{file_list}"
                    else:
                        file_list = "\n".join(f"  {f}" for f in files[:20])
                        final_response = f"**{count} files** in {path} (showing first 20):\n{file_list}"

                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response

                # For read_file - show content directly
                elif detected_action.tool_name == "read_file":
                    res = result.result if isinstance(result.result, dict) else {}
                    content = res.get("content", str(result.result))
                    path = res.get("path", detected_action.arguments.get("path", "file"))
                    lines = content.count('\n') + 1

                    # Truncate if too long
                    if len(content) > 3000:
                        content = content[:3000] + "\n... (truncated)"

                    final_response = f"**{path}** ({lines} lines):\n```\n{content}\n```"
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response

                # For search/grep - deterministic formatting
                elif detected_action.tool_name == "search":
                    res = result.result if isinstance(result.result, dict) else {}
                    matches = res.get("matches", [])
                    pattern = detected_action.arguments.get("pattern", "")
                    count = len(matches)

                    if count == 0:
                        final_response = f"No matches for `{pattern}`"
                    else:
                        match_str = "\n".join(f"  {m}" for m in matches[:20])
                        final_response = f"**{count} matches** for `{pattern}`:\n{match_str}"

                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response

                # For other tools, use prescriptive summarization
                else:
                    summary_prompt = f"""User question: {user_message}
Tool: {detected_action.tool_name}
Result:
{json.dumps(result.result, indent=2, default=str)[:2000]}

Respond in this EXACT format - no other text:
**[count] [items]** (if counting)
Brief 1-2 sentence summary of key findings."""

                    try:
                        summary = self.llm.generate(
                            prompt=summary_prompt,
                            system_prompt="Answer directly. No preamble. No 'User Query:' or 'My Analysis:' sections.",
                            temperature=0.2,
                            max_tokens=400
                        )
                        final_response = self._clean_verbose_patterns(summary)
                    except Exception:
                        # Fallback to raw result summary
                        final_response = self._build_final_response([], all_tool_results)
            else:
                final_response = f"Error executing {detected_action.tool_name}: {result.error}"

            self.conversation_history.append({"role": "assistant", "content": final_response})
            return final_response

        # SECOND: If no action detected, let LLM reason
        system_prompt = self._build_system_prompt()
        conversation_context = self._format_conversation_history()

        all_responses = []
        current_prompt = user_message
        tool_results_context = ""

        for iteration in range(self.max_iterations):
            full_prompt = f"{conversation_context}\n\nUser: {current_prompt}"
            if tool_results_context:
                full_prompt = f"{conversation_context}\n\n{tool_results_context}\n\nContinue with the task based on these results."

            try:
                response = self.llm.generate(
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                    temperature=0.4,
                    max_tokens=2000
                )
            except Exception as e:
                return f"Error generating response: {e}"

            all_responses.append(response)

            # Parse tool calls from LLM response
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                break

            # Execute tools
            results = []
            for tc in tool_calls:
                result = self._execute_tool(tc)
                results.append(result)
                all_tool_results.append(result)

            tool_results_context = f"Assistant's previous response:\n{response}\n\nTool results:\n\n{self._format_tool_results(results)}"
            current_prompt = ""

        final_response = self._build_final_response(all_responses, all_tool_results)

        self.conversation_history.append({
            "role": "assistant",
            "content": final_response
        })

        return final_response

    def _format_conversation_history(self) -> str:
        """Format recent conversation history for the prompt."""
        # Get last few exchanges (not current message - that's added separately)
        recent = self.conversation_history[:-1][-6:]  # Last 3 exchanges

        if not recent:
            return ""

        parts = ["Previous conversation:"]
        for msg in recent:
            role = msg["role"].capitalize()
            content = msg["content"][:500]  # Truncate long messages
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    def _build_messages(self) -> List[Dict[str, str]]:
        """Build messages list from conversation history."""
        # Include recent history for context
        recent = self.conversation_history[-10:]  # Last 5 exchanges
        return recent

    def _build_final_response(self, responses: List[str], tool_results: List[ToolResult]) -> str:
        """Build the final response to show the user."""
        if not responses:
            return "I wasn't able to process that request."

        # Get the last response and clean it
        final = responses[-1]
        cleaned = self._strip_tool_calls(final)
        cleaned = self._clean_verbose_patterns(cleaned)  # Also strip verbose patterns

        # If the response is empty after stripping, generate a summary
        if not cleaned or len(cleaned) < 20:
            # Build summary from tool results
            if tool_results:
                summary_parts = []
                for r in tool_results:
                    if r.success:
                        if isinstance(r.result, dict):
                            if r.result.get("total_findings") is not None:
                                summary_parts.append(f"Scan found {r.result['total_findings']} findings")
                            elif r.result.get("fixed_count") is not None:
                                summary_parts.append(f"Fixed {r.result['fixed_count']} issues")
                        else:
                            summary_parts.append(f"{r.tool_name}: completed")
                    else:
                        summary_parts.append(f"{r.tool_name}: {r.error}")

                cleaned = "**Actions completed:**\n" + "\n".join(f"- {p}" for p in summary_parts)
            else:
                cleaned = "Task completed."

        return cleaned


# Tool factory functions - these create Tool instances that wrap real functionality

def create_scan_tool(scan_func: Callable) -> Tool:
    """Create the scan tool."""
    return Tool(
        name="scan",
        description="Run security scans on a target directory (gitleaks, bandit, semgrep, trivy, grype)",
        parameters={
            "target": {"type": "string", "description": "Path to directory to scan"}
        },
        execute=scan_func
    )


def create_fix_tool(fix_func: Callable) -> Tool:
    """Create the fix tool."""
    return Tool(
        name="fix",
        description="Apply security fixes to findings from the last scan",
        parameters={
            "severity_filter": {"type": "string", "description": "Optional: filter by severity (HIGH, MEDIUM, etc.)"},
            "scanner_filter": {"type": "string", "description": "Optional: filter by scanner (bandit, trivy, etc.)"}
        },
        execute=fix_func
    )


def create_query_rag_tool(rag_func: Callable) -> Tool:
    """Create the RAG query tool."""
    return Tool(
        name="query_knowledge",
        description="Search the security knowledge base for information",
        parameters={
            "question": {"type": "string", "description": "The question to search for"}
        },
        execute=rag_func
    )


def create_run_command_tool(cmd_func: Callable) -> Tool:
    """Create the command execution tool."""
    return Tool(
        name="run_command",
        description="Run a shell command (kubectl, git, npm, etc.)",
        parameters={
            "command": {"type": "string", "description": "The command to run"},
            "timeout": {"type": "number", "description": "Timeout in seconds (default: 30)"}
        },
        execute=cmd_func
    )


def create_read_file_tool(read_func: Callable) -> Tool:
    """Create the file reading tool."""
    return Tool(
        name="read_file",
        description="Read contents of a file",
        parameters={
            "path": {"type": "string", "description": "Path to the file"},
            "lines": {"type": "number", "description": "Max lines to read (default: 100)"}
        },
        execute=read_func
    )


def create_list_files_tool(list_func: Callable) -> Tool:
    """Create the file listing tool."""
    return Tool(
        name="list_files",
        description="List files in a directory",
        parameters={
            "path": {"type": "string", "description": "Directory path"},
            "pattern": {"type": "string", "description": "Optional glob pattern (e.g., *.py)"}
        },
        execute=list_func
    )


def create_grep_tool(grep_func: Callable) -> Tool:
    """Create the grep/search tool."""
    return Tool(
        name="search",
        description="Search for patterns in files",
        parameters={
            "pattern": {"type": "string", "description": "Pattern to search for"},
            "path": {"type": "string", "description": "Path to search in"},
            "file_type": {"type": "string", "description": "Optional file extension filter (e.g., py, js)"}
        },
        execute=grep_func
    )


def create_kubectl_tool(kubectl_func: Callable) -> Tool:
    """Create the kubectl tool."""
    return Tool(
        name="kubectl",
        description="Run kubectl commands on the cluster",
        parameters={
            "command": {"type": "string", "description": "kubectl subcommand and args (e.g., 'get pods -n default')"}
        },
        execute=kubectl_func
    )


def create_list_tasks_tool(list_func: Callable) -> Tool:
    """Create the list tasks tool."""
    return Tool(
        name="list_tasks",
        description="List available task files in /JADE-AI/tasks/",
        parameters={},
        execute=list_func
    )


def create_process_task_file_tool(process_func: Callable) -> Tool:
    """Create the task file processing tool."""
    return Tool(
        name="process_task_file",
        description="Parse a task file and get routing (which tasks go to JSA, JADE, or human)",
        parameters={
            "file": {"type": "string", "description": "Task file name (e.g., 'day3.md')"}
        },
        execute=process_func
    )


def create_answer_task_tool(answer_func: Callable) -> Tool:
    """Create the task answering tool."""
    return Tool(
        name="answer_task",
        description="Answer a specific task using RAG knowledge (for E-C rank tasks)",
        parameters={
            "task_id": {"type": "string", "description": "Task ID (e.g., 'TICKET-014')"},
            "file": {"type": "string", "description": "Task file name"}
        },
        execute=answer_func
    )


__all__ = [
    "AgenticEngine",
    "Tool",
    "ToolCall",
    "ToolResult",
    "create_scan_tool",
    "create_fix_tool",
    "create_query_rag_tool",
    "create_run_command_tool",
    "create_read_file_tool",
    "create_list_files_tool",
    "create_grep_tool",
    "create_kubectl_tool",
    "create_list_tasks_tool",
    "create_process_task_file_tool",
    "create_answer_task_tool",
]
