"""
AC Access Control Audit Crew — BERU-AI version of 02-access-control-hardening.md

Playbook: GP-CONSULTING/AC/playbooks/02-access-control-hardening.md
Controls:  AC-2, AC-3, AC-6, AC-17

Architecture:
  Step 1 (collect) — pure Python kubectl, no LLM. See collectors.py.
  Step 2 (assess)  — CrewAI: assessor agent reads evidence + control cards, assigns S/OTS/NA.
  Step 3 (report)  — CrewAI: sar_writer produces SAR, poam_writer produces POA&M items.

Why Step 1 is not a CrewAI agent:
  kubectl output is structured data. An LLM adds nothing to data collection and adds
  failure modes (hallucinated resource names, ReAct loop confusion). The collector runs
  deterministically and hands structured evidence to the agents.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from crewai import Crew, Task, Process

# Resolve agents.py from parent crew/ directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents import assessor, sar_writer, poam_writer  # noqa: E402

from .collectors import run_ac_collectors

CONTROLS = ["AC-2", "AC-3", "AC-6", "AC-17"]
SYSTEM_NAME = "Anthra-SecLAB (k3d-seclab)"


def _format_evidence_block(evidence: dict) -> str:
    """Render collected evidence as readable text for task descriptions."""
    lines = []

    # AC-2
    ac2 = evidence.get("ac2_account_management", {})
    admin_bindings = [b for b in ac2.get("cluster_admin_bindings", []) if b.get("is_cluster_admin")]
    lines.append(f"AC-2 — Account Management:")
    lines.append(f"  cluster-admin bindings: {len(admin_bindings)}")
    for b in admin_bindings:
        subj_names = [s.get("name") for s in b.get("subjects", [])]
        lines.append(f"    {b['binding']} → subjects: {subj_names}")
    sas = ac2.get("service_accounts", [])
    automount_on = [s for s in sas if s.get("automount_token") is True]
    lines.append(f"  service accounts with automount=True: {len(automount_on)} of {len(sas)}")
    iam = ac2.get("iam_users", {})
    if "skipped" in iam:
        lines.append(f"  IAM users: {iam['skipped']}")
    else:
        lines.append(f"  IAM users collected: {len(iam) if isinstance(iam, list) else 'see raw'}")

    # AC-3
    ac3 = evidence.get("ac3_access_enforcement", {}).get("rbac_enforcement", {})
    lines.append(f"\nAC-3 — Access Enforcement:")
    lines.append(f"  rbac_api_enabled: {ac3.get('rbac_api_enabled')}")
    lines.append(f"  anonymous_access_allowed: {ac3.get('anonymous_access_allowed')}")
    lines.append(f"  unauthenticated_access_allowed: {ac3.get('unauthenticated_access_allowed')}")

    # AC-6
    ac6 = evidence.get("ac6_least_privilege", {})
    root_pods = ac6.get("root_pods", [])
    priv = ac6.get("privileged_containers", [])
    wildcards = ac6.get("wildcard_roles", [])
    lines.append(f"\nAC-6 — Least Privilege:")
    lines.append(f"  pods missing runAsNonRoot: {len(root_pods)}")
    for p in root_pods[:5]:
        lines.append(f"    {p['namespace']}/{p['pod']} ({p['container']})")
    if len(root_pods) > 5:
        lines.append(f"    ... and {len(root_pods) - 5} more")
    lines.append(f"  privileged containers: {len(priv)}")
    lines.append(f"  wildcard ClusterRoles: {len(wildcards)}")
    for w in wildcards:
        lines.append(f"    {w['name']}: {w['rule']}")

    # AC-17
    ac17 = evidence.get("ac17_remote_access", {}).get("remote_access_posture", {})
    lines.append(f"\nAC-17 — Remote Access:")
    lines.append(f"  api_server_tls: {ac17.get('api_server_tls')}")
    exposed = ac17.get("exposed_services", [])
    lines.append(f"  exposed LoadBalancer/NodePort services: {len(exposed)}")
    eks = ac17.get("eks_public_endpoint", {})
    if "skipped" in eks:
        lines.append(f"  EKS endpoint: {eks['skipped']}")
    else:
        lines.append(f"  EKS endpoint: {eks}")

    return "\n".join(lines)


def build_ac_audit_crew(evidence: dict, system_name: str = SYSTEM_NAME) -> Crew:
    """
    Build the 3-agent AC audit crew with pre-collected evidence baked into task descriptions.

    Agents:
      assessor   — assigns S / OTS / NA per control, states the gap
      sar_writer — compiles Security Assessment Report from assessor output
      poam_writer — converts every OTS to a FedRAMP POA&M item
    """
    assess = assessor()
    sar = sar_writer()
    poam = poam_writer()

    evidence_text = _format_evidence_block(evidence)
    raw_json = json.dumps(evidence, indent=2)

    # ------------------------------------------------------------------ #
    # Task 1: Control Assessment                                           #
    # ------------------------------------------------------------------ #
    assessment_task = Task(
        description=(
            f"Assess AC-family controls for system: {system_name}\n\n"
            "Controls in scope: AC-2, AC-3, AC-6, AC-17\n\n"
            "EVIDENCE COLLECTED FROM CLUSTER (kubectl output, no LLM involved):\n"
            f"{evidence_text}\n\n"
            "FULL RAW EVIDENCE (JSON):\n"
            f"{raw_json}\n\n"
            "Control assessment criteria:\n"
            "- AC-2 (Account Management): Are all accounts documented with business justifications? "
            "Is token automount disabled on default SAs? Are cluster-admin bindings justified?\n"
            "- AC-3 (Access Enforcement): Is RBAC active? Is anonymous access blocked? "
            "Is unauthenticated access blocked?\n"
            "- AC-6 (Least Privilege): Are all pods running as non-root? "
            "Are there privileged containers? Are wildcard RBAC verbs/resources eliminated?\n"
            "- AC-17 (Remote Access): Is API server TLS-only? "
            "Are there unnecessary LoadBalancer/NodePort exposures? Is EKS endpoint private?\n\n"
            "Determination values: Satisfied / Other Than Satisfied / Not Applicable\n"
            "For every Other Than Satisfied determination you MUST provide:\n"
            "  - The specific finding from the evidence (exact pod name, role name, binding name)\n"
            "  - The gap: what is missing or wrong\n"
            "  - The impact if not remediated\n"
            "  - Severity: High / Medium / Low\n"
        ),
        expected_output=(
            "A control determination table — one row per control:\n"
            "CONTROL | DETERMINATION | EVIDENCE REVIEWED | GAP | IMPACT | SEVERITY\n"
            "Followed by a count: X Satisfied, Y Other Than Satisfied, Z Not Applicable."
        ),
        agent=assess,
    )

    # ------------------------------------------------------------------ #
    # Task 2: SAR                                                          #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the Security Assessment Report for {system_name}.\n\n"
            "Controls assessed: AC-2, AC-3, AC-6, AC-17\n\n"
            "The SAR must contain:\n\n"
            "1. EXECUTIVE SUMMARY\n"
            "   - System: Anthra-SecLAB (k3d-seclab)\n"
            "   - Assessment date (use today's date)\n"
            "   - Total controls assessed, S / OTS / NA counts\n"
            "   - Overall risk posture (one paragraph)\n\n"
            "2. ASSESSMENT FINDINGS (one section per OTS control)\n"
            "   - Control ID and full name\n"
            "   - Determination: Other Than Satisfied\n"
            "   - Evidence reviewed (specific resource names from kubectl output)\n"
            "   - Gap description\n"
            "   - Risk impact\n\n"
            "3. SATISFIED CONTROLS\n"
            "   - Table with one-line evidence summary per control\n\n"
            "4. NOT APPLICABLE CONTROLS\n"
            "   - Table with justification\n\n"
            "Reference exact resource names (pod names, role names, binding names) "
            "from the assessment. Write in formal GRC language."
        ),
        expected_output=(
            "A complete Security Assessment Report with all four sections. "
            "OTS findings reference specific cluster resources by name. "
            "Format: Markdown, ready for attachment to the CA-2 evidence package."
        ),
        agent=sar,
        context=[assessment_task],
    )

    # ------------------------------------------------------------------ #
    # Task 3: POA&M                                                        #
    # ------------------------------------------------------------------ #
    poam_task = Task(
        description=(
            "Generate a POA&M item for every Other Than Satisfied finding in the SAR.\n\n"
            "FedRAMP POA&M required fields:\n"
            "- Control ID\n"
            "- Weakness Name (specific — not 'RBAC issue', but 'Wildcard verbs in local-path-provisioner-role')\n"
            "- Weakness Description (2-3 sentences: what is wrong, where, why it matters)\n"
            "- Detection Method (gp-crewai kubectl collector / BERU analysis)\n"
            "- Responsible Role (Platform Engineer / Security Engineer)\n"
            "- Resources Required (effort estimate)\n"
            "- Scheduled Completion (YYYY-MM-DD, within 30-90 days for Medium/High)\n"
            "- Milestones (at least one checkpoint before the completion date)\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON. "
            "Every OTS from the SAR gets exactly one POA&M item. No exceptions."
        ),
        expected_output=(
            "A POA&M registry as a JSON array — one object per OTS finding. "
            "All FedRAMP fields populated. "
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


def run_ac_audit(system_name: str = SYSTEM_NAME) -> dict:
    """
    Full AC audit pipeline: collect → assess → SAR → POA&M.

    Returns the crew result plus the raw evidence for archival.
    """
    run_ts = datetime.now(timezone.utc)
    run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")

    print(f"[{run_id}] Collecting AC evidence (kubectl, no LLM)...")
    evidence = run_ac_collectors()

    print(f"[{run_id}] Running BERU crew: assessor → sar_writer → poam_writer...")
    crew = build_ac_audit_crew(evidence, system_name)
    result = crew.kickoff()

    return {
        "run_id": run_id,
        "system": system_name,
        "controls": CONTROLS,
        "raw_evidence": evidence,
        "crew_output": str(result),
    }


if __name__ == "__main__":
    output = run_ac_audit()
    print(json.dumps({"run_id": output["run_id"], "system": output["system"]}, indent=2))
