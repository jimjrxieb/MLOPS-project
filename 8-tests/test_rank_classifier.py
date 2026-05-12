"""
test_rank_classifier.py — Validates RANK-AI classification logic.

Tests both scanner findings and operational K8s events against expected ranks.
These are deterministic tests — no LLM needed, no Ollama needed.

Run: python3 -m pytest 8-tests/test_rank_classifier.py -v
"""

import sys
from pathlib import Path

import pytest

# Add RANK-AI to path
RANK_AI_PATH = Path(__file__).resolve().parent.parent / "RANK-AI"
sys.path.insert(0, str(RANK_AI_PATH))

from rank_classifier import RankClassifier, Rank


@pytest.fixture(scope="module")
def classifier():
    return RankClassifier()


class TestScannerFindings:
    """Scanner findings should classify correctly by rule ID and scanner."""

    def test_gitleaks_is_d_rank(self, classifier):
        result = classifier.classify({
            "scanner": "gitleaks", "rule_id": "generic-api-key",
            "severity": "HIGH", "title": "API key in source"
        })
        assert result.rank == Rank.D

    def test_trivy_cve_with_fix_is_d_rank(self, classifier):
        result = classifier.classify({
            "scanner": "trivy", "rule_id": "CVE-2024-1234",
            "severity": "CRITICAL", "title": "Vulnerable package",
            "fixed_version": "2.0.1"
        })
        assert result.rank == Rank.D

    def test_checkov_k8s_is_d_rank(self, classifier):
        result = classifier.classify({
            "scanner": "checkov", "rule_id": "CKV_K8S_22",
            "severity": "MEDIUM", "title": "Missing readOnlyRootFilesystem"
        })
        assert result.rank == Rank.D

    def test_prowler_iam_wildcard_is_b_rank(self, classifier):
        result = classifier.classify({
            "scanner": "prowler", "rule_id": "iam-wildcard",
            "severity": "HIGH", "title": "IAM policy too permissive"
        })
        assert result.rank == Rank.B

    def test_log4shell_is_s_rank(self, classifier):
        result = classifier.classify({
            "scanner": "trivy", "rule_id": "CVE-2021-44228",
            "severity": "CRITICAL", "title": "Log4Shell"
        })
        assert result.rank == Rank.S

    def test_hadolint_is_e_rank(self, classifier):
        result = classifier.classify({
            "scanner": "hadolint", "rule_id": "DL3002",
            "severity": "LOW", "title": "Last USER should not be root"
        })
        assert result.rank == Rank.E

    def test_tfsec_is_c_rank(self, classifier):
        result = classifier.classify({
            "scanner": "tfsec", "rule_id": "aws-s3-no-encryption",
            "severity": "HIGH", "title": "S3 bucket without encryption"
        })
        assert result.rank == Rank.C

    def test_unknown_defaults_to_c_rank(self, classifier):
        result = classifier.classify({
            "scanner": "unknown-scanner", "rule_id": "",
            "severity": "MEDIUM", "title": "Something weird happened"
        })
        assert result.rank == Rank.C


class TestOperationalEvents:
    """K8s operational events should classify by fix complexity."""

    def test_crashloopbackoff_is_c_rank(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "CrashLoopBackOff",
            "title": "Pod payments/api-7f restarting"
        })
        assert result.rank == Rank.C

    def test_oomkilled_is_c_rank(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "OOMKilled",
            "title": "Container killed: memory limit exceeded"
        })
        assert result.rank == Rank.C

    def test_imagepullbackoff_is_e_rank(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "ImagePullBackOff",
            "title": "Failed to pull image registry.io/app:v2"
        })
        assert result.rank == Rank.E

    def test_failedmount_is_d_rank(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "FailedMount",
            "title": "MountVolume.SetUp failed: configmap not found"
        })
        assert result.rank == Rank.D

    def test_node_notready_is_b_rank(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "NodeNotReady",
            "title": "Node ip-10-0-1-42 NotReady"
        })
        assert result.rank == Rank.B

    def test_control_plane_down_is_s_rank(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "control-plane:unreachable",
            "title": "API server not responding"
        })
        assert result.rank == Rank.S


class TestArgoCD:
    """ArgoCD events should classify correctly."""

    def test_argocd_outofsync_is_c_rank(self, classifier):
        result = classifier.classify({
            "source": "argocd", "sync_status": "OutOfSync",
            "health_status": "Degraded",
            "title": "Application portfolio-api OutOfSync"
        })
        assert result.rank == Rank.C

    def test_argocd_syncfailed_is_c_rank(self, classifier):
        result = classifier.classify({
            "source": "argocd", "sync_status": "SyncFailed",
            "title": "Sync failed on portfolio-api"
        })
        assert result.rank == Rank.C

    def test_argocd_sync_loop_is_b_rank(self, classifier):
        result = classifier.classify({
            "source": "argocd", "reason": "argocd:sync-loop",
            "title": "Infinite sync loop on security-policies"
        })
        assert result.rank == Rank.B


class TestAdmissionDenies:
    """OPA/Kyverno/PSA denies should classify correctly."""

    def test_opa_deny_run_as_root_is_d_rank(self, classifier):
        result = classifier.classify({
            "source": "opa-gatekeeper", "reason": "denied",
            "title": "Container must not run as root",
            "description": "denied by run-as-root policy"
        })
        assert result.rank == Rank.D

    def test_generic_admission_deny_is_d_rank(self, classifier):
        result = classifier.classify({
            "source": "kyverno",
            "title": "Admission webhook denied: some policy violated",
            "description": "blocked by validation policy"
        })
        assert result.rank == Rank.D

    def test_readonly_rootfs_deny_is_c_rank(self, classifier):
        """readOnlyRootFilesystem deny needs multi-step fix (emptyDir volumes)."""
        result = classifier.classify({
            "source": "kyverno", "reason": "deny:readonlyrootfilesystem",
            "title": "Container must have readOnlyRootFilesystem"
        })
        assert result.rank == Rank.C


class TestClassificationMetadata:
    """Classification results should have correct metadata."""

    def test_e_rank_is_auto_fixable(self, classifier):
        result = classifier.classify({
            "scanner": "hadolint", "rule_id": "DL3002",
            "severity": "LOW", "title": "test"
        })
        assert result.auto_fixable is True
        assert result.requires_approval is False
        assert result.escalate is False
        assert result.suggested_action == "auto_fix"

    def test_c_rank_requires_approval(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "CrashLoopBackOff",
            "title": "Pod crashing"
        })
        assert result.requires_approval is True
        assert result.suggested_action == "request_approval"

    def test_b_rank_escalates(self, classifier):
        result = classifier.classify({
            "source": "kubectl-events", "reason": "NodeNotReady",
            "title": "Node down"
        })
        assert result.escalate is True
        assert result.suggested_action == "escalate"

    def test_confidence_is_valid_range(self, classifier):
        result = classifier.classify({
            "scanner": "trivy", "rule_id": "CVE-2024-1234",
            "severity": "HIGH", "title": "test"
        })
        assert 0.0 <= result.confidence <= 1.0
