# AI RMF — MAP Function

> MAP categorizes and contextualizes AI risk before you measure or manage it.
> MAP is where you document what the AI system is, what it does, who it affects, and what can go wrong.
> Without MAP, MEASURE has nothing to measure against.
> Source: NIST AI RMF 1.0 (January 2023) + AI 600-1 (July 2024)

---

## What MAP Covers

MAP is the "understand before you act" function. You are answering: what is this AI system, what context does it operate in, who are the stakeholders, and what risks exist before you even turn it on?

**3PAO question this answers:** "Before you deployed BERU, how did you characterize its risks and document its context of use?"

---

## MAP 1 — Context Establishment

### MAP 1.1
**Subcategory:** Context is established for AI risk assessment
**In plain English:** You documented the environment, use case, and constraints before building
**BERU Evidence Required:**
- AI system registration form completed: what BERU does, who uses it, what data it processes
- Scope defined: BERU assesses GP-Copilot's K8s cluster and AWS environment — not arbitrary systems
- Hard constraints documented: C-rank max authority, never fixes, human review for B/S

**Auditor Question:** "Before you started training BERU, what did you document about its intended use and constraints?"

**Answer you must give:** "We completed the AI system registration form documenting: BERU assesses NIST 800-53 and AI RMF compliance. It processes scanner output (no PII). It produces advisory findings only. B/S-rank findings require human review before any action. These constraints are encoded in the system prompt and rank system."

---

### MAP 1.5
**Subcategory:** Organizational risk tolerance communicated to teams
**BERU Evidence Required:**
- Rank system (E/D/C/B/S) documented and shared — this IS the risk tolerance framework
- MLOps engineer (you) knows: "BERU cannot approve its own B/S-rank findings"
- Architecture law: BERU max authority hardcoded, not just documented in a policy PDF

---

### MAP 1.6
**Subcategory:** AI risk documentation policies established
**BERU Evidence Required:**
- `CAPSTONE-PROJECT/beru-design-decisions.md` — every major choice traced to a control
- Model card updated before any promotion to production
- Training data lineage manifest (`4-TRAINING-DATA/03-templates/data-lineage/lineage-manifest.json`)

---

## MAP 2 — AI System Characterization

### MAP 2.1
**Subcategory:** AI system deployed in its context (not lab conditions only)
**In plain English:** BERU has been tested on real scanner output from a real cluster, not just synthetic examples
**BERU Evidence Required:**
- Eval suite includes real scanner output from `GP-PROJECTS/01-instance/slot-3/`
- At least one end-to-end demo run documented in `5-experiments/`
- MLflow run showing real-world performance, not just synthetic test accuracy

**Auditor Question:** "Has BERU ever been run on real scanner output? What did it produce?"

---

### MAP 2.2
**Subcategory:** Scientific findings and established knowledge documented
**In plain English:** You can point to why your architecture choices are justified (not just "it seemed right")
**BERU Evidence Required:**
- RAG grounding reduces hallucination — cite: Lewis et al. "Retrieval-Augmented Generation" (NeurIPS 2020)
- LoRA fine-tuning on domain data improves domain accuracy — cite: Hu et al. "LoRA" (ICLR 2022)
- Rank system for HITL — cite: NIST AI RMF 1.0 MANAGE-2.2

**Why this matters:** A 3PAO auditor for a federal system will ask "what evidence supports your architectural choices?" You need more than "we tested it."

---

### MAP 2.3
**Subcategory:** AI system scope, characteristics, limitations documented
**In plain English:** You wrote down what BERU cannot do, not just what it can
**BERU Evidence Required:**
- `BERU-COVERAGE.md` — explicit list of controls BERU cannot assess autonomously
- Model card: known failure modes (e.g., "BERU struggles with compound findings that span multiple control families")
- System prompt hard stop: "NEVER write 'investigate further' without specifying exactly what to look for"

**Auditor Question:** "What are BERU's documented limitations? Can it assess all 20 NIST 800-53 families?"

---

## MAP 3 — Risk Identification

### MAP 3.1
**Subcategory:** AI system tested in context prior to deployment
**BERU Evidence Required:**
- 30-question eval suite run on the target environment (K8s cluster)
- End-to-end demo: scanner input → BERU agent → POA&M output
- MLflow experiment `beru-eval` showing pre-deployment eval results

---

### MAP 3.2
**Subcategory:** Risks and benefits mapped to specific stakeholders
**BERU Evidence Required:**

| Stakeholder | Benefit | Risk |
|---|---|---|
| ISSO | Faster control assessment, consistent output | Missed finding if scanner data is incomplete |
| CISO | Auditor-ready briefings on demand | Over-reliance on BERU's risk classification |
| DevSecOps | Faster POA&M creation | POA&M quality depends on BERU's accuracy |
| 3PAO Auditor | Structured evidence packages | Cannot fully replace human auditor judgment |

---

### MAP 3.5
**Subcategory:** Likelihood of impacts assessed
**BERU Evidence Required:**
- Risk assessment template completed for BERU itself as an AI system
- Probability × impact table: what happens if BERU misses a finding at each severity level

---

## MAP 4 — Risk Identification Across Lifecycle

### MAP 4.1
**Subcategory:** Risk identification across lifecycle stages
**In plain English:** You thought about risks at each stage — not just at deployment

| Stage | Risk | Mitigation |
|---|---|---|
| Data collection | Training data contains sensitive real scan output | Use synthetic data (Gemini-generated) for training corpus |
| Training | Model learns wrong NIST control mappings | Eval suite validates mappings before promotion |
| Deployment | BERU produces hallucinated CVE IDs | System prompt hard stop + RAG grounding |
| Production | Model drifts as NIST guidance updates | Periodic re-eval against updated eval suite |
| Decommission | Trained weights contain organizational data patterns | Model card documents data sources; weights deleted per policy |

---

### MAP 4.2
**Subcategory:** Interface between AI and humans specified
**In plain English:** Every touch point where a human interacts with BERU output is documented
**BERU Evidence Required:**
- Human review queue for B/S-rank findings (HITL router)
- CISO briefing: human reads and signs before distribution
- POA&M: human confirms before filing with AO
- SSP narrative: ISSO reviews before inclusion in SSP

---

## MAP 5 — Likelihood and Impact Assessment

### MAP 5.1
**Subcategory:** Likelihood of risks identified and documented
**BERU Evidence Required:**
- Risk assessment template completed with probability × impact estimates
- B/S-rank findings: high likelihood of human harm if acted on without review
- E/D-rank findings: low likelihood — pattern-matched, well-understood

### MAP 5.2
**Subcategory:** Practices for risk identification documented
**BERU Evidence Required:**
- `CAPSTONE-PROJECT/templates/ai-risk-assessment.md` template exists and is used
- Risk assessment completed for BERU before training begins, before deployment, after major version changes

---

## Quick Reference: MAP → 800-53 Controls

| AI RMF Subcategory | Maps to 800-53 | Why |
|---|---|---|
| MAP 1.1 (context) | RA-3, PL-2 | Risk framing before system authorization |
| MAP 2.3 (limitations) | CA-2, RA-3 | Assessment methodology, risk assessment |
| MAP 3.1 (testing in context) | CA-2, SA-11 | Security assessment, developer testing |
| MAP 3.2 (stakeholder risks) | PL-2, PM-9 | System security plan, risk management |
| MAP 4.1 (lifecycle risks) | SA-11, SR-3 | Developer testing, supply chain risk |
| MAP 4.2 (human interface) | CA-5, IR-4 | POA&M, incident handling |
| MAP 5.1 (likelihood) | RA-3, RA-5 | Risk assessment, vulnerability scanning |
