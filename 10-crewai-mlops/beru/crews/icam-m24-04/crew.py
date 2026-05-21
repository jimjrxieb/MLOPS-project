"""
ICAM M-24-04 Crew -- OMB Memorandum M-24-04 ICAM compliance assessment.

Encodes the playbook at:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-24-04-playbooks/01-implement-icam-authentication.md

Architecture:
  Step 1 (collect) -- pure Python: AWS CLI + kubectl. No LLM.
  Step 2 (assess)  -- assessor agent: assigns service compliance + S/OTS/NA per control.
  Step 3 (report)  -- sar_writer: M-24-04 ICAM compliance report.
  Step 4 (poam)    -- poam_writer: POA&M items for each mandate gap.

Controls: IA-2, IA-4, IA-5, AC-2, AC-6, AC-17, SC-8
Framework: M-24-04 (OMB Memorandum, February 2024)
Baseline: ICAM-Mandate -- phishing-resistant MFA + no long-lived static credentials

Why Step 1 is not a CrewAI agent:
  AWS IAM and kubectl output is structured data. An LLM adds nothing to data
  collection and introduces failure modes (hallucinated resource names, ReAct
  loop confusion). The collector runs deterministically and hands clean ICAM
  signals to the agents.

IDENTITY PROOFING (IA-4) BOUNDARY:
  IAL2 identity proofing cannot be assessed via API. The collectors flag this
  explicitly. The assessor agent will mark IA-4 as "requires process review"
  and the SAR will note that human audit of onboarding documentation is required.
  This is not an evasion -- it is an honest boundary of automated assessment.
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

from .collectors import run_icam_collectors

CONTROLS = ["IA-2", "IA-4", "IA-5", "AC-2", "AC-6", "AC-17", "SC-8"]


# M-24-04 ICAM service framework -- baked into task descriptions
_ICAM_FRAMEWORK = """
M-24-04 ICAM Services (OMB Memorandum, February 2024):

Authentication (IA-2):
  Mandate: Phishing-resistant MFA required for ALL federal users by FY2024.
  Phishing-resistant = FIDO2/WebAuthn hardware tokens OR PIV/CAC smart cards.
  NON-COMPLIANT: TOTP apps (Google Authenticator, Authy), SMS codes, push notifications.
  COMPLIANT: FIDO2 hardware keys (YubiKey, etc.), PIV/CAC cards.
  Note: OIDC configuration on a cluster is a federation signal (AC-17), not MFA evidence.

Identity Proofing (IA-4):
  Mandate: IAL2 identity proofing required before privileged account creation.
  IAL2: Government-issued ID verified against authoritative source; proofing record retained.
  CANNOT BE ASSESSED VIA API: Proofing is a process/documentation control, not a
  system configuration. Assessment requires human review of HR onboarding records,
  identity proofing system logs, and process documentation.
  Assessor must flag this as "requires process review" -- do not mark S or OTS from API data alone.

Credentialing (IA-5):
  Mandate: No long-lived static credentials. Automated credential rotation required.
  NON-COMPLIANT: IAM users with long-term access keys (especially >90 days old).
  NON-COMPLIANT: Kubernetes service-account-token type secrets (legacy static tokens).
  COMPLIANT: IRSA (IAM Roles for Service Accounts), instance profiles, managed identities.
  COMPLIANT: Automated key rotation via Secrets Manager or equivalent.

Authorization (AC-2, AC-6):
  Mandate: Full account lifecycle (provision, review, deprovision); no standing privileged access.
  Privileged accounts must be reviewed quarterly. Attribute-based access control preferred.
  NON-COMPLIANT: Manual account management, no review cycle, accounts inactive 90+ days.
  NON-COMPLIANT: Wildcard IAM/K8s permissions, privileged containers, standing admin access.
  COMPLIANT: Automated lifecycle, RBAC least-privilege, periodic access reviews documented.

Federation (AC-17, SC-8):
  Mandate: SAML 2.0 or OIDC federation for cross-agency access; TLS on all auth flows.
  NON-COMPLIANT: Local accounts for cross-agency access, HTTP authentication flows.
  NON-COMPLIANT: Proprietary SSO silos with no federation capability.
  COMPLIANT: AWS IAM OIDC providers configured; SAML IdP integration; TLS on all ingress.
"""

# Per-control M-24-04 requirements
_CONTROL_ICAM_REQUIREMENTS = {
    "IA-2": {
        "icam_service": "Authentication",
        "mandate": "Phishing-resistant MFA (FIDO2/WebAuthn or PIV/CAC) for all users by FY2024",
        "satisfied_signal": "All console users have MFA enabled; MFA devices are FIDO2/U2F type",
        "ots_signal": "Console users without MFA OR users with TOTP/virtual MFA only",
    },
    "IA-4": {
        "icam_service": "Identity_Proofing",
        "mandate": "IAL2 identity proofing before privileged account creation",
        "satisfied_signal": "Human review confirms IAL2 process documentation and proofing records exist",
        "ots_signal": "No proofing documentation found OR process review not completed",
        "api_limitation": (
            "CANNOT be assessed via API. Assessor must assign determination of "
            "'Requires Process Review' -- neither S nor OTS can be assigned from API data alone."
        ),
    },
    "IA-5": {
        "icam_service": "Credentialing",
        "mandate": "No long-lived static credentials; automated rotation required",
        "satisfied_signal": "No IAM keys >90 days; no kubernetes.io/service-account-token secrets; IRSA in use",
        "ots_signal": "IAM keys older than 90 days OR long-lived SA token secrets present",
    },
    "AC-2": {
        "icam_service": "Authorization",
        "mandate": "Full account lifecycle; no accounts inactive 90+ days without deprovisioning evidence",
        "satisfied_signal": "No stale users; all users in groups (managed lifecycle); orphaned bindings resolved",
        "ots_signal": "Stale accounts present OR users without group membership (no lifecycle policy)",
    },
    "AC-6": {
        "icam_service": "Authorization",
        "mandate": "Least privilege; no wildcard permissions; no standing privileged access",
        "satisfied_signal": "No wildcard ClusterRoles; no privileged containers; runAsNonRoot enforced",
        "ots_signal": "Wildcard permissions found OR privileged containers running",
    },
    "AC-17": {
        "icam_service": "Federation",
        "mandate": "OIDC/SAML federation for cross-agency access; no proprietary SSO silos",
        "satisfied_signal": "AWS OIDC providers configured; EKS OIDC or SAML IdP active",
        "ots_signal": "No OIDC providers configured AND no SAML providers detected",
    },
    "SC-8": {
        "icam_service": "Federation",
        "mandate": "Transmission confidentiality -- TLS on all authentication flows",
        "satisfied_signal": "TLS configured on all ingress resources; no plaintext auth endpoints",
        "ots_signal": "Ingress resources found without TLS configuration",
    },
}


def _format_evidence_block(evidence: dict) -> str:
    """Render collected ICAM evidence as readable text for task descriptions."""
    lines = []

    # Authentication (IA-2)
    auth = evidence.get("authentication", {})
    mfa = auth.get("mfa_configuration", {})
    lines.append("AUTHENTICATION (IA-2) -- Phishing-Resistant MFA:")
    if "skipped" in mfa:
        lines.append(f"  MFA assessment: {mfa['skipped']}")
    elif "error" in mfa:
        lines.append(f"  MFA assessment error: {mfa['error']}")
    else:
        lines.append(f"  OIDC configured on cluster: {mfa.get('oidc_configured', False)}")
        lines.append(f"  OIDC issuer: {mfa.get('oidc_issuer', 'None')}")
        lines.append(f"  Console users assessed: {mfa.get('console_users_assessed', 0)}")
        lines.append(f"  MFA enabled: {mfa.get('aws_mfa_enabled_users', 0)}")
        lines.append(f"  MFA disabled: {mfa.get('aws_mfa_disabled_users', 0)}")
        lines.append(f"  Virtual/TOTP MFA devices (NON-COMPLIANT): {mfa.get('virtual_mfa_devices', 0)}")
        lines.append(f"  FIDO2/U2F devices (compliant): {mfa.get('fido2_devices', 0)}")
        lines.append(f"  Phishing-resistant MFA detected: {mfa.get('phishing_resistant_detected', False)}")
        lines.append(f"  Collector assessment: {mfa.get('compliance_assessment', 'unknown')}")

    # Identity Proofing (IA-4) -- API boundary
    id_proof = evidence.get("identity_proofing", {})
    lines.append("\nIDENTITY PROOFING (IA-4) -- IAL2 Proofing:")
    lines.append(f"  API assessment possible: {id_proof.get('api_assessment_possible', False)}")
    lines.append(f"  Note: {id_proof.get('note', 'Not assessed')}")
    lines.append("  ASSESSOR INSTRUCTION: Mark as 'Requires Process Review' -- do NOT assign S or OTS from API data.")

    # Credentialing (IA-5)
    cred = evidence.get("credentialing", {})
    iam_keys = cred.get("iam_key_ages", {})
    sa_creds = cred.get("service_account_credentials", {})
    lines.append("\nCREDENTIALING (IA-5) -- No Long-Lived Static Credentials:")
    if "skipped" in iam_keys:
        lines.append(f"  IAM key ages: {iam_keys['skipped']}")
    elif "error" in iam_keys:
        lines.append(f"  IAM key ages error: {iam_keys['error']}")
    else:
        lines.append(f"  Total active IAM keys: {iam_keys.get('total_active_keys', 0)}")
        lines.append(f"  Keys older than 90 days (VIOLATION): {iam_keys.get('keys_over_90_days', 0)}")
        lines.append(f"  Keys older than 365 days (CRITICAL): {iam_keys.get('keys_over_365_days', 0)}")
        lines.append(f"  Keys never used: {iam_keys.get('keys_never_used', 0)}")
        lines.append(f"  Highest-privilege user with key: {iam_keys.get('highest_privilege_with_key', 'None')}")
    if "skipped" in sa_creds:
        lines.append(f"  SA credentials: {sa_creds['skipped']}")
    elif "error" in sa_creds:
        lines.append(f"  SA credentials error: {sa_creds['error']}")
    else:
        lines.append(f"  Total service accounts: {sa_creds.get('total_service_accounts', 0)}")
        lines.append(f"  IRSA-annotated SAs: {sa_creds.get('irsa_annotated', 0)}")
        lines.append(f"  Long-lived SA token secrets (VIOLATION): {sa_creds.get('long_lived_secret_tokens', 0)}")
        lines.append(f"  Automount true: {sa_creds.get('automount_true', 0)}")
        lines.append(f"  Collector assessment: {sa_creds.get('compliance_assessment', 'unknown')}")

    # Authorization (AC-2, AC-6)
    authz = evidence.get("authorization", {})
    lifecycle = authz.get("account_lifecycle", {})
    least_priv = authz.get("least_privilege", {})
    lines.append("\nAUTHORIZATION (AC-2, AC-6) -- Account Lifecycle + Least Privilege:")
    if "skipped" in lifecycle or "error" in lifecycle:
        lines.append(f"  Lifecycle: {lifecycle.get('skipped', lifecycle.get('error', 'unknown'))}")
    else:
        lines.append(f"  Stale users (90+ days inactive): {len(lifecycle.get('stale_users', []))}")
        lines.append(f"  Users without group membership: {len(lifecycle.get('users_without_groups', []))}")
        lines.append(f"  Console users without MFA: {len(lifecycle.get('console_users_without_mfa', []))}")
        lines.append(f"  Service accounts in default namespace: {len(lifecycle.get('service_accounts_in_default_ns', []))}")
        lines.append(f"  Orphaned role bindings: {len(lifecycle.get('orphaned_rolebindings', []))}")
    if "skipped" in least_priv or "error" in least_priv:
        lines.append(f"  Least privilege: {least_priv.get('skipped', least_priv.get('error', 'unknown'))}")
    else:
        lines.append(f"  Cluster-admin role count: {least_priv.get('admin_role_count', 0)}")
        lines.append(f"  Wildcard permissions (VIOLATION): {len(least_priv.get('wildcard_permissions', []))}")
        lines.append(f"  Broad cluster roles: {len(least_priv.get('broad_cluster_roles', []))}")
        lines.append(f"  Privileged pods (VIOLATION): {len(least_priv.get('privileged_pods', []))}")
        lines.append(f"  Pods without runAsNonRoot: {len(least_priv.get('root_running_pods', []))}")

    # Federation (AC-17, SC-8)
    fed = evidence.get("federation", {})
    fed_cfg = fed.get("federation_config", {})
    lines.append("\nFEDERATION (AC-17, SC-8) -- OIDC/SAML + TLS:")
    if "skipped" in fed_cfg or "error" in fed_cfg:
        lines.append(f"  Federation: {fed_cfg.get('skipped', fed_cfg.get('error', 'unknown'))}")
    else:
        lines.append(f"  AWS OIDC providers: {len(fed_cfg.get('oidc_providers', []))}")
        lines.append(f"  EKS OIDC configured: {fed_cfg.get('eks_oidc_configured', False)}")
        lines.append(f"  SAML provider detected: {fed_cfg.get('saml_provider_detected', False)}")
        lines.append(f"  Total ingress resources: {fed_cfg.get('total_ingress', 0)}")
        lines.append(f"  TLS on all ingress: {fed_cfg.get('tls_on_all_ingress', False)}")
        lines.append(f"  Ingress without TLS (VIOLATION): {len(fed_cfg.get('ingress_without_tls', []))}")

    # ICAM signals summary
    signals = evidence.get("icam_signals", {})
    lines.append("\nCOLLECTOR ICAM SIGNALS (starting point -- verify before finalizing):")
    svc_compliance = signals.get("service_compliance", {})
    for svc, status in svc_compliance.items():
        lines.append(f"  {svc}: {status}")
    lines.append(f"  Mandate satisfied (all assessable services): {signals.get('mandate_satisfied', False)}")
    violations = signals.get("critical_violations", [])
    if violations:
        lines.append("  Critical violations:")
        for v in violations:
            lines.append(f"    - {v}")
    else:
        lines.append("  Critical violations: none detected")

    return "\n".join(lines)


def build_icam_crew(evidence: dict, eng: dict) -> Crew:
    """
    Build the 3-agent M-24-04 ICAM crew with pre-collected evidence.

    Agents:
      assessor   -- assigns ICAM service compliance + S / OTS / NA per control
      sar_writer -- compiles M-24-04 ICAM compliance report from assessor output
      poam_writer -- converts every OTS to a POA&M item with M-24-04 mandate language
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
    critical_deadline = (today + timedelta(days=90)).strftime("%Y-%m-%d")
    high_deadline = (today + timedelta(days=180)).strftime("%Y-%m-%d")
    medium_deadline = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    # Build control requirements text for task descriptions
    ctrl_req_lines = []
    for ctrl_id, req in _CONTROL_ICAM_REQUIREMENTS.items():
        ctrl_req_lines.append(f"{ctrl_id} ({req['icam_service']}):")
        ctrl_req_lines.append(f"  Mandate: {req['mandate']}")
        ctrl_req_lines.append(f"  Satisfied when: {req['satisfied_signal']}")
        ctrl_req_lines.append(f"  OTS when: {req['ots_signal']}")
        if "api_limitation" in req:
            ctrl_req_lines.append(f"  API LIMITATION: {req['api_limitation']}")
    control_requirements_text = "\n".join(ctrl_req_lines)

    # ------------------------------------------------------------------ #
    # Task 1: ICAM Service Compliance + Control Assessment                 #
    # ------------------------------------------------------------------ #
    assessment_task = Task(
        description=(
            f"Assess ICAM controls for M-24-04 mandate compliance.\n"
            f"System: {system_name} | Cluster: {cluster} | Analyst: {analyst}\n"
            f"Assessment Date: {assessment_date}\n\n"
            f"Controls in scope: {', '.join(CONTROLS)}\n"
            f"Framework: M-24-04 (OMB Memorandum, February 2024)\n"
            f"Mandate baseline: Phishing-resistant MFA + no long-lived static credentials\n\n"
            "=== M-24-04 ICAM SERVICE FRAMEWORK ===\n"
            f"{_ICAM_FRAMEWORK}\n\n"
            "=== CONTROL-LEVEL MANDATE REQUIREMENTS ===\n"
            f"{control_requirements_text}\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (AWS CLI + kubectl, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS:\n"
            "1. The collector provides service compliance signals as a starting point. "
            "   Verify against raw evidence before finalizing.\n"
            "2. For each ICAM service (Authentication, Identity Proofing, Credentialing, "
            "   Authorization, Federation), assign: compliant / partial / non_compliant.\n"
            "3. For EACH control (IA-2, IA-4, IA-5, AC-2, AC-6, AC-17, SC-8), assign:\n"
            "   - Determination: Satisfied (S) / Other Than Satisfied (OTS) / "
            "     Requires Process Review (RPR) / Not Applicable (NA)\n"
            "   - Specific gap if OTS (quote exact metric from evidence)\n"
            "   - Severity: Critical / High / Medium / Low\n"
            "4. CRITICAL RULE for IA-4: The collector explicitly states this cannot be assessed "
            "   via API. You MUST assign 'Requires Process Review' -- not S or OTS. "
            "   Note that human auditor review of onboarding documentation is required.\n"
            "5. Overall mandate status: COMPLIANT / PARTIAL / NON-COMPLIANT with M-24-04.\n"
            "6. OTS for phishing-resistant MFA mandate = Critical severity. "
            "   OTS for long-lived credentials = High severity.\n"
        ),
        expected_output=(
            "1. OVERALL MANDATE STATUS: COMPLIANT / PARTIAL / NON-COMPLIANT (with justification)\n"
            "2. ICAM SERVICE TABLE (one row per service):\n"
            "   SERVICE | STATUS | KEY FINDING\n"
            "3. CONTROL TABLE (one row per control):\n"
            "   CONTROL | ICAM SERVICE | DETERMINATION | SPECIFIC FINDING | SEVERITY\n"
            "   IA-4 row must show 'Requires Process Review' determination.\n"
            "4. COUNT: X Satisfied, Y OTS, Z Requires Process Review, W Not Applicable\n"
            "5. CRITICAL VIOLATIONS: bullet list of mandate-breaking findings\n"
            "6. REMEDIATION PRIORITY: ordered list of what must be fixed first"
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: M-24-04 ICAM Compliance Report (SAR)                        #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the M-24-04 ICAM Compliance Report for {system_name}.\n\n"
            "Controls assessed: IA-2, IA-4, IA-5, AC-2, AC-6, AC-17, SC-8\n\n"
            "The report must contain ALL of the following sections:\n\n"
            "1. SYSTEM IDENTIFICATION\n"
            f"   - System name: {system_name}\n"
            f"   - Cluster: {cluster}\n"
            f"   - Analyst: {analyst}\n"
            f"   - Assessment date: {assessment_date}\n"
            "   - Framework: M-24-04 (OMB Memorandum, February 2024)\n"
            "   - Mandate baseline: Phishing-resistant MFA + no long-lived static credentials\n\n"
            "2. ASSESSMENT DATE AND SCOPE\n"
            "   - Date of evidence collection\n"
            "   - Tools used (AWS CLI, kubectl)\n"
            "   - Scope: IAM MFA configuration, credential ages, K8s service accounts,\n"
            "     account lifecycle, RBAC least-privilege, OIDC/SAML federation, ingress TLS\n"
            "   - Explicit scope exclusion: Identity Proofing (IA-4) requires process review\n\n"
            "3. ICAM SERVICE COMPLIANCE TABLE\n"
            "   Format: Service | Status | Mandate Requirement | Gap (if any)\n"
            "   One row per service. Include Identity Proofing row with status "
            "   'Requires Process Review'.\n\n"
            "4. CONTROL-BY-CONTROL TABLE\n"
            "   Format: Control | ICAM Service | Determination | Specific Finding\n"
            "   One row per control. OTS rows include specific gap from evidence.\n"
            "   IA-4 row: Determination = 'Requires Process Review'; note human audit required.\n\n"
            "5. M-24-04 MANDATE STATUS\n"
            "   - Overall: COMPLIANT / PARTIAL / NON-COMPLIANT\n"
            "   - Authentication mandate met? (phishing-resistant MFA)\n"
            "   - Credentialing mandate met? (no long-lived static credentials)\n"
            "   - Authorization mandate met? (least privilege + lifecycle)\n"
            "   - Federation mandate met? (OIDC/SAML + TLS)\n\n"
            "6. REMEDIATION PRIORITY\n"
            "   - Critical items (must fix immediately, mandate violation)\n"
            "   - High items (must fix within 180 days)\n"
            "   - Medium items (fix within 365 days)\n\n"
            "7. EVIDENCE REFERENCED\n"
            "   - List the collector functions that provided evidence\n"
            "   - Note IA-4 as requiring separate process documentation review\n"
            "   - Note any skipped collectors and why (AWS not configured, etc.)\n\n"
            "Write in formal GRC language. Reference exact metrics from evidence "
            "(user counts, key ages, pod names). Do not editorialize."
        ),
        expected_output=(
            "A complete M-24-04 ICAM Compliance Report in Markdown format with all seven sections. "
            "ICAM service compliance table in section 3. "
            "Control table in section 4 with specific findings. "
            "IA-4 clearly marked as 'Requires Process Review' in both tables. "
            "Mandate status section uses exact metrics. "
            "Ready for attachment to the IA/CA evidence package."
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
            "from the M-24-04 ICAM compliance report.\n\n"
            "CRITICAL: Use M-24-04 mandate language, not just NIST control language.\n"
            "  WRONG: 'IA-5 requires credential rotation'\n"
            "  RIGHT: 'M-24-04 Section 3 prohibits long-lived static credentials -- "
            "12 IAM users have access keys older than 90 days'\n\n"
            "IMPORTANT: IA-4 (Identity Proofing) marked 'Requires Process Review' does NOT "
            "automatically generate a POA&M item -- only generate one if the assessor "
            "specifically found a documented gap (e.g., proofing process does not exist). "
            "If IA-4 is 'RPR' only, note it as a documentation gap for process review.\n\n"
            "POA&M required fields for each item:\n"
            "- control_id: IA-X / AC-X / SC-X\n"
            "- weakness_name: specific, not generic "
            "  (e.g. 'IAM users with access keys older than 90 days')\n"
            "- weakness_description: 2-3 sentences -- what is wrong, where, M-24-04 mandate "
            "  requirement vs. current state (with exact metrics)\n"
            "- detection_method: gp-crewai icam-m24-04-collectors / BERU M-24-04 assessment\n"
            "- responsible_role: Platform Engineer / Cloud Engineer / Security Engineer / "
            "  Identity Engineer\n"
            "- resources_required: effort estimate (e.g. '3 days Cloud Engineer')\n"
            f"- scheduled_completion: Critical (mandate violation) = {critical_deadline} (90 days). "
            f"  High = {high_deadline} (180 days). Medium = {medium_deadline} (365 days).\n"
            "- milestones: at least one checkpoint before completion date\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON.\n"
            "Every OTS from the report gets exactly one POA&M item. No exceptions."
        ),
        expected_output=(
            "A POA&M registry as a JSON array -- one object per OTS finding. "
            "All fields populated. weakness_description uses M-24-04 mandate language "
            "with specific metrics. "
            "IA-4 handling documented (RPR note or POA&M item only if gap confirmed). "
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


def run_icam_crew(run_id: str | None = None) -> dict:
    """
    Full M-24-04 ICAM pipeline: collect -> assess -> SAR -> POA&M.

    Returns the crew result plus raw evidence for archival.
    Identity Proofing (IA-4) is flagged as requiring process review
    throughout -- this is by design, not a gap in the crew.
    """
    run_ts = datetime.now(timezone.utc)
    if run_id is None:
        run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    eng = get_engagement_config()
    system_name = eng.get("system_name", "Target System")

    print(f"[{run_id}] Collecting ICAM evidence (AWS CLI + kubectl, no LLM)...")
    evidence = run_icam_collectors()

    icam_signals = evidence.get("icam_signals", {})
    service_compliance = icam_signals.get("service_compliance", {})
    mandate_satisfied = icam_signals.get("mandate_satisfied", False)
    violations = icam_signals.get("critical_violations", [])

    print(f"[{run_id}] Collector ICAM signals:")
    for svc, status in service_compliance.items():
        print(f"[{run_id}]   {svc}: {status}")
    print(f"[{run_id}] Mandate satisfied (assessable services): {mandate_satisfied}")
    if violations:
        print(f"[{run_id}] Critical violations detected: {len(violations)}")
        for v in violations:
            print(f"[{run_id}]   - {v}")

    print(f"[{run_id}] Running BERU crew: assessor -> sar_writer -> poam_writer...")
    crew = build_icam_crew(evidence, eng)
    result = crew.kickoff()

    return {
        "run_id": run_id,
        "system": system_name,
        "cluster": eng.get("cluster"),
        "analyst": eng.get("analyst"),
        "framework": "M-24-04",
        "baseline": "ICAM-Mandate",
        "controls": CONTROLS,
        "collector_icam_signals": service_compliance,
        "mandate_satisfied": mandate_satisfied,
        "critical_violations": violations,
        "raw_evidence": evidence,
        "crew_output": str(result),
    }


if __name__ == "__main__":
    output = run_icam_crew()
    print(json.dumps({
        "run_id": output["run_id"],
        "system": output["system"],
        "framework": output["framework"],
        "collector_icam_signals": output["collector_icam_signals"],
        "mandate_satisfied": output["mandate_satisfied"],
        "critical_violations": output["critical_violations"],
    }, indent=2))
