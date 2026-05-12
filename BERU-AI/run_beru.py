"""BERU CLI — drives the LangGraph agent end-to-end.

Examples:
    # Audit a scanner output file (real brain via Ollama)
    python run_beru.py audit \
        --input ../../GP-S3/seclab-findings/trivy-2026-05-01.json \
        --system NovaSec-Cloud --client DHS --ai-context

    # Grade an SSP against rubric
    python run_beru.py grade-ssp --input ./training-data/ssps/ssp-01-bad.md

    # Free-form ad-hoc request
    python run_beru.py ask --text "Audit AC-2 for the dev cluster"

    # Dry-run (stubs the brain — verifies graph wiring without Ollama)
    python run_beru.py audit --input ./fixture.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent.graph import (  # type: ignore[import-not-found]
    run_audit,
    run_ciso_briefing,
    run_freeform,
    run_ssp_grading,
)


def _common_args(p: argparse.ArgumentParser):
    p.add_argument("--system", default="unknown-system", help="System name (for evidence package)")
    p.add_argument("--client", default="unknown-client", help="Client name (for evidence package)")
    p.add_argument(
        "--ai-context", action="store_true",
        help="Mark the system as AI-in-scope → dual citation + AI RMF allow-list",
    )
    p.add_argument("--output-dir", default="/tmp/beru-out", help="Where the evidence ZIP lands")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Bypass the LLM with a stub provider — verifies graph wiring only",
    )


def _run_id(prefix: str, dry: bool) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{ts}{'-dry' if dry else ''}"


def _print_summary(result: dict) -> None:
    findings = result.get("findings") or []
    blocked = result.get("blocked_findings") or []
    poam = result.get("poam_items") or []
    ssp = result.get("ssp_narratives") or []
    errs = result.get("errors") or []
    pkg = result.get("artifact_archive_path")

    print()
    print("=" * 64)
    print(f"BERU run {result.get('run_id', '?')} complete")
    print("=" * 64)
    print(f"Findings produced : {len(findings)}")
    print(f"Blocked (B/S HITL): {len(blocked)}")
    print(f"POA&M items       : {len(poam)}")
    print(f"SSP narratives    : {len(ssp)}")
    if pkg:
        print(f"Evidence archive  : {pkg}")
    if errs:
        print("Errors:")
        for e in errs:
            print(f"  - {e}")
    for f in findings:
        print(
            f"  • {f.get('control_id', '?'):8} "
            f"{f.get('status', '?'):8} "
            f"rank={f.get('rank', '?'):2} "
            f"hitl={f.get('hitl_status', '?')}"
        )


def cmd_audit(ns: argparse.Namespace) -> int:
    run_id = _run_id("audit", ns.dry_run)
    result = run_audit(
        scanner_output_path=ns.input,
        system_name=ns.system,
        client=ns.client,
        ai_context=ns.ai_context,
        output_dir=ns.output_dir,
        run_id=run_id,
    )
    _print_summary(result)
    return 0


def cmd_grade_ssp(ns: argparse.Namespace) -> int:
    run_id = _run_id("ssp", ns.dry_run)
    result = run_ssp_grading(
        ssp_path=ns.input,
        system_name=ns.system,
        client=ns.client,
        ai_context=ns.ai_context,
        output_dir=ns.output_dir,
        run_id=run_id,
    )
    _print_summary(result)
    return 0


def cmd_ask(ns: argparse.Namespace) -> int:
    run_id = _run_id("ask", ns.dry_run)
    result = run_freeform(
        text=ns.text,
        system_name=ns.system,
        client=ns.client,
        ai_context=ns.ai_context,
        output_dir=ns.output_dir,
        run_id=run_id,
    )
    _print_summary(result)
    return 0


def cmd_ciso_brief(ns: argparse.Namespace) -> int:
    run_id = _run_id("ciso", ns.dry_run)
    findings_path = Path(ns.findings)
    findings = json.loads(findings_path.read_text())
    if isinstance(findings, dict):
        findings = findings.get("findings", [])
    result = run_ciso_briefing(
        findings=findings,
        system_name=ns.system,
        client=ns.client,
        output_dir=ns.output_dir,
        run_id=run_id,
    )
    print(result.get("ciso_summary", "(empty)"))
    if result.get("artifact_archive_path"):
        print(f"\nEvidence archive: {result['artifact_archive_path']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_beru", description="BERU agent CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="Audit scanner output → findings + POA&M")
    p_audit.add_argument("--input", required=True, help="Path to scanner output (json/csv/log)")
    _common_args(p_audit)
    p_audit.set_defaults(fn=cmd_audit)

    p_ssp = sub.add_parser("grade-ssp", help="Grade an SSP against rubric")
    p_ssp.add_argument("--input", required=True, help="Path to SSP markdown")
    _common_args(p_ssp)
    p_ssp.set_defaults(fn=cmd_grade_ssp)

    p_ask = sub.add_parser("ask", help="Free-form audit request (text prompt)")
    p_ask.add_argument("--text", required=True, help="The question/request to assess")
    _common_args(p_ask)
    p_ask.set_defaults(fn=cmd_ask)

    p_ciso = sub.add_parser("ciso-brief", help="CISO briefing over a findings JSON file")
    p_ciso.add_argument("--findings", required=True, help="JSON file with findings list")
    _common_args(p_ciso)
    p_ciso.set_defaults(fn=cmd_ciso_brief)

    ns = parser.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    sys.exit(main())
