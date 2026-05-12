"""
BERU-AI Core Module Tests
Tests findings ingestion, tool output parsing, NIST mapping,
triage engine, and risk summary generation.
Runs WITHOUT Ollama — tests template-based fallback paths.
"""

import json
from pathlib import Path

import pytest

import sys
BERU_PATH = Path(__file__).parent.parent / "BERU-AI"
sys.path.insert(0, str(BERU_PATH))

from core.tool_output_parser import ToolOutputParser
from core.findings_ingestion import FindingsIngestion
from core.nist_mapper import NISTMapper
from core.triage_engine import TriageEngine
from core.risk_summary import RiskSummaryGenerator


class TestToolOutputParser:

    def setup_method(self):
        self.parser = ToolOutputParser()

    def test_supported_scanners_includes_known(self):
        scanners = self.parser.supported_scanners()
        assert "guardduty" in scanners
        assert "nessus" in scanners
        assert "prowler" in scanners
        assert "wazuh" in scanners

    def test_parse_json_guardduty(self):
        raw = json.dumps({
            "type": "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom",
            "severity": 8.0,
            "title": "EC2 instance communicating with malicious IP",
            "description": "Instance i-0abc123 is communicating with a known malicious IP.",
            "resource": {"resourceType": "Instance"},
        })
        findings = self.parser.parse("guardduty", raw)
        assert len(findings) == 1
        assert findings[0]["scanner"] == "guardduty"
        assert findings[0]["severity"] == "HIGH"
        assert findings[0]["parse_status"] == "ok"

    def test_parse_csv_nessus(self):
        raw = (
            "Plugin ID,CVE,CVSS,Risk,Host,Name\n"
            "19506,CVE-2024-1234,9.8,Critical,10.0.0.1,Remote Code Execution\n"
            "11219,,2.1,Low,10.0.0.1,SSH Weak Algorithms\n"
        )
        findings = self.parser.parse("nessus", raw, format_hint="csv")
        assert len(findings) == 2
        assert findings[0]["severity"] == "CRITICAL"
        assert findings[1]["severity"] == "LOW"

    def test_parse_jsonl_nuclei(self):
        raw = (
            '{"template-id": "cve-2024-1234", "severity": "critical", "host": "example.com"}\n'
            '{"template-id": "cve-2024-5678", "severity": "medium", "host": "example.com"}\n'
        )
        findings = self.parser.parse("nuclei", raw, format_hint="jsonl")
        assert len(findings) == 2
        assert findings[0]["severity"] == "CRITICAL"

    def test_unsupported_format_returns_unparsed(self):
        findings = self.parser.parse("unknown_scanner", "some raw data")
        assert len(findings) == 1
        assert findings[0]["parse_status"] == "unsupported_format"

    def test_severity_normalization_numeric(self):
        assert self.parser._normalize_severity(9.5) == "CRITICAL"
        assert self.parser._normalize_severity(7.0) == "HIGH"
        assert self.parser._normalize_severity(4.0) == "MEDIUM"
        assert self.parser._normalize_severity(1.0) == "LOW"
        assert self.parser._normalize_severity(0.0) == "INFO"

    def test_severity_normalization_string(self):
        assert self.parser._normalize_severity("Critical") == "CRITICAL"
        assert self.parser._normalize_severity("IMPORTANT") == "HIGH"
        assert self.parser._normalize_severity("Moderate") == "MEDIUM"
        assert self.parser._normalize_severity("informational") == "INFO"


class TestFindingsIngestion:

    def setup_method(self):
        self.ingestion = FindingsIngestion()

    def test_ingest_file_adds_metadata(self, tmp_path):
        test_file = tmp_path / "guardduty_test.json"
        test_file.write_text(json.dumps({
            "type": "Recon:EC2/PortProbeUnprotectedPort",
            "severity": 5.0,
            "title": "Port probe on unprotected port",
        }))
        findings = self.ingestion.ingest_file(test_file, scanner="guardduty")
        assert len(findings) == 1
        assert "finding_id" in findings[0]
        assert findings[0]["finding_id"].startswith("guardduty-")
        assert "ingested_at" in findings[0]
        assert "source_file" in findings[0]

    def test_ingest_directory(self, tmp_path):
        for i in range(3):
            f = tmp_path / f"prowler_{i}.json"
            f.write_text(json.dumps({
                "CheckID": f"check-{i}",
                "Status": "FAIL",
                "Severity": "high",
                "title": f"Finding {i}",
            }))
        findings = self.ingestion.ingest_directory(tmp_path, scanner="prowler")
        assert len(findings) == 3

    def test_detect_scanner_from_filename(self):
        path = Path("/tmp/nessus_scan_2026.csv")
        assert self.ingestion._detect_scanner(path) == "nessus"


class TestNISTMapper:

    def setup_method(self):
        self.mapper = NISTMapper()

    def test_maps_guardduty_finding(self):
        finding = {
            "scanner": "guardduty",
            "title": "Unauthorized access detected",
            "description": "Malicious IP communication",
            "raw_fields": {},
        }
        result = self.mapper.map_finding(finding)
        assert "SI-4" in result["controls"]
        assert len(result["controls"]) > 0
        assert result["primary_control"] is not None

    def test_keyword_matching_encryption(self):
        finding = {
            "scanner": "prowler",
            "title": "S3 bucket without encryption at rest",
            "description": "KMS encryption not enabled",
            "raw_fields": {},
        }
        result = self.mapper.map_finding(finding)
        assert "SC-28" in result["controls"]

    def test_validate_control_id_valid(self):
        assert self.mapper.validate_control_id("SI-4") is True
        assert self.mapper.validate_control_id("AC-2") is True
        assert self.mapper.validate_control_id("IR-4") is True

    def test_validate_control_id_invalid(self):
        assert self.mapper.validate_control_id("XX-99") is False
        assert self.mapper.validate_control_id("not-a-control") is False
        assert self.mapper.validate_control_id("") is False


class TestTriageEngine:

    def setup_method(self):
        self.engine = TriageEngine()

    def test_critical_severity_gets_p1(self):
        finding = {
            "severity": "CRITICAL",
            "scanner": "nessus",
            "title": "Remote Code Execution",
            "description": "Critical RCE vulnerability",
            "raw_fields": {},
            "finding_id": "test-001",
            "nist_controls_hint": ["SI-2"],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        result = self.engine.triage(finding)
        assert result["triage"]["priority"] == "P1"
        assert result["finding_id"] == "test-001"

    def test_high_in_production_escalates(self):
        finding = {
            "severity": "HIGH",
            "scanner": "guardduty",
            "title": "Unauthorized access",
            "description": "Malicious IP in production",
            "raw_fields": {},
            "finding_id": "test-002",
            "nist_controls_hint": ["SI-4"],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        context = {"environment": "production", "data_classification": "PII"}
        result = self.engine.triage(finding, context)
        assert result["triage"]["priority"] == "P1"

    def test_low_severity_gets_p4(self):
        finding = {
            "severity": "LOW",
            "scanner": "lynis",
            "title": "Informational finding",
            "description": "Minor configuration note",
            "raw_fields": {},
            "finding_id": "test-003",
            "nist_controls_hint": [],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        result = self.engine.triage(finding)
        assert result["triage"]["priority"] == "P4"

    def test_triage_batch_sorts_by_priority(self):
        findings = [
            {"severity": "LOW", "scanner": "a", "title": "low", "description": "",
             "raw_fields": {}, "finding_id": "f1", "nist_controls_hint": [],
             "parse_status": "ok", "ingested_at": ""},
            {"severity": "CRITICAL", "scanner": "b", "title": "crit", "description": "",
             "raw_fields": {}, "finding_id": "f2", "nist_controls_hint": [],
             "parse_status": "ok", "ingested_at": ""},
        ]
        results = self.engine.triage_batch(findings)
        assert results[0]["triage"]["priority"] == "P1"
        assert results[1]["triage"]["priority"] == "P4"

    def test_triage_includes_nist_controls(self):
        finding = {
            "severity": "HIGH",
            "scanner": "guardduty",
            "title": "Monitoring alert",
            "description": "Intrusion detection triggered",
            "raw_fields": {},
            "finding_id": "test-004",
            "nist_controls_hint": ["SI-4"],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        result = self.engine.triage(finding)
        assert len(result["triage"]["nist_controls"]) > 0

    def test_confidence_is_bounded(self):
        finding = {
            "severity": "HIGH", "scanner": "nessus", "title": "test",
            "description": "", "raw_fields": {}, "finding_id": "test",
            "nist_controls_hint": ["SI-2"], "parse_status": "ok",
            "ingested_at": "",
        }
        result = self.engine.triage(finding)
        assert 0.0 <= result["triage"]["confidence"] <= 1.0


class TestRiskSummaryGenerator:

    def setup_method(self):
        self.generator = RiskSummaryGenerator(llm_provider=None)

    def test_template_summary_executive(self):
        triage_result = {
            "finding_id": "test-001",
            "triage": {
                "priority": "P1",
                "severity_context": "CRITICAL in production",
                "blast_radius": "3 instances affected",
                "immediate_action": "Isolate affected instance",
                "remediation": "Patch and rotate credentials",
                "nist_controls": ["SI-4", "IR-4"],
                "confidence": 0.85,
            },
            "ciso_summary": "",
            "evidence": {
                "scanner": "guardduty",
                "finding_type": "UnauthorizedAccess",
                "timestamp": "2026-04-09T00:00:00Z",
            },
        }
        result = self.generator.summarize_finding(triage_result, tier="executive")
        assert len(result["ciso_summary"]) > 0
        assert "guardduty" in result["ciso_summary"]

    def test_template_summary_technical(self):
        triage_result = {
            "finding_id": "test-002",
            "triage": {
                "priority": "P2",
                "severity_context": "HIGH in staging",
                "blast_radius": "1 instance",
                "immediate_action": "Review configuration",
                "remediation": "Apply CIS benchmark",
                "nist_controls": ["CM-6"],
                "confidence": 0.7,
            },
            "ciso_summary": "",
            "evidence": {
                "scanner": "prowler",
                "finding_type": "S3 misconfiguration",
                "timestamp": "2026-04-09T00:00:00Z",
            },
        }
        result = self.generator.summarize_finding(triage_result, tier="technical")
        assert "Remediation:" in result["ciso_summary"]

    def test_batch_summary_counts_priorities(self):
        triage_results = [
            {"triage": {"priority": "P1", "nist_controls": ["SI-4"]},
             "evidence": {"scanner": "guardduty", "finding_type": "a", "timestamp": ""}},
            {"triage": {"priority": "P2", "nist_controls": ["CM-6"]},
             "evidence": {"scanner": "prowler", "finding_type": "b", "timestamp": ""}},
            {"triage": {"priority": "P2", "nist_controls": ["AC-6"]},
             "evidence": {"scanner": "prowler", "finding_type": "c", "timestamp": ""}},
        ]
        result = self.generator.summarize_batch(triage_results)
        assert result["total_findings"] == 3
        assert result["by_priority"]["P1"] == 1
        assert result["by_priority"]["P2"] == 2
        assert len(result["narrative"]) > 0
