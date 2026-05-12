# AI RMF — GOVERN Function

> GOVERN establishes accountability, policies, and culture for responsible AI risk management.
> Without GOVERN, MAP/MEASURE/MANAGE have no authority and no owner.
> Source: NIST AI RMF 1.0 (January 2023) + AI 600-1 (July 2024)

---

## What GOVERN Covers

GOVERN is the policy and accountability layer. Before you can measure or manage AI risk, someone has to own it, document what "acceptable" looks like, and create the structures that make risk decisions traceable.

**3PAO question this answers:** "Who is responsible for this AI system's risk decisions, and how were those responsibilities documented before the system went live?"

---

## GOVERN 1 — Policies and Culture

### GOVERN 1.1
**Subcategory:** Policies, processes, procedures established for AI risk management
**In plain English:** You have written-down rules for how AI systems get approved, deployed, and monitored
**BERU Evidence Required:**
- AI system registration form completed before deployment
- Approval documented (who signed off and at what authority level)
- Reference to org-level AI policy or acceptable use document

**Auditor Question:** "Show me the approval record for BERU's deployment. Who authorized it?"

---

### GOVERN 1.2
**Subcategory:** Accountability designated for AI risk management decisions
**In plain English:** A named person or role owns each AI system's risk
**BERU Evidence Required:**
- ISSO or system owner named in AI system registration
- Control owner matrix updated to include BERU (AI system owner, not just IT controls)
- Escalation path documented: BERU → J (human) for B/S-rank findings

**Auditor Question:** "If BERU produces an incorrect finding that causes a false POA&M to be filed, who is accountable?"

---

### GOVERN 1.3
**Subcategory:** Organizational teams document AI risk and benefits
**In plain English:** You wrote down what BERU is good at AND where it fails
**BERU Evidence Required:**
- `BERU-COVERAGE.md` — honest capability and gap documentation
- Model card in `6-model-cards/` documenting eval scores, known failure modes
- `beru-design-decisions.md` explaining trade-offs made

**Auditor Question:** "What are the three most significant risks of using BERU as a GRC analyst?"

---

### GOVERN 1.4
**Subcategory:** AI risk management goals established and documented
**In plain English:** You defined what "good enough" looks like before you started
**BERU Evidence Required:**
- Eval promotion gates in curriculum: ≥70% on GRC eval suite before production
- Defined failure modes that block deployment (hallucinated control IDs, zero RAG retrieval)
- MLflow experiment `beru-eval` showing gate criteria as tracked metrics

**Auditor Question:** "What eval score threshold did you set for production deployment, and who approved that threshold?"

---

### GOVERN 1.5
**Subcategory:** Organizational risk tolerance established for AI
**In plain English:** You decided what level of AI error is acceptable for compliance findings
**BERU Evidence Required:**
- Rank system documented: E/D auto, C human-review, B/S human-only
- Human-in-the-loop workflow for all B/S-rank findings BERU produces
- Statement: "BERU findings at B/S rank are advisory only — a human must confirm before any POA&M is filed"

**Auditor Question:** "What happens if BERU misclassifies a critical finding as low risk?"

---

### GOVERN 1.6
**Subcategory:** Policies and procedures for AI workers (developers, operators) established
**In plain English:** The people building and operating BERU know the rules
**BERU Evidence Required:**
- This CAPSTONE-PROJECT documentation is the "policy" for the MLOps engineer
- CLAUDE.md rules (architecture-laws.md, security-standards.md) govern the build
- `NIST-800-53/playbooks/00-beru-start-here.md` governs BERU's behavior

**Auditor Question:** "How does the MLOps engineer know what constraints apply to BERU's training data?"

---

## GOVERN 2 — Risk Tolerance and Reporting

### GOVERN 2.1
**Subcategory:** Risk tolerances set by senior leadership
**In plain English:** The decision about how much AI error is acceptable came from someone with authority
**BERU Evidence Required:**
- Rank system (C-rank max autonomy) approved by J (human decision-maker)
- Documented in `architecture-laws.md`: "BERU max authority: never fixes, never approves above C"

---

### GOVERN 2.2
**Subcategory:** Risk-reporting processes established
**In plain English:** There is a defined path from BERU's findings to a human who acts on them
**BERU Evidence Required:**
- HITL router: B/S findings write to human review queue with full evidence context
- CISO briefing template: executive-level risk summary on a defined cadence
- Escalation path: BERU output → ISSO review → J decision for B/S rank

---

## GOVERN 4 — Governance Structure

### GOVERN 4.1
**Subcategory:** AI risk governance structure documented
**In plain English:** You can draw a box-and-line diagram showing who owns what for BERU's risk
**BERU Evidence Required:**
- Authority chain in `architecture-laws.md`: J → JADE → Katie → JSA Agents
- BERU's position: outputs advisory findings, never executes

### GOVERN 4.2
**Subcategory:** Organizational risks of AI use quantified
**In plain English:** You attempted to quantify the blast radius if BERU gets something wrong
**BERU Evidence Required:**
- Risk assessment completed at intake: what happens if BERU misses a critical finding?
- At minimum: "A missed SI-2 finding could allow an unpatched critical CVE to persist"

---

## GOVERN 5 — Responsible AI Practices

### GOVERN 5.1
**Subcategory:** Organizational policies support responsible AI deployment
**In plain English:** The organization's policy doesn't just allow AI — it constrains it
**BERU Evidence Required:**
- System prompt hard stops: "NEVER hallucinate control IDs, CVEs, CVSS scores"
- Hard stop on B/S-rank approval: architecturally constrained, not just documented

### GOVERN 5.2
**Subcategory:** AI risk management considered at organizational level (not just project level)
**BERU Evidence Required:**
- `ai-inventory-register.md` exists and BERU is registered in it
- BERU risk posture visible at the platform level, not siloed in one playbook

---

## GOVERN 6 — Continuous Improvement

### GOVERN 6.1
**Subcategory:** Policies and practices for AI risk reviewed
**BERU Evidence Required:**
- MLflow eval runs tracked with timestamps — shows ongoing monitoring
- GitHub Actions eval gate: every push re-validates BERU's performance

### GOVERN 6.2
**Subcategory:** Policies and practices improved based on feedback
**BERU Evidence Required:**
- Feedback loop: `1-data-pipeline/feedback_loop.py` identifies weak categories
- When BERU makes an error, a new training example is generated and added to corpus
- Model card updated when champion version changes

---

## Quick Reference: GOVERN → 800-53 Controls

| AI RMF Subcategory | Maps to 800-53 | Why |
|---|---|---|
| GOVERN 1.1 (policies) | PL-1, PL-2 | System security plan covers AI policy |
| GOVERN 1.2 (accountability) | CA-2, PM-10 | Assessment and authorization chain |
| GOVERN 1.3 (document risks) | RA-3, PM-9 | Risk assessment, risk management strategy |
| GOVERN 1.4 (goals) | CA-5, PM-4 | POA&M, plan of action |
| GOVERN 1.5 (risk tolerance) | RA-3, PM-9 | Organization-level risk framing |
| GOVERN 2.2 (reporting) | IR-6, CA-7 | Incident reporting, continuous monitoring |
| GOVERN 5.1 (responsible AI policy) | PL-1, PM-1 | Policy and procedures |
| GOVERN 6.1 (review) | CA-7, SI-4 | Continuous monitoring |
| GOVERN 6.2 (improve) | CA-5, SI-2 | Plan of action, flaw remediation |
