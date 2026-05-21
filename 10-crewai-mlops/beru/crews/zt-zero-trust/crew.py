"""
ZT Zero Trust Crew -- M-22-09 compliance assessment.

Encodes the playbook at:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-22-09-playbooks/01-assess-zt-network-pillar.md

Architecture:
  Step 1 (collect) -- pure Python: kubectl + AWS CLI. No LLM.
  Step 2 (assess)  -- assessor agent: assigns ZT pillar stage + S/OTS/NA per control.
  Step 3 (report)  -- sar_writer: M-22-09 ZT compliance report.
  Step 4 (poam)    -- poam_writer: POA&M items for each gap.

Controls: SC-7, SC-8, SC-28, AC-2, AC-3, AC-6, AC-17, IA-2, IA-3, IA-5, CM-8, SI-4, CA-7
Framework: M-22-09 (OMB Memorandum, January 2022)
Baseline: ZT-Initial -- minimum viable (Traditional is non-compliant)

Why Step 1 is not a CrewAI agent:
  Network and kubectl data is structured. An LLM adds nothing to data collection and adds
  failure modes (hallucinated resource names, ReAct loop confusion). The collector runs
  deterministically and hands clean ZT pillar signals to the agents.
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

from .collectors import run_zt_collectors

CONTROLS = [
    "SC-7", "SC-8", "SC-28",
    "AC-2", "AC-3", "AC-6", "AC-17",
    "IA-2", "IA-3", "IA-5",
    "CM-8", "SI-4", "CA-7",
]


# M-22-09 ZT pillar framework -- baked into task descriptions so agents have full context
_ZT_FRAMEWORK = """
M-22-09 Zero Trust Architecture (ZTA) Maturity Stages:

Traditional -- Pre-ZT baseline (non-compliant with M-22-09):
  Perimeter-based trust. Flat network with no micro-segmentation. Passwords and static
  credentials. No asset inventory. Minimal monitoring. Implicit internal trust assumed.
  This is the default state of most federal systems before ZT implementation.

Initial -- Minimum viable ZT (M-22-09 mandate minimum):
  - Identity: Centralized IdP, enterprise-managed accounts, MFA deployed
  - Devices: Asset inventory exists, some device health checks
  - Networks: Basic segmentation (VPC/namespace isolation), TLS on all ingress
  - Applications: Basic authorization checks, some application logging
  - Data: Encryption at rest for sensitive data, basic classification
  Federal agencies must reach Initial by FY2024 per M-22-09.

Advanced -- Mature ZT posture (FY2026 target):
  - Identity: Phishing-resistant MFA for all users, JIT access, no standing privilege,
    workload identity (IRSA / SPIFFE) replaces static credentials
  - Devices: All devices enrolled and compliance-enforced before access granted
  - Networks: Per-workload NetworkPolicy with default-deny, mTLS everywhere,
    encrypted inter-pod traffic, no implicit lateral movement paths
  - Applications: Per-request authorization, SPIFFE/SVID workload identity,
    full runtime monitoring (Falco), SIEM integration
  - Data: All data classified and encrypted, access tied to classification level

Optimal -- Full ZT (long-term goal):
  - Identity: Continuous identity validation, risk-based authentication,
    full attribute-based access control (ABAC)
  - Devices: Real-time device posture, continuous compliance validation
  - Networks: Dynamic micro-segmentation, automated policy enforcement,
    zero lateral movement paths
  - Applications: Continuous authorization, zero standing access, behavioral analytics
  - Data: Data-centric access control, DLP enforcement, automated classification
"""

# Per-control ZT pillar and minimum stage requirements
_CONTROL_ZT_REQUIREMENTS = {
    "SC-7":  {"pillar": "Networks",      "min_stage": "Initial",  "description": "Boundary Protection -- NetworkPolicy coverage >= 50%, TLS on ingress"},
    "SC-8":  {"pillar": "Networks",      "min_stage": "Initial",  "description": "Transmission Confidentiality/Integrity -- TLS on all ingress; mTLS for Advanced"},
    "SC-28": {"pillar": "Data",          "min_stage": "Initial",  "description": "Protection at Rest -- encryption for Kubernetes secrets and S3"},
    "AC-2":  {"pillar": "Identity",      "min_stage": "Initial",  "description": "Account Management -- centralized IdP, enterprise-managed accounts"},
    "AC-3":  {"pillar": "Applications",  "min_stage": "Initial",  "description": "Access Enforcement -- basic authorization; per-request for Advanced"},
    "AC-6":  {"pillar": "Identity",      "min_stage": "Initial",  "description": "Least Privilege -- no non-system cluster-admin; no wildcard roles for Advanced"},
    "AC-17": {"pillar": "Networks",      "min_stage": "Initial",  "description": "Remote Access -- API server TLS-only, no unnecessary external exposure"},
    "IA-2":  {"pillar": "Identity",      "min_stage": "Initial",  "description": "MFA -- enterprise MFA deployed; phishing-resistant for Advanced"},
    "IA-3":  {"pillar": "Devices",       "min_stage": "Initial",  "description": "Device Identification -- all nodes identified and in managed inventory"},
    "IA-5":  {"pillar": "Identity",      "min_stage": "Initial",  "description": "Authenticator Management -- no long-lived static credentials; IRSA for workloads"},
    "CM-8":  {"pillar": "Devices",       "min_stage": "Initial",  "description": "System Component Inventory -- complete node inventory, no unmanaged nodes"},
    "SI-4":  {"pillar": "Applications",  "min_stage": "Initial",  "description": "System Monitoring -- runtime monitoring (Falco) for Advanced; basic logging for Initial"},
    "CA-7":  {"pillar": "Cross-Pillar",  "min_stage": "Initial",  "description": "Continuous Monitoring -- Security Hub + runtime detection across all pillars"},
}


def _format_evidence_block(evidence: dict) -> str:
    """Render collected ZT evidence as readable text for task descriptions."""
    lines = []

    # ZT Signals summary -- lead with the collector's pillar stage assessments
    signals = evidence.get("zt_signals", {})
    pillar_stages = signals.get("pillar_stages", {})
    lines.append("ZT COLLECTOR SIGNALS (starting point for assessment -- verify before finalizing):")
    lines.append(f"  Overall ZT stage:   {signals.get('overall_stage', 'Unknown')}")
    lines.append(f"  M-22-09 compliant:  {signals.get('m22_09_compliant', False)}")
    for pillar, stage in pillar_stages.items():
        lines.append(f"  {pillar:<16} {stage}")
    critical_gaps = signals.get("critical_gaps", [])
    if critical_gaps:
        lines.append(f"\n  Critical gaps identified by collector ({len(critical_gaps)}):")
        for gap in critical_gaps:
            lines.append(f"    - {gap}")

    # Networks pillar
    nets = evidence.get("networks_pillar", {})
    netpol = nets.get("network_policies", {})
    tls = nets.get("tls_enforcement", {})
    lines.append("\nNetworks Pillar (SC-7, SC-8, AC-17):")
    if "skipped" in netpol:
        lines.append(f"  NetworkPolicy data: {netpol['skipped']}")
    else:
        lines.append(f"  Total namespaces:            {netpol.get('total_namespaces', 0)}")
        lines.append(f"  Namespaces with NetworkPolicy: {netpol.get('namespaces_with_netpol', 0)}")
        lines.append(f"  Namespaces without:          {len(netpol.get('namespaces_without_netpol', []))}")
        lines.append(f"  Coverage:                    {netpol.get('coverage_pct', 0)}%")
        lines.append(f"  Default-deny-all detected:   {netpol.get('has_default_deny', False)}")
        ns_without = netpol.get("namespaces_without_netpol", [])
        if ns_without:
            lines.append(f"  Unprotected namespaces: {', '.join(ns_without[:8])}")
    if "skipped" in tls:
        lines.append(f"  TLS data: {tls['skipped']}")
    else:
        lines.append(f"  TLS enforced on ingress:     {tls.get('tls_enforced_pct', 0)}%")
        lines.append(f"  mTLS detected:               {tls.get('mtls_detected', False)}")
        lines.append(f"  Istio detected:              {tls.get('istio_detected', False)}")
        lines.append(f"  Linkerd detected:            {tls.get('linkerd_detected', False)}")
        non_tls = [r["name"] for r in tls.get("ingress_resources", []) if not r["tls"]]
        if non_tls:
            lines.append(f"  Ingress without TLS: {', '.join(non_tls[:5])}")

    # Identity pillar
    ident = evidence.get("identity_pillar", {})
    rbac = ident.get("rbac_privilege", {})
    mfa = ident.get("mfa_signals", {})
    wi = ident.get("workload_identity", {})
    lines.append("\nIdentity Pillar (AC-2, AC-6, IA-2, IA-5):")
    if "skipped" not in rbac:
        lines.append(f"  Cluster-admin bindings:       {rbac.get('cluster_admin_count', 0)}")
        non_sys = rbac.get("non_system_cluster_admins", [])
        lines.append(f"  Non-system cluster-admins:    {len(non_sys)}")
        for a in non_sys[:5]:
            lines.append(f"    {a['binding']} -> {a['kind']}/{a['name']}")
        lines.append(f"  Wildcard ClusterRoles:        {len(rbac.get('wildcard_roles', []))}")
        lines.append(f"  Privileged pods:              {len(rbac.get('privileged_pods', []))}")
    if "skipped" not in mfa:
        lines.append(f"  OIDC issuer detected:         {mfa.get('oidc_issuer_detected', False)}")
        lines.append(f"  OIDC issuer:                  {mfa.get('oidc_issuer', 'None')}")
        lines.append(f"  AWS SSO detected:             {mfa.get('aws_sso_detected', False)}")
        lines.append(f"  MFA-enabled IAM users:        {mfa.get('mfa_enabled_count', 0)}")
        lines.append(f"  Long-lived SA tokens (k8s):   {mfa.get('long_lived_sa_token_count', 0)}")
    if "skipped" not in wi:
        sa_with = wi.get("service_accounts_with_irsa", 0)
        sa_without = wi.get("service_accounts_without_irsa", 0)
        lines.append(f"  SAs with IRSA annotation:     {sa_with} of {sa_with + sa_without}")
        lines.append(f"  Long-lived IAM access keys:   {wi.get('long_lived_access_key_count', 0)}")
        lines.append(f"  automountServiceAccountToken defaults on: {wi.get('automount_default_on', False)}")

    # Devices pillar
    devs = evidence.get("devices_pillar", {})
    inv = devs.get("device_inventory", {})
    lines.append("\nDevices Pillar (IA-3, CM-8):")
    if "skipped" in inv:
        lines.append(f"  Device inventory: {inv['skipped']}")
    else:
        lines.append(f"  Node count:                   {inv.get('node_count', 0)}")
        lines.append(f"  Unmanaged node detected:      {inv.get('unmanaged_node_detected', False)}")
        for node in inv.get("nodes", [])[:10]:
            lines.append(
                f"    {node['name']} ({node['role']}, {node['os']}, "
                f"managed={node['managed']})"
            )

    # Applications pillar
    apps = evidence.get("applications_pillar", {})
    mon = apps.get("monitoring_coverage", {})
    lines.append("\nApplications Pillar (AC-3, SI-4):")
    if "skipped" not in mon:
        lines.append(f"  Falco running:                {mon.get('falco_running', False)}")
        lines.append(f"  Prometheus running:           {mon.get('prometheus_running', False)}")
        lines.append(f"  Grafana running:              {mon.get('grafana_running', False)}")
        lines.append(f"  Security Hub enabled:         {mon.get('security_hub_enabled', False)}")

    # Data pillar
    data = evidence.get("data_pillar", {})
    enc = data.get("encryption_at_rest", {})
    lines.append("\nData Pillar (SC-28):")
    if "skipped" not in enc:
        lines.append(f"  Etcd/secrets encryption:      {enc.get('etcd_encryption_detected', False)}")
        lines.append(f"  KMS-managed secrets:          {enc.get('k8s_secrets_kms', False)}")
        s3_buckets = enc.get("s3_default_encryption", [])
        total_s3 = len(s3_buckets)
        encrypted_s3 = sum(1 for b in s3_buckets if b.get("encrypted"))
        if total_s3 > 0:
            lines.append(f"  S3 buckets encrypted:         {encrypted_s3} of {total_s3}")
            unencrypted = [b["bucket"] for b in s3_buckets if not b.get("encrypted")]
            if unencrypted:
                lines.append(f"  Unencrypted buckets: {', '.join(unencrypted[:5])}")
        else:
            lines.append("  S3 buckets: AWS not configured or no buckets found")

    return "\n".join(lines)


def build_zt_crew(evidence: dict, eng: dict) -> Crew:
    """
    Build the 3-agent ZT compliance crew with pre-collected evidence.

    Agents:
      assessor   -- assigns ZT pillar stage (T/I/A/O) + S / OTS / NA per control, states the gap
      sar_writer -- compiles M-22-09 ZT compliance report from assessor output
      poam_writer -- converts every OTS to a POA&M item with M-22-09 ZT language
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
    initial_deadline = (today + timedelta(days=90)).strftime("%Y-%m-%d")
    advanced_deadline = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    # Control requirements table for task descriptions
    ctrl_req_lines = []
    for ctrl_id, req in _CONTROL_ZT_REQUIREMENTS.items():
        ctrl_req_lines.append(
            f"  {ctrl_id:<6} pillar={req['pillar']:<16} min={req['min_stage']:<12} "
            f"requirement={req['description']}"
        )
    ctrl_req_text = "\n".join(ctrl_req_lines)

    # ------------------------------------------------------------------ #
    # Task 1: ZT Pillar Stage + Control Assessment                         #
    # ------------------------------------------------------------------ #
    assessment_task = Task(
        description=(
            f"Assess ZT controls for M-22-09 compliance.\n"
            f"System: {system_name} | Cluster: {cluster} | Analyst: {analyst}\n"
            f"Assessment Date: {assessment_date}\n\n"
            f"Controls in scope: {', '.join(CONTROLS)}\n"
            f"Framework: M-22-09 (OMB Memorandum, January 2022)\n"
            f"Mandate baseline: ZT-Initial (required by FY2024)\n\n"
            "=== M-22-09 ZT MATURITY FRAMEWORK ===\n"
            f"{_ZT_FRAMEWORK}\n\n"
            "=== CONTROL-LEVEL ZT REQUIREMENTS ===\n"
            f"{ctrl_req_text}\n\n"
            "=== EVIDENCE COLLECTED FROM ENVIRONMENT (kubectl + AWS CLI, no LLM) ===\n"
            f"{evidence_text}\n\n"
            "=== FULL RAW EVIDENCE (JSON) ===\n"
            f"{raw_json}\n\n"
            "ASSESSMENT INSTRUCTIONS:\n"
            "1. The collector has provided 'pillar_stages' as a starting point. "
            "   Use them as hints, but verify against the raw evidence before finalizing.\n"
            "2. For EACH ZT pillar (Identity, Devices, Networks, Applications, Data), assign:\n"
            "   - Stage: Traditional (T) / Initial (I) / Advanced (A) / Optimal (O)\n"
            "   - Justification: cite specific evidence metrics (coverage_pct, node_count, etc.)\n"
            "   - Gap: what must be done to reach the next stage\n"
            "3. For EACH control, assign:\n"
            "   - Determination: Satisfied (S) / Other Than Satisfied (OTS) / Not Applicable (NA)\n"
            "   - ZT pillar it belongs to\n"
            "   - Specific gap if OTS (exact resource names, exact metrics)\n"
            "   - Severity: High / Medium / Low\n"
            "4. Flag whether the system meets the M-22-09 Initial mandate minimum "
            "   (all pillars >= Initial).\n"
            "5. OTS blocking M-22-09 Initial compliance = High severity. "
            "   OTS above Initial = Medium. Below Traditional baseline = Critical.\n"
        ),
        expected_output=(
            "1. ZT PILLAR SUMMARY TABLE:\n"
            "   PILLAR | STAGE (T/I/A/O) | JUSTIFICATION | GAP TO NEXT STAGE\n"
            "   One row per pillar (Identity, Devices, Networks, Applications, Data)\n\n"
            "2. OVERALL ZT STAGE: Traditional / Initial / Advanced / Optimal "
            "(lowest pillar stage, with 2-sentence justification)\n\n"
            "3. M-22-09 MANDATE STATUS: Compliant / Non-Compliant with ZT-Initial mandate\n\n"
            "4. CONTROL TABLE (one row per control):\n"
            "   CONTROL | PILLAR | DETERMINATION | SPECIFIC FINDING | SEVERITY\n\n"
            "5. COUNT: X Satisfied, Y Other Than Satisfied, Z Not Applicable\n\n"
            "6. GAP PRIORITY LIST: ordered list of what must be fixed to reach Initial, "
            "then Advanced"
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: M-22-09 ZT Compliance Report (SAR)                          #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the M-22-09 Zero Trust Architecture Compliance Report for {system_name}.\n\n"
            f"Controls assessed: {', '.join(CONTROLS)}\n\n"
            "The report must contain ALL of the following sections:\n\n"
            "1. SYSTEM IDENTIFICATION\n"
            f"   - System name: {system_name}\n"
            f"   - Cluster: {cluster}\n"
            f"   - Analyst: {analyst}\n"
            f"   - Assessment date: {assessment_date}\n"
            "   - Framework: M-22-09 (OMB Memorandum, January 2022)\n"
            "   - Mandate baseline: ZT-Initial (required by FY2024)\n\n"
            "2. ASSESSMENT DATE AND SCOPE\n"
            "   - Date of evidence collection\n"
            "   - Tools used (kubectl, AWS CLI)\n"
            "   - Scope: ZT pillars assessed (Identity, Devices, Networks, Applications, Data)\n"
            "   - Controls in scope and their pillar mapping\n\n"
            "3. ZT PILLAR SUMMARY TABLE\n"
            "   Format: Pillar | Stage | Key Gap | Controls\n"
            "   One row per pillar. Stage = Traditional / Initial / Advanced / Optimal.\n"
            "   Key gap is the single most blocking issue for that pillar.\n\n"
            "4. CONTROL-BY-CONTROL TABLE\n"
            "   Format: Control | Pillar | Determination | Specific Finding\n"
            "   One row per control. OTS rows cite exact resource names and metrics.\n\n"
            "5. M-22-09 MANDATE STATUS\n"
            "   - Overall ZT stage (lowest pillar)\n"
            "   - COMPLIANT / NON-COMPLIANT with ZT-Initial mandate\n"
            "   - If non-compliant: which pillars are below Initial and what they need\n\n"
            "6. GAP PRIORITY RANKING\n"
            "   6a. Critical gaps blocking M-22-09 Initial compliance (if any)\n"
            "   6b. Gaps to reach Advanced (FY2026 target)\n"
            "   Use specific metrics: 'SC-7: 3 of 8 namespaces have no NetworkPolicy'\n\n"
            "Write in formal GRC language. Reference exact metrics from the evidence. "
            "Do not editorialize."
        ),
        expected_output=(
            "A complete M-22-09 Zero Trust Architecture Compliance Report in Markdown format "
            "with all six sections. ZT pillar summary table in section 3. "
            "Control table in section 4 with specific findings and pillar mapping. "
            "M-22-09 mandate compliance status clearly stated in section 5. "
            "Gap rankings use exact metric comparisons. "
            "Ready for attachment to the CA/SC evidence package."
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
            "from the M-22-09 ZT compliance report.\n\n"
            "CRITICAL: Use M-22-09 ZT pillar language, not just NIST control language.\n"
            "  WRONG: 'SC-7 NetworkPolicy is not configured'\n"
            "  RIGHT: 'M-22-09 Networks pillar requires default-deny NetworkPolicy on all namespaces "
            "-- 3 of 8 namespaces have no NetworkPolicy (coverage: 62.5%)'\n\n"
            "POA&M required fields for each item:\n"
            "- control_id: e.g. SC-7\n"
            "- weakness_name: specific, not generic "
            "(e.g. 'No default-deny NetworkPolicy -- 3 namespaces unprotected')\n"
            "- weakness_description: 2-3 sentences -- what is wrong, which ZT pillar, "
            "M-22-09 requirement vs. current state (with exact metrics from evidence)\n"
            "- detection_method: gp-crewai zt-collectors / BERU M-22-09 assessment\n"
            "- responsible_role: Platform Engineer / Security Engineer / Cloud Engineer\n"
            "- resources_required: effort estimate (e.g. '1 day Platform Engineer')\n"
            f"- scheduled_completion: Gaps blocking M-22-09 Initial use {initial_deadline} "
            f"(90 days). Advanced-stage gaps use {advanced_deadline} (365 days). "
            "High severity = 90 days max.\n"
            "- milestones: at least one checkpoint before completion date\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON.\n"
            "Every OTS from the report gets exactly one POA&M item. No exceptions."
        ),
        expected_output=(
            "A POA&M registry as a JSON array -- one object per OTS finding. "
            "All fields populated. weakness_description uses M-22-09 ZT pillar language with "
            "specific metrics from the collector evidence. "
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


def run_zt_crew(run_id: str | None = None) -> dict:
    """
    Full ZT compliance pipeline: collect -> assess -> SAR -> POA&M.

    Returns the crew result plus raw evidence for archival.
    """
    run_ts = datetime.now(timezone.utc)
    if run_id is None:
        run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    eng = get_engagement_config()
    system_name = eng.get("system_name", "Target System")

    print(f"[{run_id}] Collecting ZT evidence (kubectl + AWS CLI, no LLM)...")
    evidence = run_zt_collectors()

    zt_signals = evidence.get("zt_signals", {})
    overall_stage = zt_signals.get("overall_stage", "Unknown")
    m22_compliant = zt_signals.get("m22_09_compliant", False)
    pillar_stages = zt_signals.get("pillar_stages", {})

    print(f"[{run_id}] Collector ZT signal: overall={overall_stage} "
          f"m22_compliant={m22_compliant} (agents will verify)")
    for pillar, stage in pillar_stages.items():
        print(f"[{run_id}]   {pillar:<16} {stage}")

    print(f"[{run_id}] Running BERU crew: assessor -> sar_writer -> poam_writer...")
    crew = build_zt_crew(evidence, eng)
    result = crew.kickoff()

    return {
        "run_id": run_id,
        "system": system_name,
        "cluster": eng.get("cluster"),
        "analyst": eng.get("analyst"),
        "framework": "M-22-09",
        "baseline": "ZT-Initial",
        "controls": CONTROLS,
        "collector_zt_stage": overall_stage,
        "collector_m22_09_compliant": m22_compliant,
        "collector_pillar_stages": pillar_stages,
        "raw_evidence": evidence,
        "crew_output": str(result),
    }


if __name__ == "__main__":
    output = run_zt_crew()
    print(json.dumps({
        "run_id": output["run_id"],
        "system": output["system"],
        "framework": output["framework"],
        "collector_zt_stage": output["collector_zt_stage"],
        "collector_m22_09_compliant": output["collector_m22_09_compliant"],
        "collector_pillar_stages": output["collector_pillar_stages"],
    }, indent=2))
