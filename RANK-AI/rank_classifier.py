"""
RankClassifier - Unified Rank Classification System
===================================================
Single source of truth for E/D/C/B/S rank classification.

Consolidated from:
- GP-CONSULTING/3-Runtime-Scans-NPC/rank_classifier.py (production)
- GP-BEDROCK-AGENTS/shared/permissions/rank.py (simpler)

Classification strategy (in order):
1. Rule ID pattern matching (highest priority)
2. Scanner base rank lookup
3. Text pattern fallback (title/description)
4. JADE fallback for ambiguous C-rank (optional)
5. Default to C-rank (safe)
"""

import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Rank(Enum):
    """Automation rank levels"""
    E = "E"  # 95-100% automated - trivial fixes
    D = "D"  # 70-90% automated - standard fixes
    C = "C"  # 40-70% automated - needs approval
    B = "B"  # 20-40% automated - escalate
    S = "S"  # 0-5% automated - escalate


@dataclass
class ConfidenceFactors:
    """
    Honest breakdown of confidence calculation.

    Instead of a single magic number, we track WHY we're confident (or not).
    This enables:
    1. Debugging: See exactly what contributed to the score
    2. Training: Use factors as features for ML model
    3. Calibration: Adjust weights based on historical accuracy
    """
    # Source-based confidence (how we matched)
    source_type: str = "unknown"  # rule_override, scanner, text_pattern, jade, default
    source_base_confidence: float = 0.5

    # Pattern specificity (how precise was the match)
    pattern_matched: str = ""
    pattern_is_exact: bool = False  # Exact match vs substring
    pattern_specificity_bonus: float = 0.0  # +0.1 for exact, +0.05 for specific substring

    # Historical calibration (future: from feedback data)
    historical_accuracy: Optional[float] = None  # None = no data yet
    historical_sample_size: int = 0

    # Uncertainty flags
    is_novel_pattern: bool = False  # Never seen this exact pattern before
    multiple_matches: bool = False  # Multiple patterns matched (conflicting signals)
    severity_mismatch: bool = False  # Severity doesn't match expected for rank

    def compute_final(self) -> float:
        """
        Compute final confidence from factors.

        Formula:
        - Start with source base confidence
        - Add pattern specificity bonus
        - If we have historical data, weight toward that
        - Apply uncertainty penalties
        """
        confidence = self.source_base_confidence + self.pattern_specificity_bonus

        # Historical calibration (when we have feedback data)
        if self.historical_accuracy is not None and self.historical_sample_size >= 10:
            # Blend: weight historical more as sample size grows
            weight = min(0.7, self.historical_sample_size / 100)
            confidence = (1 - weight) * confidence + weight * self.historical_accuracy

        # Uncertainty penalties
        if self.is_novel_pattern:
            confidence *= 0.9  # 10% penalty for never-seen patterns
        if self.multiple_matches:
            confidence *= 0.85  # 15% penalty for conflicting signals
        if self.severity_mismatch:
            confidence *= 0.95  # 5% penalty for severity mismatch

        return round(max(0.1, min(0.99, confidence)), 2)


@dataclass
class ClassificationResult:
    """Result of rank classification"""
    rank: Rank
    confidence: float  # 0.0 to 1.0 (computed from factors)
    reason: str
    auto_fixable: bool
    requires_approval: bool
    escalate: bool
    suggested_action: str  # "auto_fix", "request_approval", "escalate"
    fix_complexity: str  # "trivial", "simple", "moderate", "complex", "architectural"

    # Track classification source for debugging/training
    classification_source: str = field(default="unknown")

    # Honest confidence breakdown (new!)
    confidence_factors: Optional[ConfidenceFactors] = field(default=None)


class RankClassifier:
    """
    Classify security findings into E/D/C/B/S ranks.

    Uses a tiered approach:
    1. Rule ID overrides (most specific)
    2. Scanner base ranks (tool-specific)
    3. Text pattern matching (fallback)
    4. JADE LLM for ambiguous cases (optional)
    5. Safe default to C-rank
    """

    # ================================================================
    # OPERATIONAL EVENT CLASSIFICATION (K8s runtime, not just scans)
    # ================================================================
    # These classify by WHAT HAPPENED, not who found it.
    # Source: kubectl events, OPA/Gatekeeper denies, ArgoCD status,
    # k8sgpt analysis, pod logs, node conditions.
    #
    # Ranked by fix complexity from a platform engineer's POV:
    #   E = one command, zero diagnosis
    #   D = known fix, <3 steps, single resource
    #   C = multi-step diagnosis, or affects multiple resources
    #   B = cross-namespace/cluster impact, blast radius assessment needed
    #   S = architectural, irreversible, or active incident
    # ================================================================

    # Source → base rank for operational event sources
    OPERATIONAL_SOURCE_RANKS = {
        "kubectl-events": Rank.C,     # Events need diagnosis — default C
        "k8sgpt": Rank.C,             # k8sgpt findings need diagnosis
        "kubectl-ai": Rank.C,         # kubectl-ai suggestions need review
        "argocd": Rank.C,             # Sync issues need investigation
        "opa-gatekeeper": Rank.D,     # Deny = fix the manifest
        "kyverno": Rank.D,            # Deny = fix the manifest
        "falco": Rank.C,              # Runtime alert = investigate
        "prometheus-alert": Rank.C,   # Alert = diagnose
        "pod-log": Rank.C,            # Log error = diagnose
        "node-condition": Rank.B,     # Node issues = blast radius
    }

    # Operational event patterns → Rank (matched against event reason/message)
    # These override OPERATIONAL_SOURCE_RANKS when matched
    OPERATIONAL_PATTERNS = {
        # ── E-Rank: One command, zero diagnosis ──────────────────
        "ImagePullBackOff": Rank.E,           # Fix image tag or pull secret
        "ErrImagePull": Rank.E,               # Same — image ref is wrong
        "InvalidImageName": Rank.E,           # Typo in image name
        "FailedScheduling:insufficient cpu": Rank.E,  # Scale nodes or reduce requests
        "FailedScheduling:insufficient memory": Rank.E,

        # ── D-Rank: Known fix, <3 steps, single resource ────────
        "CreateContainerConfigError": Rank.D, # Missing ConfigMap/Secret ref
        "FailedMount": Rank.D,                # Volume mount issue — check PVC/ConfigMap
        "FailedAttachVolume": Rank.D,         # PVC not bound or wrong storage class
        "BackOff:restarting": Rank.D,         # Container restarting — check logs + limits
        "Unhealthy:readiness": Rank.D,        # Readiness probe failing — check endpoint/port
        "Unhealthy:liveness": Rank.D,         # Liveness probe failing — check config
        "Unhealthy:startup": Rank.D,          # Startup probe — increase timeout or fix app
        "FailedCreate:quota": Rank.D,         # ResourceQuota exceeded — adjust or request
        "forbidden:SecurityContext": Rank.D,  # PSA/PSS violation — add security context

        # ── D-Rank: Admission controller denies (fix the manifest) ──
        "deny:privileged": Rank.D,            # OPA/Kyverno denied privileged container
        "deny:host-namespace": Rank.D,        # Denied host PID/Network/IPC
        "deny:latest-tag": Rank.D,            # Denied :latest image tag
        "deny:missing-limits": Rank.D,        # Denied missing resource limits
        "deny:run-as-root": Rank.D,           # Denied running as root
        "deny:capabilities": Rank.D,          # Denied dangerous capabilities
        "deny:no-seccomp": Rank.D,            # Denied missing seccomp profile
        "deny:no-readonly-root": Rank.D,      # Denied missing readOnlyRootFilesystem

        # ── C-Rank: Multi-step diagnosis, or multi-resource fix ──
        "CrashLoopBackOff": Rank.C,           # Could be OOM, bad config, app bug, missing dep
        "OOMKilled": Rank.C,                  # Check actual usage → right-size → verify
        "Evicted": Rank.C,                    # Node pressure — check which, relocate workload
        "DeadlineExceeded": Rank.C,           # Job timeout — check resources + logic
        "FailedScheduling:taint": Rank.C,     # Toleration/affinity mismatch — cluster topology
        "FailedScheduling:pvc": Rank.C,       # PVC in wrong AZ or storage class issue
        "dns:resolution-failed": Rank.C,      # CoreDNS issue or service name wrong
        "connection-refused": Rank.C,         # Service up but app not listening — check ports
        "5xx:upstream": Rank.C,               # Ingress/Gateway → backend failing
        "cert-expired": Rank.C,               # TLS cert rotation needed
        "secret-rotation-due": Rank.C,        # External secret needs rotation

        # ── C-Rank: ArgoCD operational issues ────────────────────
        "argocd:OutOfSync": Rank.C,           # Drift detected — investigate what changed
        "argocd:SyncFailed": Rank.C,          # Sync broke — check manifests + hooks
        "argocd:Degraded": Rank.C,            # App unhealthy after sync
        "argocd:ComparisonError": Rank.C,     # Manifest parse error
        "argocd:sync-loop": Rank.B,           # Infinite sync = mutation/webhook conflict

        # ── C-Rank: Admission denies that need investigation ─────
        "deny:readonlyrootfilesystem": Rank.C,  # Needs emptyDir mounts (multi-step)
        "deny:network-policy-required": Rank.C, # Need to write + test NetworkPolicy
        "deny:seccomp-strict": Rank.C,          # Need to profile + apply seccomp

        # ── B-Rank: Cross-namespace/cluster, blast radius ────────
        "NodeNotReady": Rank.B,               # Node-level — affects all pods on node
        "NodePressure:disk": Rank.B,          # Node disk — could cascade
        "NodePressure:memory": Rank.B,        # Node memory — OOM killer risk
        "NodePressure:pid": Rank.B,           # PID exhaustion — process leak
        "CordonNode": Rank.B,                 # Intentional drain — verify workload migration
        "NetworkPartition": Rank.B,           # CNI issue — cluster-wide impact
        "karpenter:provisioning-failed": Rank.B,  # Can't scale — capacity issue
        "rbac:cluster-admin-binding": Rank.B,     # Overprivileged — audit blast radius
        "rbac:wildcard-permission": Rank.B,       # Same
        "admission-webhook-timeout": Rank.B,      # Webhook down = all deploys blocked
        "PDB:violation": Rank.B,                  # Disrupting protected workload

        # ── S-Rank: Architectural, irreversible, active incident ─
        "etcd:corruption": Rank.S,            # Data store damaged
        "etcd:quorum-lost": Rank.S,           # Cluster brain-dead
        "control-plane:unreachable": Rank.S,  # API server down
        "cluster-upgrade-failed": Rank.S,     # Partial upgrade state
        "cve:active-exploit": Rank.S,         # Known exploited vulnerability
        "data-loss": Rank.S,                  # PVC deleted or corrupted
        "breach:detected": Rank.S,            # Security incident
    }

    # Scanner → Base Rank mapping
    # Updated January 2026 based on JSA agent specialties
    SCANNER_BASE_RANKS = {
        # E-Rank (trivial formatting/linting)
        "eslint": Rank.E,
        "hadolint": Rank.E,
        "prettier": Rank.E,
        "black": Rank.E,
        "isort": Rank.E,

        # D-Rank - jsa-ci specialties (CI/CD, SAST, dependencies)
        "bandit": Rank.D,
        "semgrep": Rank.D,
        "trivy": Rank.D,
        "grype": Rank.D,
        "snyk": Rank.D,
        "gitleaks": Rank.D,
        "gha": Rank.D,

        # D-Rank - jsa-devsecops specialties (K8s security)
        "checkov": Rank.D,
        "polaris": Rank.D,
        "kubescape": Rank.D,
        "kube-bench": Rank.D,
        "conftest": Rank.D,

        # C-Rank (infrastructure changes need approval)
        "tfsec": Rank.C,
        "helm": Rank.C,

        # B-Rank (org-wide impact)
        "prowler": Rank.B,

        # CI/CD integration scanners (external API sources)
        "sonarcloud": Rank.D,
        "github-code-scanning": Rank.D,
        "github-dependabot": Rank.D,
        "github-secret-scanning": Rank.C,  # Leaked secrets = higher rank
        "sarif-codeql": Rank.D,
        "sarif-checkov": Rank.D,
        "sarif-semgrep": Rank.D,
        "sarif-tfsec": Rank.C,
        "sarif-trivy": Rank.D,
        "sarif-bandit": Rank.D,
        "sarif-generic": Rank.D,
    }

    # Rule ID patterns → Rank overrides (substring matching)
    RULE_RANK_OVERRIDES = {
        # E-Rank (trivial)
        "no-unused-vars": Rank.E,
        "semi": Rank.E,
        "indent": Rank.E,
        "quotes": Rank.E,
        "formatting": Rank.E,

        # D-Rank - K8s checks (CKA/CKS level)
        "ckv-k8s": Rank.D,
        "ckv_k8s": Rank.D,
        "c-00": Rank.D,  # Kubescape
        "deny-": Rank.D,  # OPA deny patterns
        "missing-resource-limits": Rank.D,
        "run-as-root": Rank.D,
        "privileged-container": Rank.D,
        "readonlyrootfilesystem": Rank.D,
        "host-network": Rank.D,
        "capability": Rank.D,
        "seccomp": Rank.D,

        # D-Rank - SAST/secrets
        "hardcoded-secret": Rank.D,
        "hardcoded-password": Rank.D,
        "hardcoded-api-key": Rank.D,
        "hardcoded-token": Rank.D,
        "generic-api-key": Rank.D,
        "sql-injection": Rank.D,
        "xss": Rank.D,
        "command-injection": Rank.D,
        "subprocess": Rank.D,
        "b6": Rank.D,  # Bandit B6XX
        "cve-": Rank.D,
        "ghsa-": Rank.D,

        # D-Rank - GHA/CI security (auto-fixable)
        "gha/unpinned": Rank.D,
        "gha/hardcoded": Rank.D,
        "gha/excessive": Rank.D,

        # C-Rank - GHA needs review
        "gha/artifact-poisoning": Rank.C,

        # B-Rank - GHA dangerous patterns
        "gha/pwn-request": Rank.B,

        # C-Rank (IaC/cloud changes)
        "ckv-aws": Rank.C,
        "ckv_aws": Rank.C,
        "ckv-gcp": Rank.C,
        "ckv-azure": Rank.C,
        "terraform-": Rank.C,
        "avd-aws": Rank.C,    # Trivy IaC: AWS misconfigs
        "avd-gcp": Rank.C,    # Trivy IaC: GCP misconfigs
        "avd-azure": Rank.C,  # Trivy IaC: Azure misconfigs
        "avd-": Rank.C,       # Trivy IaC: all other cloud misconfigs
        "helm-": Rank.C,

        # B-Rank (architecture)
        "iam-wildcard": Rank.B,
        "cluster-admin": Rank.B,
        "compliance-gap": Rank.B,
        "vpc-": Rank.B,

        # S-Rank (escalate immediately)
        "aws-root": Rank.S,
        "cve-2021-44228": Rank.S,  # Log4Shell
        "cisa-kev": Rank.S,
        "active-exploit": Rank.S,
    }

    # Text pattern matching (from simpler classifier)
    # Used when rule_id and scanner don't give clear signal
    TEXT_PATTERNS = {
        Rank.E: [
            ("secret", "api_key"),
            ("resource", "limit"),
            ("http:", "https"),
        ],
        Rank.D: [
            ("sql injection",),
            ("sqli",),
            ("xss",),
            ("cross-site scripting",),
            ("dependency", "vulnerable"),
            ("upgrade", "available"),
        ],
        Rank.C: [
            ("network", "policy"),
            ("rbac",),
            ("role", "permission"),
            ("gatekeeper",),
            ("constraint",),
        ],
        Rank.B: [
            ("architecture",),
            ("service mesh",),
            ("zero-trust",),
            ("vault",),
            ("soc2",),
            ("pci",),
            ("hipaa",),
        ],
    }

    # Automation percentages by rank (for reporting)
    AUTOMATION_PERCENTAGES = {
        Rank.E: 0.975,  # 95-100%
        Rank.D: 0.80,   # 70-90%
        Rank.C: 0.55,   # 40-70%
        Rank.B: 0.30,   # 20-40%
        Rank.S: 0.025,  # 0-5%
    }

    def __init__(
        self,
        jade_model: str = "jade:v1.0",
        use_jade_fallback: bool = False,
        feedback_dir: Optional[Path] = None
    ):
        """
        Initialize RankClassifier.

        Args:
            jade_model: Ollama model for JADE fallback
            use_jade_fallback: Whether to use JADE for ambiguous C-rank cases
            feedback_dir: Path to feedback directory containing decisions.jsonl
                         If provided, historical accuracy is loaded to improve confidence
        """
        self.jade_model = jade_model
        self.use_jade_fallback = use_jade_fallback
        self.feedback_dir = Path(feedback_dir) if feedback_dir else None

        # Historical accuracy cache: {(pattern, rank): (accuracy, sample_size)}
        self.accuracy_cache: Dict[Tuple[str, str], Tuple[float, int]] = {}

        # Load historical accuracy if feedback dir provided
        if self.feedback_dir:
            self._load_historical_accuracy()

    def classify(self, finding: Dict[str, Any]) -> ClassificationResult:
        """
        Classify a security finding OR operational event into E/D/C/B/S rank.

        Accepts both scanner findings and K8s operational events.

        Args:
            finding: Dict with keys (not all required):
                Scanner findings:
                - scanner: Which tool found it (trivy, kubescape, etc.)
                - rule_id: The rule that triggered
                - severity: CRITICAL/HIGH/MEDIUM/LOW
                - title/message: Finding title
                - description: What's wrong

                Operational events:
                - source: Event source (kubectl-events, argocd, k8sgpt, etc.)
                - reason: K8s event reason (CrashLoopBackOff, OOMKilled, etc.)
                - kind: Resource kind (Pod, Node, Deployment, etc.)
                - namespace: Affected namespace
                - name: Resource name

        Returns:
            ClassificationResult with rank and metadata
        """
        # Normalize scanner name
        scanner_raw = finding.get("scanner") or finding.get("source_scanner") or finding.get("source", "unknown")
        scanner = scanner_raw.lower().replace("npc", "").strip()

        # Normalize rule_id
        rule_id = finding.get("rule_id", "").lower().replace("_", "-")

        # Get title, description, and event reason
        title = finding.get("title") or finding.get("message", "")
        description = finding.get("description", "")
        reason = finding.get("reason", "")
        text = f"{title} {description} {reason}".lower()

        # Step 0: Check operational event patterns (K8s runtime events)
        # This catches CrashLoopBackOff, OOMKilled, ArgoCD sync issues, OPA denies, etc.
        result = self._check_operational_patterns(finding, text)
        if result:
            return result

        # Step 1: Check rule ID overrides (highest priority for scan findings)
        result = self._check_rule_overrides(rule_id, finding)
        if result:
            return result

        # Step 2: Check if auto-fixable dependency CVE
        if self._is_auto_fixable_dependency(scanner, finding):
            return self._build_result(
                Rank.D, 0.9,
                f"Dependency CVE with fix: {finding.get('fixed_version', 'available')}",
                finding,
                source="dependency_fix"
            )

        # Step 3: Get base rank from scanner or operational source
        if scanner in self.OPERATIONAL_SOURCE_RANKS:
            base_rank = self.OPERATIONAL_SOURCE_RANKS[scanner]
            result = self._build_result(
                base_rank, 0.7,
                f"Operational source base rank: {scanner}",
                finding,
                source="operational_source"
            )
        elif scanner in self.SCANNER_BASE_RANKS:
            base_rank = self.SCANNER_BASE_RANKS[scanner]
            result = self._build_result(
                base_rank, 0.8,
                f"Scanner base rank: {scanner}",
                finding,
                source="scanner"
            )
            # Don't return yet - check if text patterns suggest different rank
        else:
            base_rank = None

        # Step 4: Text pattern matching (fallback or override)
        pattern_rank = self._check_text_patterns(text)
        if pattern_rank:
            # If we had a base rank, only override if pattern rank is more severe
            if base_rank is None or self._rank_priority(pattern_rank) > self._rank_priority(base_rank):
                return self._build_result(
                    pattern_rank, 0.7,
                    f"Text pattern match in: {title[:50]}",
                    finding,
                    source="text_pattern"
                )

        # If we found a scanner-based rank, use it
        if base_rank:
            return self._build_result(
                base_rank, 0.75,
                f"Scanner base rank: {scanner}",
                finding,
                source="scanner"
            )

        # Step 5: JADE fallback for ambiguous cases
        if self.use_jade_fallback:
            jade_rank, jade_confidence = self._jade_classify(finding)
            if jade_confidence > 0.6:
                return self._build_result(
                    jade_rank, jade_confidence,
                    f"JADE classified ({jade_confidence:.0%})",
                    finding,
                    source="jade"
                )

        # Step 6: Default to C-rank (safe - requires approval)
        return self._build_result(
            Rank.C, 0.5,
            "Unknown pattern, defaulting to approval-required",
            finding,
            source="default"
        )

    def classify_batch(self, findings: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """Classify multiple findings."""
        return [self.classify(f) for f in findings]

    def _check_rule_overrides(self, rule_id: str, finding: Dict) -> Optional[ClassificationResult]:
        """Check if rule has a specific rank override.

        Checks longer (more specific) patterns first so that
        'cve-2021-44228' (S-rank) matches before 'cve-' (D-rank).
        """
        for pattern, rank in sorted(self.RULE_RANK_OVERRIDES.items(), key=lambda x: len(x[0]), reverse=True):
            if pattern in rule_id:
                # Determine if exact match vs substring
                is_exact = (pattern == rule_id)
                specificity_bonus = 0.1 if is_exact else 0.05

                # Get historical accuracy for this pattern/rank
                hist_accuracy, hist_samples = self._get_historical_accuracy(rule_id, rank)

                factors = ConfidenceFactors(
                    source_type="rule_override",
                    source_base_confidence=0.85,  # High confidence for rule matches
                    pattern_matched=pattern,
                    pattern_is_exact=is_exact,
                    pattern_specificity_bonus=specificity_bonus,
                    historical_accuracy=hist_accuracy,
                    historical_sample_size=hist_samples,
                )

                return self._build_result(
                    rank,
                    factors.compute_final(),
                    f"Rule override: {pattern}" + (" (exact)" if is_exact else ""),
                    finding,
                    source="rule_override",
                    factors=factors
                )
        return None

    def _check_operational_patterns(self, finding: Dict, text: str) -> Optional[ClassificationResult]:
        """
        Check if this is a K8s operational event (not a scan finding).

        Matches event reason, message text, and source against OPERATIONAL_PATTERNS.
        This is what lets the classifier handle CrashLoopBackOff, OPA denies,
        ArgoCD sync failures, node conditions, etc.
        """
        reason = finding.get("reason", "")
        source = finding.get("source", "")
        kind = finding.get("kind", "")

        # Direct reason match (highest confidence)
        for pattern, rank in self.OPERATIONAL_PATTERNS.items():
            # Check against event reason
            if reason and pattern.lower() in reason.lower():
                return self._build_result(
                    rank, 0.90,
                    f"Operational event: {reason} (pattern: {pattern})",
                    finding,
                    source="operational_pattern"
                )
            # Check against text (title + description + reason combined)
            if pattern.lower() in text:
                return self._build_result(
                    rank, 0.85,
                    f"Operational pattern in text: {pattern}",
                    finding,
                    source="operational_pattern"
                )

        # ArgoCD-specific: check for sync status in structured data
        sync_status = finding.get("sync_status") or finding.get("syncStatus", "")
        health_status = finding.get("health_status") or finding.get("healthStatus", "")
        if sync_status:
            argocd_key = f"argocd:{sync_status}"
            if argocd_key in self.OPERATIONAL_PATTERNS:
                return self._build_result(
                    self.OPERATIONAL_PATTERNS[argocd_key], 0.90,
                    f"ArgoCD status: {sync_status} / {health_status}",
                    finding,
                    source="operational_pattern"
                )

        # OPA/Kyverno deny: check for admission deny patterns
        if any(kw in text for kw in ["denied", "violated", "blocked by", "admission webhook"]):
            # Try to match specific deny reason
            for pattern, rank in self.OPERATIONAL_PATTERNS.items():
                if pattern.startswith("deny:") and pattern.split(":", 1)[1] in text:
                    return self._build_result(
                        rank, 0.85,
                        f"Admission deny: {pattern}",
                        finding,
                        source="operational_pattern"
                    )
            # Generic admission deny — D-rank (fix the manifest)
            return self._build_result(
                Rank.D, 0.75,
                "Admission controller deny (fix manifest to comply)",
                finding,
                source="operational_pattern"
            )

        return None

    def _is_auto_fixable_dependency(self, scanner: str, finding: Dict) -> bool:
        """Check if this is a dependency CVE with an auto-fix available."""
        if scanner not in ["trivy", "grype", "snyk", "npm-audit", "pip-audit"]:
            return False
        return self._has_fix_available(finding)

    def _has_fix_available(self, finding: Dict) -> bool:
        """Check if a fix/patch is available."""
        fix_version = (
            finding.get("fixed_version") or
            finding.get("fix_version") or
            finding.get("fixed_in")
        )
        if fix_version:
            if isinstance(fix_version, list):
                return len(fix_version) > 0
            return True

        fix_suggestion = finding.get("fix_suggestion", "")
        if fix_suggestion and any(cmd in fix_suggestion.lower() for cmd in
                                   ["npm", "yarn", "pip", "go get", "upgrade", "update"]):
            return True
        return False

    def _check_text_patterns(self, text: str) -> Optional[Rank]:
        """Check text against pattern lists."""
        for rank, patterns in self.TEXT_PATTERNS.items():
            for pattern_tuple in patterns:
                if all(p in text for p in pattern_tuple):
                    return rank
        return None

    def _rank_priority(self, rank: Rank) -> int:
        """Get priority of rank (higher = more severe/urgent)."""
        priorities = {Rank.E: 1, Rank.D: 2, Rank.C: 3, Rank.B: 4, Rank.S: 5}
        return priorities.get(rank, 3)

    def _jade_classify(self, finding: Dict) -> Tuple[Rank, float]:
        """Use JADE LLM to classify ambiguous findings."""
        prompt = f"""Classify this security finding for automation level.

Finding:
- Scanner: {finding.get('scanner', 'unknown')}
- Rule: {finding.get('rule_id', 'unknown')}
- Severity: {finding.get('severity', 'unknown')}
- Description: {finding.get('description', 'No description')[:200]}

Reply with ONE letter: E, D, C, B, or S."""

        try:
            result = subprocess.run(
                ["ollama", "run", self.jade_model, prompt],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                response = result.stdout.strip().upper()
                if response in ["E", "D", "C", "B", "S"]:
                    return Rank(response), 0.75
        except Exception:
            pass

        return Rank.C, 0.5

    def _build_result(
        self,
        rank: Rank,
        confidence: float,
        reason: str,
        finding: Dict,
        source: str = "unknown",
        factors: Optional[ConfidenceFactors] = None
    ) -> ClassificationResult:
        """Build ClassificationResult from rank."""
        # If no factors provided, create default ones based on source
        if factors is None:
            source_confidence_map = {
                "rule_override": 0.85,
                "dependency_fix": 0.80,
                "scanner": 0.70,
                "text_pattern": 0.55,
                "jade": 0.60,
                "default": 0.40,
            }
            factors = ConfidenceFactors(
                source_type=source,
                source_base_confidence=source_confidence_map.get(source, 0.50),
            )
            # Use the computed confidence instead of passed-in value
            confidence = factors.compute_final()

        if rank in [Rank.E, Rank.D]:
            auto_fixable = True
            requires_approval = False
            escalate = False
            suggested_action = "auto_fix"
            fix_complexity = "trivial" if rank == Rank.E else "simple"
        elif rank == Rank.C:
            auto_fixable = True
            requires_approval = True
            escalate = False
            suggested_action = "request_approval"
            fix_complexity = "moderate"
        else:  # B or S
            auto_fixable = False
            requires_approval = False
            escalate = True
            suggested_action = "escalate"
            fix_complexity = "complex" if rank == Rank.B else "architectural"

        return ClassificationResult(
            rank=rank,
            confidence=confidence,
            reason=reason,
            auto_fixable=auto_fixable,
            requires_approval=requires_approval,
            escalate=escalate,
            suggested_action=suggested_action,
            fix_complexity=fix_complexity,
            classification_source=source,
            confidence_factors=factors,
        )

    def get_automation_percentage(self, rank: Rank) -> float:
        """Get expected automation percentage for rank."""
        return self.AUTOMATION_PERCENTAGES.get(rank, 0.5)

    def get_rank_stats(self, results: List[ClassificationResult]) -> Dict[str, int]:
        """Get count of findings by rank."""
        stats = {"E": 0, "D": 0, "C": 0, "B": 0, "S": 0}
        for r in results:
            stats[r.rank.value] += 1
        return stats

    def _load_historical_accuracy(self) -> None:
        """
        Load historical accuracy from feedback data.

        Populates self.accuracy_cache with (pattern, rank) -> (accuracy, sample_size)
        mappings computed from human feedback in decisions.jsonl.
        """
        if not self.feedback_dir:
            return

        feedback_file = self.feedback_dir / "decisions.jsonl"
        if not feedback_file.exists():
            logger.warning(f"Feedback file not found: {feedback_file}")
            return

        try:
            # Import here to avoid circular imports
            from feedback.accuracy_aggregator import AccuracyAggregator

            aggregator = AccuracyAggregator(feedback_file)
            self.accuracy_cache = aggregator.compute_all()
            logger.info(
                f"Loaded historical accuracy for {len(self.accuracy_cache)} "
                f"pattern/rank combinations"
            )
        except ImportError:
            logger.warning("Could not import accuracy_aggregator, skipping historical accuracy")
        except Exception as e:
            logger.error(f"Error loading historical accuracy: {e}")

    def reload_historical_accuracy(self) -> None:
        """
        Reload historical accuracy from feedback data.

        Call this periodically to update confidence scores as more
        human feedback is collected.
        """
        self._load_historical_accuracy()

    def _get_historical_accuracy(
        self,
        pattern: str,
        rank: Rank
    ) -> Tuple[Optional[float], int]:
        """
        Get historical accuracy for a pattern/rank combination.

        Args:
            pattern: The pattern to look up (will be normalized)
            rank: The rank to look up

        Returns:
            (accuracy, sample_size) or (None, 0) if no data
        """
        if not self.accuracy_cache:
            return None, 0

        # Normalize pattern (same logic as aggregator)
        normalized = pattern.lower().replace("_", "-")
        if "." in normalized:
            parts = normalized.split(".")
            normalized = parts[-1] if parts[-1] else parts[-2] if len(parts) > 1 else normalized

        key = (normalized, rank.value)
        return self.accuracy_cache.get(key, (None, 0))


# Convenience function for simple API
def classify_finding(
    scanner: str,
    severity: str,
    title: str,
    description: str = "",
    rule_id: str = "",
    feedback_dir: Optional[Path] = None,
    **kwargs
) -> ClassificationResult:
    """
    Convenience function for classifying a single finding.

    Allows both dict-based API and individual args.

    Args:
        scanner: Scanner name (trivy, bandit, etc.)
        severity: CRITICAL/HIGH/MEDIUM/LOW
        title: Finding title
        description: Finding description
        rule_id: Rule that triggered
        feedback_dir: Optional path to feedback dir for historical accuracy
        **kwargs: Additional finding fields
    """
    classifier = RankClassifier(use_jade_fallback=False, feedback_dir=feedback_dir)
    finding = {
        "scanner": scanner,
        "severity": severity,
        "title": title,
        "description": description,
        "rule_id": rule_id,
        **kwargs
    }
    return classifier.classify(finding)


if __name__ == "__main__":
    print("=" * 60)
    print("RankClassifier Test (Consolidated)")
    print("=" * 60)

    classifier = RankClassifier()

    # ── Scanner findings (original) ──
    test_findings = [
        {"scanner": "gitleaks", "rule_id": "generic-api-key", "severity": "HIGH",
         "title": "API key in source", "description": "Hardcoded API key detected"},
        {"scanner": "trivy", "rule_id": "CVE-2024-1234", "severity": "CRITICAL",
         "title": "Vulnerable package", "fixed_version": "2.0.1"},
        {"scanner": "checkov", "rule_id": "CKV_K8S_22", "severity": "MEDIUM",
         "title": "Container missing readOnlyRootFilesystem"},
        {"scanner": "prowler", "rule_id": "iam-wildcard", "severity": "HIGH",
         "title": "IAM policy too permissive"},
    ]

    # ── Operational events (new — K8s runtime) ──
    test_ops = [
        {"source": "kubectl-events", "reason": "CrashLoopBackOff",
         "title": "Pod payments/api-7f8b9d restarting", "kind": "Pod", "namespace": "payments"},
        {"source": "kubectl-events", "reason": "OOMKilled",
         "title": "Container killed: memory limit exceeded", "kind": "Pod"},
        {"source": "kubectl-events", "reason": "ImagePullBackOff",
         "title": "Failed to pull image: registry.io/app:v2.1", "kind": "Pod"},
        {"source": "kubectl-events", "reason": "FailedMount",
         "title": "MountVolume.SetUp failed: configmap 'app-config' not found", "kind": "Pod"},
        {"source": "argocd", "sync_status": "OutOfSync", "health_status": "Degraded",
         "title": "Application portfolio-api is OutOfSync", "kind": "Application"},
        {"source": "opa-gatekeeper", "reason": "denied",
         "title": "Admission webhook denied: container must not run as root",
         "description": "denied by run-as-root policy"},
        {"source": "kubectl-events", "reason": "NodeNotReady",
         "title": "Node ip-10-0-1-42 condition NotReady", "kind": "Node"},
        {"source": "kubectl-events", "reason": "BackOff:restarting",
         "title": "Back-off restarting failed container", "kind": "Pod"},
        {"source": "prometheus-alert", "reason": "5xx:upstream",
         "title": "Ingress returning 502 for api.example.com", "kind": "Ingress"},
        {"source": "kubectl-events", "reason": "control-plane:unreachable",
         "title": "API server not responding", "kind": "Cluster"},
    ]

    all_tests = test_findings + test_ops

    print("\n── Scanner Findings ──")
    for f in test_findings:
        result = classifier.classify(f)
        print(f"\n  {f.get('scanner', '?')}: {f.get('rule_id', f.get('reason', '?'))}")
        print(f"    Rank: {result.rank.value} | Confidence: {result.confidence:.0%} | Action: {result.suggested_action}")
        print(f"    Source: {result.classification_source}")
        print(f"    Reason: {result.reason}")

    print("\n── Operational Events ──")
    for f in test_ops:
        result = classifier.classify(f)
        reason = f.get('reason', f.get('sync_status', '?'))
        print(f"\n  {f.get('source', '?')}: {reason}")
        print(f"    Rank: {result.rank.value} | Confidence: {result.confidence:.0%} | Action: {result.suggested_action}")
        print(f"    Complexity: {result.fix_complexity}")
        print(f"    Reason: {result.reason}")

    results = classifier.classify_batch(all_tests)
    stats = classifier.get_rank_stats(results)
    print(f"\n{'=' * 60}")
    print(f"Summary ({len(all_tests)} events): {stats}")
