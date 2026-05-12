"""
TriageRouter (Katie) - Fast finding triage and routing.

Sits between RankClassifier and JADE/Runbooks in the pipeline:

    Scanner -> RankClassifier -> TriageRouter (Katie)
                                   |-> E/D: route to Runbook (Pattern NPC)
                                   |-> C: enrich context, forward to JADE
                                   |-> B/S: format and queue for human dashboard

Katie does NOT make C-rank decisions. She routes, she doesn't decide.
Uses LLaMA 3B via Ollama ONLY for ambiguous cases (confidence < 0.6).
Most routing is deterministic pattern matching.

Usage:
    from katie.src.triage_router import TriageRouter

    router = TriageRouter()
    result = router.triage(finding, classification)
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("katie.triage-router")


@dataclass
class TriageResult:
    """Result of Katie's triage routing decision."""
    finding_id: str
    route: str                  # "runbook", "jade", "human_dashboard"
    rank: str                   # E/D/C/B/S
    handler: str                # Specific handler name or queue
    enrichment: Dict[str, Any] = field(default_factory=dict)
    deduplicated: bool = False
    duplicate_of: Optional[str] = None
    confidence: float = 1.0
    triage_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "route": self.route,
            "rank": self.rank,
            "handler": self.handler,
            "enrichment": self.enrichment,
            "deduplicated": self.deduplicated,
            "duplicate_of": self.duplicate_of,
            "confidence": self.confidence,
            "triage_time_ms": self.triage_time_ms,
        }


@dataclass
class TriageMetrics:
    """Routing metrics tracked by Katie."""
    total_triaged: int = 0
    by_route: Dict[str, int] = field(default_factory=lambda: {
        "runbook": 0, "jade": 0, "human_dashboard": 0
    })
    by_rank: Dict[str, int] = field(default_factory=lambda: {
        "E": 0, "D": 0, "C": 0, "B": 0, "S": 0
    })
    duplicates_caught: int = 0
    llm_calls: int = 0
    avg_triage_time_ms: float = 0.0
    _total_time_ms: int = 0

    def record(self, result: TriageResult):
        self.total_triaged += 1
        self.by_route[result.route] = self.by_route.get(result.route, 0) + 1
        self.by_rank[result.rank] = self.by_rank.get(result.rank, 0) + 1
        if result.deduplicated:
            self.duplicates_caught += 1
        self._total_time_ms += result.triage_time_ms
        self.avg_triage_time_ms = self._total_time_ms / self.total_triaged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_triaged": self.total_triaged,
            "by_route": self.by_route,
            "by_rank": self.by_rank,
            "duplicates_caught": self.duplicates_caught,
            "llm_calls": self.llm_calls,
            "avg_triage_time_ms": round(self.avg_triage_time_ms, 1),
        }


# Runbook handler mapping: rule_id prefix, scanner, or event reason -> handler name
# These are the deterministic routing rules for E/D rank findings + operational events.
_RUNBOOK_HANDLERS = {
    # ── Scanner-based routing ──
    "hadolint": "dockerfile_fixer",
    "eslint": "lint_fixer",
    "black": "format_fixer",
    "isort": "import_fixer",
    "prettier": "format_fixer",

    # ── Rule-based routing (substring match on rule_id) ──
    "c-00": "k8s_security_fixer",      # Kubescape controls
    "ckv-k8s": "k8s_security_fixer",
    "ckv_k8s": "k8s_security_fixer",
    "missing-resource-limits": "resource_limits_fixer",
    "run-as-root": "security_context_fixer",
    "readonlyrootfilesystem": "readonly_fs_fixer",
    "privileged-container": "security_context_fixer",
    "host-network": "network_policy_fixer",
    "capability": "capabilities_fixer",
    "seccomp": "seccomp_fixer",
    "hardcoded-secret": "secret_rotation_handler",
    "hardcoded-password": "secret_rotation_handler",
    "hardcoded-api-key": "secret_rotation_handler",
    "generic-api-key": "secret_rotation_handler",
    "sql-injection": "sast_fixer",
    "xss": "sast_fixer",
    "command-injection": "sast_fixer",
    "cve-": "dependency_updater",
    "ghsa-": "dependency_updater",
    "gha/unpinned": "gha_pin_fixer",
    "gha/hardcoded": "gha_secret_fixer",

    # ── Operational event routing (E/D rank events) ──
    # E-rank: one command fixes
    "imagepullbackoff": "image_fixer",
    "errimagepull": "image_fixer",
    "invalidimagename": "image_fixer",

    # D-rank: known pattern, <3 steps
    "createcontainerconfigerror": "config_fixer",
    "failedmount": "volume_fixer",
    "failedattachvolume": "volume_fixer",
    "unhealthy": "probe_fixer",
    "backoff:restarting": "container_restart_fixer",
    "failedcreate:quota": "quota_fixer",

    # D-rank: admission denies (fix the manifest)
    "deny:privileged": "security_context_fixer",
    "deny:host-namespace": "security_context_fixer",
    "deny:latest-tag": "image_fixer",
    "deny:missing-limits": "resource_limits_fixer",
    "deny:run-as-root": "security_context_fixer",
    "deny:capabilities": "capabilities_fixer",
    "deny:no-seccomp": "seccomp_fixer",
}


class TriageRouter:
    """
    Fast finding triage and routing engine (Katie).

    Receives classified findings from RankClassifier and routes them:
    - E/D-rank: directly to the correct Runbook (no LLM call)
    - C-rank: enriches with RAG context + blast radius, forwards to JADE
    - B/S-rank: formats and queues for human dashboard

    Deduplicates findings across scanners (e.g. Polaris + Kubescape
    both flagging the same issue).
    """

    def __init__(
        self,
        findings_store=None,
        rag_engine=None,
        ollama_url: str = "http://localhost:11434",
        katie_model: str = "katie:v1.0",
    ):
        """
        Initialize TriageRouter.

        Args:
            findings_store: FindingsStore instance for deduplication lookups
            rag_engine: RAGGraph engine for C-rank context enrichment
            ollama_url: Ollama API URL (used only for ambiguous cases)
            katie_model: Model name for LLM fallback routing
        """
        self.findings_store = findings_store
        self.rag_engine = rag_engine
        self.ollama_url = ollama_url
        self.katie_model = katie_model
        self.metrics = TriageMetrics()

        # Dedup cache: fingerprint -> finding_id (in-memory, cleared per scan cycle)
        self._dedup_cache: Dict[str, str] = {}

    def triage(
        self,
        finding: Dict[str, Any],
        classification: Optional[Dict[str, Any]] = None,
    ) -> TriageResult:
        """
        Triage a single finding and determine its route.

        Args:
            finding: Finding dict with: id, title, severity, scanner, rule_id,
                     resource, description, rank (if pre-classified)
            classification: Optional ClassificationResult dict from RankClassifier
                           with: rank, confidence, suggested_action, auto_fixable

        Returns:
            TriageResult with routing decision
        """
        start = time.monotonic()

        finding_id = finding.get("id", "unknown")
        rank = self._get_rank(finding, classification)
        confidence = self._get_confidence(classification)

        # Step 1: Deduplication check
        fingerprint = self._fingerprint(finding)
        if fingerprint in self._dedup_cache:
            existing_id = self._dedup_cache[fingerprint]
            if existing_id != finding_id:
                elapsed = int((time.monotonic() - start) * 1000)
                result = TriageResult(
                    finding_id=finding_id,
                    route="runbook" if rank in ("E", "D") else "jade",
                    rank=rank,
                    handler="deduplicated",
                    deduplicated=True,
                    duplicate_of=existing_id,
                    confidence=1.0,
                    triage_time_ms=elapsed,
                )
                self.metrics.record(result)
                logger.debug("Deduplicated %s (duplicate of %s)", finding_id, existing_id)
                return result

        self._dedup_cache[fingerprint] = finding_id

        # Step 2: Route by rank
        if rank in ("E", "D"):
            result = self._route_to_runbook(finding, rank, confidence)
        elif rank == "C":
            result = self._route_to_jade(finding, rank, confidence)
        else:  # B, S
            result = self._route_to_human(finding, rank)

        result.triage_time_ms = int((time.monotonic() - start) * 1000)
        self.metrics.record(result)
        return result

    def triage_batch(
        self,
        findings: List[Dict[str, Any]],
        classifications: Optional[List[Dict[str, Any]]] = None,
    ) -> List[TriageResult]:
        """Triage multiple findings."""
        results = []
        for i, finding in enumerate(findings):
            classification = classifications[i] if classifications and i < len(classifications) else None
            results.append(self.triage(finding, classification))
        return results

    def clear_dedup_cache(self):
        """Clear the deduplication cache. Call at the start of each scan cycle."""
        count = len(self._dedup_cache)
        self._dedup_cache.clear()
        if count:
            logger.info("Cleared dedup cache (%d entries)", count)

    def get_metrics(self) -> Dict[str, Any]:
        """Return current routing metrics."""
        return self.metrics.to_dict()

    # ------------------------------------------------------------------
    # Internal routing methods
    # ------------------------------------------------------------------

    def _route_to_runbook(
        self, finding: Dict, rank: str, confidence: float
    ) -> TriageResult:
        """Route E/D-rank finding to the appropriate Runbook handler."""
        handler = self._match_runbook_handler(finding)
        enrichment = {}

        # RAG-augment E/D rank fixes — retrieve past fixes for this exact issue
        if self.rag_engine:
            try:
                query = self._build_rag_query(finding)
                results = self.rag_engine.query(query, top_k=2)
                if results:
                    enrichment["past_fixes"] = [
                        {
                            "content": r.get("content", "")[:300] if isinstance(r, dict) else str(r)[:300],
                            "source": r.get("source", "unknown") if isinstance(r, dict) else "unknown",
                        }
                        for r in results
                    ]
            except Exception as e:
                logger.debug("RAG enrichment for E/D rank: %s", e)

        # If confidence is low and we can't match a handler, use LLM
        if handler == "generic_fixer" and confidence < 0.6:
            handler = self._llm_route(finding)

        logger.info(
            "Routing %s to runbook:%s (rank=%s, rag_hits=%d)",
            finding.get("id"), handler, rank, len(enrichment.get("past_fixes", [])),
        )

        return TriageResult(
            finding_id=finding.get("id", "unknown"),
            route="runbook",
            rank=rank,
            handler=handler,
            enrichment=enrichment,
            confidence=confidence,
        )

    def _route_to_jade(
        self, finding: Dict, rank: str, confidence: float
    ) -> TriageResult:
        """Route C-rank finding to JADE with enriched context."""
        enrichment = {}

        # Pull similar findings + past fixes from RAG
        if self.rag_engine:
            try:
                query = self._build_rag_query(finding)
                results = self.rag_engine.query(query, top_k=5)
                if results:
                    enrichment["similar_findings"] = [
                        {
                            "content": r.get("content", "")[:300] if isinstance(r, dict) else str(r)[:300],
                            "source": r.get("source", "unknown") if isinstance(r, dict) else "unknown",
                            "score": r.get("score", 0.0) if isinstance(r, dict) else 0.0,
                        }
                        for r in results
                    ]
            except Exception as e:
                logger.warning("RAG enrichment failed: %s", e)

        # Pull blast radius estimate from findings store
        if self.findings_store:
            try:
                title = finding.get("title", "")
                past = self.findings_store.get_devsec_findings_by_title(title)
                if past:
                    enrichment["cascade_match"] = True
                    enrichment["devsec_occurrences"] = len(past)
            except Exception as e:
                logger.warning("FindingsStore lookup failed: %s", e)

        # Add severity-based blast radius hint
        severity = finding.get("severity", "MEDIUM").upper()
        enrichment["estimated_blast_radius"] = {
            "CRITICAL": "HIGH",
            "HIGH": "MEDIUM",
            "MEDIUM": "LOW",
            "LOW": "LOW",
        }.get(severity, "MEDIUM")

        logger.info(
            "Routing %s to JADE (rank=C, enrichment_keys=%s)",
            finding.get("id"), list(enrichment.keys()),
        )

        return TriageResult(
            finding_id=finding.get("id", "unknown"),
            route="jade",
            rank=rank,
            handler="advisory_engine",
            enrichment=enrichment,
            confidence=confidence,
        )

    def _route_to_human(self, finding: Dict, rank: str) -> TriageResult:
        """Route B/S-rank finding to human dashboard queue."""
        logger.info(
            "Routing %s to human dashboard (rank=%s, severity=%s)",
            finding.get("id"), rank, finding.get("severity"),
        )

        return TriageResult(
            finding_id=finding.get("id", "unknown"),
            route="human_dashboard",
            rank=rank,
            handler="human_review_queue",
            enrichment={
                "title": finding.get("title", ""),
                "severity": finding.get("severity", "UNKNOWN"),
                "scanner": finding.get("scanner", "unknown"),
                "resource": finding.get("resource", "unknown"),
                "description": finding.get("description", "")[:500],
            },
            confidence=1.0,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_rank(self, finding: Dict, classification: Optional[Dict]) -> str:
        """Extract rank from classification or finding."""
        if classification:
            rank = classification.get("rank")
            if rank:
                return rank.value if hasattr(rank, "value") else str(rank)
        return finding.get("rank", "C")

    def _get_confidence(self, classification: Optional[Dict]) -> float:
        if classification:
            return classification.get("confidence", 0.8)
        return 0.8

    def _fingerprint(self, finding: Dict) -> str:
        """Generate deduplication fingerprint for a finding.

        Two findings are duplicates if they target the same resource
        with the same issue, regardless of which scanner found them.
        """
        parts = [
            finding.get("title", "").lower().strip(),
            finding.get("resource", "").lower().strip(),
            finding.get("severity", "").upper(),
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _build_rag_query(self, finding: Dict) -> str:
        """Build a RAG query from a finding or operational event.

        Constructs a search query that retrieves relevant past fixes,
        scanner rule explanations, and playbook steps from ChromaDB.
        """
        parts = []

        # Title/message is the primary search signal
        title = finding.get("title") or finding.get("message", "")
        if title:
            parts.append(title)

        # For operational events, include the reason (CrashLoopBackOff, OOMKilled, etc.)
        reason = finding.get("reason", "")
        if reason and reason not in title:
            parts.append(reason)

        # Scanner + rule_id helps retrieve exact rule documentation
        scanner = finding.get("scanner") or finding.get("source", "")
        rule_id = finding.get("rule_id", "")
        if scanner:
            parts.append(scanner)
        if rule_id:
            parts.append(rule_id)

        # Description adds context for ambiguous titles
        description = finding.get("description", "")
        if description and len(description) < 200:
            parts.append(description)

        return " ".join(parts)

    def _match_runbook_handler(self, finding: Dict) -> str:
        """Match finding to a runbook handler by scanner, rule_id, or event reason."""
        scanner = (finding.get("scanner") or finding.get("source", "")).lower()
        rule_id = (finding.get("rule_id") or "").lower().replace("_", "-")
        reason = (finding.get("reason") or "").lower()

        # Check scanner/source first
        if scanner in _RUNBOOK_HANDLERS:
            return _RUNBOOK_HANDLERS[scanner]

        # Check event reason (operational events: CrashLoopBackOff, OPA deny, etc.)
        if reason:
            for pattern, handler in _RUNBOOK_HANDLERS.items():
                if pattern in reason:
                    return handler

        # Check rule_id substring matches
        for pattern, handler in _RUNBOOK_HANDLERS.items():
            if pattern in rule_id:
                return handler

        # Check title for admission deny patterns
        title = (finding.get("title") or "").lower()
        if "denied" in title or "violated" in title or "forbidden" in title:
            for pattern, handler in _RUNBOOK_HANDLERS.items():
                if pattern.startswith("deny:") and pattern.split(":", 1)[1] in title:
                    return handler

        return "generic_fixer"

    def _llm_route(self, finding: Dict) -> str:
        """Use Katie LLM (3B) to determine handler for ambiguous findings.

        Only called when confidence < 0.6 and no pattern match.
        """
        try:
            import requests

            prompt = (
                f"Classify this security finding into ONE handler category.\n\n"
                f"Finding: {finding.get('title', '')}\n"
                f"Scanner: {finding.get('scanner', 'unknown')}\n"
                f"Severity: {finding.get('severity', 'MEDIUM')}\n\n"
                f"Categories: k8s_security_fixer, sast_fixer, dependency_updater, "
                f"secret_rotation_handler, dockerfile_fixer, network_policy_fixer, "
                f"resource_limits_fixer, generic_fixer\n\n"
                f"Reply with ONLY the category name."
            )

            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.katie_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 30},
                },
                timeout=15,
            )

            if resp.status_code == 200:
                answer = resp.json().get("response", "").strip().lower()
                # Validate the answer is a known handler
                known = {v for v in _RUNBOOK_HANDLERS.values()}
                known.add("generic_fixer")
                if answer in known:
                    self.metrics.llm_calls += 1
                    logger.info("Katie LLM routed to: %s", answer)
                    return answer

        except Exception as e:
            logger.warning("Katie LLM routing failed: %s", e)

        return "generic_fixer"


if __name__ == "__main__":
    router = TriageRouter()

    test_findings = [
        # Scanner findings (original)
        {"id": "f-001", "title": "Container running as root", "severity": "HIGH",
         "scanner": "kubescape", "rule_id": "C-0013", "rank": "D", "resource": "Deployment/web"},
        {"id": "f-002", "title": "Container running as root", "severity": "HIGH",
         "scanner": "polaris", "rule_id": "run-as-root", "rank": "D", "resource": "Deployment/web"},
        {"id": "f-003", "title": "Missing network policy", "severity": "MEDIUM",
         "scanner": "checkov", "rule_id": "CKV_K8S_28", "rank": "C", "resource": "Namespace/prod"},
        {"id": "f-004", "title": "IAM wildcard permission", "severity": "HIGH",
         "scanner": "prowler", "rule_id": "iam-wildcard", "rank": "B"},
        {"id": "f-005", "title": "CVE-2024-1234 in openssl", "severity": "CRITICAL",
         "scanner": "trivy", "rule_id": "CVE-2024-1234", "rank": "D"},

        # Operational events (new)
        {"id": "o-001", "title": "Pod api-7f restarting", "source": "kubectl-events",
         "reason": "CrashLoopBackOff", "rank": "C", "kind": "Pod", "namespace": "payments"},
        {"id": "o-002", "title": "Failed to pull image registry.io/app:v2",
         "source": "kubectl-events", "reason": "ImagePullBackOff", "rank": "E"},
        {"id": "o-003", "title": "Denied by run-as-root policy",
         "source": "opa-gatekeeper", "reason": "denied", "rank": "D",
         "description": "container must not run as root, denied by run-as-root"},
        {"id": "o-004", "title": "Application portfolio-api OutOfSync",
         "source": "argocd", "reason": "OutOfSync", "rank": "C"},
        {"id": "o-005", "title": "Node ip-10-0-1-42 NotReady",
         "source": "kubectl-events", "reason": "NodeNotReady", "rank": "B"},
    ]

    print("=" * 60)
    print("TriageRouter (Katie) Test")
    print("=" * 60)

    for f in test_findings:
        result = router.triage(f)
        dedup = " [DEDUP]" if result.deduplicated else ""
        print(f"\n{f['id']}: {f['title']}")
        print(f"  Route: {result.route} -> {result.handler}{dedup}")
        print(f"  Rank: {result.rank} | Confidence: {result.confidence}")
        if result.enrichment:
            print(f"  Enrichment: {list(result.enrichment.keys())}")

    print(f"\n{'='*60}")
    print(f"Metrics: {router.get_metrics()}")
