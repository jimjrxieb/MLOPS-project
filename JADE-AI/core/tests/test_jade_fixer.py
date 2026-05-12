"""Unit tests for JADE Fixer Engine (jade_fixer.py + jade_domains.py).

Tests domain detection, investigation, diagnosis, fix generation,
and safety limits — all with mocked LLM/RAG dependencies.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add JADE-AI/core to path
_CORE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_CORE_DIR))

from jade_domains import detect_domain, get_domain_config, DOMAINS, DEFAULT_DOMAIN
from jade_fixer import JADEFixer, InvestigationContext, Diagnosis, FixResult


# =============================================================================
# DOMAIN DETECTION TESTS
# =============================================================================

class TestDomainDetection:
    """Test detect_domain() maps findings to correct security domains."""

    def test_kubernetes_by_rule_prefix_ksv(self):
        assert detect_domain({"rule_id": "KSV011", "scanner": ""}) == "kubernetes"

    def test_kubernetes_by_rule_prefix_ckv_k8s(self):
        assert detect_domain({"rule_id": "CKV_K8S_28", "scanner": ""}) == "kubernetes"

    def test_kubernetes_by_rule_prefix_c_dash(self):
        assert detect_domain({"rule_id": "C-0013", "scanner": ""}) == "kubernetes"

    def test_kubernetes_by_scanner(self):
        assert detect_domain({"rule_id": "custom-rule", "scanner": "kubescape"}) == "kubernetes"

    def test_iac_by_rule_prefix_avd(self):
        assert detect_domain({"rule_id": "AVD-DS-0002", "scanner": ""}) == "iac"

    def test_iac_by_rule_prefix_ckv_docker(self):
        assert detect_domain({"rule_id": "CKV_DOCKER_3", "scanner": ""}) == "iac"

    def test_iac_by_scanner_checkov(self):
        assert detect_domain({"rule_id": "custom", "scanner": "checkov"}) == "iac"

    def test_cloud_by_rule_prefix_avd_aws(self):
        assert detect_domain({"rule_id": "AVD-AWS-0001", "scanner": ""}) == "cloud"

    def test_cloud_by_rule_prefix_ckv_aws(self):
        assert detect_domain({"rule_id": "CKV_AWS_18", "scanner": ""}) == "cloud"

    def test_cicd_by_rule_prefix_gha(self):
        assert detect_domain({"rule_id": "gha/unpinned-action", "scanner": ""}) == "cicd"

    def test_cicd_by_scanner(self):
        assert detect_domain({"rule_id": "custom", "scanner": "gha_scanner"}) == "cicd"

    def test_secrets_by_rule_prefix(self):
        assert detect_domain({"rule_id": "gitleaks-generic-api-key", "scanner": ""}) == "secrets"

    def test_secrets_by_scanner(self):
        assert detect_domain({"rule_id": "custom", "scanner": "gitleaks"}) == "secrets"

    def test_sast_by_rule_prefix_bandit(self):
        assert detect_domain({"rule_id": "B101", "scanner": ""}) == "sast"

    def test_sast_by_rule_prefix_python(self):
        assert detect_domain({"rule_id": "python.lang.security.eval", "scanner": ""}) == "sast"

    def test_sast_by_scanner_bandit(self):
        assert detect_domain({"rule_id": "custom", "scanner": "bandit"}) == "sast"

    def test_sast_by_scanner_semgrep(self):
        assert detect_domain({"rule_id": "custom", "scanner": "semgrep"}) == "sast"

    def test_general_fallback_unknown(self):
        assert detect_domain({"rule_id": "UNKNOWN-123", "scanner": "custom-scanner"}) == "general"

    def test_source_category_kubernetes(self):
        finding = {"rule_id": "", "scanner": "", "source_category": "kubernetes-manifest"}
        assert detect_domain(finding) == "kubernetes"

    def test_source_category_cloud(self):
        finding = {"rule_id": "", "scanner": "", "source_category": "aws-terraform"}
        assert detect_domain(finding) == "cloud"

    def test_empty_finding(self):
        assert detect_domain({}) == "general"


class TestGetDomainConfig:
    """Test get_domain_config() returns correct configs."""

    def test_known_domain(self):
        config = get_domain_config("kubernetes")
        assert config.name == "kubernetes"
        assert "CKS" in config.system_prompt

    def test_unknown_domain_returns_default(self):
        config = get_domain_config("nonexistent")
        assert config.name == "general"
        assert config is DEFAULT_DOMAIN

    def test_all_domains_have_system_prompt(self):
        for name, config in DOMAINS.items():
            assert config.system_prompt, f"Domain {name} missing system_prompt"
            assert config.name == name


# =============================================================================
# JADE FIXER UNIT TESTS
# =============================================================================

def _make_mock_llm(responses):
    """Create a mock LLM function that returns responses in order."""
    call_count = [0]

    def mock_llm(prompt, system_prompt=None, max_tokens=None):
        if call_count[0] < len(responses):
            resp = responses[call_count[0]]
            call_count[0] += 1
            return resp
        return None

    mock_llm.call_count = call_count
    return mock_llm


def _make_mock_rag(context=""):
    """Create a mock RAG function."""
    def mock_rag(query, top_k=5):
        return context
    return mock_rag


class TestJADEFixerInvestigation:
    """Test the investigation phase."""

    def test_reads_target_file(self, tmp_path):
        target = tmp_path / "deployment.yaml"
        target.write_text("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\n")

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "KSV011", "file": "deployment.yaml", "scanner": "kubescape"}
        ctx = fixer._investigate(finding, str(tmp_path))

        assert "apiVersion" in ctx.file_content
        assert ctx.domain == "kubernetes"
        assert ctx.file_path == "deployment.yaml"

    def test_reads_context_around_line(self, tmp_path):
        lines = [f"line {i}\n" for i in range(1, 101)]
        target = tmp_path / "app.py"
        target.write_text("".join(lines))

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "B101", "file": "app.py", "line": 50, "scanner": "bandit"}
        ctx = fixer._investigate(finding, str(tmp_path))

        assert "line 50" in ctx.surrounding_code
        assert " >>> " in ctx.surrounding_code  # marker on target line

    def test_missing_file_returns_empty_content(self, tmp_path):
        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "B101", "file": "nonexistent.py", "scanner": "bandit"}
        ctx = fixer._investigate(finding, str(tmp_path))

        assert ctx.file_content == ""

    def test_rag_context_included(self, tmp_path):
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([]),
            rag_query_fn=_make_mock_rag(context="Use hashlib instead of md5"),
        )

        finding = {"rule_id": "B303", "file": "test.py", "scanner": "bandit"}
        ctx = fixer._investigate(finding, str(tmp_path))

        assert ctx.rag_context == "Use hashlib instead of md5"


class TestJADEFixerDiagnosis:
    """Test the diagnosis phase."""

    def test_successful_diagnosis(self):
        diagnosis_response = json.dumps({
            "root_cause": "Container runs as root",
            "fix_location": "deployment.yaml:15",
            "fix_strategy": "Add runAsNonRoot: true to securityContext",
            "confidence": 0.85,
        })

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([diagnosis_response]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "KSV011", "severity": "HIGH", "message": "Container runs as root"}
        ctx = InvestigationContext(
            domain="kubernetes",
            domain_config=get_domain_config("kubernetes"),
            file_content="spec:\n  containers:\n    - name: app\n      image: nginx\n",
            file_path="deploy.yaml",
        )

        diagnosis = fixer._diagnose(finding, ctx)
        assert diagnosis.root_cause == "Container runs as root"
        assert diagnosis.confidence == 0.85
        assert fixer._llm_calls == 1

    def test_diagnosis_with_markdown_json(self):
        response = '```json\n{"root_cause": "test", "fix_location": "a:1", "fix_strategy": "do x", "confidence": 0.7}\n```'

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([response]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "B101", "severity": "MEDIUM", "message": "test"}
        ctx = InvestigationContext(
            domain="sast",
            domain_config=get_domain_config("sast"),
            file_content="assert True\n",
            file_path="test.py",
        )

        diagnosis = fixer._diagnose(finding, ctx)
        assert diagnosis.root_cause == "test"

    def test_diagnosis_llm_returns_none(self):
        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([None]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "B101", "severity": "MEDIUM", "message": "test"}
        ctx = InvestigationContext(domain="sast", domain_config=get_domain_config("sast"),
                                   file_content="x = 1\n", file_path="t.py")

        diagnosis = fixer._diagnose(finding, ctx)
        assert diagnosis.root_cause == ""


class TestJADEFixerGeneration:
    """Test the fix generation phase."""

    def test_successful_fix_generation(self):
        fix_response = json.dumps({
            "fix_type": "direct",
            "description": "Add runAsNonRoot to securityContext",
            "code_before": "      image: nginx",
            "code_after": "      image: nginx\n      securityContext:\n        runAsNonRoot: true",
            "confidence": 0.9,
        })

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([fix_response]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "KSV011", "severity": "HIGH"}
        ctx = InvestigationContext(
            domain="kubernetes",
            domain_config=get_domain_config("kubernetes"),
            file_content="spec:\n  containers:\n    - name: app\n      image: nginx\n",
            file_path="deploy.yaml",
        )
        diagnosis = Diagnosis(
            root_cause="No securityContext",
            fix_location="deploy.yaml:4",
            fix_strategy="Add runAsNonRoot",
            confidence=0.85,
        )

        result = fixer._generate_fix(finding, ctx, diagnosis)
        assert result.success
        assert result.code_before == "      image: nginx"
        assert "runAsNonRoot" in result.code_after

    def test_fix_validation_rejects_bad_code_before(self):
        fix_response = json.dumps({
            "fix_type": "direct",
            "description": "test fix",
            "code_before": "THIS DOES NOT EXIST IN FILE",
            "code_after": "fixed code",
            "confidence": 0.8,
        })
        # Retry also fails
        retry_response = json.dumps({
            "fix_type": "direct",
            "description": "test fix retry",
            "code_before": "STILL DOES NOT EXIST",
            "code_after": "fixed code",
            "confidence": 0.8,
        })

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([fix_response, retry_response]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "B101"}
        ctx = InvestigationContext(
            domain="sast",
            domain_config=get_domain_config("sast"),
            file_content="actual_code = True\n",
            file_path="test.py",
        )
        diagnosis = Diagnosis(root_cause="test", fix_strategy="fix it", confidence=0.8)

        result = fixer._generate_fix(finding, ctx, diagnosis)
        assert not result.success
        assert "not found in file" in result.error


class TestJADEFixerFullPipeline:
    """Test the full fix() pipeline end-to-end."""

    def test_full_pipeline_success(self, tmp_path):
        target_file = tmp_path / "deploy.yaml"
        target_file.write_text(
            "spec:\n  containers:\n    - name: app\n      image: nginx\n"
        )

        diagnosis_response = json.dumps({
            "root_cause": "No runAsNonRoot",
            "fix_location": "deploy.yaml:4",
            "fix_strategy": "Add securityContext",
            "confidence": 0.85,
        })
        fix_response = json.dumps({
            "fix_type": "direct",
            "description": "Add securityContext",
            "code_before": "      image: nginx",
            "code_after": "      image: nginx\n      securityContext:\n        runAsNonRoot: true",
            "confidence": 0.9,
        })

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([diagnosis_response, fix_response]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {
            "rule_id": "KSV011",
            "scanner": "kubescape",
            "file": "deploy.yaml",
            "line": 4,
            "severity": "HIGH",
            "message": "Container should not run as root",
        }

        result = fixer.fix(finding, str(tmp_path))
        assert result.success
        assert result.domain == "kubernetes"
        assert result.code_before == "      image: nginx"
        assert "runAsNonRoot" in result.code_after
        assert result.llm_calls_used == 2

    def test_pipeline_fails_on_missing_file(self, tmp_path):
        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {
            "rule_id": "B101",
            "scanner": "bandit",
            "file": "nonexistent.py",
            "severity": "MEDIUM",
            "message": "assert used",
        }

        result = fixer.fix(finding, str(tmp_path))
        assert not result.success
        assert "Could not read" in result.error

    def test_pipeline_respects_llm_call_limit(self, tmp_path):
        target_file = tmp_path / "test.py"
        target_file.write_text("x = 1\n")

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([None, None, None]),
            rag_query_fn=_make_mock_rag(),
            max_llm_calls=1,
        )

        # Diagnosis uses 1 call and returns empty → pipeline stops
        finding = {"rule_id": "B101", "scanner": "bandit", "file": "test.py",
                    "severity": "LOW", "message": "test"}

        result = fixer.fix(finding, str(tmp_path))
        assert not result.success
        assert fixer._llm_calls <= 1

    def test_low_confidence_diagnosis_stops_pipeline(self, tmp_path):
        target_file = tmp_path / "test.py"
        target_file.write_text("x = 1\n")

        diagnosis_response = json.dumps({
            "root_cause": "maybe something",
            "fix_location": "?",
            "fix_strategy": "unclear",
            "confidence": 0.1,
        })

        fixer = JADEFixer(
            llm_query_fn=_make_mock_llm([diagnosis_response]),
            rag_query_fn=_make_mock_rag(),
        )

        finding = {"rule_id": "B101", "scanner": "bandit", "file": "test.py",
                    "severity": "LOW", "message": "test"}

        result = fixer.fix(finding, str(tmp_path))
        assert not result.success
        assert "confidence too low" in result.error


class TestJADEFixerTools:
    """Test deterministic tool methods."""

    def test_read_file_relative(self, tmp_path):
        (tmp_path / "test.py").write_text("hello world\n")
        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        content = fixer._read_file("test.py", str(tmp_path))
        assert "hello world" in content

    def test_read_file_absolute(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("abs path\n")
        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        content = fixer._read_file(str(f), str(tmp_path))
        assert "abs path" in content

    def test_read_file_not_found(self, tmp_path):
        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        content = fixer._read_file("missing.py", str(tmp_path))
        assert content == ""

    def test_read_file_line_range(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")
        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        content = fixer._read_file("test.py", str(tmp_path), start=2, end=4)
        assert "line2" in content
        assert "line4" in content
        assert "line1" not in content
        assert "line5" not in content

    def test_list_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "b.yaml").write_text("")
        (tmp_path / "c.py").write_text("")

        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        files = fixer._list_files(str(tmp_path), "*.yaml")
        assert len(files) == 2
        assert any("a.yaml" in f for f in files)

    def test_validate_code_before_exact(self):
        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        assert fixer._validate_code_before("image: nginx", "spec:\n  image: nginx\n")
        assert not fixer._validate_code_before("image: apache", "spec:\n  image: nginx\n")

    def test_validate_code_before_whitespace_normalized(self):
        fixer = JADEFixer(_make_mock_llm([]), _make_mock_rag())
        assert fixer._validate_code_before("image:  nginx", "spec:\n  image: nginx\n")

    def test_extract_json_plain(self):
        result = JADEFixer._extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_extract_json_with_markdown(self):
        result = JADEFixer._extract_json('```json\n{"key": "value"}\n```')
        assert '"key"' in result

    def test_extract_json_with_leading_text(self):
        result = JADEFixer._extract_json('Here is the fix:\n{"key": "value"}')
        assert '"key"' in result

    def test_extract_json_none(self):
        assert JADEFixer._extract_json("") is None
        assert JADEFixer._extract_json("no json here") is None
