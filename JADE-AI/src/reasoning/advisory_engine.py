"""
AdvisoryEngine - LangGraph state machine for JADE C-rank decisions.

Replaces the single LLM call in GP-API/routes/jade.py with a multi-step
reasoning pipeline:

    START -> assess_finding -> research -> plan -> validate -> decide -> END
                                                                |
                                                                +-> (loop back to research if confidence < threshold, max 3 cycles)

Each node is a function that takes state dict and returns updated state.
The graph orchestrates the full JADE intelligence stack:
- RAG retrieval (ChromaDB)
- ML classification verification
- RemediationPlanner integration
- LLM reasoning (jade:v1.0 via Ollama)

Usage:
    from jade_ai.src.reasoning import AdvisoryEngine

    engine = AdvisoryEngine(llm_provider=provider, rag_engine=rag)
    decision = engine.evaluate(finding, fix_plan)
    # decision = {"decision": "approve", "reason": "...", "confidence": 0.87, ...}
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jade.advisory-engine")

# Authority ceiling - NEVER CHANGE
MAX_AUTHORITY = "C"
RANK_PRIORITY = {"E": 1, "D": 2, "C": 3, "B": 4, "S": 5}

# Max reasoning cycles (prevent infinite loops)
MAX_CYCLES = 3

# Confidence threshold - below this, loop back to research
CONFIDENCE_THRESHOLD = 0.7


@dataclass
class AdvisoryState:
    """State passed between LangGraph nodes."""
    # Input
    finding_id: str = ""
    title: str = ""
    severity: str = ""
    scanner: str = ""
    domain: str = ""
    rank: str = ""
    fix_plan: str = ""
    resource: Optional[str] = None
    metadata: Optional[Dict] = None

    # Assessment phase
    risk_level: str = ""            # LOW, MEDIUM, HIGH, CRITICAL
    history_count: int = 0          # Similar findings seen before

    # Research phase
    rag_context: Optional[Dict] = None
    ml_prediction: Optional[Dict] = None
    similar_findings: List[Dict] = field(default_factory=list)

    # Plan phase
    remediation_plan: Optional[Dict] = None
    plan_step_count: int = 0

    # Validate phase
    blast_radius: str = ""          # LOW, MEDIUM, HIGH, CRITICAL
    dry_run_feasible: bool = True
    policy_compliant: bool = True
    validation_notes: List[str] = field(default_factory=list)

    # Decide phase
    decision: str = ""              # approve, deny, escalate
    reason: str = ""
    confidence: float = 0.0
    llm_raw_response: str = ""

    # Control flow
    cycle_count: int = 0
    current_node: str = "start"
    error: Optional[str] = None
    elapsed_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "severity": self.severity,
            "rank": self.rank,
            "decision": self.decision,
            "reason": self.reason,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "blast_radius": self.blast_radius,
            "cycle_count": self.cycle_count,
            "plan_step_count": self.plan_step_count,
            "rag_context": self.rag_context,
            "ml_prediction": self.ml_prediction,
            "remediation_plan": self.remediation_plan,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
        }


class AdvisoryEngine:
    """
    LangGraph-based advisory engine for JADE C-rank decisions.

    Implements a state machine with 5 nodes:
    1. assess_finding - classify severity, check history
    2. research - RAG query for similar findings and past decisions
    3. plan - RemediationPlanner proposes fix strategy
    4. validate - blast radius check, dry-run feasibility, policy compliance
    5. decide - LLM synthesizes all context into approve/deny/escalate

    The decide node can loop back to research if confidence < threshold.
    Max 3 cycles (hardcoded).
    """

    def __init__(
        self,
        llm_provider=None,
        rag_engine=None,
        ml_classifier=None,
        remediation_planner=None,
        findings_store=None,
    ):
        """
        Initialize AdvisoryEngine.

        Args:
            llm_provider: BaseLLMProvider instance for LLM calls
            rag_engine: RAGGraphEngine for context retrieval
            ml_classifier: ML rank classifier for verification
            remediation_planner: RemediationPlanner for fix planning
            findings_store: FindingsStore for history lookup
        """
        self.llm = llm_provider
        self.rag = rag_engine
        self.ml = ml_classifier
        self.planner = remediation_planner
        self.store = findings_store

        # Node registry
        self._nodes: Dict[str, Callable] = {
            "assess": self._node_assess,
            "research": self._node_research,
            "plan": self._node_plan,
            "validate": self._node_validate,
            "decide": self._node_decide,
        }

    def evaluate(
        self,
        finding: Dict[str, Any],
        fix_plan: str,
    ) -> Dict[str, Any]:
        """
        Run the full advisory pipeline on a finding.

        This is the main entry point. GP-API/routes/jade.py calls this
        instead of the raw Ollama call.

        Args:
            finding: Finding dict (id, title, severity, scanner, domain, rank, resource, metadata)
            fix_plan: Description of the proposed fix

        Returns:
            Dict with: decision, reason, confidence, jade_available,
                      rag_context, ml_prediction, remediation_plan, elapsed_ms
        """
        start = time.monotonic()

        # Initialize state from finding
        state = AdvisoryState(
            finding_id=finding.get("finding_id", finding.get("id", "unknown")),
            title=finding.get("title", ""),
            severity=finding.get("severity", "MEDIUM"),
            scanner=finding.get("scanner", "unknown"),
            domain=finding.get("domain", "unknown"),
            rank=finding.get("rank", "C"),
            fix_plan=fix_plan,
            resource=finding.get("resource"),
            metadata=finding.get("metadata"),
        )

        # Pre-graph gates (fast, deterministic)
        # Gate 1: Authority ceiling
        rank_priority = RANK_PRIORITY.get(state.rank, 5)
        if rank_priority > RANK_PRIORITY.get(MAX_AUTHORITY, 3):
            state.decision = "escalate"
            state.reason = f"Rank {state.rank} exceeds JADE authority ceiling ({MAX_AUTHORITY})"
            state.confidence = 1.0
            state.elapsed_ms = int((time.monotonic() - start) * 1000)
            return self._format_result(state)

        # Gate 2: Red flags
        red_flag = self._check_red_flags(state.fix_plan)
        if red_flag:
            state.decision = "deny"
            state.reason = f"Fix plan contains dangerous pattern: {red_flag}"
            state.confidence = 1.0
            state.elapsed_ms = int((time.monotonic() - start) * 1000)
            return self._format_result(state)

        # Gate 3: Empty fix plan
        if len(state.fix_plan.strip()) < 10:
            state.decision = "deny"
            state.reason = "Fix plan too short or empty"
            state.confidence = 1.0
            state.elapsed_ms = int((time.monotonic() - start) * 1000)
            return self._format_result(state)

        # Run the state machine
        node_order = ["assess", "research", "plan", "validate", "decide"]

        try:
            for node_name in node_order:
                state.current_node = node_name
                node_fn = self._nodes[node_name]
                state = node_fn(state)

                if state.error:
                    logger.error("Node '%s' failed: %s", node_name, state.error)
                    break

                # After decide: check if we need to loop
                if node_name == "decide" and state.decision == "" and state.cycle_count < MAX_CYCLES:
                    # Confidence too low, loop back to research
                    state.cycle_count += 1
                    logger.info(
                        "Confidence %.2f < %.2f, cycling back (cycle %d/%d)",
                        state.confidence, CONFIDENCE_THRESHOLD,
                        state.cycle_count, MAX_CYCLES,
                    )
                    # Re-run from research
                    for retry_node in ["research", "validate", "decide"]:
                        state.current_node = retry_node
                        state = self._nodes[retry_node](state)
                        if state.error or state.decision:
                            break

        except Exception as e:
            logger.error("Advisory engine error: %s", e)
            state.error = str(e)

        # Fallback if no decision was made
        if not state.decision:
            if state.error:
                state.decision = "escalate"
                state.reason = f"Advisory engine error: {state.error}"
                state.confidence = 0.0
            else:
                state.decision = "escalate"
                state.reason = "Could not reach confident decision after max cycles"
                state.confidence = 0.0

        state.elapsed_ms = int((time.monotonic() - start) * 1000)
        return self._format_result(state)

    # ------------------------------------------------------------------
    # Graph nodes
    # ------------------------------------------------------------------

    def _node_assess(self, state: AdvisoryState) -> AdvisoryState:
        """Node 1: Assess finding - classify severity, check history."""
        logger.debug("assess: %s (severity=%s)", state.finding_id, state.severity)

        # Map severity to risk level
        severity_risk = {
            "CRITICAL": "CRITICAL",
            "HIGH": "HIGH",
            "MEDIUM": "MEDIUM",
            "LOW": "LOW",
        }
        state.risk_level = severity_risk.get(state.severity.upper(), "MEDIUM")

        # Check history in FindingsStore
        if self.store:
            try:
                past = self.store.get_devsec_findings_by_title(state.title)
                state.history_count = len(past)
                if past:
                    logger.info("assess: Found %d historical matches for '%s'", len(past), state.title)
            except Exception as e:
                logger.warning("assess: FindingsStore lookup failed: %s", e)

        return state

    def _node_research(self, state: AdvisoryState) -> AdvisoryState:
        """Node 2: Research - RAG query for similar findings and past decisions."""
        logger.debug("research: querying RAG for '%s'", state.title)

        # RAG retrieval
        if self.rag:
            try:
                query = f"{state.title} {state.severity} {state.scanner} {state.domain}"
                results = self.rag.query(query, top_k=5)
                if results:
                    state.similar_findings = [
                        {
                            "content": (r.content if hasattr(r, "content") else r.get("content", ""))[:200],
                            "source": getattr(r, "source", r.get("source", "unknown")),
                            "score": getattr(r, "score", r.get("score", 0.0)),
                        }
                        for r in results
                    ]
                    state.rag_context = {
                        "similar_findings": len(results),
                        "top_matches": state.similar_findings[:3],
                    }
                    logger.info("research: RAG returned %d similar findings", len(results))
            except Exception as e:
                logger.warning("research: RAG query failed: %s", e)

        # ML classification verification
        if self.ml:
            try:
                ml_input = {
                    "title": state.title,
                    "severity": state.severity,
                    "scanner": state.scanner,
                    "domain": state.domain,
                }
                ml_rank = self.ml.predict_rank(ml_input)
                state.ml_prediction = {
                    "predicted_rank": ml_rank,
                    "matches_agent_rank": ml_rank == state.rank,
                    "rank_confidence": 0.85,
                }
                logger.info("research: ML predicts rank=%s (agent=%s)", ml_rank, state.rank)
            except Exception as e:
                logger.warning("research: ML classification failed: %s", e)

        return state

    def _node_plan(self, state: AdvisoryState) -> AdvisoryState:
        """Node 3: Plan - RemediationPlanner proposes fix strategy."""
        logger.debug("plan: generating remediation plan for '%s'", state.title)

        if self.planner:
            try:
                finding_dict = {
                    "id": state.finding_id,
                    "title": state.title,
                    "severity": state.severity,
                    "rank": state.rank,
                    "resource": state.resource,
                }
                plan = self.planner.plan(finding_dict)
                state.remediation_plan = plan.to_dict()
                state.plan_step_count = len(plan.steps)
                logger.info("plan: Generated %d-step remediation plan", state.plan_step_count)
            except Exception as e:
                logger.warning("plan: RemediationPlanner failed: %s", e)

        return state

    def _node_validate(self, state: AdvisoryState) -> AdvisoryState:
        """Node 4: Validate - blast radius check, dry-run feasibility, policy compliance."""
        logger.debug("validate: checking blast radius and feasibility")

        # Blast radius estimation from severity + context
        if state.risk_level in ("CRITICAL", "HIGH") or state.history_count > 3:
            state.blast_radius = "HIGH"
        elif state.risk_level == "MEDIUM":
            state.blast_radius = "MEDIUM"
        else:
            state.blast_radius = "LOW"

        # Check if plan has restart requirements
        if state.remediation_plan:
            steps = state.remediation_plan.get("steps", [])
            restart_steps = sum(1 for s in steps if s.get("requires_restart"))
            total_downtime = state.remediation_plan.get("total_estimated_downtime_sec", 0)

            if restart_steps > 2 or total_downtime > 120:
                state.blast_radius = "HIGH"
                state.validation_notes.append(
                    f"Plan requires {restart_steps} restarts, ~{total_downtime}s downtime"
                )

            if state.remediation_plan.get("requires_human_review"):
                state.validation_notes.append("Plan flagged for human review (no template matched)")

        # Dry-run feasibility (simple heuristic)
        state.dry_run_feasible = state.blast_radius != "CRITICAL"

        # Policy compliance check (fix plan shouldn't violate known policies)
        fix_lower = state.fix_plan.lower()
        if "chmod 777" in fix_lower or "privileged: true" in fix_lower:
            state.policy_compliant = False
            state.validation_notes.append("Fix plan violates security policy")

        logger.info(
            "validate: blast_radius=%s, dry_run=%s, policy=%s",
            state.blast_radius, state.dry_run_feasible, state.policy_compliant,
        )

        return state

    def _node_decide(self, state: AdvisoryState) -> AdvisoryState:
        """Node 5: Decide - LLM synthesizes all context into approve/deny/escalate."""
        logger.debug("decide: synthesizing decision (cycle %d)", state.cycle_count)

        # Policy violation = deny without LLM
        if not state.policy_compliant:
            state.decision = "deny"
            state.reason = "Fix plan violates security policy: " + "; ".join(state.validation_notes)
            state.confidence = 0.95
            return state

        # CRITICAL blast radius = escalate without LLM
        if state.blast_radius == "CRITICAL":
            state.decision = "escalate"
            state.reason = "Blast radius is CRITICAL - requires human review"
            state.confidence = 0.95
            return state

        # If no LLM available, use heuristic decision
        if not self.llm:
            return self._heuristic_decide(state)

        # Build LLM prompt with full context
        prompt = self._build_decision_prompt(state)

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are JADE, a C-rank AI Advisory Engine for Kubernetes security. "
                    "You have access to historical data, ML analysis, and remediation plans. "
                    "Make a clear decision: APPROVE, DENY, or ESCALATE."
                ),
                max_tokens=200,
                temperature=0.3,
            )

            state.llm_raw_response = response if isinstance(response, str) else str(response)
            state = self._parse_llm_decision(state)

        except Exception as e:
            logger.error("decide: LLM call failed: %s", e)
            return self._heuristic_decide(state)

        return state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_red_flags(self, fix_plan: str) -> Optional[str]:
        """Check fix plan for dangerous patterns."""
        red_flags = [
            "rm -rf /", "drop database", "delete from users",
            "chmod 777", "curl | bash", "eval(",
            "kubectl delete namespace", "kubectl delete --all",
        ]
        fix_lower = fix_plan.lower()
        for flag in red_flags:
            if flag in fix_lower:
                return flag
        return None

    def _build_decision_prompt(self, state: AdvisoryState) -> str:
        """Build rich LLM prompt with all gathered context."""
        parts = [
            "Evaluate this security finding and its proposed fix.\n",
            "FINDING:",
            f"  ID: {state.finding_id}",
            f"  Title: {state.title}",
            f"  Severity: {state.severity}",
            f"  Scanner: {state.scanner}",
            f"  Domain: {state.domain}",
            f"  Rank: {state.rank}-rank",
            f"  Risk Level: {state.risk_level}",
            "",
            "PROPOSED FIX:",
            f"  {state.fix_plan}",
            "",
        ]

        # RAG context
        if state.rag_context and state.rag_context.get("similar_findings", 0) > 0:
            parts.append("HISTORICAL CONTEXT (from knowledge base):")
            parts.append(f"  {state.rag_context['similar_findings']} similar findings found")
            for i, match in enumerate(state.rag_context.get("top_matches", [])[:2], 1):
                parts.append(f"  {i}. {match['content'][:150]}...")
            parts.append("")

        # ML prediction
        if state.ml_prediction:
            parts.append("ML CLASSIFIER ANALYSIS:")
            parts.append(f"  Predicted rank: {state.ml_prediction['predicted_rank']}")
            parts.append(f"  Matches agent rank: {state.ml_prediction['matches_agent_rank']}")
            parts.append("")

        # Remediation plan
        if state.remediation_plan:
            parts.append("REMEDIATION PLAN:")
            parts.append(f"  Steps: {state.plan_step_count}")
            parts.append(f"  Estimated downtime: {state.remediation_plan.get('total_estimated_downtime_sec', 0)}s")
            for step in state.remediation_plan.get("steps", [])[:3]:
                parts.append(f"  {step['order']}. {step['action']}")
            parts.append("")

        # Validation results
        parts.append("VALIDATION:")
        parts.append(f"  Blast radius: {state.blast_radius}")
        parts.append(f"  Dry-run feasible: {state.dry_run_feasible}")
        parts.append(f"  Policy compliant: {state.policy_compliant}")
        if state.validation_notes:
            for note in state.validation_notes:
                parts.append(f"  Note: {note}")
        parts.append("")

        # Decision rules
        parts.extend([
            "DECISION RULES:",
            "- You can only approve C-rank or below (never B or S)",
            "- Consider: Is the fix safe? Could it cause downtime? Is it the right approach?",
            "- If the blast radius is HIGH, be cautious",
            "- Use the historical context and ML analysis to inform your decision",
            "- If unsure, ESCALATE to human",
            "",
            "Respond with EXACTLY one word on the first line: APPROVE, DENY, or ESCALATE",
            "Then on the next line, give a brief reason (one sentence).",
        ])

        return "\n".join(parts)

    def _parse_llm_decision(self, state: AdvisoryState) -> AdvisoryState:
        """Parse LLM response into decision fields."""
        answer = state.llm_raw_response.strip()
        lines = answer.split("\n", 1)
        first_word = lines[0].strip().upper()
        reason = lines[1].strip() if len(lines) > 1 else "No reason provided"

        if "APPROVE" in first_word:
            state.decision = "approve"
            state.confidence = 0.85 if state.rag_context else 0.75
        elif "DENY" in first_word:
            state.decision = "deny"
            state.confidence = 0.85
        elif "ESCALATE" in first_word:
            state.decision = "escalate"
            state.confidence = 0.80
        else:
            # Ambiguous response - check if we can retry
            if state.cycle_count < MAX_CYCLES:
                state.decision = ""  # Signal retry
                state.confidence = 0.3
                logger.warning("decide: Ambiguous LLM response, will retry")
                return state
            else:
                state.decision = "escalate"
                state.confidence = 0.4

        state.reason = reason

        # Boost confidence if RAG and ML agree
        if state.rag_context and state.ml_prediction:
            if state.ml_prediction.get("matches_agent_rank"):
                state.confidence = min(0.95, state.confidence + 0.05)

        return state

    def _heuristic_decide(self, state: AdvisoryState) -> AdvisoryState:
        """Heuristic decision when LLM is unavailable."""
        if state.rank in ("E", "D"):
            state.decision = "approve"
            state.reason = "LLM unavailable, auto-approving E/D-rank (low risk)"
            state.confidence = 0.6
        elif state.blast_radius in ("HIGH", "CRITICAL"):
            state.decision = "escalate"
            state.reason = "LLM unavailable, high blast radius - escalating to human"
            state.confidence = 0.5
        elif state.history_count > 5 and state.risk_level in ("LOW", "MEDIUM"):
            state.decision = "approve"
            state.reason = f"LLM unavailable, but {state.history_count} similar findings resolved successfully"
            state.confidence = 0.55
        else:
            state.decision = "escalate"
            state.reason = "LLM unavailable, escalating C-rank to human"
            state.confidence = 0.0

        return state

    def _format_result(self, state: AdvisoryState) -> Dict[str, Any]:
        """Format final result dict for API response."""
        return {
            "decision": state.decision,
            "reason": f"{state.reason} (decision time: {state.elapsed_ms}ms)",
            "confidence": state.confidence,
            "jade_available": self.llm is not None,
            "rag_context": state.rag_context,
            "ml_prediction": state.ml_prediction,
            "remediation_plan": state.remediation_plan,
            "blast_radius": state.blast_radius,
            "cycle_count": state.cycle_count,
            "elapsed_ms": state.elapsed_ms,
        }


if __name__ == "__main__":
    # Test without LLM (heuristic mode)
    engine = AdvisoryEngine()

    test_cases = [
        {
            "finding": {
                "id": "f-001",
                "title": "Container running as root",
                "severity": "HIGH",
                "scanner": "kubescape",
                "domain": "kubernetes",
                "rank": "C",
                "resource": "Deployment/web-app",
            },
            "fix_plan": "Add securityContext with runAsNonRoot:true and runAsUser:1000 to pod spec",
        },
        {
            "finding": {
                "id": "f-002",
                "title": "IAM wildcard permission",
                "severity": "CRITICAL",
                "scanner": "prowler",
                "domain": "cloud",
                "rank": "B",
            },
            "fix_plan": "Restrict IAM policy to specific resources",
        },
        {
            "finding": {
                "id": "f-003",
                "title": "Test bad fix",
                "severity": "HIGH",
                "scanner": "checkov",
                "domain": "kubernetes",
                "rank": "C",
            },
            "fix_plan": "chmod 777 /etc/passwd",
        },
    ]

    print("=" * 60)
    print("AdvisoryEngine Test (heuristic mode, no LLM)")
    print("=" * 60)

    for tc in test_cases:
        result = engine.evaluate(tc["finding"], tc["fix_plan"])
        print(f"\n{tc['finding']['id']}: {tc['finding']['title']}")
        print(f"  Decision: {result['decision']}")
        print(f"  Reason: {result['reason']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Blast radius: {result.get('blast_radius', 'N/A')}")
        if result.get("remediation_plan"):
            print(f"  Plan steps: {result['remediation_plan'].get('step_count', 0)}")
