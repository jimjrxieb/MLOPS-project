"""
CMMC Level 2 Crew — BERU-AI assessment for CMMC 2.0 Level 2 (110 practices).

Framework: CMMC 2.0 Level 2
Baseline:  NIST SP 800-171 Rev 2 (110 practices across 15 domains)
Scoring:   SPRS (Supplier Performance Risk System, 0–110 range)
Assessor:  C3PAO (Certified Third-Party Assessment Organization) prep

Architecture:
  Step 1 (collect) — pure Python: kubectl + AWS CLI. No LLM. See collectors.py.
  Step 2 (assess)  — assessor agent: assigns MET/NOT MET/NA per domain, estimates SPRS.
  Step 3 (report)  — sar_writer: Security Assessment Report with SPRS score summary.
  Step 4 (poam)    — poam_writer: practice-level POA&M items for each NOT MET finding.

API-assessable vs. process-review boundary:
  This crew strictly enforces the boundary. Domains AT, MA, MP, PE, PS and specific
  practices in CA and IR require process artifacts (training records, maintenance logs,
  media sanitization records, physical site review, personnel records, tabletop exercise
  after-action reports, SSP completeness review) that cannot be verified via API.
  Agents are explicitly instructed to use "Requires Process Review" for these items
  and never assign MET/NOT MET/NA to them.

SPRS scoring note:
  Official SPRS uses a DoD-specific weighting table. This crew uses a conservative
  1-point-per-practice planning estimate. Final SPRS score requires C3PAO validation
  using the official DoD scoring table.
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

from .collectors import run_cmmc_collectors

# SPRS scoring constants
_SPRS_PRACTICE_VALUE = 1  # points per practice (conservative planning estimate)
_SPRS_MAX_SCORE = 110

# CMMC practice domain summary for assessor context
_DOMAIN_PRACTICES = {
    "AC": {"count": 22, "key_l2": ["AC.L2-3.1.1", "AC.L2-3.1.5", "AC.L2-3.1.12", "AC.L2-3.1.13"]},
    "AU": {"count": 9, "key_l2": ["AU.L2-3.3.1", "AU.L2-3.3.2", "AU.L2-3.3.4", "AU.L2-3.3.8"]},
    "CA": {"count": 4, "key_l2": ["CA.L2-3.12.1", "CA.L2-3.12.2", "CA.L2-3.12.3", "CA.L2-3.12.4"]},
    "CM": {"count": 9, "key_l2": ["CM.L2-3.4.1", "CM.L2-3.4.2", "CM.L2-3.4.3", "CM.L2-3.4.6"]},
    "IA": {"count": 11, "key_l2": ["IA.L2-3.5.3", "IA.L2-3.5.7", "IA.L2-3.5.8", "IA.L2-3.5.10"]},
    "IR": {"count": 3, "key_l2": ["IR.L2-3.6.1", "IR.L2-3.6.2", "IR.L2-3.6.3"]},
    "RA": {"count": 3, "key_l2": ["RA.L2-3.11.1", "RA.L2-3.11.2", "RA.L2-3.11.3"]},
    "SC": {"count": 16, "key_l2": ["SC.L2-3.13.6", "SC.L2-3.13.8", "SC.L2-3.13.11", "SC.L2-3.13.16"]},
    "SI": {"count": 7, "key_l2": ["SI.L1-3.14.1", "SI.L1-3.14.2", "SI.L2-3.14.6", "SI.L2-3.14.7"]},
    "SR": {"count": 3, "key_l2": ["SR.L2-3.17.1", "SR.L2-3.17.2", "SR.L2-3.17.3"]},
    # Process-only domains — cannot assess via API
    "AT": {"count": 3, "note": "Requires training records review"},
    "MA": {"count": 6, "note": "Requires maintenance procedure review"},
    "MP": {"count": 9, "note": "Requires media handling records review"},
    "PE": {"count": 6, "note": "Requires physical site review"},
    "PS": {"count": 2, "note": "Requires personnel records review"},
}


def _format_domain_summary() -> str:
    """Render CMMC domain summary for assessor task context."""
    lines = ["CMMC 2.0 Level 2 — Domain and Practice Summary:"]
    for domain, info in _DOMAIN_PRACTICES.items():
        if "note" in info:
            lines.append(f"  {domain} ({info['count']} practices): {info['note']}")
        else:
            key = ", ".join(info["key_l2"])
            lines.append(f"  {domain} ({info['count']} practices): Key L2 — {key}")
    return "\n".join(lines)


def _format_evidence_block(evidence: dict) -> str:
    """Render collected CMMC evidence as readable text for task descriptions."""
    lines = []

    lines.append("=" * 70)
    lines.append("CMMC COLLECTOR EVIDENCE SUMMARY")
    lines.append("=" * 70)
    lines.append(f"  Framework: {evidence.get('framework')}")
    lines.append(f"  Total Level 2 practices: {evidence.get('total_l2_practices')}")

    lines.append("")
    lines.append("CRITICAL — ITEMS THAT CANNOT BE ASSESSED VIA API:")
    lines.append("  (Agents MUST mark these 'Requires Process Review' — NEVER assign MET/NOT MET/NA)")
    for item in evidence.get("cannot_assess_via_api", []):
        lines.append(f"  !! {item}")

    # AC domain
    ac = evidence.get("ac", {})
    lines.append("")
    lines.append("AC — Access Control:")
    if "skipped" in ac or "error" in ac:
        lines.append(f"  {ac.get('skipped') or ac.get('error')}")
    else:
        lines.append(f"  cluster-admin bindings (non-system subjects): {len(ac.get('cluster_admin_bindings', []))}")
        for binding in ac.get("cluster_admin_bindings", [])[:5]:
            lines.append(f"    {binding.get('binding')} → {[s.get('name') for s in binding.get('subjects', [])]}")
        lines.append(f"  default ServiceAccounts with automount exposed: {ac.get('default_sa_exposed', 0)}")
        lines.append(f"  namespaces without NetworkPolicy: {len(ac.get('namespaces_without_netpol', []))}")
        if ac.get("namespaces_without_netpol"):
            lines.append(f"    {ac['namespaces_without_netpol'][:10]}")
        lines.append(f"  root account MFA enabled (AWS): {ac.get('root_mfa_enabled')}")
        lines.append(f"  IAM users with AdministratorAccess: {ac.get('admin_users_count', 0)}")

    # AU domain
    au = evidence.get("au", {})
    lines.append("")
    lines.append("AU — Audit and Accountability:")
    if "skipped" in au or "error" in au:
        lines.append(f"  {au.get('skipped') or au.get('error')}")
    else:
        lines.append(f"  EKS audit logging enabled: {au.get('eks_audit_logging_enabled')}")
        lines.append(f"  Log shipper found: {au.get('log_shipper_found')} ({au.get('log_shipper_name')})")
        lines.append(f"  Loki found: {au.get('loki_found')} | Grafana found: {au.get('grafana_found')}")
        lines.append(f"  CloudTrail enabled: {au.get('cloudtrail_enabled')}")
        lines.append(f"  CloudTrail multi-region: {au.get('cloudtrail_multi_region')}")
        retention = au.get("log_retention_days", {})
        lines.append(f"  CloudWatch log groups: {len(retention)} (see raw JSON for retention details)")

    # CM domain
    cm = evidence.get("cm", {})
    lines.append("")
    lines.append("CM — Configuration Management:")
    if "skipped" in cm or "error" in cm:
        lines.append(f"  {cm.get('skipped') or cm.get('error')}")
    else:
        lines.append(f"  Policy engine: {cm.get('policy_engine')} ({cm.get('policy_count', 0)} policies)")
        lines.append(f"  GitOps (ArgoCD) present: {cm.get('gitops_present')}")
        lines.append(f"  Pods without resource limits: {cm.get('pods_without_limits', 0)}")
        lines.append(f"  Privileged containers: {cm.get('privileged_pods', 0)}")

    # IA domain
    ia = evidence.get("ia", {})
    lines.append("")
    lines.append("IA — Identification and Authentication:")
    if "skipped" in ia or "error" in ia:
        lines.append(f"  {ia.get('skipped') or ia.get('error')}")
    else:
        lines.append(f"  IAM users without MFA: {len(ia.get('users_without_mfa', []))}")
        if ia.get("users_without_mfa"):
            lines.append(f"    {ia['users_without_mfa'][:10]}")
        lines.append(f"  Virtual MFA users: {len(ia.get('virtual_mfa_users', []))}")
        lines.append(f"  Hardware MFA users: {len(ia.get('hardware_mfa_users', []))}")
        lines.append(f"  Access keys older than 90 days: {len(ia.get('old_access_keys', []))}")
        for key in ia.get("old_access_keys", [])[:5]:
            lines.append(f"    {key.get('user')} — key #{key.get('key_num')} — {key.get('age_days')} days old")
        lines.append(f"  IRSA configured: {ia.get('irsa_configured')}")
        lines.append(f"  Secrets manager present: {ia.get('secrets_manager_present')}")

    # RA domain
    ra = evidence.get("ra", {})
    lines.append("")
    lines.append("RA — Risk Assessment:")
    if "skipped" in ra or "error" in ra:
        lines.append(f"  {ra.get('skipped') or ra.get('error')}")
    else:
        lines.append(f"  Trivy available: {ra.get('trivy_available')}")
        lines.append(f"  Critical vulns found: {ra.get('critical_vulns', 0)}")
        lines.append(f"  High vulns found: {ra.get('high_vulns', 0)}")
        lines.append(f"  Images with :latest tag: {len(ra.get('latest_tag_images', []))}")
        if ra.get("latest_tag_images"):
            lines.append(f"    {ra['latest_tag_images'][:5]}")
        lines.append(f"  AWS Inspector enabled: {ra.get('inspector_enabled')}")

    # SC domain
    sc = evidence.get("sc", {})
    lines.append("")
    lines.append("SC — System and Communications Protection:")
    if "skipped" in sc or "error" in sc:
        lines.append(f"  {sc.get('skipped') or sc.get('error')}")
    else:
        lines.append(f"  Namespaces with default-deny ingress policy: {len(sc.get('default_deny_namespaces', []))}")
        if sc.get("default_deny_namespaces"):
            lines.append(f"    {sc['default_deny_namespaces']}")
        lines.append(f"  Service mesh present: {sc.get('service_mesh_present')} ({sc.get('service_mesh_name')})")
        lines.append(f"  TLS secrets count: {sc.get('tls_secrets_count', 0)}")
        lines.append(f"  S3 unencrypted buckets: {len(sc.get('s3_unencrypted_buckets', []))}")
        if sc.get("s3_unencrypted_buckets"):
            lines.append(f"    {sc['s3_unencrypted_buckets'][:5]}")
        lines.append(f"  RDS instances unencrypted: {len(sc.get('rds_unencrypted', []))}")
        if sc.get("rds_unencrypted"):
            lines.append(f"    {sc['rds_unencrypted']}")
        lines.append(f"  GovCloud / FIPS region: {sc.get('govcloud_region')}")

    # SI domain
    si = evidence.get("si", {})
    lines.append("")
    lines.append("SI — System and Information Integrity:")
    if "skipped" in si or "error" in si:
        lines.append(f"  {si.get('skipped') or si.get('error')}")
    else:
        lines.append(f"  Falco deployed: {si.get('falco_deployed')}")
        lines.append(f"  Read-only root filesystem ratio: {si.get('readonly_filesystem_ratio', 0):.1%}")
        lines.append(f"  Security context violations: {si.get('security_context_violations', 0)}")
        lines.append(f"  Digest-pinned images: {si.get('digest_pinned_images', 0)}")
        lines.append(f"  Tag-only images (no digest): {si.get('tag_only_images', 0)}")
        lines.append(f"  GuardDuty enabled: {si.get('guardduty_enabled')}")

    # SR domain
    sr = evidence.get("sr", {})
    lines.append("")
    lines.append("SR — Supply Chain Risk Management:")
    if "skipped" in sr or "error" in sr:
        lines.append(f"  {sr.get('skipped') or sr.get('error')}")
    else:
        lines.append(f"  External registry images (docker.io, gcr.io, ghcr.io, quay.io): {len(sr.get('external_registry_images', []))}")
        if sr.get("external_registry_images"):
            lines.append(f"    {sr['external_registry_images'][:5]}")
        lines.append(f"  ECR images count: {sr.get('ecr_images_count', 0)}")
        lines.append(f"  Private registry images: {sr.get('private_registry_images_count', 0)}")
        lines.append(f"  Image signing enabled (cosign/Kyverno verify-image): {sr.get('image_signing_enabled')}")
        lines.append(f"  ECR scan-on-push enabled (all repos): {sr.get('ecr_scanning_enabled')}")
        lines.append(f"  SBOM references detected: {sr.get('sbom_present')}")

    return "\n".join(lines)


def run_cmmc_crew(run_id: str = None) -> dict:
    """
    Full CMMC Level 2 pipeline: collect -> assess -> SAR -> POA&M.

    Returns structured result with SPRS estimate, SAR, and POA&M registry.
    """
    run_ts = datetime.now(timezone.utc)
    if run_id is None:
        run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    config = get_engagement_config()
    system_name = config.get("system_name", "Target System")
    cluster = config.get("cluster", "unknown-cluster")
    analyst = config.get("analyst", "beru:v1.6")
    assessment_date = run_ts.strftime("%Y-%m-%d")

    print(f"[{run_id}] Collecting CMMC Level 2 evidence (kubectl + AWS CLI, no LLM)...")
    evidence = run_cmmc_collectors()

    cannot_assess = evidence.get("cannot_assess_via_api", [])
    cannot_assess_str = "\n".join(f"    - {item}" for item in cannot_assess)

    print(f"[{run_id}] Evidence collected. Items requiring process review: {len(cannot_assess)}")
    print(f"[{run_id}] Running BERU crew: assessor -> sar_writer -> poam_writer...")

    evidence_text = _format_evidence_block(evidence)
    raw_json = json.dumps(evidence, indent=2)
    domain_summary = _format_domain_summary()

    # POA&M target dates
    today = run_ts.date()
    short_deadline = (today + timedelta(days=90)).strftime("%Y-%m-%d")
    medium_deadline = (today + timedelta(days=180)).strftime("%Y-%m-%d")
    long_deadline = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    assess = assessor()
    sar = sar_writer()
    poam = poam_writer()

    # ------------------------------------------------------------------ #
    # Task 1: CMMC Domain Assessment + SPRS Estimate                       #
    # ------------------------------------------------------------------ #
    assessor_task = Task(
        description=(
            f"Assess CMMC 2.0 Level 2 practices for system: {system_name}\n"
            f"Cluster: {cluster} | Analyst: {analyst} | Assessment Date: {assessment_date}\n\n"
            "Framework: CMMC 2.0 Level 2 (110 practices, NIST SP 800-171 Rev 2)\n"
            "Scoring:   SPRS (Supplier Performance Risk System) — max 110 points\n\n"
            f"{domain_summary}\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (kubectl + AWS CLI, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS:\n\n"
            "CRITICAL BOUNDARY — READ BEFORE ASSESSING:\n"
            "The following items CANNOT be assessed via kubectl or AWS CLI.\n"
            "For each of these, you MUST use determination: 'Requires Process Review'.\n"
            "Do NOT assign MET, NOT MET, or NOT APPLICABLE to these items.\n"
            "Items requiring C3PAO process review:\n"
            f"{cannot_assess_str}\n\n"
            "For API-assessable domains (AC, AU, CM, IA, RA, SC, SI, SR, CA partial, IR partial):\n\n"
            "1. Assess each domain holistically based on the evidence signals above.\n"
            "   Assign per-domain determination: MET / NOT MET / NOT APPLICABLE\n\n"
            "2. For NOT MET domains, identify which specific key practices are failing:\n"
            "   - AC.L2-3.1.1: Authorized access (cluster-admin bindings, root MFA)\n"
            "   - AC.L2-3.1.5: Least privilege (default SA automount, IAM admin users)\n"
            "   - AC.L2-3.1.12/13: Control CUI flow (NetworkPolicy gaps)\n"
            "   - AU.L2-3.3.1: Create and retain audit logs (EKS audit logging, CloudTrail)\n"
            "   - AU.L2-3.3.2: Protect audit information (log retention, encryption)\n"
            "   - CM.L2-3.4.1: Baseline configurations (policy engine present)\n"
            "   - CM.L2-3.4.3: Change control (GitOps/ArgoCD)\n"
            "   - CM.L2-3.4.6: Least functionality (no privileged pods, resource limits)\n"
            "   - IA.L2-3.5.3: MFA for privileged users (users without MFA)\n"
            "   - IA.L2-3.5.7: Password/key rotation (access keys > 90 days old)\n"
            "   - IA.L2-3.5.8: Replay-resistant authentication (IRSA, hardware MFA)\n"
            "   - RA.L2-3.11.2: Scan for vulnerabilities (Trivy, CRITICAL/HIGH findings)\n"
            "   - RA.L2-3.11.3: Remediate vulnerabilities (images with :latest, no Inspector)\n"
            "   - SC.L2-3.13.1: Monitor/control communications (NetworkPolicy, default-deny)\n"
            "   - SC.L2-3.13.8: Cryptographic mechanisms (TLS, service mesh, mTLS)\n"
            "   - SC.L2-3.13.16: Protect CUI at rest (S3 encryption, RDS encryption)\n"
            "   - SI.L1-3.14.1/2: Flaw remediation and malicious code protection\n"
            "   - SI.L2-3.14.6: Monitor for unauthorized activity (Falco)\n"
            "   - SI.L2-3.14.7: Identify unauthorized use (GuardDuty)\n"
            "   - SR.L2-3.17.1: Manage supply chain risks (external registry images)\n"
            "   - SR.L2-3.17.2: Protect against tampering (image signing, ECR scanning)\n"
            "   - SR.L2-3.17.3: Evaluate supply chain risks (SBOM)\n\n"
            "3. For partial domains (CA and IR):\n"
            "   - CA.L2-3.12.2 (periodic assessment) and CA.L2-3.12.3 (corrective actions):\n"
            "     Assess as MET/NOT MET via API proxy (policy engine + SIEM signals).\n"
            "   - CA.L2-3.12.1 and CA.L2-3.12.4: Mark 'Requires Process Review'.\n"
            "   - IR.L2-3.6.1 (incident response capability) and IR.L2-3.6.2 (incident tracking):\n"
            "     Assess via API proxy (Falco + GuardDuty signals).\n"
            "   - IR.L2-3.6.3 (test incident response): Mark 'Requires Process Review'.\n\n"
            "4. SPRS Score Estimate:\n"
            "   Start at 110. For each NOT MET domain, subtract the number of key practices\n"
            "   failing in that domain (use conservative estimate of 1 point per practice).\n"
            "   State the estimated SPRS score with breakdown by domain.\n"
            "   NOTE: Official SPRS uses DoD weighting table. This is a planning estimate only.\n"
        ),
        expected_output=(
            "1. DOMAIN ASSESSMENT TABLE — one row per domain:\n"
            "   DOMAIN | PRACTICES | DETERMINATION | KEY PRACTICES FAILING | SPRS IMPACT\n"
            "   Determinations: MET / NOT MET / NOT APPLICABLE / Requires Process Review\n"
            "   Include all 15 CMMC domains. Process-only domains (AT, MA, MP, PE, PS)\n"
            "   and flagged practices must use 'Requires Process Review'.\n\n"
            "2. SPRS SCORE ESTIMATE:\n"
            "   Starting score: 110\n"
            "   Deductions: list each NOT MET domain and point deduction\n"
            "   Estimated SPRS: [X] / 110\n"
            "   Note: excludes process-review items (cannot compute accurately without C3PAO)\n\n"
            "3. COUNT: X MET, Y NOT MET, Z Requires Process Review, W Not Applicable\n\n"
            "4. CRITICAL GAPS (top 5 by SPRS impact): bulleted list\n\n"
            "5. PROCESS REVIEW ITEMS: bullet list of what C3PAO must verify via document review"
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: Security Assessment Report                                    #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the CMMC 2.0 Level 2 Security Assessment Report for {system_name}.\n\n"
            "Framework: CMMC 2.0 Level 2 | Scoring: SPRS (0–110) | "
            "Assessment Body: C3PAO (Certified Third-Party Assessment Organization)\n\n"
            "The SAR must contain ALL of the following sections:\n\n"
            "1. EXECUTIVE SUMMARY\n"
            f"   - System: {system_name}\n"
            f"   - Cluster: {cluster}\n"
            f"   - Analyst: {analyst}\n"
            f"   - Assessment Date: {assessment_date}\n"
            "   - Framework: CMMC 2.0 Level 2 (110 practices, NIST SP 800-171 Rev 2)\n"
            "   - Assessment Method: Automated API-based evidence collection + expert analysis\n"
            "   - Estimated SPRS Score: [extract from assessor output] / 110\n"
            "   - Overall posture (one paragraph, formal GRC language)\n\n"
            "2. DOMAIN ASSESSMENT TABLE\n"
            "   One row per domain (all 15 CMMC domains).\n"
            "   Format: Domain | Practices | Status | Key Findings\n"
            "   Status: MET / NOT MET / NOT APPLICABLE / Requires Process Review\n\n"
            "3. NOT MET DOMAIN FINDINGS (one section per NOT MET domain)\n"
            "   For each NOT MET domain include:\n"
            "   - Domain name and practice count\n"
            "   - Key CMMC practice IDs failing (e.g., IA.L2-3.5.3)\n"
            "   - Evidence cited (exact metric from collector output)\n"
            "   - Gap description (what is missing or wrong)\n"
            "   - SPRS impact (estimated point deduction)\n\n"
            "4. ITEMS REQUIRING C3PAO PROCESS REVIEW\n"
            "   Dedicated section for the engagement team and system owner.\n"
            "   List every item from cannot_assess_via_api.\n"
            "   For each item: domain, CMMC practice ID(s), what artifact must be provided,\n"
            "   what the C3PAO will verify, and format as a checklist.\n"
            "   These items are not scored in the automated SPRS estimate.\n\n"
            "5. SPRS SCORING SUMMARY\n"
            "   - Maximum score: 110\n"
            "   - Automated deductions: table — domain, failing practices, deduction\n"
            "   - Estimated automated SPRS: [X] / 110\n"
            "   - Practices excluded (process review): list\n"
            "   - Note: Final SPRS requires C3PAO assessment using DoD weighting table\n\n"
            "6. NEXT STEPS (prioritized by SPRS impact)\n"
            "   Bulleted list of remediation priorities, highest SPRS impact first.\n"
            "   Include: what to fix, which practice it closes, estimated SPRS recovery.\n\n"
            "Reference exact metrics from evidence. Write in formal GRC/CMMC language.\n"
            "Use CMMC practice IDs (e.g., IA.L2-3.5.3) not just control names.\n"
            "Format: Markdown, ready for attachment to C3PAO pre-assessment package."
        ),
        expected_output=(
            "A complete CMMC 2.0 Level 2 Security Assessment Report in Markdown format "
            "with all six sections. Executive summary includes SPRS estimate. "
            "Domain table covers all 15 domains. NOT MET sections reference exact evidence metrics. "
            "C3PAO Process Review section formatted as a checklist for the engagement team. "
            "SPRS summary table shows deductions by domain. "
            "Next steps prioritized by SPRS recovery potential."
        ),
        agent=sar,
        context=[assessor_task],
    )

    # ------------------------------------------------------------------ #
    # Task 3: POA&M Items                                                  #
    # ------------------------------------------------------------------ #
    poam_task = Task(
        description=(
            "Generate POA&M items for every NOT MET finding from the CMMC Level 2 SAR.\n\n"
            "Use CMMC practice IDs in the control_id field (e.g., 'IA.L2-3.5.3').\n\n"
            "CRITICAL: For 'Requires Process Review' items (AT, MA, MP, PE, PS domains and\n"
            "specific CA/IR practices), do NOT create individual POA&M items. Instead,\n"
            "create one summary note:\n"
            "  'Domains AT, MA, MP, PE, PS and practices CA.L2-3.12.1, CA.L2-3.12.4,\n"
            "  IR.L2-3.6.3 require C3PAO document review. Schedule documentation review\n"
            "  as part of C3PAO prep timeline.'\n\n"
            "POA&M required fields for each NOT MET practice:\n"
            "- control_id: CMMC practice ID (e.g., 'IA.L2-3.5.3')\n"
            "- weakness_name: specific — include practice name\n"
            "  WRONG: 'MFA not configured'\n"
            "  RIGHT: 'IA.L2-3.5.3 — Multi-factor authentication not enforced for IAM users'\n"
            "- weakness_description: 2-3 sentences — what is wrong, which CMMC practice requires it,\n"
            "  exact metric from evidence vs. requirement\n"
            "  Example: 'CMMC practice IA.L2-3.5.3 requires MFA for all privileged user accounts.\n"
            "  Credential report shows 3 IAM users with password enabled and MFA not active.\n"
            "  Without MFA, CUI access cannot be restricted to authenticated users per NIST 800-171 §3.5.3.'\n"
            "- detection_method: gp-crewai cmmc-collectors / BERU CMMC Level 2 assessment\n"
            "- responsible_role: System Owner / ISSO\n"
            "- resources_required: effort estimate (e.g., '2 hours — enable MFA in IAM console')\n"
            f"- scheduled_completion:\n"
            f"  Critical findings (directly blocking MET status for high-value domains): {short_deadline} (90 days)\n"
            f"  High findings (significant SPRS deduction): {medium_deadline} (180 days)\n"
            f"  Medium findings (minor SPRS deduction): {long_deadline} (365 days)\n"
            "- milestones: at least one checkpoint before the completion date\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON.\n"
            "Every NOT MET finding gets exactly one POA&M item. No exceptions.\n"
            "Do not create POA&M items for 'Requires Process Review' determinations.\n"
            "End with the C3PAO process-review summary note and a total count:\n"
            "total items, Critical/High/Medium breakdown, earliest and latest completion dates."
        ),
        expected_output=(
            "A POA&M registry as a JSON array — one object per NOT MET finding. "
            "All fields populated. control_id uses CMMC practice ID format (e.g. IA.L2-3.5.3). "
            "weakness_description cites specific evidence metrics and CMMC practice requirement. "
            "Followed by C3PAO process-review summary note for excluded domains. "
            "Followed by summary: total items, Critical/High/Medium/Low breakdown, "
            "earliest and latest scheduled completion dates, estimated SPRS recovery if all items resolved."
        ),
        agent=poam,
        context=[assessor_task, sar_task],
    )

    crew = Crew(
        agents=[assess, sar, poam],
        tasks=[assessor_task, sar_task, poam_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    # Extract SPRS estimate from SAR output (best-effort string search)
    sar_raw = sar_task.output.raw if hasattr(sar_task, "output") else str(result)
    sprs_from_assessor = "see SAR section 5"
    for line in sar_raw.splitlines():
        if "Estimated" in line and "SPRS" in line and "/" in line:
            sprs_from_assessor = line.strip()
            break

    return {
        "run_id": run_id,
        "framework": "CMMC 2.0 Level 2",
        "system": system_name,
        "cluster": cluster,
        "analyst": analyst,
        "sprs_estimate": sprs_from_assessor,
        "sar": sar_raw,
        "poam": poam_task.output.raw if hasattr(poam_task, "output") else "",
        "evidence_collected": [k for k in evidence.keys() if k not in
                                ("cannot_assess_via_api", "cmmc_signals",
                                 "run_id", "timestamp", "framework", "total_l2_practices")],
        "cannot_assess_count": len(evidence.get("cannot_assess_via_api", [])),
    }


if __name__ == "__main__":
    import sys as _sys
    run_id = _sys.argv[1] if len(_sys.argv) > 1 else None
    result = run_cmmc_crew(run_id=run_id)
    print(json.dumps(
        {k: v for k, v in result.items() if k not in ("sar", "poam")},
        indent=2,
    ))
