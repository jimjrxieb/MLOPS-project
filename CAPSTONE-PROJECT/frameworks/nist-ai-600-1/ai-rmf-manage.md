# AI RMF — MANAGE Function

> MANAGE activates risk responses — prioritizing, treating, tracking, and learning from AI risks.
> MANAGE is where "we identified the risk" becomes "we did something about it."
> Source: NIST AI RMF 1.0 (January 2023) + AI 600-1 (July 2024)

---

## What MANAGE Covers

MANAGE is the execution layer. GOVERN created the policies. MAP identified the risks. MEASURE quantified them. MANAGE decides what to do and does it — while keeping humans in the loop for decisions above the AI's authority level.

**3PAO question this answers:** "When BERU identifies a risk in your AI system, what happens next?"

---

## MANAGE 1 — Risk Prioritization

### MANAGE 1.1
**Subcategory:** Risks prioritized and responses planned
**In plain English:** Not all risks get the same response — you have a triage system
**BERU Evidence Required:**
- Rank system (E/D/C/B/S) maps directly to MANAGE 1.1
- E/D-rank: auto-fix (pattern NPCs)
- C-rank: JADE proposes, human approves
- B/S-rank: human only, BERU provides context and evidence

**Auditor Question:** "How does BERU decide which findings are urgent vs. low priority?"

---

### MANAGE 1.2
**Subcategory:** Resources acquired for risk mitigation
**BERU Evidence Required:**
- Control owner matrix — the human who owns each control is identified
- HITL router — routes B/S-rank findings to the correct human with full context
- POA&M milestone tracking — resources (people + dates) assigned to each weakness

---

### MANAGE 1.3
**Subcategory:** Responses to AI risks prioritized
**In plain English:** You have a documented order of operations for responding to AI-specific risks
**BERU Evidence Required:**

| AI Risk Type | Priority | Response |
|---|---|---|
| Hallucinated control ID in production finding | P1 | Immediate retraction, BERU retrained, MLflow experiment flagged |
| BERU misclassifies B-rank as D-rank | P1 | Human review queue for all B-rank outputs (existing control) |
| BERU's RAG retrieval returns wrong control | P2 | Re-embed affected collection, re-run affected findings |
| BERU eval score drops below promotion gate | P2 | Block deployment, trigger feedback loop |
| BERU's system prompt bypassed via prompt injection | P1 | Output safety check, input sanitization (02-PROMPT-INJECTION playbook) |

---

## MANAGE 2 — Risk Treatment

### MANAGE 2.1
**Subcategory:** Treatments to address identified AI risks managed
**In plain English:** You have explicit mitigations for each documented risk
**BERU Evidence Required:**
- Hallucination risk → RAG grounding over NIST controls (M2 in curriculum)
- Wrong control ID → `validate_control_id()` in `nist_mapper.py` rejects invalid IDs
- B/S escalation failure → HITL router is not optional — B/S output goes to queue or is blocked

---

### MANAGE 2.2
**Subcategory:** Mechanisms for AI risk mitigation implemented
**In plain English:** The mitigations are code, not just documents
**BERU Evidence Required:**
- `nist_mapper.py` — `validate_control_id()` rejects malformed IDs
- System prompt hard stops — embedded in Modelfile, not just a readme
- HITL router — `hitl_router.py` exists and is called by `BERU-AI/agent/nodes.py`
- Eval gate — GitHub Actions workflow blocks merge if eval score drops

**Auditor Question:** "Show me where the 'BERU cannot approve B/S-rank findings' constraint is enforced in code, not just documentation."

**Answer you must give:** Point to `BERU-AI/agent/nodes.py` where B/S findings route to `hitl_router.py` before any output is written. Show the test that validates this path.

---

### MANAGE 2.3
**Subcategory:** Unintended consequences of AI risk responses addressed
**In plain English:** Fixing one thing doesn't break another
**BERU Evidence Required:**
- Regression test suite: `8-tests/` runs on every push — if BERU change breaks existing behavior, CI fails
- When a new training example is added, the full eval suite re-runs before promotion
- Feedback loop traces back to specific training examples — no silent corpus changes

---

### MANAGE 2.4
**Subcategory:** Actions taken to address AI risks documented
**BERU Evidence Required:**
- MLflow run metadata: every training run documents what changed and why
- `5-experiments/` notes.md per experiment: what was tried, what happened, what was decided
- Commit messages reference the control or risk being addressed

---

## MANAGE 3 — Incident Response for AI

### MANAGE 3.1
**Subcategory:** Responses to AI risk incidents documented
**In plain English:** When BERU makes a mistake that matters, you have a post-mortem process
**BERU Evidence Required:**
- Session handoff files in `0-data-lab/claudecode-fixes/` — this pattern already exists
- When BERU produces an incorrect finding in production: document in `claudecode-fixes/`, add training example, re-eval
- Template: problem → root cause → fix → new eval question added → training signal

**Auditor Question:** "Has BERU ever produced an incorrect finding? What did you do?"

---

### MANAGE 3.2
**Subcategory:** Risk treatment effectiveness evaluated
**BERU Evidence Required:**
- Before/after eval scores documented in `5-experiments/` when a mitigation is applied
- "We added 20 AC-6 training examples because BERU was misclassifying privilege escalation findings. Eval accuracy on AC-family improved from 62% to 79%. Evidence: exp-003-beru-ac-focus/metrics.json"

---

## MANAGE 4 — Post-Deployment Management

### MANAGE 4.1
**Subcategory:** Post-deployment AI risk management policies established
**In plain English:** You don't stop managing risk after you deploy — you have a continuing process
**BERU Evidence Required:**
- MLflow inference tracking: every production BERU run is logged
- Periodic re-eval cadence: BERU is re-evaluated when NIST guidance updates or after 90 days
- Drift detection: if BERU's confidence scores drop on a category, trigger feedback loop
- Re-training trigger: defined (confidence drop threshold OR new major NIST revision)

**Auditor Question:** "NIST released AI 600-1 after you trained BERU. How does your process ensure BERU stays current?"

---

### MANAGE 4.2
**Subcategory:** AI risk management continues across the full lifecycle
**BERU Evidence Required:**
- Model card is a living document — updated at each major version
- Decommissioning policy: when BERU is retired, what happens to the weights?
- Version history maintained in `3-model-registry/`
- Old versions retained for audit trail (30-day minimum before deletion)

---

## Quick Reference: MANAGE → 800-53 Controls

| AI RMF Subcategory | Maps to 800-53 | Why |
|---|---|---|
| MANAGE 1.1 (prioritize) | RA-3, CA-5 | Risk assessment, plan of action |
| MANAGE 1.2 (resources) | CA-5, PM-4 | POA&M milestones, resource allocation |
| MANAGE 2.2 (implement mitigations) | SI-2, CM-4 | Flaw remediation, security impact analysis |
| MANAGE 2.3 (unintended consequences) | CA-2, SA-11 | Testing, security impact analysis |
| MANAGE 2.4 (document actions) | CA-5, AU-12 | POA&M, audit logging |
| MANAGE 3.1 (incident response) | IR-4, IR-8 | Incident handling, incident response plan |
| MANAGE 3.2 (evaluate effectiveness) | CA-7, SI-4 | Continuous monitoring |
| MANAGE 4.1 (post-deployment) | CA-7, PM-31 | Continuous monitoring, continuous improvement |
| MANAGE 4.2 (lifecycle) | SA-22, CM-8 | Unsupported components, system inventory |
