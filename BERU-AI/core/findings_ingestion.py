"""
Findings Ingestion — Raw Scanner Output to Normalized Findings

Entry point for all scanner data entering BERU's pipeline.
Reads files from 0-data-lab/seclab-findings/, parses them via
ToolOutputParser, and produces normalized finding records.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .tool_output_parser import ToolOutputParser


class FindingsIngestion:
    """Ingest raw scanner output into normalized findings."""

    def __init__(self):
        self.parser = ToolOutputParser()

    def ingest_file(self, file_path: Path,
                    scanner: Optional[str] = None,
                    format_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ingest a single scanner output file.

        Args:
            file_path: Path to raw scanner output
            scanner: Scanner name (auto-detected from filename if not provided)
            format_hint: Format override

        Returns:
            List of normalized finding dicts
        """
        raw = file_path.read_text()
        scanner = scanner or self._detect_scanner(file_path)
        findings = self.parser.parse(scanner, raw, format_hint)

        # Enrich with ingestion metadata
        for finding in findings:
            finding["finding_id"] = f"{scanner}-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
            finding["source_file"] = str(file_path)
            finding["ingested_at"] = datetime.utcnow().isoformat() + "Z"

        return findings

    def ingest_directory(self, dir_path: Path,
                         scanner: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ingest all scanner output files in a directory.

        Args:
            dir_path: Path to directory containing scanner output files
            scanner: Scanner name (auto-detected per file if not provided)

        Returns:
            Aggregated list of all normalized findings
        """
        all_findings = []
        supported_extensions = {".json", ".jsonl", ".csv", ".xml", ".log", ".txt"}
        for f in sorted(dir_path.iterdir()):
            if f.is_file() and f.suffix in supported_extensions:
                findings = self.ingest_file(f, scanner=scanner)
                all_findings.extend(findings)
        return all_findings

    def _detect_scanner(self, file_path: Path) -> str:
        """Detect scanner from filename patterns."""
        name = file_path.stem.lower()
        known = self.parser.supported_scanners()
        for scanner in known:
            if scanner in name:
                return scanner
        return "unknown"
