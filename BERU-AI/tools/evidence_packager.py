"""
Evidence Packager — Bundle BERU Outputs into Auditor-Ready ZIP

Collects BERU findings, POA&M items, SSP narratives, and CISO briefings
into a timestamped ZIP archive with a signed manifest.

Control traceability:
  CA-5   — Plan of Action: every BERU finding that becomes a POA&M item is included
  AU-3   — Audit Record Content: manifest records system, timestamp, artifact type, sha256
  CA-7   — Continuous Monitoring: evidence package is the deliverable that shows monitoring occurred
  MANAGE-2.4 — AI RMF: post-deployment evidence collection documents ongoing risk management
  MAP-4.2    — AI RMF: evidence of human-in-the-loop for B/S findings (approved queue records)

3PAO question this answers:
  "Show me the evidence package for the last BERU assessment run."
  "How do you know the package hasn't been tampered with?"
  "Where is the record that a human reviewed the B-rank findings before they were included?"
"""

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Artifact types BERU produces — each maps to a directory or file pattern
_ARTIFACT_TYPES = {
    "findings": "*.jsonl",
    "poam": "*.md",
    "ssp_narrative": "*.md",
    "ciso_briefing": "*.md",
    "hitl_approved": "approved.jsonl",
    "mlflow_run": "*.json",
}


class EvidencePackager:
    """
    Bundle BERU assessment artifacts into a timestamped, checksummed ZIP.

    Usage:
        packager = EvidencePackager(output_dir="/tmp/beru-evidence")
        pkg = packager.package(
            findings=[...],        # BERU finding dicts
            poam_text="...",       # POA&M Markdown
            ciso_briefing="...",   # CISO briefing Markdown
            hitl_log_path="...",   # HITLRouter approved queue path
            system_name="NovaSec Cloud",
            run_id="beru-eval-001",
        )
        print(pkg["archive_path"])
    """

    def __init__(self, output_dir: str | Path = "/tmp/beru-evidence"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def package(
        self,
        findings: List[Dict[str, Any]],
        poam_text: str = "",
        ssp_narrative: str = "",
        ciso_briefing: str = "",
        hitl_log_path: Optional[str | Path] = None,
        system_name: str = "unknown",
        run_id: str = "",
        assessor: str = "BERU-AI",
    ) -> Dict[str, Any]:
        """
        Create an evidence package ZIP.

        Args:
            findings:        List of BERU finding dicts
            poam_text:       POA&M Markdown
            ssp_narrative:   SSP narrative Markdown (BERU-generated)
            ciso_briefing:   CISO briefing Markdown
            hitl_log_path:   Path to HITLRouter approved.jsonl (MANAGE-2.2 evidence)
            system_name:     System under assessment
            run_id:          Eval run or assessment identifier (for traceability)
            assessor:        Who/what produced the artifacts (BERU-AI + version)

        Returns:
            {
                "archive_path": str,
                "manifest": dict,    # full manifest for logging
                "sha256": str,       # archive checksum
                "artifact_count": int,
            }
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = system_name.replace(" ", "-").lower()
        archive_name = f"beru-evidence-{safe_name}-{ts}.zip"
        archive_path = self.output_dir / archive_name

        artifacts: List[Dict[str, Any]] = []

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:

            # 1. Findings JSONL
            if findings:
                content = "\n".join(json.dumps(f) for f in findings) + "\n"
                arc_name = "findings/beru-findings.jsonl"
                zf.writestr(arc_name, content)
                artifacts.append(self._artifact_entry(arc_name, content.encode(), "findings"))

            # 2. POA&M
            if poam_text:
                arc_name = "poam/poam.md"
                zf.writestr(arc_name, poam_text)
                artifacts.append(self._artifact_entry(arc_name, poam_text.encode(), "poam"))

            # 3. SSP narrative
            if ssp_narrative:
                arc_name = "ssp/ssp-narrative.md"
                zf.writestr(arc_name, ssp_narrative)
                artifacts.append(self._artifact_entry(arc_name, ssp_narrative.encode(), "ssp_narrative"))

            # 4. CISO briefing
            if ciso_briefing:
                arc_name = "ciso/ciso-briefing.md"
                zf.writestr(arc_name, ciso_briefing)
                artifacts.append(self._artifact_entry(arc_name, ciso_briefing.encode(), "ciso_briefing"))

            # 5. HITL approved queue (MANAGE-2.2 evidence)
            if hitl_log_path:
                hitl_path = Path(hitl_log_path)
                if hitl_path.exists():
                    hitl_bytes = hitl_path.read_bytes()
                    arc_name = "hitl/approved.jsonl"
                    zf.writestr(arc_name, hitl_bytes)
                    artifacts.append(self._artifact_entry(arc_name, hitl_bytes, "hitl_approved"))

            # 6. Write manifest (AU-3 — audit record)
            manifest = self._build_manifest(
                artifacts=artifacts,
                system_name=system_name,
                run_id=run_id,
                assessor=assessor,
                ts=ts,
            )
            manifest_content = json.dumps(manifest, indent=2)
            zf.writestr("manifest.json", manifest_content)

        # Compute archive checksum (SI-7 — integrity verification)
        archive_sha256 = self._sha256_file(archive_path)
        manifest["archive_sha256"] = archive_sha256

        # Write detached checksum file alongside archive
        checksum_path = archive_path.with_suffix(".sha256")
        checksum_path.write_text(f"{archive_sha256}  {archive_name}\n")

        return {
            "archive_path": str(archive_path),
            "checksum_path": str(checksum_path),
            "manifest": manifest,
            "sha256": archive_sha256,
            "artifact_count": len(artifacts),
        }

    def verify(self, archive_path: str | Path) -> Dict[str, Any]:
        """
        Verify an existing evidence package.
        Checks: ZIP integrity, manifest present, all artifacts checksummed.

        Returns:
            {"valid": bool, "errors": List[str], "manifest": dict}
        """
        path = Path(archive_path)
        errors = []
        manifest = {}

        if not path.exists():
            return {"valid": False, "errors": [f"Archive not found: {path}"], "manifest": {}}

        # Check companion checksum file
        checksum_path = path.with_suffix(".sha256")
        if checksum_path.exists():
            expected = checksum_path.read_text().split()[0]
            actual = self._sha256_file(path)
            if expected != actual:
                errors.append(
                    f"Archive checksum mismatch. Expected {expected[:12]}…, got {actual[:12]}…"
                )
        else:
            errors.append("No companion .sha256 file — archive integrity cannot be verified")

        # Check ZIP can be opened and contains manifest
        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                if "manifest.json" not in names:
                    errors.append("manifest.json missing from archive")
                else:
                    manifest = json.loads(zf.read("manifest.json"))

                # Verify each artifact checksum from manifest
                for artifact in manifest.get("artifacts", []):
                    arc_name = artifact.get("path")
                    expected_sha = artifact.get("sha256")
                    if arc_name and expected_sha:
                        if arc_name not in names:
                            errors.append(f"Artifact missing from archive: {arc_name}")
                        else:
                            actual_sha = hashlib.sha256(zf.read(arc_name)).hexdigest()
                            if actual_sha != expected_sha:
                                errors.append(
                                    f"Artifact checksum mismatch: {arc_name}"
                                )
        except zipfile.BadZipFile:
            errors.append("Archive is corrupted or not a valid ZIP file")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "manifest": manifest,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _artifact_entry(
        self, arc_name: str, content: bytes, artifact_type: str
    ) -> Dict[str, Any]:
        return {
            "path": arc_name,
            "type": artifact_type,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }

    def _build_manifest(
        self,
        artifacts: List[Dict[str, Any]],
        system_name: str,
        run_id: str,
        assessor: str,
        ts: str,
    ) -> Dict[str, Any]:
        """
        Build the audit manifest.
        AU-3: who, what, when, result — all represented.
        """
        return {
            "schema_version": "1.0",
            "system_name": system_name,
            "run_id": run_id,
            "assessor": assessor,
            "timestamp": ts,
            "framework": "NIST 800-53 Rev 5 + NIST AI RMF 1.0 / AI 600-1",
            "hitl_required": True,
            "hitl_control": "MANAGE-2.2",
            "artifacts": artifacts,
            "artifact_count": len(artifacts),
            "nist_controls_cited": ["AU-3", "CA-5", "CA-7", "MANAGE-2.4", "MAP-4.2"],
        }

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()
