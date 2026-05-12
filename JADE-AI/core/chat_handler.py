"""
JADE Chat Handler
Manages conversation flow, context persistence, and response generation.

Extracted from jade.py monolith — handles:
- Agentic chat (LLM reasoning with tools)
- Classic chat (intent classification fallback)
- Context management (history, save/load)
- Session logging (JSON chat logs)
- RAG-powered response generation
- Response cleaning and validation
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class ChatHandler:
    """Handles JADE's conversation flow — agentic and classic modes."""

    def __init__(self, jade):
        """
        Args:
            jade: JADE instance (provides llm, rag, agentic_engine, history, context, etc.)
        """
        self.jade = jade

    # =========================================================================
    # CHAT ENTRY POINTS
    # =========================================================================

    def agentic_chat(self, message: str) -> str:
        """Agentic chat — LLM reasons about what to do and uses tools."""
        self.jade.history.append({"role": "user", "content": message})

        try:
            response = self.jade.agentic_engine.reason(message)
        except Exception as e:
            print(f"  [agentic] Error: {e}, falling back to classic")
            response = self.classic_chat_internal(message)

        self.jade.history.append({"role": "assistant", "content": response})

        if len(self.jade.history) > self.jade.max_history * 2:
            self.jade.history = self.jade.history[-self.jade.max_history * 2:]

        self.log_exchange(message, response, {"type": "agentic"})
        self.save_context()
        return response

    def classic_chat(self, message: str) -> str:
        """Classic chat — intent classification and routing."""
        self.jade.history.append({"role": "user", "content": message})

        response = self.classic_chat_internal(message)

        self.jade.history.append({"role": "assistant", "content": response})

        if len(self.jade.history) > self.jade.max_history * 2:
            self.jade.history = self.jade.history[-self.jade.max_history * 2:]

        intent = self.jade.intent_router.understand(message)
        self.log_exchange(message, response, intent)
        self.save_context()
        return response

    def classic_chat_internal(self, message: str) -> str:
        """Internal classic chat logic without history management."""
        intent = self.jade.intent_router.understand(message)
        return self.jade.intent_router.act(message, intent)

    # =========================================================================
    # CONTEXT MANAGEMENT
    # =========================================================================

    def load_context(self) -> tuple:
        """Load conversation history and context from disk."""
        history = []
        context = {}
        try:
            if self.jade.context_file.exists():
                with open(self.jade.context_file, 'r') as f:
                    data = json.load(f)
                history = data.get("history", [])[-self.jade.max_history * 2:]
                context = data.get("context", {})
        except Exception:
            pass  # Start fresh if file is corrupted
        return history, context

    def save_context(self):
        """Save conversation history and context to disk."""
        try:
            safe_context = {}
            for k, v in self.jade.context.items():
                try:
                    json.dumps(v)
                    safe_context[k] = v
                except (TypeError, ValueError):
                    pass

            data = {
                "history": self.jade.history[-self.jade.max_history * 2:],
                "context": safe_context,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.jade.context_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def clear_context(self) -> str:
        """Clear conversation history and context."""
        self.jade.history = []
        self.jade.context = {}
        if self.jade.context_file.exists():
            self.jade.context_file.unlink()
        return "Context cleared. Starting fresh."

    # =========================================================================
    # LOGGING
    # =========================================================================

    def init_log_file(self):
        """Initialize the session log file with metadata."""
        try:
            session_data = {
                "session_id": self.jade.session_id,
                "started_at": datetime.now().isoformat(),
                "model": getattr(self.jade, 'model_name', 'jade:v1.0'),
                "exchanges": []
            }
            with open(self.jade.log_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def log_exchange(self, question: str, response: str, intent: Dict):
        """Log chat exchange to readable JSON."""
        try:
            with open(self.jade.log_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            exchange = {
                "timestamp": datetime.now().isoformat(),
                "intent": intent.get("type", "unknown"),
                "question": question,
                "response": response[:500],
                "rag_used": self.jade.rag is not None and intent.get("type") == "conversation"
            }
            session_data["exchanges"].append(exchange)

            with open(self.jade.log_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # =========================================================================
    # RESPONSE GENERATION
    # =========================================================================

    def answer_with_rag(self, message: str, collection: str = None) -> str:
        """Answer using RAG (searches platform knowledge + general knowledge)."""
        system = """You are JADE, the C-rank DevSecOps supervisor for GP-Copilot's Iron Legion.
You answer DevSecOps questions using your RAG knowledge base. Be specific and accurate.
Your scope: Kubernetes security (CKS), cloud security (AWS), OPA/Gatekeeper, IaC, compliance.
If you don't have enough information, say so honestly."""

        rag_context = ""
        if self.jade.rag:
            try:
                results = self.jade.rag.query(message, top_k=5)
                if results:
                    context_parts = []
                    for r in results:
                        content = r.content[:600] if len(r.content) > 600 else r.content
                        source = r.metadata.get('file', r.collection) if hasattr(r, 'metadata') else r.collection
                        context_parts.append(f"[{source}]\n{content}")
                    rag_context = "\n\n---\n\n".join(context_parts)
            except Exception:
                pass

        if rag_context:
            prompt = f"""Context from GP-Copilot knowledge base:

{rag_context}

Question: {message}

Answer based on the context above:"""
        else:
            prompt = message

        try:
            response = self.jade.llm.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=0.3,
                max_tokens=600
            )

            if self.is_bad_response(response):
                return "I don't have enough information to answer that accurately. Try asking differently."

            return self.clean(response)
        except Exception:
            return "Failed to generate response."

    def handle_generate(self, message: str) -> str:
        """Handle code generation requests using RAG + LLM."""
        rag_context = ""
        if self.jade.rag:
            try:
                results = self.jade.rag.query(message, top_k=5)
                if results:
                    context_parts = []
                    for r in results:
                        content = r.content[:800] if len(r.content) > 800 else r.content
                        context_parts.append(content)
                    rag_context = "\n\n---\n\n".join(context_parts)
            except Exception:
                pass

        system = """You are JADE, C-rank DevSecOps supervisor. Generate production-ready code.
For Kubernetes resources, Gatekeeper constraints, OPA policies, or Terraform:
- Include all required fields and security contexts
- Follow CIS/PSS best practices
- Add comments explaining security decisions
- Make it copy-paste ready"""

        prompt = f"""Generate the requested code:

{message}

Context from knowledge base:
{rag_context if rag_context else 'No specific examples found, use your knowledge.'}

Generate the code:"""

        try:
            response = self.jade.llm.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=0.3,
                max_tokens=1000
            )
            return self.clean(response)
        except Exception:
            return "Failed to generate code. Try being more specific."

    def converse(self, message: str) -> str:
        """Natural conversation using LLM with RAG context."""
        system = """You are JADE, the C-rank DevSecOps supervisor for GP-Copilot's Iron Legion.

You orchestrate JSA agents and provide expert guidance on:
- Kubernetes security and operations (CKS certified)
- Cloud security (AWS, Azure, GCP)
- Security scanning and remediation (Trivy, Bandit, Semgrep, Gitleaks)
- Infrastructure as Code (Terraform, CloudFormation)
- Policy as Code (OPA/Rego, Gatekeeper, Kyverno)
- Compliance and policy (SOC2, PCI-DSS, CIS)

Be concise and practical. Give actionable answers like a senior engineer.
If context is provided from the knowledge base, use it."""

        rag_context = ""
        if self.jade.rag:
            try:
                results = self.jade.rag.query(message, top_k=3)
                if results:
                    context_parts = []
                    for r in results:
                        content = r.content[:600] if len(r.content) > 600 else r.content
                        context_parts.append(f"[{r.collection}] {content}")
                    rag_context = "\n\n---\n\n".join(context_parts)
            except Exception:
                pass

        if rag_context:
            prompt = f"""Context from knowledge base:
{rag_context}

Question: {message}

Answer:"""
        else:
            prompt = message

        try:
            response = self.jade.llm.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=0.4,
                max_tokens=500
            )

            if self.is_bad_response(response):
                return self.fallback_response(message)

            return self.clean(response)
        except Exception:
            return self.fallback_response(message)

    # =========================================================================
    # GREETING / HELP
    # =========================================================================

    def greeting(self) -> str:
        """Friendly greeting."""
        return """Hey! I'm JADE — C-rank DevSecOps supervisor for the Iron Legion.

I orchestrate JSA agents and handle security findings:
- **Scan/Fix**: "scan this project" / "fix these findings"
- **JSA Fleet**: "agent status" / "list agents"
- **Escalate**: B-S rank findings go to Jimmie
- **Knowledge**: Ask me anything about K8s security, OPA, IaC

What do you need?"""

    def help_text(self) -> str:
        """Show capabilities."""
        caps = []
        if self.jade.orchestrator:
            caps.append("Project management")
        if self.jade.jsa:
            caps.append("JSA deployment")
        if self.jade.logs:
            caps.append("Log/training status")
        if self.jade.cluster:
            caps.append("K8s cluster ops")
        if hasattr(self.jade, 'commander') and self.jade.commander:
            caps.append("Commander (fleet control)")

        ctx_count = len(self.jade.history) // 2
        ctx_info = f"{ctx_count} prior exchanges" if ctx_count > 0 else "empty"

        return f"""**JADE [C-rank] — DevSecOps Supervisor**

**Capabilities:** {', '.join(caps)}
**Context:** {ctx_info} (persisted)

**Orchestrator Commands:**
- "scan <project>" — Run security scans
- "fix these" — Apply fixes to findings
- "agent status" — Check JSA fleet
- "list agents" — Show deployed agents
- "escalate" — Push B-S rank to human

**Knowledge:**
- "what is a NetworkPolicy?" — DevSecOps Q&A via RAG
- "generate gatekeeper policy" — Code generation
- "show pods" / "cluster status" — K8s operations

**Context:**
- "clear" / "reset" — Fresh conversation
- "classic" / "agentic" — Switch modes

Authority ceiling: C-rank. B-S rank findings escalate to Jimmie."""

    # =========================================================================
    # RESPONSE HELPERS
    # =========================================================================

    def is_bad_response(self, resp: str) -> bool:
        """Detect garbage output."""
        if not resp or len(resp) < 10:
            return True
        if resp.count('?') > 8:
            return True
        lower = resp.lower()
        if lower.startswith('system') or 'you are scdao' in lower:
            return True
        return False

    def clean(self, resp: str) -> str:
        """Clean up response."""
        resp = re.sub(r'(how can [iI][^?]*\?){2,}', '', resp)
        resp = re.sub(r'(\[\]\([^)]+\)\s*){2,}', '', resp)

        if resp.lower().startswith('system'):
            lines = resp.split('\n')
            resp = '\n'.join(lines[1:]) if len(lines) > 1 else resp

        if len(resp) > 600:
            idx = resp[:600].rfind('.')
            resp = resp[:idx + 1] if idx > 300 else resp[:600] + "..."

        return resp.strip()

    def fallback_response(self, message: str) -> str:
        """When LLM fails."""
        msg = message.lower()

        if any(w in msg for w in ["security", "secure", "vulnerability"]):
            return "I can help with security. Try 'scan <project>' or 'cluster security' for specific checks."

        if any(w in msg for w in ["kubernetes", "k8s", "pod", "deploy"]):
            return "For Kubernetes help, try 'cluster info', 'show pods', or ask a specific question."

        return "I'm not sure how to help with that. Try 'help' to see what I can do, or ask about security/DevOps topics."
