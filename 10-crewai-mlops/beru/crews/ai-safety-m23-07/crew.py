"""
AI Safety M-23-07 Crew — EO 14110 AI Safety compliance assessment.

Encodes the playbook at:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-23-07-playbooks/01-assess-ai-security-baseline.md

Architecture:
  Step 1 (collect) -- pure Python: kubectl + AWS CLI. No LLM.
  Step 2 (assess)  -- assessor agent: assigns EO section status per control.
                      CRITICAL: uses "Requires Process Review" (not S/OTS/NA) for
                      items in cannot_assess_via_api.
  Step 3 (report)  -- sar_writer: M-23-07 / EO 14110 compliance report with dedicated
                      "Items Requiring Manual Review" section.
  Step 4 (poam)    -- poam_writer: POA&M items with EO 14110 section language.

Controls: SA-11, RA-3, SI-4, CA-7, AC-6, SC-28
Framework: M-23-07 (OMB Memorandum implementing EO 14110)
Baseline: EO-14110-Section-4 (pre-deployment evaluation + risk assessment + monitoring)

Why Step 1 is not a CrewAI agent:
  AI workload detection is pattern matching against kubectl/AWS CLI output — deterministic.
  An LLM adds hallucination risk when the task is "does this image name contain 'pytorch'?"
  The collector runs deterministically and hands clean AI signals to the agents.
  Agents reason about the signals — they do not collect them.

API-assessable vs. process-review boundary:
  This crew strictly enforces the boundary. Many EO 14110 requirements are process
  artifacts (red-teaming reports, risk documentation, AI use case inventories) that
  cannot be verified via kubectl or AWS CLI. Agents are explicitly instructed to use
  "Requires Process Review" for these items — never S/OTS/NA.
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

from .collectors import run_ai_safety_collectors

CONTROLS = ["SA-11", "RA-3", "SI-4", "CA-7", "AC-6", "SC-28"]


# EO 14110 + NIST AI RMF framework definitions — baked into task descriptions
_EO_FRAMEWORK = """
EO 14110 / M-23-07 AI Safety Framework:

Section 4.1 — AI Safety and Security:
  Mandate: Agencies deploying dual-use AI must conduct pre-deployment safety evaluation
  including red-teaming. AI systems must implement least privilege access control and
  runtime isolation. Agencies must maintain records of pre-deployment safety evaluations.
  Controls: SA-11 (Developer Testing), AC-6 (Least Privilege)
  API-assessable proxy: AI workload security context, inference endpoint access control,
    CI/CD gate signals.
  NOT API-assessable: Red-teaming records, dual-use AI designation, CBRN uplift assessment.

Section 4.2 — AI Risk Assessment:
  Mandate: Agencies must conduct AI-specific risk assessments using NIST AI RMF.
  Model weights and training data must be protected (encryption at rest + access control).
  Agencies must maintain AI risk documentation.
  Controls: RA-3 (Risk Assessment), SC-28 (Protection at Rest)
  API-assessable: Model storage encryption, S3 bucket public access, SageMaker VPC config.
  NOT API-assessable: AI risk documentation, NIST AI RMF artifacts, risk acceptance records.

Section 4.3 — AI Transparency and Monitoring:
  Mandate: Agencies must maintain an inventory of AI use cases. AI systems used in
  consequential decisions must be monitored. Agencies must report AI incidents.
  Controls: SI-4 (System Monitoring), CA-7 (Continuous Monitoring)
  API-assessable: Falco deployment, Prometheus/SIEM, SecurityHub, GuardDuty.
  NOT API-assessable: AI use case inventory, consequential-decision classification,
    AI incident reporting process.

NIST AI RMF Integration (AI 600-1):
  GOVERN: AI risk governance — policies, roles, accountability structures.
  MAP:    AI context identification — use cases, risk categories, impacted populations.
  MEASURE: AI risk analysis — testing, red-teaming, bias evaluation, monitoring metrics.
  MANAGE:  AI risk treatment — mitigations, incident response, recovery procedures.

NIST AI 600-1 High-Priority Risk Categories:
  - Hallucination and fabrication (affects consequential decisions)
  - Prompt injection and jailbreaking (security boundary violation)
  - Training data poisoning (integrity risk to model behavior)
  - Model inversion and extraction (confidentiality risk)
  - Insecure output handling (downstream injection risk)
  - CBRN uplift potential (dual-use designation trigger)
"""

# Per-control EO requirements
_CONTROL_EO_REQUIREMENTS = """
Control-by-control EO 14110 / M-23-07 requirements:

SA-11 (Developer Testing and Evaluation):
  EO 4.1 mandate: Pre-deployment safety evaluation including red-teaming for dual-use AI.
  API-assessable: CI/CD security gate signals, presence of testing infrastructure.
  NOT assessable via API: Red-teaming records, evaluation reports, test methodology docs.
  Gap indicators: No CI/CD security gates detected; AI workloads deployed without test signals.

AC-6 (Least Privilege):
  EO 4.1 mandate: AI systems must operate under least privilege — no unnecessary access.
  API-assessable: AI pod security context (root, privileged), inference endpoint exposure.
  Gap indicators: AI containers running as root, privileged AI pods, unauthenticated
    inference endpoints externally exposed, AI pods with hostNetwork or hostPath.

RA-3 (Risk Assessment):
  EO 4.2 mandate: AI-specific risk assessment using NIST AI RMF before deployment.
  API-assessable: AWS managed AI service configuration (SageMaker VPC, Bedrock guardrails).
  NOT assessable via API: Risk assessment documents, NIST AI RMF artifacts, risk records.
  Gap indicators: SageMaker with direct internet access; Bedrock without guardrails.

SC-28 (Protection at Rest):
  EO 4.2 mandate: Model weights and training data must be encrypted at rest.
  API-assessable: S3 bucket encryption, public access block, SageMaker KMS config, PVC storage class.
  Gap indicators: Unencrypted S3 buckets with model name signals; publicly accessible model storage.

SI-4 (System Monitoring):
  EO 4.3 mandate: AI systems in consequential decisions must be monitored for anomalous behavior.
  API-assessable: Falco deployment, AI-specific Falco rules, Prometheus, SecurityHub, GuardDuty.
  NOT assessable via API: Consequential-decision classification, monitoring scope definition.
  Gap indicators: No runtime detection (Falco absent); no metrics collection on AI pods.

CA-7 (Continuous Monitoring):
  EO 4.3 mandate: Ongoing AI risk tracking — not a one-time assessment.
  API-assessable: Security Hub, GuardDuty, Prometheus continuous collection signals.
  NOT assessable via API: AI incident reporting process, AI use case inventory currency.
  Gap indicators: No SecurityHub; no GuardDuty; no behavioral baseline configured.
"""


def _format_evidence_block(evidence: dict) -> str:
    """Render collected AI safety evidence as readable text for task descriptions."""
    lines = []

    # ── AI Signals Summary ─────────────────────────────────────────────────────
    signals = evidence.get("ai_signals", {})
    lines.append("=" * 70)
    lines.append("COLLECTOR AI SIGNALS SUMMARY")
    lines.append("=" * 70)
    lines.append(f"  AI workloads detected: {signals.get('ai_workloads_detected', False)}")
    lines.append(f"  AI workload count: {signals.get('ai_workload_count', 0)}")
    lines.append(f"  AWS managed AI detected: {signals.get('aws_managed_ai_detected', False)}")

    section_compliance = signals.get("section_compliance", {})
    lines.append(f"  EO §4.1 collector status: {section_compliance.get('4.1', 'unknown')}")
    lines.append(f"  EO §4.2 collector status: {section_compliance.get('4.2', 'unknown')}")
    lines.append(f"  EO §4.3 collector status: {section_compliance.get('4.3', 'unknown')}")

    lines.append("")
    lines.append("CRITICAL — ITEMS THAT CANNOT BE ASSESSED VIA API:")
    lines.append("  (Agents MUST mark these 'Requires Process Review' — NEVER assign S/OTS/NA)")
    for item in signals.get("cannot_assess_via_api", []):
        lines.append(f"  !! {item}")

    if signals.get("critical_findings"):
        lines.append("")
        lines.append("API-ASSESSABLE CRITICAL FINDINGS:")
        for finding in signals["critical_findings"]:
            lines.append(f"  [CRITICAL] {finding}")

    # ── EO 4.1: Safety and Security ───────────────────────────────────────────
    eo41 = evidence.get("eo_4_1_safety", {})
    lines.append("")
    lines.append("EO §4.1 — AI Safety and Security:")

    workloads = eo41.get("ai_workloads", {})
    if "skipped" in workloads:
        lines.append(f"  AI workload detection: {workloads['skipped']}")
    else:
        lines.append(f"  AI pods detected: {workloads.get('ai_workload_count', 0)}")
        lines.append(f"  AI namespaces: {workloads.get('ai_namespaces', [])}")
        lines.append(f"  GPU nodes: {workloads.get('gpu_node_count', 0)}")
        lines.append(f"  Model serving endpoints (AI port signals): "
                     f"{len(workloads.get('model_serving_endpoints', []))}")

    exposure = eo41.get("inference_endpoint_exposure", {})
    if "skipped" in exposure:
        lines.append(f"  Endpoint exposure: {exposure['skipped']}")
    else:
        lines.append(f"  Externally exposed services: {len(exposure.get('exposed_services', []))}")
        lines.append(f"  LoadBalancer AI endpoints: "
                     f"{len(exposure.get('loadbalancer_inference_endpoints', []))}")
        lines.append(f"  Ingress AI endpoints: {len(exposure.get('ingress_ai_endpoints', []))}")
        lines.append(f"  Unauthenticated endpoints detected: "
                     f"{exposure.get('unauthenticated_endpoints_detected', False)}")

    sec_ctx = eo41.get("ai_security_context", {})
    if "skipped" in sec_ctx:
        lines.append(f"  AI security context: {sec_ctx['skipped']}")
    else:
        lines.append(f"  AI pods running as root: {len(sec_ctx.get('ai_pods_running_as_root', []))}")
        lines.append(f"  AI pods privileged: {len(sec_ctx.get('ai_pods_privileged', []))}")
        lines.append(f"  AI pods without resource limits: "
                     f"{len(sec_ctx.get('ai_pods_without_resource_limits', []))}")
        lines.append(f"  AI pods with hostNetwork: {len(sec_ctx.get('ai_pods_with_host_network', []))}")
        lines.append(f"  AI pods with hostPath: {len(sec_ctx.get('ai_pods_with_host_path', []))}")

    cicd = eo41.get("cicd_gates", {})
    if "skipped" in cicd:
        lines.append(f"  CI/CD gates: {cicd['skipped']}")
    else:
        lines.append(f"  GitHub Actions detected (proxy): {cicd.get('github_actions_detected', False)}")
        lines.append(f"  Security scan in CI/CD (proxy): {cicd.get('security_scan_in_cicd', False)}")
        lines.append(f"  CI/CD credential secrets found: "
                     f"{len(cicd.get('ci_credential_secrets_found', []))}")
        lines.append(f"  Note: {cicd.get('note', '')}")

    # ── EO 4.2: Risk Assessment ───────────────────────────────────────────────
    eo42 = evidence.get("eo_4_2_risk", {})
    lines.append("")
    lines.append("EO §4.2 — AI Risk Assessment:")

    storage = eo42.get("model_storage", {})
    if "skipped" in storage:
        lines.append(f"  Model storage: {storage['skipped']}")
    else:
        lines.append(f"  S3 buckets with model signals: "
                     f"{len(storage.get('s3_buckets_with_model_signals', []))}")
        lines.append(f"  Unencrypted model storage: {storage.get('unencrypted_model_storage', 0)}")
        lines.append(f"  Publicly accessible model storage: "
                     f"{storage.get('publicly_accessible_model_storage', 0)}")
        lines.append(f"  PVCs with model signals: {len(storage.get('pvc_with_model_signals', []))}")

    aws_ai = eo42.get("aws_ai_services", {})
    if "skipped" in aws_ai:
        lines.append(f"  AWS AI services: {aws_ai['skipped']}")
    else:
        lines.append(f"  SageMaker domains: {len(aws_ai.get('sagemaker_domains', []))}")
        lines.append(f"  Bedrock foundation models enabled: "
                     f"{len(aws_ai.get('bedrock_model_access', []))}")
        lines.append(f"  Bedrock guardrails configured: "
                     f"{aws_ai.get('bedrock_guardrails_configured', False)}")
        lines.append(f"  SageMaker VPC-only (no direct internet): "
                     f"{aws_ai.get('sagemaker_vpc_only', True)}")
        lines.append(f"  Rekognition in use: {aws_ai.get('rekognition_in_use', False)}")
        lines.append(f"  Comprehend in use: {aws_ai.get('comprehend_in_use', False)}")

    # ── EO 4.3: Monitoring ────────────────────────────────────────────────────
    eo43 = evidence.get("eo_4_3_monitoring", {})
    lines.append("")
    lines.append("EO §4.3 — AI Transparency and Monitoring:")

    monitoring = eo43.get("monitoring_for_ai", {})
    if "skipped" in monitoring:
        lines.append(f"  Monitoring: {monitoring['skipped']}")
    else:
        lines.append(f"  Falco running: {monitoring.get('falco_running', False)}")
        lines.append(f"  Falco AI-specific rules detected: "
                     f"{monitoring.get('falco_ai_rules_detected', False)}")
        lines.append(f"  Prometheus running: {monitoring.get('prometheus_running', False)}")
        lines.append(f"  Model metrics endpoints (/metrics on AI pods): "
                     f"{len(monitoring.get('model_metrics_endpoints', []))}")
        lines.append(f"  Behavioral baseline configured: "
                     f"{monitoring.get('behavioral_baseline_configured', False)}")
        lines.append(f"  AWS SecurityHub enabled: {monitoring.get('security_hub_enabled', False)}")
        lines.append(f"  AWS GuardDuty enabled: {monitoring.get('guardduty_enabled', False)}")

    return "\n".join(lines)


def build_ai_safety_crew(evidence: dict, eng: dict) -> Crew:
    """
    Build the 3-agent AI Safety crew with pre-collected evidence.

    Agents:
      assessor   -- assigns EO section status per control; uses "Requires Process Review"
                    for items in cannot_assess_via_api (never S/OTS/NA for those)
      sar_writer -- M-23-07 / EO 14110 compliance report with dedicated manual review section
      poam_writer -- POA&M items using EO 14110 section language for each gap
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

    # POA&M target dates
    today = datetime.now(timezone.utc).date()
    short_deadline = (today + timedelta(days=90)).strftime("%Y-%m-%d")
    medium_deadline = (today + timedelta(days=180)).strftime("%Y-%m-%d")
    long_deadline = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    cannot_assess = evidence.get("ai_signals", {}).get("cannot_assess_via_api", [])
    cannot_assess_str = "\n".join(f"    - {item}" for item in cannot_assess)

    # ------------------------------------------------------------------ #
    # Task 1: EO Section + Control Assessment                              #
    # ------------------------------------------------------------------ #
    assessment_task = Task(
        description=(
            f"Assess AI Safety controls for M-23-07 / EO 14110 compliance.\n"
            f"System: {system_name} | Cluster: {cluster} | Analyst: {analyst}\n"
            f"Assessment Date: {assessment_date}\n\n"
            f"Controls in scope: {', '.join(CONTROLS)}\n"
            "Framework: M-23-07 (OMB Memorandum implementing EO 14110)\n"
            "Baseline: EO 14110 Sections 4.1, 4.2, 4.3\n\n"
            "=== EO 14110 / M-23-07 FRAMEWORK ===\n"
            f"{_EO_FRAMEWORK}\n\n"
            "=== CONTROL-LEVEL EO REQUIREMENTS ===\n"
            f"{_CONTROL_EO_REQUIREMENTS}\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (kubectl + AWS CLI, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS:\n\n"
            "CRITICAL BOUNDARY — READ BEFORE ASSESSING:\n"
            "The following items CANNOT be assessed via kubectl or AWS CLI.\n"
            "For each of these, you MUST use determination: 'Requires Process Review'.\n"
            "Do NOT assign Satisfied (S), Other Than Satisfied (OTS), or Not Applicable (NA).\n"
            "Items requiring process review:\n"
            f"{cannot_assess_str}\n\n"
            "For items the collectors CAN verify, follow these instructions:\n"
            "1. Assess each EO section (4.1, 4.2, 4.3) holistically — what did the "
            "   collectors find, what does it mean for EO compliance?\n"
            "2. For EACH control (SA-11, RA-3, SI-4, CA-7, AC-6, SC-28), assign:\n"
            "   - Determination: Satisfied (S) / Other Than Satisfied (OTS) / "
            "     Not Applicable (NA) / Requires Process Review\n"
            "   - EO section and mandate it maps to\n"
            "   - Specific gap if OTS (quote exact metric from evidence)\n"
            "   - Whether this is API-assessable or requires process review\n"
            "   - Severity for OTS items: Critical / High / Medium / Low\n"
            "3. Collector status signals ('assessable_gap', 'assessable_compliant', "
            "   'requires_process_review') are starting points — verify against raw evidence.\n"
            "4. If no AI workloads are detected and no AWS managed AI is configured, "
            "   note this — EO 14110 may be NA for this system (but confirm via process review).\n"
        ),
        expected_output=(
            "1. AI WORKLOAD PRESENCE: AI workloads detected / Not detected / Unknown\n"
            "2. EO SECTION TABLE (one row per section):\n"
            "   SECTION | TITLE | API-ASSESSABLE | STATUS | KEY FINDING\n"
            "   Use: Compliant / Gap Found / Requires Process Review\n"
            "3. CONTROL TABLE (one row per control):\n"
            "   CONTROL | EO SECTION | DETERMINATION | SPECIFIC FINDING | SEVERITY\n"
            "   Valid determinations: S / OTS / NA / Requires Process Review\n"
            "4. COUNT: X Satisfied, Y OTS, Z Requires Process Review, W Not Applicable\n"
            "5. ITEMS REQUIRING PROCESS REVIEW: bullet list of what the engagement team\n"
            "   must verify through document review and interviews\n"
            "6. GAP SUMMARY: bullet list of API-assessable gaps ranked by severity"
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: M-23-07 / EO 14110 Compliance Report (SAR)                  #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the M-23-07 / EO 14110 AI Safety Compliance Report for {system_name}.\n\n"
            "Controls assessed: SA-11, RA-3, SI-4, CA-7, AC-6, SC-28\n\n"
            "The report must contain ALL of the following sections:\n\n"
            "1. SYSTEM IDENTIFICATION\n"
            f"   - System name: {system_name}\n"
            f"   - Cluster: {cluster}\n"
            f"   - Analyst: {analyst}\n"
            f"   - Assessment date: {assessment_date}\n"
            "   - Framework: M-23-07 (implementing EO 14110)\n"
            "   - Scope: EO 14110 Sections 4.1, 4.2, 4.3\n\n"
            "2. AI WORKLOAD INVENTORY\n"
            "   - AI workloads detected (from collectors): count, namespaces, signals\n"
            "   - AWS managed AI services detected: SageMaker, Bedrock, Rekognition, Comprehend\n"
            "   - GPU node count\n"
            "   - Note: Full AI use case inventory requires process review (not API-assessable)\n\n"
            "3. EO SECTION ASSESSMENT TABLE\n"
            "   Format: Section | API-Assessable | Status | Key Finding\n"
            "   Sections: 4.1 (Safety), 4.2 (Risk), 4.3 (Monitoring)\n"
            "   Status options: Compliant / Gap Found / Requires Process Review\n\n"
            "4. CONTROL-BY-CONTROL TABLE\n"
            "   Format: Control | EO Section | Determination | EO Mandate | Finding\n"
            "   OTS rows include specific gap from evidence with exact metrics.\n"
            "   'Requires Process Review' rows explain what must be reviewed.\n\n"
            "5. ITEMS REQUIRING MANUAL REVIEW (separate, prominent section)\n"
            "   This section is for the engagement team. List every item that cannot be\n"
            "   assessed via API, what artifact or process must be reviewed, and which\n"
            "   EO section it satisfies. Format as a checklist the team can hand to the\n"
            "   system owner.\n\n"
            "6. GAP SUMMARY\n"
            "   6a. API-assessable gaps (found by collectors) — ranked by severity\n"
            "   6b. Gaps requiring process review — listed for engagement team action\n\n"
            "7. EVIDENCE REFERENCED\n"
            "   - Collector functions that provided evidence\n"
            "   - Any skipped collectors and reason\n"
            "   - Note that process artifacts (red-teaming records, risk docs) are NOT\n"
            "     included in this API-based evidence run\n\n"
            "Write in formal GRC language. Use EO 14110 section citations (e.g., 'EO 14110 §4.1').\n"
            "Reference exact metrics from evidence. Do not editorialize.\n"
            "The 'Items Requiring Manual Review' section must be actionable — "
            "not a list of unknowns, but a checklist of specific artifacts to request."
        ),
        expected_output=(
            "A complete M-23-07 / EO 14110 AI Safety Compliance Report in Markdown format "
            "with all seven sections. AI workload inventory in section 2. "
            "EO section assessment table in section 3. "
            "Control table in section 4 with specific findings and EO citations. "
            "Dedicated 'Items Requiring Manual Review' section (5) formatted as an "
            "engagement team checklist. "
            "Gap summaries in section 6 separated by API-assessable vs. process-review. "
            "Ready for attachment to the CA/SA evidence package."
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
            "from the M-23-07 / EO 14110 compliance report.\n\n"
            "CRITICAL: Use EO 14110 section language, not just NIST control language.\n"
            "  WRONG: 'AC-6 least privilege not enforced'\n"
            "  RIGHT: 'EO 14110 §4.1 requires AI system least privilege access control — "
            "    AI containers detected running as root with no runAsNonRoot enforcement'\n\n"
            "For 'Requires Process Review' items: do NOT create a POA&M item. Instead,\n"
            "create a single summary note: 'Process review items require engagement team\n"
            "action — see SAR Section 5 for checklist.' One note, not individual items.\n\n"
            "POA&M required fields for each OTS item:\n"
            "- control_id: CONTROL-ID (e.g. AC-6)\n"
            "- weakness_name: specific, not generic "
            "  (e.g. 'AI inference containers running as root — EO 14110 §4.1 isolation gap')\n"
            "- weakness_description: 2-3 sentences — what is wrong, EO section mandate, "
            "  exact metric from evidence vs. requirement\n"
            "- detection_method: gp-crewai ai-safety-collectors / BERU M-23-07 assessment\n"
            "- responsible_role: Platform Engineer / Security Engineer / AI Engineer\n"
            "- resources_required: effort estimate (e.g. '1 day AI Engineer')\n"
            f"- scheduled_completion: Critical findings use {short_deadline} (90 days). "
            f"  High severity use {medium_deadline} (180 days). "
            f"  Medium severity use {long_deadline} (365 days).\n"
            "- milestones: at least one checkpoint before completion date\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON.\n"
            "Every OTS finding gets exactly one POA&M item. No exceptions.\n"
            "Do not create POA&M items for 'Requires Process Review' determinations."
        ),
        expected_output=(
            "A POA&M registry as a JSON array — one object per OTS finding. "
            "All fields populated. weakness_description uses EO 14110 section language "
            "with specific metrics from evidence. "
            "Followed by a process-review note for items requiring manual engagement. "
            "Followed by a summary: total items, Critical/High/Medium/Low breakdown, "
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


def run_ai_safety_crew(run_id: str | None = None) -> dict:
    """
    Full AI Safety pipeline: collect -> assess -> SAR -> POA&M.

    Returns the crew result plus raw evidence for archival.
    Framework: M-23-07 / EO 14110 Sections 4.1, 4.2, 4.3.
    """
    run_ts = datetime.now(timezone.utc)
    if run_id is None:
        run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    eng = get_engagement_config()
    system_name = eng.get("system_name", "Target System")

    print(f"[{run_id}] Collecting AI Safety evidence (kubectl + AWS CLI, no LLM)...")
    evidence = run_ai_safety_collectors()

    ai_signals = evidence.get("ai_signals", {})
    ai_count = ai_signals.get("ai_workload_count", 0)
    aws_ai = ai_signals.get("aws_managed_ai_detected", False)
    section_status = ai_signals.get("section_compliance", {})
    cannot_assess_count = len(ai_signals.get("cannot_assess_via_api", []))

    print(f"[{run_id}] AI workloads detected: {ai_count} | AWS managed AI: {aws_ai}")
    print(f"[{run_id}] EO §4.1: {section_status.get('4.1')} | "
          f"§4.2: {section_status.get('4.2')} | §4.3: {section_status.get('4.3')}")
    print(f"[{run_id}] Items requiring process review: {cannot_assess_count} "
          "(agents will flag, not hallucinate)")

    print(f"[{run_id}] Running BERU crew: assessor -> sar_writer -> poam_writer...")
    crew = build_ai_safety_crew(evidence, eng)
    result = crew.kickoff()

    return {
        "run_id": run_id,
        "system": system_name,
        "cluster": eng.get("cluster"),
        "analyst": eng.get("analyst"),
        "framework": "M-23-07",
        "baseline": "EO-14110-Section-4",
        "controls": CONTROLS,
        "ai_signals": ai_signals,
        "raw_evidence": evidence,
        "crew_output": str(result),
    }


if __name__ == "__main__":
    output = run_ai_safety_crew()
    print(json.dumps({
        "run_id": output["run_id"],
        "system": output["system"],
        "framework": output["framework"],
        "ai_workloads_detected": output["ai_signals"].get("ai_workloads_detected"),
        "ai_workload_count": output["ai_signals"].get("ai_workload_count"),
        "aws_managed_ai_detected": output["ai_signals"].get("aws_managed_ai_detected"),
        "section_compliance": output["ai_signals"].get("section_compliance"),
        "cannot_assess_count": len(output["ai_signals"].get("cannot_assess_via_api", [])),
        "critical_findings": output["ai_signals"].get("critical_findings"),
    }, indent=2))
