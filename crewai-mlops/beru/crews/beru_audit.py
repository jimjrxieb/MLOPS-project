from crewai import Crew, Task, Process
from agents import beru_auditor, triage_agent


def build_audit_crew(finding: str) -> Crew:
    triager = triage_agent()
    auditor = beru_auditor()

    triage_task = Task(
        description=(
            f"Triage the following security finding. Classify severity (Critical/High/Medium/Low), "
            f"assign a rank (E/D/C/B/S), and summarize what needs auditing:\n\n{finding}"
        ),
        expected_output=(
            "A triage report with: severity classification, rank assignment, "
            "affected system/component, and a one-sentence audit scope statement."
        ),
        agent=triager,
    )

    audit_task = Task(
        description=(
            "Using the triage report, perform a full NIST 800-53 assessment. "
            "Identify the applicable control family and control ID. "
            "Call BERU to generate a POA&M item. "
            "Produce a CISO-ready summary with control citation and remediation timeline."
        ),
        expected_output=(
            "A structured audit output containing: "
            "NIST 800-53 control ID + enhancement, "
            "AI RMF subcategory (if AI system in scope), "
            "POA&M item (weakness, detection method, scheduled completion, responsible role), "
            "and a 3-sentence CISO briefing."
        ),
        agent=auditor,
        context=[triage_task],
    )

    return Crew(
        agents=[triager, auditor],
        tasks=[triage_task, audit_task],
        process=Process.sequential,
        verbose=True,
    )
