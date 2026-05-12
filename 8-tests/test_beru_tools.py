"""
BERU-AI Tools Tests — SSPParser, HITLRouter, EvidencePackager

Runs WITHOUT Ollama — all tests are pure-Python unit tests.

Control traceability:
  MANAGE-2.2  — hitl_router tests prove B/S-rank is never auto-output
  MAP-4.1     — ssp_parser tests prove synthetic-only enforcement works
  AU-3        — evidence_packager manifest tests prove audit record completeness
  GOVERN-1.5  — rank routing table tests prove risk tolerance is architecturally enforced
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

BERU_PATH = Path(__file__).parent.parent / "BERU-AI"
sys.path.insert(0, str(BERU_PATH))

from tools.ssp_parser import SSPParser
from tools.hitl_router import HITLRouter
from tools.evidence_packager import EvidencePackager


# ── Fixtures ──────────────────────────────────────────────────────────────────

SYNTHETIC_SSP_MINIMAL = """\
# NovaSec Cloud SSP
<!-- synthetic training data -->

System Name: NovaSec Cloud
Security Categorization: Moderate
Version: 1.0

## System Description

NovaSec Cloud is a fictional multi-tenant SaaS security monitoring platform.

## AC — Access Control

### AC-2 Account Management

Part a: The organization manages information system accounts by establishing account
types required for organization access. System administrators create accounts using
the IDP provisioning workflow.

Part b: Account creation requires manager approval via ServiceNow ticket.

### AC-6 Least Privilege

Users are granted the minimum access required to perform their duties.
Privilege escalation requires Change Advisory Board approval.

## SI — System and Information Integrity

### SI-2 Flaw Remediation

Critical patches are applied within 15 days of release. The CI/CD pipeline
includes automated dependency scanning via Dependabot.

### SI-4 Information System Monitoring

GuardDuty is enabled in all AWS accounts. Findings are forwarded to Splunk SIEM.

## POA&M Items

### Item 1

Control: AC-2
Weakness: Privileged accounts lack MFA enforcement
Scheduled Completion: 2026-06-30
Milestones: Enable MFA policy in IAM Identity Center by 2026-05-15

### Item 2

Control: SI-2
Weakness: 3 EC2 instances running end-of-life AMIs
Scheduled Completion: 2026-07-15
"""

REAL_SSP_NO_MARKER = """\
# Acme Corp System Security Plan

System Name: Acme Corp Production
Security Categorization: High
Version: 3.2

## AC — Access Control

### AC-2

All accounts managed per ISSO guidelines.
"""


class TestSSPParser:

    def setup_method(self):
        self.parser = SSPParser(enforce_synthetic=True)

    def test_parse_synthetic_marker_passes(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        assert len(chunks) > 0

    def test_synthetic_enforcement_blocks_real_ssp(self):
        """MAP-4.1: real client SSPs must be rejected from the training corpus."""
        with pytest.raises(ValueError, match="lacks a synthetic marker"):
            self.parser.parse_text(REAL_SSP_NO_MARKER, source_file="real.md")

    def test_enforcement_disabled_allows_any(self):
        parser = SSPParser(enforce_synthetic=False)
        chunks = parser.parse_text(REAL_SSP_NO_MARKER, source_file="real.md")
        assert len(chunks) > 0

    def test_control_implementation_chunks_extracted(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        control_chunks = [c for c in chunks if c["chunk_type"] == "control_implementation"]
        assert len(control_chunks) >= 3  # AC-2, AC-6, SI-2, SI-4

    def test_poam_chunks_extracted(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        poam_chunks = [c for c in chunks if c["chunk_type"] == "poam_item"]
        assert len(poam_chunks) >= 1

    def test_system_metadata_captured(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        assert all(c["system_name"] for c in chunks if c["chunk_type"] != "system_description")
        ctrl_chunks = [c for c in chunks if c["chunk_type"] == "control_implementation"]
        assert ctrl_chunks[0]["categorization"] == "Moderate"

    def test_control_id_on_implementation_chunk(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        ctrl_chunks = [c for c in chunks if c["chunk_type"] == "control_implementation"]
        control_ids = {c["control_id"] for c in ctrl_chunks if c["control_id"]}
        assert "AC-2" in control_ids or any("AC" in str(cid) for cid in control_ids)

    def test_chunk_id_is_deterministic(self):
        chunks1 = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        chunks2 = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        ids1 = {c["id"] for c in chunks1}
        ids2 = {c["id"] for c in chunks2}
        assert ids1 == ids2

    def test_chunk_id_no_duplicates(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_collection_field_is_beru_nist(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        assert all(c["collection"] == "beru-nist-800-53" for c in chunks)

    def test_write_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
            out_path = Path(tmpdir) / "output.jsonl"
            count = self.parser.write_jsonl(chunks, out_path)
            assert count == len(chunks)
            assert out_path.exists()
            lines = out_path.read_text().strip().splitlines()
            assert len(lines) == count
            parsed = [json.loads(l) for l in lines]
            assert all("chunk_type" in p for p in parsed)

    def test_parse_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ssp_path = Path(tmpdir) / "ssp.md"
            ssp_path.write_text(SYNTHETIC_SSP_MINIMAL)
            chunks = self.parser.parse_file(ssp_path)
            assert len(chunks) > 0

    def test_stats_tracks_parsed_count(self):
        self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="a.md")
        self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="b.md")
        stats = self.parser.stats()
        assert stats["parsed"] == 2

    def test_family_name_resolved(self):
        chunks = self.parser.parse_text(SYNTHETIC_SSP_MINIMAL, source_file="test.md")
        ctrl_chunks = [c for c in chunks if c["control_id"] and c["control_family"]]
        assert len(ctrl_chunks) > 0
        families = {c["control_family"] for c in ctrl_chunks}
        assert any("Access Control" in f for f in families)


class TestHITLRouter:
    """
    BERU Build Rule 7: B/S-rank findings MUST be blocked.
    These tests prove the architectural enforcement is in place.
    MANAGE-2.2, GOVERN-1.5.
    """

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.router = HITLRouter(queue_dir=self._tmpdir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _finding(self, rank: str, finding_id: str = "test-001") -> dict:
        return {
            "finding_id": finding_id,
            "rank": rank,
            "title": f"Test finding rank {rank}",
            "description": "Test",
        }

    # Rank E — must auto-output
    def test_e_rank_is_auto(self):
        result = self.router.route(self._finding("E"))
        assert result["status"] == "auto"
        assert result["auto_ok"] is True

    # Rank D — must auto-output
    def test_d_rank_is_auto(self):
        result = self.router.route(self._finding("D"))
        assert result["status"] == "auto"
        assert result["auto_ok"] is True

    # Rank C — must auto-output (Katie's authority ceiling)
    def test_c_rank_is_auto(self):
        result = self.router.route(self._finding("C"))
        assert result["status"] == "auto"
        assert result["auto_ok"] is True

    # Rank B — MUST be blocked (MANAGE-2.2)
    def test_b_rank_is_blocked(self):
        result = self.router.route(self._finding("B"))
        assert result["status"] == "pending_human"
        assert result["auto_ok"] is False
        assert result["queue_id"] is not None

    # Rank S — MUST be blocked (MANAGE-2.2)
    def test_s_rank_is_blocked(self):
        result = self.router.route(self._finding("S"))
        assert result["status"] == "pending_human"
        assert result["auto_ok"] is False

    def test_b_rank_written_to_pending_queue(self):
        self.router.route(self._finding("B", "finding-b-001"))
        pending = self.router.list_pending()
        assert any(r["finding_id"] == "finding-b-001" for r in pending)

    def test_s_rank_written_to_pending_queue(self):
        self.router.route(self._finding("S", "finding-s-001"))
        pending = self.router.list_pending()
        assert any(r["finding_id"] == "finding-s-001" for r in pending)

    def test_approve_moves_from_pending_to_approved(self):
        result = self.router.route(self._finding("B", "b-approve-test"))
        queue_id = result["queue_id"]

        approved = self.router.approve(queue_id, approver="J", notes="Reviewed and confirmed")
        assert approved["finding_id"] == "b-approve-test"

        pending = self.router.list_pending()
        assert not any(r["queue_id"] == queue_id for r in pending)

    def test_reject_moves_from_pending_to_rejected(self):
        result = self.router.route(self._finding("S", "s-reject-test"))
        queue_id = result["queue_id"]
        self.router.reject(queue_id, reviewer="J", reason="False positive")

        pending = self.router.list_pending()
        assert not any(r["queue_id"] == queue_id for r in pending)

    def test_approve_unknown_queue_id_raises(self):
        with pytest.raises(KeyError):
            self.router.approve("nonexistent-id")

    def test_stats_reflects_queue_state(self):
        self.router.route(self._finding("B", "b-stat-1"))
        self.router.route(self._finding("S", "s-stat-1"))
        stats = self.router.stats()
        assert stats["pending"] >= 2

    def test_auto_log_written_for_e_d_c(self):
        self.router.route(self._finding("E", "e-log-1"))
        self.router.route(self._finding("D", "d-log-1"))
        self.router.route(self._finding("C", "c-log-1"))
        log_path = Path(self._tmpdir) / "auto_log.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_batch_routing(self):
        findings = [
            self._finding("E", "batch-e"),
            self._finding("B", "batch-b"),
            self._finding("S", "batch-s"),
            self._finding("C", "batch-c"),
        ]
        results = self.router.route_batch(findings)
        auto = [r for r in results if r["status"] == "auto"]
        blocked = [r for r in results if r["status"] == "pending_human"]
        assert len(auto) == 2  # E, C
        assert len(blocked) == 2  # B, S

    def test_queue_id_is_deterministic_format(self):
        """Queue IDs must be non-empty strings (SHA256 prefix)."""
        result = self.router.route(self._finding("B"))
        assert isinstance(result["queue_id"], str)
        assert len(result["queue_id"]) == 12

    def test_message_cites_manage_2_2(self):
        """Blocked message must cite the control — AU-3."""
        result = self.router.route(self._finding("B"))
        assert "MANAGE-2.2" in result["message"]


class TestEvidencePackager:

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.packager = EvidencePackager(output_dir=self._tmpdir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _sample_findings(self) -> list:
        return [
            {
                "finding_id": "F-001",
                "rank": "C",
                "title": "MFA not enforced on privileged accounts",
                "control": "IA-2",
                "status": "FAIL",
            },
            {
                "finding_id": "F-002",
                "rank": "B",
                "title": "Model card missing for BERU v1.0",
                "control": "GOVERN-1.3",
                "ai_context": True,
                "status": "FAIL",
            },
        ]

    def test_package_creates_zip(self):
        result = self.packager.package(
            findings=self._sample_findings(),
            system_name="NovaSec Cloud",
            run_id="test-run-001",
        )
        assert Path(result["archive_path"]).exists()
        assert result["archive_path"].endswith(".zip")

    def test_package_creates_sha256_checksum(self):
        result = self.packager.package(
            findings=self._sample_findings(),
            system_name="NovaSec Cloud",
        )
        assert Path(result["checksum_path"]).exists()
        assert result["sha256"]

    def test_manifest_contains_required_fields(self):
        result = self.packager.package(
            findings=self._sample_findings(),
            system_name="NovaSec Cloud",
            run_id="test-001",
            assessor="BERU-AI v1.0",
        )
        m = result["manifest"]
        assert m["system_name"] == "NovaSec Cloud"
        assert m["run_id"] == "test-001"
        assert m["assessor"] == "BERU-AI v1.0"
        assert m["hitl_required"] is True
        assert "MANAGE-2.2" in m["hitl_control"]

    def test_manifest_cites_nist_controls(self):
        """AU-3: manifest must cite the controls it evidences."""
        result = self.packager.package(findings=self._sample_findings())
        controls = result["manifest"]["nist_controls_cited"]
        assert "AU-3" in controls
        assert "CA-5" in controls

    def test_findings_artifact_in_zip(self):
        import zipfile
        result = self.packager.package(findings=self._sample_findings())
        with zipfile.ZipFile(result["archive_path"]) as zf:
            assert "findings/beru-findings.jsonl" in zf.namelist()

    def test_poam_artifact_in_zip(self):
        import zipfile
        result = self.packager.package(
            findings=[],
            poam_text="## POA&M Item 1\n\nControl: AC-2\nWeakness: MFA not enforced",
        )
        with zipfile.ZipFile(result["archive_path"]) as zf:
            assert "poam/poam.md" in zf.namelist()

    def test_ciso_briefing_artifact_in_zip(self):
        import zipfile
        result = self.packager.package(
            findings=[],
            ciso_briefing="# CISO Briefing\n\n2 findings this cycle.",
        )
        with zipfile.ZipFile(result["archive_path"]) as zf:
            assert "ciso/ciso-briefing.md" in zf.namelist()

    def test_verify_valid_package(self):
        result = self.packager.package(findings=self._sample_findings())
        verify = self.packager.verify(result["archive_path"])
        assert verify["valid"] is True
        assert verify["errors"] == []

    def test_verify_detects_tampered_archive(self):
        import zipfile
        result = self.packager.package(findings=self._sample_findings())
        archive_path = Path(result["archive_path"])

        # Tamper: overwrite archive with garbage
        archive_path.write_bytes(b"tampered content")

        verify = self.packager.verify(archive_path)
        assert verify["valid"] is False
        assert len(verify["errors"]) > 0

    def test_verify_missing_archive_returns_invalid(self):
        verify = self.packager.verify("/tmp/does-not-exist.zip")
        assert verify["valid"] is False

    def test_artifact_count_matches_inputs(self):
        result = self.packager.package(
            findings=self._sample_findings(),
            poam_text="## Item 1\ntest",
            ciso_briefing="# Briefing",
        )
        # findings + poam + ciso = 3 artifacts
        assert result["artifact_count"] == 3

    def test_empty_package_has_manifest_only(self):
        import zipfile
        result = self.packager.package(findings=[])
        with zipfile.ZipFile(result["archive_path"]) as zf:
            assert "manifest.json" in zf.namelist()

    def test_hitl_log_included_when_path_provided(self):
        import zipfile
        hitl_log = Path(self._tmpdir) / "approved.jsonl"
        hitl_log.write_text(json.dumps({
            "queue_id": "abc123",
            "finding_id": "F-002",
            "approved_by": "J",
        }) + "\n")

        result = self.packager.package(
            findings=self._sample_findings(),
            hitl_log_path=hitl_log,
        )
        with zipfile.ZipFile(result["archive_path"]) as zf:
            assert "hitl/approved.jsonl" in zf.namelist()
