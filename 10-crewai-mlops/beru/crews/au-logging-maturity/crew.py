"""
AU Logging Maturity Crew -- M-21-31 compliance assessment.

Encodes the playbook at:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-21-31-playbooks/01-assess-logging-maturity.md

Architecture:
  Step 1 (collect) -- pure Python: AWS CLI + kubectl. No LLM.
  Step 2 (assess)  -- assessor agent: assigns EL level + S/OTS/NA per control.
  Step 3 (report)  -- sar_writer: M-21-31 compliance report.
  Step 4 (poam)    -- poam_writer: POA&M items for each gap.

Controls: AU-2, AU-3, AU-6, AU-7, AU-9, AU-11, AU-12
Framework: M-21-31 (OMB Memorandum, August 2021)
Baseline: EL2 minimum mandate

Why Step 1 is not a CrewAI agent:
  AWS CLI and kubectl output is structured data. An LLM adds nothing to data
  collection and introduces failure modes (hallucinated resource names, ReAct
  loop confusion). The collector runs deterministically and hands clean EL
  signals to the agents.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from crewai import Crew, Task, Process

# Resolve agents.py from the beru/ root (two levels up from this file)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents import assessor, sar_writer, poam_writer  # noqa: E402

# config_loader is in beru/ root -- same sys.path resolution applies
from config_loader import get_engagement_config  # noqa: E402

from .collectors import run_au_collectors

CONTROLS = ["AU-2", "AU-3", "AU-6", "AU-7", "AU-9", "AU-11", "AU-12"]


# M-21-31 EL definitions -- baked into task descriptions so agents have full context
_EL_FRAMEWORK = """
M-21-31 Event Logging (EL) Maturity Tiers:

EL0 -- Not Logging:
  No centralized logging. No active CloudTrail. No EKS control plane logging.
  No Kubernetes audit policy. Agency cannot reconstruct events after an incident.

EL1 -- Basic Logging (foundation):
  - CloudTrail enabled with management events (active and logging)
  - EKS control plane logging enabled (all 5 types: api, audit, authenticator,
    controllerManager, scheduler)
  - Kubernetes audit policy configured (or EKS managed audit = equivalent)
  - Minimum 12-month (365-day) log retention
  NIST mapping: AU-2, AU-3, AU-11

EL2 -- Intermediate Logging (MANDATE -- required by August 2022):
  All EL1 requirements PLUS:
  - Centralized log aggregation pipeline (Fluent Bit DaemonSet on ALL nodes,
    or CloudWatch agent with equivalent coverage)
  - Log storage system available (Loki, OpenSearch, or Splunk)
  - Minimum 90-day hot retention (queryable, not just archived)
  - CloudTrail log file validation enabled
  - Log pipeline covers both infrastructure and application layers
  NIST mapping: AU-6, AU-7, AU-9, AU-12

EL3 -- Advanced Logging (full mandate):
  All EL2 requirements PLUS:
  - SIEM integration with cross-system correlation capability
  - Minimum 12-month (365-day) hot retention
  - Runtime threat detection (Falco) forwarding alerts to log pipeline
  - Automated alerting on anomalous activity patterns
  - Capability to correlate events across cloud, cluster, and application layers
  NIST mapping: AU-6 (enhanced), AU-7, SI-4
"""

# Per-control EL requirements -- what each control needs at each level
_CONTROL_EL_REQUIREMENTS = """
Control-by-control M-21-31 requirements:

AU-2 (Event Logging):
  EL1: CloudTrail active (management events) + EKS logging all 5 types enabled
  EL2: EL1 + log pipeline ingesting from all node types
  EL3: EL2 + runtime event capture (Falco) in log stream

AU-3 (Content of Audit Records):
  EL1: Structured log records with timestamp, event type, source (K8s audit policy configured)
  EL2: EL1 + consistent schema across infrastructure and application logs
  EL3: EL2 + enriched records with threat context

AU-6 (Audit Record Review, Analysis, and Reporting):
  EL1: Manual review possible (logs exist and are accessible)
  EL2: Centralized log system with query capability (Loki / OpenSearch)
  EL3: SIEM with automated analysis, correlation, and alerting

AU-7 (Audit Record Reduction and Report Generation):
  EL1: Logs can be searched manually
  EL2: Queryable log store (Loki LogQL / OpenSearch DSL)
  EL3: SIEM dashboards and automated report generation

AU-9 (Protection of Audit Information):
  EL1: CloudTrail logs protected in S3 (bucket policy, not publicly accessible)
  EL2: EL1 + CloudTrail log file validation enabled
  EL3: EL2 + KMS encryption on log groups

AU-11 (Audit Record Retention):
  EL1: Minimum 12 months total retention (hot or cold)
  EL2: Minimum 90 days hot retention (queryable)
  EL3: Minimum 12 months hot retention (queryable)

AU-12 (Audit Record Generation):
  EL1: Logs generated and flowing to CloudTrail / EKS logging
  EL2: Fluent Bit (or equivalent) running on ALL nodes, logs reaching aggregation layer
  EL3: EL2 + Falco runtime alerts in log pipeline
"""


def _format_evidence_block(evidence: dict) -> str:
    """Render collected AU evidence as readable text for task descriptions."""
    lines = []

    # AU-2
    au2 = evidence.get("au2_event_logging", {})
    eks = au2.get("eks_logging", {})
    k8s_audit = au2.get("k8s_audit_policy", {})
    ct = au2.get("cloudtrail", {})

    lines.append("AU-2 -- Event Logging:")
    if "skipped" in eks:
        lines.append(f"  EKS logging: {eks['skipped']}")
    else:
        lines.append(f"  EKS log types enabled: {eks.get('enabled_types', [])}")
        lines.append(f"  EKS log types missing: {eks.get('missing_types', [])}")
        lines.append(f"  All 5 EKS types enabled: {eks.get('all_five_enabled', False)}")
    if "skipped" in ct:
        lines.append(f"  CloudTrail: {ct['skipped']}")
    else:
        lines.append(f"  CloudTrail any active: {ct.get('any_active', False)}")
        lines.append(f"  Multi-region trail: {ct.get('multi_region_trail', False)}")
        lines.append(f"  Trail count: {len(ct.get('trails', []))}")
    if "skipped" in k8s_audit:
        lines.append(f"  K8s audit policy: {k8s_audit['skipped']}")
    elif k8s_audit.get("is_eks_managed"):
        lines.append(f"  K8s audit policy: EKS managed (audit configured via EKS logging)")
    else:
        lines.append(f"  K8s audit policy found: {k8s_audit.get('audit_policy_found', False)}")
        lines.append(f"  Audit policy file: {k8s_audit.get('policy_file', 'None')}")

    # AU-3
    au3 = evidence.get("au3_record_content", {})
    lines.append("\nAU-3 -- Content of Audit Records:")
    lines.append(f"  Audit policy level: {au3.get('audit_policy_level', 'None')}")
    lines.append(f"  Structured logging detected: {au3.get('structured_logging_detected', False)}")

    # AU-6
    au6 = evidence.get("au6_review_analysis", {})
    siem = au6.get("siem", {})
    lines.append("\nAU-6 -- Audit Record Review, Analysis, and Reporting:")
    lines.append(f"  SIEM detected: {siem.get('siem_detected', False)}")
    if siem.get("siem_detected"):
        lines.append(f"  SIEM type: {siem.get('type')} in namespace {siem.get('namespace')}")
    lines.append(f"  Alerting configured: {au6.get('alerting_configured', False)}")

    # AU-7
    au7 = evidence.get("au7_reduction_reporting", {})
    lines.append("\nAU-7 -- Audit Record Reduction and Report Generation:")
    lines.append(f"  Log query capability: {au7.get('log_query_capability', 'none')}")

    # AU-9
    au9 = evidence.get("au9_protection", {})
    enc = au9.get("log_group_encryption", {})
    lines.append("\nAU-9 -- Protection of Audit Information:")
    lines.append(f"  CloudTrail log validation: {au9.get('cloudtrail_log_validation', False)}")
    if "skipped" in enc:
        lines.append(f"  Log group encryption: {enc['skipped']}")
    else:
        lines.append(
            f"  Log groups encrypted: {enc.get('encrypted_count', 0)} of {enc.get('total_count', 0)}"
        )

    # AU-11
    au11 = evidence.get("au11_retention", {})
    lines.append("\nAU-11 -- Audit Record Retention:")
    worst = au11.get("worst_retention_days")
    lines.append(f"  Worst-case retention: {'indefinite' if worst is None else f'{worst} days'}")
    lines.append(f"  EL1 compliant (>=365d): {au11.get('el1_compliant', False)}")
    lines.append(f"  EL2 compliant (>=90d hot): {au11.get('el2_compliant', False)}")
    lines.append(f"  EL3 compliant (>=365d hot): {au11.get('el3_compliant', False)}")
    log_groups = au11.get("log_groups", [])
    non_compliant = [
        lg for lg in log_groups
        if isinstance(lg, dict) and not lg.get("el_compliant", {}).get("EL2", True)
    ]
    if non_compliant:
        lines.append(f"  Log groups below EL2 retention ({len(non_compliant)} groups):")
        for lg in non_compliant[:5]:
            lines.append(f"    {lg['name']}: {lg['retention_days']} days")
        if len(non_compliant) > 5:
            lines.append(f"    ... and {len(non_compliant) - 5} more")

    # AU-12
    au12 = evidence.get("au12_generation", {})
    fb = au12.get("fluent_bit", {})
    loki = au12.get("loki", {})
    falco = au12.get("falco", {})
    lines.append("\nAU-12 -- Audit Record Generation:")
    if "skipped" in fb:
        lines.append(f"  Fluent Bit: {fb['skipped']}")
    else:
        lines.append(f"  Fluent Bit found: {fb.get('found', False)}")
        if fb.get("found"):
            lines.append(
                f"  Fluent Bit coverage: {fb.get('ready', 0)}/{fb.get('desired', 0)} nodes"
                f" (all covered: {fb.get('all_nodes_covered', False)})"
            )
    if "skipped" in loki:
        lines.append(f"  Loki: {loki['skipped']}")
    else:
        lines.append(f"  Loki found: {loki.get('found', False)}")
        if loki.get("found"):
            lines.append(f"  Loki pods: {loki.get('running_pods', 0)}/{loki.get('total_pods', 0)} running")
    if "skipped" in falco:
        lines.append(f"  Falco: {falco['skipped']}")
    else:
        lines.append(f"  Falco running: {falco.get('falco_running', False)}")
        if falco.get("falco_running"):
            lines.append(f"  Falco covers all nodes: {falco.get('expected_on_all_nodes', False)}")
    lines.append(f"  Pipeline complete: {au12.get('pipeline_complete', False)}")

    # EL signals
    signals = evidence.get("el_signals", {})
    lines.append("\nCOLLECTOR EL SIGNALS (starting point for assessment -- verify before finalizing):")
    lines.append(f"  Likely EL level: {signals.get('likely_el', 'Unknown')}")
    lines.append(f"  EL0 indicators: {signals.get('el0_indicators', [])}")
    lines.append(f"  EL1 satisfied: {signals.get('el1_satisfied', False)}")
    lines.append(f"  EL2 satisfied: {signals.get('el2_satisfied', False)}")
    lines.append(f"  EL3 satisfied: {signals.get('el3_satisfied', False)}")

    return "\n".join(lines)


def build_au_maturity_crew(evidence: dict, eng: dict) -> Crew:
    """
    Build the 3-agent AU logging maturity crew with pre-collected evidence.

    Agents:
      assessor   -- assigns EL level + S / OTS / NA per control, states the gap
      sar_writer -- compiles M-21-31 compliance report from assessor output
      poam_writer -- converts every OTS to a POA&M item with M-21-31 language
    """
    assess = assessor()
    sar = sar_writer()
    poam = poam_writer()

    system_name = eng.get("system_name", "Target System")
    cluster = eng.get("cluster", "unknown-cluster")
    analyst = eng.get("analyst", "beru:v1.6")
    assessment_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    evidence_text = _format_evidence_block(evidence)
    raw_json = json.dumps(evidence, indent=2)

    # Compute POA&M target dates (relative to today)
    today = datetime.now(timezone.utc).date()
    el2_deadline = (today + timedelta(days=180)).strftime("%Y-%m-%d")
    el3_deadline = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    # ------------------------------------------------------------------ #
    # Task 1: EL Level + Control Assessment                                #
    # ------------------------------------------------------------------ #
    assessment_task = Task(
        description=(
            f"Assess AU-family controls for M-21-31 compliance.\n"
            f"System: {system_name} | Cluster: {cluster} | Analyst: {analyst}\n"
            f"Assessment Date: {assessment_date}\n\n"
            f"Controls in scope: {', '.join(CONTROLS)}\n"
            f"Framework: M-21-31 (OMB Memorandum, August 2021)\n"
            f"Mandate baseline: EL2 (required by August 2022)\n\n"
            "=== M-21-31 MATURITY FRAMEWORK ===\n"
            f"{_EL_FRAMEWORK}\n\n"
            "=== CONTROL-LEVEL EL REQUIREMENTS ===\n"
            f"{_CONTROL_EL_REQUIREMENTS}\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (AWS CLI + kubectl, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS:\n"
            "1. The collector has provided a 'likely_el' signal as a starting point. "
            "   Use it as a hint, but verify against the raw evidence before finalizing.\n"
            "2. Assign an overall EL level (EL0 / EL1 / EL2 / EL3) with justification.\n"
            "3. For EACH control (AU-2, AU-3, AU-6, AU-7, AU-9, AU-11, AU-12), assign:\n"
            "   - Determination: Satisfied (S) / Other Than Satisfied (OTS) / Not Applicable (NA)\n"
            "   - EL requirement at current level vs. target EL2\n"
            "   - Specific gap if OTS (quote exact metric: 'retention is 7 days, EL2 requires 90')\n"
            "   - Severity: High / Medium / Low\n"
            "4. Flag whether the system meets the EL2 mandate minimum.\n"
            "5. OTS at EL2 threshold is High severity. OTS above EL2 is Medium. Below EL1 is Critical.\n"
        ),
        expected_output=(
            "1. OVERALL EL DETERMINATION: EL0 / EL1 / EL2 / EL3 (with 2-sentence justification)\n"
            "2. MANDATE STATUS: Meets EL2 mandate / Does not meet EL2 mandate\n"
            "3. CONTROL TABLE (one row per control):\n"
            "   CONTROL | DETERMINATION | EL REQUIREMENT | SPECIFIC FINDING | SEVERITY\n"
            "4. COUNT: X Satisfied, Y Other Than Satisfied, Z Not Applicable\n"
            "5. GAP SUMMARY: bullet list of what must be fixed to reach EL2, then EL3"
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: M-21-31 Compliance Report (SAR)                             #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the M-21-31 Logging Maturity Compliance Report for {system_name}.\n\n"
            "Controls assessed: AU-2, AU-3, AU-6, AU-7, AU-9, AU-11, AU-12\n\n"
            "The report must contain ALL of the following sections:\n\n"
            "1. SYSTEM IDENTIFICATION\n"
            f"   - System name: {system_name}\n"
            f"   - Cluster: {cluster}\n"
            f"   - Analyst: {analyst}\n"
            f"   - Assessment date: {assessment_date}\n"
            "   - Framework: M-21-31 (OMB Memorandum, August 2021)\n"
            "   - Mandate baseline: EL2 (required by August 2022)\n\n"
            "2. M-21-31 ASSESSMENT DATE AND SCOPE\n"
            "   - Date of evidence collection\n"
            "   - Tools used (AWS CLI, kubectl)\n"
            "   - Scope: EKS control plane logging, CloudTrail, CloudWatch log groups,\n"
            "     Fluent Bit pipeline, Loki/SIEM, Falco runtime detection\n\n"
            "3. CURRENT EL LEVEL\n"
            "   - EL level determined (EL0 / EL1 / EL2 / EL3)\n"
            "   - Justification (what evidence supports this level)\n"
            "   - Mandate compliance status: COMPLIANT / NON-COMPLIANT with EL2 mandate\n\n"
            "4. CONTROL-BY-CONTROL TABLE\n"
            "   Format: Control | Determination | EL Requirement | Finding\n"
            "   One row per control. OTS rows include specific gap from evidence.\n\n"
            "5. GAP SUMMARY\n"
            "   5a. Gaps to reach EL2 (mandate minimum) -- REQUIRED if system is below EL2\n"
            "   5b. Gaps to reach EL3 (full mandate) -- list even if EL2 is satisfied\n"
            "   Use specific metrics: 'Retention is 7 days -- EL2 requires 90 days'\n\n"
            "6. EVIDENCE REFERENCED\n"
            "   - List the collector functions that provided evidence\n"
            "   - Note any skipped collectors and why (AWS not configured, etc.)\n\n"
            "Write in formal GRC language. Reference exact metrics from the evidence "
            "(days of retention, pod counts, trail names). Do not editorialize."
        ),
        expected_output=(
            "A complete M-21-31 Logging Maturity Compliance Report in Markdown format "
            "with all six sections. Current EL level stated in section 3. "
            "Control table in section 4 with specific findings. "
            "Gap summaries use exact metric comparisons. "
            "Ready for attachment to the AU/CA evidence package."
        ),
        agent=sar,
        context=[assessment_task],
    )

    # ------------------------------------------------------------------ #
    # Task 3: POA&M Items                                                  #
    # ------------------------------------------------------------------ #
    poam_task = Task(
        description=(
            "Generate a POA&M item for every Other Than Satisfied (OTS) finding "
            "from the M-21-31 compliance report.\n\n"
            "CRITICAL: Use M-21-31 language, not just NIST control language.\n"
            "  WRONG: 'AU-11 retention is insufficient'\n"
            "  RIGHT: 'M-21-31 EL2 requires 90-day hot retention -- current retention is 7 days'\n\n"
            "POA&M required fields for each item:\n"
            "- control_id: AU-X\n"
            "- weakness_name: specific, not generic (e.g. 'Fluent Bit not deployed on worker nodes')\n"
            "- weakness_description: 2-3 sentences -- what is wrong, where, M-21-31 EL requirement "
            "  vs. current state (with exact metrics)\n"
            "- detection_method: gp-crewai au-collectors / BERU M-21-31 assessment\n"
            "- responsible_role: Platform Engineer / Security Engineer / Cloud Engineer\n"
            "- resources_required: effort estimate (e.g. '2 days Platform Engineer')\n"
            f"- scheduled_completion: EL2 gaps use {el2_deadline} (180 days). "
            f"  EL3 gaps use {el3_deadline} (365 days). High severity = 90 days max.\n"
            "- milestones: at least one checkpoint before completion date\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON.\n"
            "Every OTS from the report gets exactly one POA&M item. No exceptions."
        ),
        expected_output=(
            "A POA&M registry as a JSON array -- one object per OTS finding. "
            "All fields populated. weakness_description uses M-21-31 EL language with "
            "specific metrics. "
            "Followed by a summary: total items, High/Medium/Low breakdown, "
            "earliest and latest scheduled completion dates."
        ),
        agent=poam,
        context=[assessment_task, sar_task],
    )

    return Crew(
        agents=[assess, sar, poam],
        tasks=[assessment_task, sar_task, poam_task],
        process=Process.sequential,
        verbose=True,
    )


def run_au_crew(run_id: str | None = None) -> dict:
    """
    Full AU logging maturity pipeline: collect -> assess -> SAR -> POA&M.

    Returns the crew result plus raw evidence for archival.
    """
    run_ts = datetime.now(timezone.utc)
    if run_id is None:
        run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    eng = get_engagement_config()
    system_name = eng.get("system_name", "Target System")

    print(f"[{run_id}] Collecting AU evidence (AWS CLI + kubectl, no LLM)...")
    evidence = run_au_collectors()

    el_signal = evidence.get("el_signals", {}).get("likely_el", "Unknown")
    print(f"[{run_id}] Collector EL signal: {el_signal} (agents will verify)")

    print(f"[{run_id}] Running BERU crew: assessor -> sar_writer -> poam_writer...")
    crew = build_au_maturity_crew(evidence, eng)
    result = crew.kickoff()

    return {
        "run_id": run_id,
        "system": system_name,
        "cluster": eng.get("cluster"),
        "analyst": eng.get("analyst"),
        "framework": "M-21-31",
        "baseline": "EL2",
        "controls": CONTROLS,
        "collector_el_signal": el_signal,
        "raw_evidence": evidence,
        "crew_output": str(result),
    }


if __name__ == "__main__":
    output = run_au_crew()
    print(json.dumps({
        "run_id": output["run_id"],
        "system": output["system"],
        "framework": output["framework"],
        "collector_el_signal": output["collector_el_signal"],
    }, indent=2))
