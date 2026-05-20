"""
SSP → SAR → POA&M crew.

Input:
  ssp_text      — full SSP control narratives (plain text or markdown)
  findings      — optional scanner findings that serve as evidence context
  system_name   — name of the system being assessed

Flow:
  1. SSP Reviewer   — flags unsupported/vague control claims
  2. Assessor       — assigns S / OTS / NA per control with justification
  3. SAR Writer     — produces the Security Assessment Report
  4. POA&M Writer   — converts every OTS into a FedRAMP POA&M item
"""

from crewai import Crew, Task, Process
from agents import ssp_reviewer, assessor, sar_writer, poam_writer


def build_ssp_to_poam_crew(
    ssp_text: str,
    system_name: str = "Target System",
    findings: str = "",
) -> Crew:
    reviewer = ssp_reviewer()
    assess = assessor()
    sar = sar_writer()
    poam = poam_writer()

    evidence_block = (
        f"\n\nScanner findings provided as evidence context:\n{findings}"
        if findings.strip()
        else "\n\nNo scanner findings provided — assess based on SSP narrative alone."
    )

    # ------------------------------------------------------------------ #
    # Task 1: SSP Review                                                   #
    # ------------------------------------------------------------------ #
    review_task = Task(
        description=(
            f"Review the SSP for system: {system_name}\n\n"
            f"SSP CONTROL NARRATIVES:\n{ssp_text}"
            f"{evidence_block}\n\n"
            "For each control section found in the SSP:\n"
            "1. Identify the control ID (e.g. AC-2, SC-7)\n"
            "2. State what the narrative claims is implemented\n"
            "3. State whether cited evidence supports the claim (Yes / Partial / None)\n"
            "4. Flag specific gaps — missing evidence, vague language, untestable claims\n\n"
            "Output format per control:\n"
            "CONTROL: <ID>\n"
            "CLAIM: <what the SSP says>\n"
            "EVIDENCE SUPPORT: Yes / Partial / None\n"
            "GAPS: <specific gaps or 'None'>\n"
        ),
        expected_output=(
            "A structured review of every control in the SSP. "
            "Each control has: ID, claim summary, evidence support level (Yes/Partial/None), "
            "and a gap description. Controls with no gaps are listed as 'Evidence Support: Yes / Gaps: None'."
        ),
        agent=reviewer,
    )

    # ------------------------------------------------------------------ #
    # Task 2: Control Assessment                                           #
    # ------------------------------------------------------------------ #
    assessment_task = Task(
        description=(
            "Using the SSP review results, assess each control and assign a determination.\n\n"
            "Determination criteria:\n"
            "- Satisfied (S): evidence fully supports the implementation claim\n"
            "- Other Than Satisfied (OTS): evidence is missing, partial, or contradicts the claim\n"
            "- Not Applicable (NA): control does not apply to this system type\n\n"
            "For every OTS determination you MUST provide:\n"
            "- The specific control ID and enhancement (e.g. AC-2(1))\n"
            "- The exact gap that caused the OTS\n"
            "- The impact if this gap is not remediated\n"
            "- A severity: High / Medium / Low\n\n"
            "Use the assess_control tool for controls where BERU API context helps."
        ),
        expected_output=(
            "A complete control determination table:\n"
            "CONTROL | DETERMINATION | GAP | IMPACT | SEVERITY\n"
            "One row per control. OTS rows must have all fields populated."
        ),
        agent=assess,
        context=[review_task],
    )

    # ------------------------------------------------------------------ #
    # Task 3: SAR                                                          #
    # ------------------------------------------------------------------ #
    sar_task = Task(
        description=(
            f"Write the Security Assessment Report for {system_name}.\n\n"
            "The SAR must contain:\n\n"
            "1. EXECUTIVE SUMMARY\n"
            "   - System name, assessment date, total controls assessed\n"
            "   - Count of S / OTS / NA determinations\n"
            "   - Overall risk posture (one paragraph)\n\n"
            "2. ASSESSMENT FINDINGS (one section per OTS control)\n"
            "   - Control ID and name\n"
            "   - Determination: Other Than Satisfied\n"
            "   - Evidence reviewed\n"
            "   - Gap description\n"
            "   - Risk impact\n\n"
            "3. SATISFIED CONTROLS\n"
            "   - Table listing all Satisfied controls with one-line evidence summary\n\n"
            "4. NOT APPLICABLE CONTROLS\n"
            "   - Table with justification\n\n"
            "Write in formal GRC language. No opinions — only findings and evidence."
        ),
        expected_output=(
            "A complete Security Assessment Report with all four sections. "
            "OTS findings are detailed. Satisfied and NA controls are tabulated. "
            "The executive summary gives the AO a clear risk picture in one page."
        ),
        agent=sar,
        context=[review_task, assessment_task],
    )

    # ------------------------------------------------------------------ #
    # Task 4: POA&M                                                        #
    # ------------------------------------------------------------------ #
    poam_task = Task(
        description=(
            "Generate a POA&M item for every OTS finding in the SAR.\n\n"
            "FedRAMP POA&M required fields per item:\n"
            "- Control ID\n"
            "- Weakness Name (short, specific — not 'MFA issue', but 'MFA not enforced on privileged accounts')\n"
            "- Weakness Description (2-3 sentences: what is wrong, where, why it matters)\n"
            "- Detection Method (how it was found — SSP review, Trivy scan, kube-bench, etc.)\n"
            "- Responsible Role (the team/role who owns remediation)\n"
            "- Resources Required (effort estimate: eng hours, tooling, cost)\n"
            "- Scheduled Completion (realistic date in YYYY-MM-DD format)\n"
            "- Milestones (at least one intermediate milestone before completion)\n\n"
            "Use the format_poam_item tool to produce each item as structured JSON. "
            "Use the beru_poam tool if you need BERU's assessment context for a specific control.\n\n"
            "Every OTS from the SAR gets a POA&M item. No exceptions."
        ),
        expected_output=(
            "A complete POA&M registry as a JSON array — one object per OTS finding. "
            "Every item has all required FedRAMP fields populated. "
            "Followed by a summary: total items, High/Medium/Low breakdown, "
            "earliest and latest scheduled completion dates."
        ),
        agent=poam,
        context=[assessment_task, sar_task],
    )

    return Crew(
        agents=[reviewer, assess, sar, poam],
        tasks=[review_task, assessment_task, sar_task, poam_task],
        process=Process.sequential,
        verbose=True,
    )
