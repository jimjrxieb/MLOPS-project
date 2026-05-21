"""
NIST AI RMF 1.0 Crew — AI Risk Management Framework assessment.

Framework: NIST AI RMF 1.0
Supplement: NIST AI 600-1 (Generative AI Profile)
Scope: All four AI RMF functions — GOVERN, MAP, MEASURE, MANAGE (52 subcategories total)

Architecture:
  Step 1 (collect) -- pure Python: kubectl + AWS CLI + filesystem. No LLM. See collectors.py.
  Step 2 (assess GOVERN/MAP) -- assessor agent: determines process artifact coverage.
                                CRITICAL: uses "Requires Process Review" (not Met/Not Met)
                                for subcategories in requires_process_review list.
  Step 3 (assess MEASURE/MANAGE) -- assessor agent: determines technical control coverage.
  Step 4 (report) -- sar_writer: structured AI RMF Assessment Report across all four functions.
  Step 5 (improve) -- poam_writer: MANAGE-4.2 improvement actions for each Not Met finding.

API-assessable vs. process-review boundary:
  This crew strictly enforces the boundary. Most GOVERN, MAP, and MANAGE subcategories
  are process artifacts (policies, risk documentation, stakeholder engagement records)
  that cannot be verified via kubectl or AWS CLI. Agents are explicitly instructed to
  use "Requires Process Review" for these items — never Met/Not Met/N/A.

Why Step 1 is not a CrewAI agent:
  Evidence collection is deterministic pattern matching — does this file exist?
  does this kubectl label appear? An LLM adds hallucination risk to yes/no checks.
  Collectors run deterministically and hand clean signals to agents for reasoning.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from crewai import Crew, Task, Process

# Resolve agents.py from beru/ root (two levels up from this file)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents import assessor, sar_writer, poam_writer  # noqa: E402

from config_loader import get_engagement_config  # noqa: E402

from .collectors import run_ai_rmf_collectors

# ── AI RMF function definitions ────────────────────────────────────────────────

_AI_RMF_FUNCTIONS = {
    "GOVERN": {
        "subcategories": 15,
        "focus": "Policies, accountability, organizational risk tolerance, team culture",
        "api_assessable": ["GOVERN-5.1 (HITL enforcement)", "GOVERN-6.1 (AI inventory)"],
        "process_review": ["GOVERN-1.1 through GOVERN-2.2 (12 subcategories)"],
    },
    "MAP": {
        "subcategories": 13,
        "focus": "System context, stakeholders, risk scenarios, human-AI interaction",
        "api_assessable": [
            "MAP-4.1 partial (RAG security signals)",
            "MAP-5.2 partial (monitoring existence)",
        ],
        "process_review": ["Most MAP subcategories require documentation and stakeholder review"],
    },
    "MEASURE": {
        "subcategories": 13,
        "focus": "AI evaluation, testing, benchmarking, trustworthy characteristics",
        "api_assessable": [
            "MEASURE-2.5 (red-team artifacts)",
            "MEASURE-2.6 (adversarial testing artifacts)",
            "MEASURE-2.x monitoring signals",
        ],
        "process_review": ["MEASURE-2.1 through MEASURE-2.4 (require eval methodology review)"],
    },
    "MANAGE": {
        "subcategories": 11,
        "focus": "Risk treatment, HITL, incidents, lifecycle improvement",
        "api_assessable": [
            "MANAGE-4.1 (incident log existence)",
            "MANAGE-4.2 partial (improvement evidence)",
        ],
        "process_review": ["MANAGE-1.x through MANAGE-3.x (require governance documentation review)"],
    },
}

_DETERMINATIONS = ["Met", "Partial", "Not Met", "N/A", "Requires Process Review"]


def _format_function_summary() -> str:
    """Render AI RMF function summary for assessor task context."""
    lines = ["NIST AI RMF 1.0 — Function and Subcategory Summary:"]
    for fn_name, info in _AI_RMF_FUNCTIONS.items():
        lines.append(f"  {fn_name} ({info['subcategories']} subcategories): {info['focus']}")
        if info["api_assessable"]:
            lines.append(f"    API-assessable: {', '.join(info['api_assessable'])}")
        if info["process_review"]:
            lines.append(f"    Process review: {', '.join(info['process_review'])}")
    return "\n".join(lines)


def _format_evidence_block(evidence: dict) -> str:
    """Render collected AI RMF evidence as readable text for task descriptions."""
    lines = []

    lines.append("=" * 70)
    lines.append("AI RMF COLLECTOR EVIDENCE SUMMARY")
    lines.append("=" * 70)
    lines.append(f"  Framework: {evidence.get('framework')}")
    lines.append(f"  Supplement: {evidence.get('supplement')}")

    lines.append("")
    lines.append("CRITICAL — ITEMS THAT CANNOT BE ASSESSED VIA API:")
    lines.append(
        "  (Agents MUST mark these 'Requires Process Review' — NEVER assign Met/Not Met/N/A)"
    )
    for item in evidence.get("requires_process_review", []):
        lines.append(f"  !! {item}")

    # AI Inventory (GOVERN-1.1, GOVERN-6.1)
    inv = evidence.get("ai_inventory", {})
    lines.append("")
    lines.append("GOVERN-6.1 / GOVERN-1.1 — AI System Inventory:")
    if "skipped" in inv or "error" in inv:
        lines.append(f"  {inv.get('skipped') or inv.get('error')}")
    else:
        lines.append(f"  Inventory file found: {inv.get('inventory_file_found')}")
        lines.append(f"  Inventory path: {inv.get('inventory_path') or '(none)'}")
        lines.append(f"  Model registry entries: {inv.get('model_registry_entries', 0)}")
        lines.append(f"  Model cards found: {inv.get('model_cards_found', 0)}")

    # HITL Enforcement (GOVERN-5.1)
    hitl = evidence.get("hitl_enforcement", {})
    lines.append("")
    lines.append("GOVERN-5.1 — HITL Enforcement:")
    if "skipped" in hitl or "error" in hitl:
        lines.append(f"  {hitl.get('skipped') or hitl.get('error')}")
    else:
        lines.append(f"  HITL code signals found: {hitl.get('hitl_code_found')}")
        if hitl.get("hitl_files"):
            lines.append(f"  HITL files: {hitl['hitl_files'][:5]}")
        lines.append(f"  Rank gating logic found: {hitl.get('rank_gating_found')}")
        lines.append(f"  Max authority (C-rank boundary) defined: {hitl.get('max_rank_defined')}")

    # Red-Team Artifacts (MEASURE-2.5, MEASURE-2.6)
    rt = evidence.get("redteam_artifacts", {})
    lines.append("")
    lines.append("MEASURE-2.5 / MEASURE-2.6 — Red-Team and Adversarial Testing Artifacts:")
    if "skipped" in rt or "error" in rt:
        lines.append(f"  {rt.get('skipped') or rt.get('error')}")
    else:
        lines.append(f"  Garak results found: {rt.get('garak_results_found')}")
        lines.append(f"  PyRIT results found: {rt.get('pyrit_results_found')}")
        lines.append(f"  Eval/benchmark artifacts found: {rt.get('eval_artifacts_found', 0)}")
        lines.append(
            f"  Days since last red-team artifact: "
            f"{rt.get('days_since_last_redteam', 'N/A')}"
        )
        lines.append(f"  Red-team coverage cadence: {rt.get('redteam_coverage')}")

    # Incident Management (MANAGE-4.1)
    inc = evidence.get("incident_management", {})
    lines.append("")
    lines.append("MANAGE-4.1 — AI Incident Log:")
    if "skipped" in inc or "error" in inc:
        lines.append(f"  {inc.get('skipped') or inc.get('error')}")
    else:
        lines.append(f"  Incident procedure document found: {inc.get('incident_procedure_found')}")
        lines.append(f"  Total AI incidents logged: {inc.get('total_incidents_logged', 0)}")
        lines.append(f"  Open incidents: {inc.get('open_incidents', 0)}")
        lines.append(f"  Incident log path: {inc.get('incident_log_path') or '(none)'}")

    # Monitoring Coverage (MEASURE-2.6, MAP-5.2)
    mon = evidence.get("monitoring", {})
    lines.append("")
    lines.append("MEASURE-2.6 / MAP-5.2 — Monitoring Coverage:")
    if "skipped" in mon or "error" in mon:
        lines.append(f"  {mon.get('skipped') or mon.get('error')}")
    else:
        lines.append(f"  Prometheus found: {mon.get('prometheus_found')}")
        lines.append(f"  Grafana found: {mon.get('grafana_found')}")
        lines.append(f"  Falco found: {mon.get('falco_found')}")
        lines.append(f"  MLflow experiment tracking found: {mon.get('mlflow_found')}")
        lines.append(
            f"  AI-specific monitoring deployments: {mon.get('ai_monitoring_deployments', [])}"
        )

    # AI Workload Security (GOVERN-5.1, MEASURE-2.6)
    ws = evidence.get("ai_workload_security", {})
    lines.append("")
    lines.append("GOVERN-5.1 / MEASURE-2.6 — AI Workload Security Posture:")
    if "skipped" in ws or "error" in ws:
        lines.append(f"  {ws.get('skipped') or ws.get('error')}")
    else:
        lines.append(f"  AI pods detected: {len(ws.get('ai_pods_found', []))}")
        lines.append(
            f"  AI pods without security context: {ws.get('pods_without_security_context', 0)}"
        )
        lines.append(
            f"  AI services exposed as LoadBalancer: {len(ws.get('ai_services_exposed', []))}"
        )
        lines.append(f"  GPU pods without resource limits: {ws.get('gpu_pods_without_limits', 0)}")
        if ws.get("ai_services_exposed"):
            for svc in ws["ai_services_exposed"][:5]:
                lines.append(f"    {svc.get('name')} (ns: {svc.get('namespace')})")

    # RAG Security (MAP-4.1, MANAGE-2.4)
    rag = evidence.get("rag_security", {})
    lines.append("")
    lines.append("MAP-4.1 / MANAGE-2.4 — RAG Pipeline Security:")
    if "skipped" in rag or "error" in rag:
        lines.append(f"  {rag.get('skipped') or rag.get('error')}")
    else:
        lines.append(f"  ChromaDB found: {rag.get('chroma_found')}")
        lines.append(f"  Collection count (parquet files): {rag.get('collection_count', 0)}")
        lines.append(f"  Ingestion audit logs found: {rag.get('ingest_logs_found')}")
        lines.append(f"  Hash verification in ingest pipeline: {rag.get('hash_verification_found')}")
        lines.append(f"  Provenance tracking in pipeline: {rag.get('provenance_tracking_found')}")

    return "\n".join(lines)


def run_ai_rmf_crew(run_id: str = None) -> dict:
    """
    Full NIST AI RMF 1.0 pipeline:
      collect -> GOVERN/MAP assess -> MEASURE/MANAGE assess -> SAR -> improvements.

    Returns structured result with function determinations, SAR, and improvement actions.
    """
    run_ts = datetime.now(timezone.utc)
    if run_id is None:
        run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    config = get_engagement_config()
    system_name = config.get("system_name", "Target System")
    cluster = config.get("cluster", "unknown-cluster")
    analyst = config.get("analyst", "beru:v1.6")
    assessment_date = run_ts.strftime("%Y-%m-%d")

    print(f"[{run_id}] Collecting AI RMF evidence (kubectl + AWS CLI + filesystem, no LLM)...")
    evidence = run_ai_rmf_collectors()

    process_review_items = evidence.get("requires_process_review", [])
    print(
        f"[{run_id}] Evidence collected. "
        f"Subcategories requiring process review: {len(process_review_items)} of 52"
    )
    print(f"[{run_id}] Running BERU crew: GOVERN/MAP assess -> MEASURE/MANAGE assess -> SAR -> improvements...")

    evidence_text = _format_evidence_block(evidence)
    raw_json = json.dumps(evidence, indent=2)
    function_summary = _format_function_summary()

    # POA&M target dates
    today = run_ts.date()
    critical_deadline = (today + timedelta(days=30)).strftime("%Y-%m-%d")   # GOVERN-5.1 HITL gap
    high_deadline = (today + timedelta(days=90)).strftime("%Y-%m-%d")       # MEASURE-2.5/2.6
    medium_deadline = (today + timedelta(days=180)).strftime("%Y-%m-%d")    # other findings

    process_review_str = "\n".join(f"    - {item}" for item in process_review_items)

    assess = assessor()
    sar = sar_writer()
    poam = poam_writer()

    # ------------------------------------------------------------------ #
    # Task 1: GOVERN + MAP Assessment                                      #
    # ------------------------------------------------------------------ #
    govern_map_assess_task = Task(
        description=(
            f"Assess NIST AI RMF 1.0 GOVERN and MAP functions for system: {system_name}\n"
            f"Cluster: {cluster} | Analyst: {analyst} | Assessment Date: {assessment_date}\n\n"
            "Framework: NIST AI RMF 1.0 | Supplement: NIST AI 600-1 (Generative AI)\n\n"
            f"{function_summary}\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (kubectl + filesystem, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS — GOVERN and MAP functions only:\n\n"
            "CRITICAL BOUNDARY — READ BEFORE ASSESSING:\n"
            "Items in requires_process_review CANNOT be determined from API/CLI evidence alone.\n"
            "For each of these, you MUST use determination: 'Requires Process Review — schedule "
            "documentation review and stakeholder interviews to complete assessment.'\n"
            "Do NOT assign Met, Not Met, Partial, or N/A to these items.\n"
            "Items requiring process review:\n"
            f"{process_review_str}\n\n"
            "For API-assessable GOVERN subcategories:\n\n"
            "GOVERN-5.1 (HITL enforcement):\n"
            "  - If hitl_enforcement.hitl_code_found is True AND rank_gating_found is True:\n"
            "    note this as a 'Met signal' but state: 'Full determination requires code review "
            "    and operational testing — mark Partial pending verification.'\n"
            "  - If neither is found: mark Not Met with evidence gap noted.\n"
            "  - If max_rank_defined is 'C-rank': note this supports the HITL boundary claim.\n\n"
            "GOVERN-6.1 (AI system inventory):\n"
            "  - If inventory_file_found is True OR model_registry_entries > 0: Partial "
            "    (registry exists but completeness requires document review).\n"
            "  - If model_cards_found > 0: note as supporting evidence.\n"
            "  - If both are zero/False: Not Met.\n\n"
            "For API-assessable MAP subcategories:\n\n"
            "MAP-4.1 (RAG data source traceability — proxy signal only):\n"
            "  - If rag_security.hash_verification_found is False: note as a gap signal "
            "    for MAP-4.1. Data poisoning protection absent is a traceability gap.\n"
            "  - If provenance_tracking_found is False: note as additional MAP-4.1 gap signal.\n"
            "  - Mark as Partial if one of the two is found, Not Met if neither.\n\n"
            "MAP-5.2 (monitoring practices existence — proxy signal only):\n"
            "  - If monitoring.prometheus_found or monitoring.falco_found: note as a Partial "
            "    signal (monitoring infrastructure exists but AI-specific scope unverified).\n"
            "  - If neither found: gap signal — requires process review for full determination.\n\n"
            "All other MAP subcategories: Requires Process Review.\n"
        ),
        expected_output=(
            "1. GOVERN FUNCTION ASSESSMENT TABLE:\n"
            "   SUBCATEGORY | DETERMINATION | EVIDENCE CITED | NOTES\n"
            "   Cover all 15 GOVERN subcategories.\n"
            "   Determinations: Met / Partial / Not Met / N/A / Requires Process Review\n"
            "   GOVERN-5.1 and GOVERN-6.1 must reference exact evidence field values.\n"
            "   All other GOVERN-1.x through GOVERN-2.x and GOVERN-5.2/6.2 must use "
            "   'Requires Process Review' with scheduling note.\n\n"
            "2. MAP FUNCTION ASSESSMENT TABLE:\n"
            "   SUBCATEGORY | DETERMINATION | EVIDENCE CITED | NOTES\n"
            "   Cover all 13 MAP subcategories.\n"
            "   MAP-4.1 and MAP-5.2 reference RAG security and monitoring evidence.\n"
            "   All other MAP subcategories use 'Requires Process Review'.\n\n"
            "3. GOVERN COUNT: X Met, Y Partial, Z Not Met, W Requires Process Review\n"
            "4. MAP COUNT: X Met, Y Partial, Z Not Met, W Requires Process Review\n"
            "5. KEY API-ASSESSABLE GAPS: bulleted list of Not Met findings with evidence"
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: MEASURE + MANAGE Assessment                                  #
    # ------------------------------------------------------------------ #
    measure_manage_assess_task = Task(
        description=(
            f"Assess NIST AI RMF 1.0 MEASURE and MANAGE functions for system: {system_name}\n"
            f"Cluster: {cluster} | Analyst: {analyst} | Assessment Date: {assessment_date}\n\n"
            "Framework: NIST AI RMF 1.0 | Supplement: NIST AI 600-1 (Generative AI)\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (kubectl + filesystem, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS — MEASURE and MANAGE functions only:\n\n"
            "CRITICAL BOUNDARY — READ BEFORE ASSESSING:\n"
            "Items in requires_process_review cannot be determined from API/CLI evidence alone.\n"
            "Mark those as 'Requires Process Review'. Do NOT assign Met/Not Met/Partial/N/A.\n"
            f"Process review items:\n{process_review_str}\n\n"
            "For API-assessable MEASURE subcategories:\n\n"
            "MEASURE-2.5 (red-team and evaluation artifacts):\n"
            "  - If redteam_artifacts.days_since_last_redteam > 90 OR redteam_coverage is "
            "    '> 90 days': Not Met — red-team cadence gap. Cite exact days value.\n"
            "  - If redteam_coverage is '30-90 days': Partial — artifacts exist but cadence "
            "    may be insufficient.\n"
            "  - If redteam_coverage is '< 30 days': Met.\n"
            "  - If redteam_coverage is 'No artifacts found': Not Met.\n\n"
            "MEASURE-2.6 (adversarial testing and monitoring metrics):\n"
            "  - Check both redteam_artifacts (garak_results_found, pyrit_results_found) "
            "    and monitoring (prometheus_found, falco_found).\n"
            "  - If neither prometheus_found nor falco_found is True: flag as a monitoring gap.\n"
            "  - If neither garak_results_found nor pyrit_results_found is True: adversarial "
            "    testing gap.\n"
            "  - Both gaps present: Not Met. One gap: Partial. Neither gap: Met.\n\n"
            "For API-assessable MANAGE subcategories:\n\n"
            "MANAGE-4.1 (post-deployment AI risk monitoring and incident tracking):\n"
            "  - If incident_management.incident_procedure_found is False: Not Met.\n"
            "  - If incident_procedure_found is True but total_incidents_logged is 0: Partial "
            "    (procedure exists but no incident records to verify it is operational).\n"
            "  - If both procedure and incident records exist: Partial "
            "    (full determination requires process review of record quality).\n\n"
            "MANAGE-4.2 (improvement actions — proxy from MLflow and eval artifacts):\n"
            "  - If monitoring.mlflow_found is True: note as improvement tracking signal.\n"
            "  - Partial if mlflow found + eval artifacts exist; otherwise Not Met signal.\n\n"
            "AI workload security (cross-cutting GOVERN-5.1 / MEASURE-2.6 overlap):\n"
            "  - If ai_workload_security.pods_without_security_context > 0: cite as MEASURE-2.6 "
            "    risk metric gap and GOVERN-5.1 enforcement gap.\n"
            "  - If gpu_pods_without_limits > 0: cite as resource risk (DoS vector).\n"
            "  - If ai_services_exposed list is non-empty: cite as attack surface finding.\n\n"
            "MANAGE-1.x through MANAGE-3.x: Requires Process Review.\n"
        ),
        expected_output=(
            "1. MEASURE FUNCTION ASSESSMENT TABLE:\n"
            "   SUBCATEGORY | DETERMINATION | EVIDENCE CITED | NOTES\n"
            "   Cover all 13 MEASURE subcategories.\n"
            "   MEASURE-2.5 and MEASURE-2.6 must reference exact redteam_coverage value "
            "   and days_since_last_redteam.\n"
            "   MEASURE-2.1 through MEASURE-2.4 use 'Requires Process Review'.\n\n"
            "2. MANAGE FUNCTION ASSESSMENT TABLE:\n"
            "   SUBCATEGORY | DETERMINATION | EVIDENCE CITED | NOTES\n"
            "   Cover all 11 MANAGE subcategories.\n"
            "   MANAGE-4.1 and MANAGE-4.2 reference incident and monitoring evidence.\n"
            "   MANAGE-1.x through MANAGE-3.x use 'Requires Process Review'.\n\n"
            "3. MEASURE COUNT: X Met, Y Partial, Z Not Met, W Requires Process Review\n"
            "4. MANAGE COUNT: X Met, Y Partial, Z Not Met, W Requires Process Review\n"
            "5. KEY API-ASSESSABLE GAPS: bulleted list of Not Met findings with evidence\n"
            "6. AI WORKLOAD SECURITY SIGNALS: summary of security posture findings"
        ),
        agent=assess,
        context=[govern_map_assess_task],
    )

    # ------------------------------------------------------------------ #
    # Task 3: Security Assessment Report                                    #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the NIST AI RMF 1.0 Assessment Report for {system_name}.\n\n"
            "Framework: NIST AI RMF 1.0 | Supplement: NIST AI 600-1\n"
            "Functions: GOVERN (15), MAP (13), MEASURE (13), MANAGE (11) — 52 subcategories total\n\n"
            "The Assessment Report must contain ALL of the following sections:\n\n"
            "1. EXECUTIVE SUMMARY\n"
            f"   - System: {system_name}\n"
            f"   - Cluster: {cluster}\n"
            f"   - Analyst: {analyst}\n"
            f"   - Assessment Date: {assessment_date}\n"
            "   - Framework: NIST AI RMF 1.0 (supplement: AI 600-1 Generative AI Profile)\n"
            "   - Assessment Method: Automated API-based evidence collection + expert analysis\n"
            "   - Overall posture per function: GOVERN / MAP / MEASURE / MANAGE determinations\n"
            "   - One paragraph formal GRC summary\n\n"
            "2. FUNCTION-BY-FUNCTION ASSESSMENT TABLE\n"
            "   One table covering all four functions:\n"
            "   | Function | Subcategories | Met | Partial | Not Met | Requires Process Review |\n"
            "   Pull counts from the assessor outputs for Tasks 1 and 2.\n\n"
            "3. KEY FINDINGS PER FUNCTION\n"
            "   For each function, list Not Met and Partial subcategories with:\n"
            "   - Subcategory ID and name\n"
            "   - Evidence cited (exact metric from collector output)\n"
            "   - Gap description\n"
            "   - Risk level (Critical / High / Medium)\n\n"
            "4. ITEMS REQUIRING PROCESS REVIEW\n"
            "   Dedicated section for the engagement team and system owner.\n"
            "   List every subcategory from requires_process_review.\n"
            "   Format as a checklist the team can hand to the AI system owner.\n"
            "   Include:\n"
            "     - Subcategory ID and name\n"
            "     - What artifact or process must be reviewed\n"
            "     - Which AI RMF function it satisfies\n"
            "   These subcategories are not assigned Met/Not Met in this automated assessment.\n\n"
            "5. RECOMMENDED ASSESSMENT SEQUENCE (for completing process review)\n"
            "   Phase 1 — Document review (1-2 days):\n"
            "     AI risk policies, model cards, risk register, accountability documentation\n"
            "   Phase 2 — Stakeholder interviews (2-3 days):\n"
            "     Team accountability structure, organizational risk tolerance, DEI policies\n"
            "   Phase 3 — Technical validation (1 day):\n"
            "     Verify and extend findings from the automated API collection\n\n"
            "6. NEXT STEPS (prioritized by risk)\n"
            "   Bulleted list of remediation priorities, highest risk first.\n"
            "   Include: what to fix, which subcategory it closes, effort estimate.\n\n"
            "Reference exact metrics from evidence. Write in formal GRC/AI governance language.\n"
            "Use AI RMF subcategory IDs (e.g., MEASURE-2.5). Do not editorialize.\n"
            "Format: Markdown, ready for attachment to the AI governance evidence package."
        ),
        expected_output=(
            "A complete NIST AI RMF 1.0 Assessment Report in Markdown format with all six "
            "sections. Executive summary includes function-level determinations. "
            "Function table covers all four functions with counts. "
            "Key findings reference exact evidence metrics. "
            "Process Review section formatted as a checklist for the engagement team. "
            "Recommended assessment sequence provides a realistic timeline. "
            "Next steps prioritized by risk level."
        ),
        agent=sar,
        context=[govern_map_assess_task, measure_manage_assess_task],
    )

    # ------------------------------------------------------------------ #
    # Task 4: Improvement Actions (MANAGE-4.2)                             #
    # ------------------------------------------------------------------ #
    improvement_task = Task(
        description=(
            "Generate improvement actions for every Not Met finding from the AI RMF "
            "Assessment Report.\n\n"
            "Use NIST AI RMF subcategory IDs in the control_id field "
            "(e.g., 'MEASURE-2.5').\n\n"
            "CRITICAL: For 'Requires Process Review' subcategories, do NOT create individual "
            "improvement items. Instead, create one summary note:\n"
            "  'Complete structured documentation review and stakeholder interviews to finalize "
            "  determinations for [list subcategories with Requires Process Review]. "
            "  Recommended timeline: 30 days. Assign to: AI Governance Lead.'\n\n"
            "For each Not Met finding, create a POA&M item:\n"
            "- control_id: AI RMF subcategory (e.g., 'MEASURE-2.5')\n"
            "- weakness_name: specific — include subcategory name\n"
            "  WRONG: 'Red-teaming not done'\n"
            "  RIGHT: 'MEASURE-2.5 — AI red-team evaluation artifacts absent or stale "
            "    (> 90 days since last adversarial test)'\n"
            "- weakness_description: 2-3 sentences — what is wrong, what AI RMF requires, "
            "  exact metric from evidence vs. requirement\n"
            "  Example: 'NIST AI RMF MEASURE-2.5 requires that AI risks and impacts are "
            "  evaluated through testing including adversarial red-teaming. No garak or PyRIT "
            "  result artifacts were found in the repository. The red-team coverage signal "
            "  is 'No artifacts found,' indicating no documented adversarial evaluation has "
            "  been performed against this AI system.'\n"
            "- detection_method: gp-crewai ai-rmf-collectors / BERU AI RMF 1.0 assessment\n"
            "- responsible_role: AI Engineer / AI Governance Lead / Platform Engineer\n"
            "- resources_required: effort estimate (e.g., '3 days AI Engineer — run garak "
            "  evaluation suite and archive results')\n"
            f"- scheduled_completion:\n"
            f"  Critical (GOVERN-5.1 HITL gap — blocks safe operation): {critical_deadline} (30 days)\n"
            f"  High (MEASURE-2.5/2.6 red-team and monitoring gaps): {high_deadline} (90 days)\n"
            f"  Medium (other Not Met findings): {medium_deadline} (180 days)\n"
            "- milestones: at least one checkpoint before the completion date\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON.\n"
            "Every Not Met finding gets exactly one improvement item. No exceptions.\n"
            "Do not create improvement items for 'Requires Process Review' determinations.\n"
            "End with the process-review summary note and a total count:\n"
            "total items, Critical/High/Medium breakdown, earliest and latest completion dates."
        ),
        expected_output=(
            "An improvement action registry as a JSON array — one object per Not Met finding. "
            "All fields populated. control_id uses AI RMF subcategory ID format (e.g. MEASURE-2.5). "
            "weakness_description cites specific evidence metrics and AI RMF subcategory requirement. "
            "Followed by the process-review summary note for subcategories requiring manual engagement. "
            "Followed by summary: total items, Critical/High/Medium breakdown, "
            "earliest and latest scheduled completion dates."
        ),
        agent=poam,
        context=[govern_map_assess_task, measure_manage_assess_task, sar_task],
    )

    crew = Crew(
        agents=[assess, sar, poam],
        tasks=[
            govern_map_assess_task,
            measure_manage_assess_task,
            sar_task,
            improvement_task,
        ],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    sar_raw = sar_task.output.raw if hasattr(sar_task, "output") else str(result)
    improvement_raw = improvement_task.output.raw if hasattr(improvement_task, "output") else ""

    return {
        "run_id": run_id,
        "framework": "NIST AI RMF 1.0",
        "supplement": "NIST AI 600-1",
        "system": system_name,
        "cluster": cluster,
        "analyst": analyst,
        "functions_assessed": list(_AI_RMF_FUNCTIONS.keys()),
        "api_assessed_count": len(evidence.get("ai_inventory", {})) + 3,  # approximate
        "process_review_required": len(evidence.get("requires_process_review", [])),
        "sar": sar_raw,
        "improvements": improvement_raw,
        "evidence_summary": {
            k: "collected"
            for k in evidence
            if not k.startswith("run") and k not in ("timestamp", "framework", "supplement",
                                                       "requires_process_review")
        },
    }


if __name__ == "__main__":
    import sys as _sys
    run_id = _sys.argv[1] if len(_sys.argv) > 1 else None
    result = run_ai_rmf_crew(run_id=run_id)
    print(json.dumps(
        {k: v for k, v in result.items() if k not in ("sar", "improvements")},
        indent=2,
    ))
