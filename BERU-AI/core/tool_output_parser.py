"""
Scanner-Specific Output Format Parsers

Parses raw scanner output (CSV, JSON, SARIF, log) into a list of
normalized finding dicts. Each parser knows the key fields for its scanner.

Scanner mappings loaded from config/scanner_mappings.yaml.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_scanner_mappings() -> Dict[str, Any]:
    mappings_path = _CONFIG_DIR / "scanner_mappings.yaml"
    if mappings_path.exists():
        with open(mappings_path) as f:
            return yaml.safe_load(f)
    return {"scanners": {}}


class ToolOutputParser:
    """Parse raw scanner output into normalized finding dicts."""

    def __init__(self):
        config = _load_scanner_mappings()
        self.scanners = config.get("scanners", {})
        self.nist_families = config.get("nist_control_families", {})

    def parse(self, scanner: str, raw_output: str,
              format_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse raw scanner output into normalized findings.

        Args:
            scanner: Scanner name (e.g., "nessus", "guardduty", "prowler")
            raw_output: Raw output string from the scanner
            format_hint: Optional format override ("json", "csv", "sarif")

        Returns:
            List of normalized finding dicts with keys:
            - scanner, severity, title, description, raw_fields, nist_controls_hint
        """
        scanner_lower = scanner.lower()
        scanner_config = self.scanners.get(scanner_lower, {})

        # Auto-detect format if not provided
        fmt = format_hint or self._detect_format(raw_output, scanner_config)

        if fmt == "json":
            return self._parse_json(scanner_lower, raw_output, scanner_config)
        elif fmt == "csv":
            return self._parse_csv(scanner_lower, raw_output, scanner_config)
        elif fmt == "jsonl":
            return self._parse_jsonl(scanner_lower, raw_output, scanner_config)
        else:
            # Return single finding with raw output for manual review
            return [{
                "scanner": scanner_lower,
                "severity": "UNKNOWN",
                "title": f"Unparsed {scanner} output",
                "description": raw_output[:500],
                "raw_fields": {},
                "nist_controls_hint": scanner_config.get("primary_controls", []),
                "parse_status": "unsupported_format",
            }]

    def _detect_format(self, raw: str, config: Dict) -> str:
        stripped = raw.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "json"
        if "\n{" in stripped and stripped.count("\n{") > 1:
            return "jsonl"
        if "," in stripped.split("\n")[0] and len(stripped.split("\n")) > 1:
            return "csv"
        return "unknown"

    def _parse_json(self, scanner: str, raw: str,
                    config: Dict) -> List[Dict[str, Any]]:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        findings = []
        for item in data:
            findings.append(self._normalize(scanner, item, config))
        return findings

    def _parse_jsonl(self, scanner: str, raw: str,
                     config: Dict) -> List[Dict[str, Any]]:
        findings = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if line:
                item = json.loads(line)
                findings.append(self._normalize(scanner, item, config))
        return findings

    def _parse_csv(self, scanner: str, raw: str,
                   config: Dict) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(raw))
        findings = []
        for row in reader:
            findings.append(self._normalize(scanner, dict(row), config))
        return findings

    def _normalize(self, scanner: str, raw_item: Dict,
                   config: Dict) -> Dict[str, Any]:
        """Normalize a single finding from raw scanner fields."""
        key_fields = config.get("key_fields", [])
        # Extract known fields
        raw_fields = {}
        for field in key_fields:
            # Handle nested fields (e.g., "resource.resourceType")
            val: Any = raw_item
            for part in field.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                raw_fields[field] = val

        # Map severity from scanner-specific field names
        severity = self._extract_severity(scanner, raw_item)
        title = self._extract_title(scanner, raw_item)

        return {
            "scanner": scanner,
            "severity": severity,
            "title": title,
            "description": raw_item.get("description", raw_item.get("Description", "")),
            "raw_fields": raw_fields,
            "nist_controls_hint": config.get("primary_controls", []),
            "parse_status": "ok",
        }

    def _extract_severity(self, scanner: str, item: Dict) -> str:
        """Extract and normalize severity across scanner formats."""
        severity_keys = ["severity", "Severity", "risk", "Risk", "rule.level"]
        for key in severity_keys:
            val: Any = item
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                return self._normalize_severity(val)
        return "UNKNOWN"

    def _extract_title(self, scanner: str, item: Dict) -> str:
        title_keys = ["title", "Title", "Name", "name",
                      "alert.signature", "rule.description", "check_id"]
        for key in title_keys:
            val: Any = item
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                return str(val)
        return "Unknown finding"

    def _normalize_severity(self, val: Any) -> str:
        """Normalize severity to CRITICAL/HIGH/MEDIUM/LOW/INFO."""
        if isinstance(val, (int, float)):
            if val >= 9.0:
                return "CRITICAL"
            if val >= 7.0:
                return "HIGH"
            if val >= 4.0:
                return "MEDIUM"
            if val >= 1.0:
                return "LOW"
            return "INFO"
        s = str(val).upper().strip()
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        if s in valid:
            return s
        # Common scanner mappings
        mapping = {"SEVERE": "CRITICAL", "IMPORTANT": "HIGH", "MODERATE": "MEDIUM",
                   "WARNING": "MEDIUM", "INFORMATIONAL": "INFO", "NONE": "INFO"}
        return mapping.get(s, "UNKNOWN")

    def supported_scanners(self) -> List[str]:
        return list(self.scanners.keys())
