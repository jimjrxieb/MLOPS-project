# AI RMF — MEASURE Function

> MEASURE evaluates AI systems for trustworthy characteristics — validity, reliability, safety, security, fairness, privacy, and transparency.
> MEASURE is where "we identified the risk" becomes "we have a number to attach to it."
> Source: NIST AI RMF 1.0 (January 2023) + AI 600-1 (July 2024)

---

## What MEASURE Covers

MEASURE is the evaluation layer. GOVERN created the policies. MAP identified the risks. MEASURE quantifies them — or, where quantification is not yet possible, documents the gap. Without MEASURE, MANAGE has no evidence base for its risk responses, and the AO has no defensible signal that the AI system is performing as intended.

**3PAO question this answers:** "What evidence do you have that BERU actually behaves the way you say it behaves?"

---

## MEASURE 1 — Appropriate Methods and Metrics

### MEASURE 1.1
**Subcategory:** Approaches and metrics for measuring AI risks are selected and implemented
**In plain English:** You picked specific tests and benchmarks before training, not after — and you can defend why you picked them
**BERU Evidence Required:**
- Four-eval architecture documented in design decision D-010: knowledge × {brain, agent}, pentest × {brain, agent}
- Pre-training brain baseline captured in `5-experiments/exp-005-beru-3b-baseline/metrics.json` (knowledge 29.4%, pentest 40.3%)
- Promotion gate threshold (≥70%) chosen before fine-tune begins, not after results land

**Auditor Question:** "Show me the metrics you committed to before you started fine-tuning. Did you change them after results came in?"

---

### MEASURE 1.2
**Subcategory:** Appropriateness of AI metrics and effectiveness of existing controls is regularly assessed
**BERU Evidence Required:**
- Eval suites versioned (`v1`, `v2`) — when a metric stops being meaningful, a new suite is authored, not a silent edit
- Quarterly review of eval-gate threshold against observed model behavior
- `test_beru_evals.py` enforces eval-suite quality (coverage across OWASP LLM categories, no duplicate questions)

---

### MEASURE 1.3
**Subcategory:** Internal experts and external stakeholders provide regular input
**BERU Evidence Required:**
- Stakeholder review of eval suites before promotion gates change
- Pentest eval includes scenarios contributed from the AI security playbooks (`AI-SEC-LENS/10-AI-SECURITY/`)
- Adversarial scenarios reviewed by human author before inclusion in the corpus

---

## MEASURE 2 — Trustworthy Characteristics Evaluation

### MEASURE 2.1
**Subcategory:** Test sets, metrics, and details about the tests used are documented
**In plain English:** Anyone can reproduce your evaluation from the documentation alone
**BERU Evidence Required:**
- Eval suite JSONL files in `4-eval-clarify/`: `beru_knowledge_brain_v2.jsonl` (30 questions), `beru_pentest_brain_v1.jsonl` (22 questions, 10 OWASP LLM categories)
- Validation set held-out at `1-local-pipeline/01-raw-data-lake/beru_validation_v1.jsonl` (75 examples)
- Lineage manifest at `BERU-AI/training-data/lineage-manifest.json` records SHA-256 per eval suite

**Auditor Question:** "Hand me your eval set. Can I run it against the model and get the same number you reported?"

---

### MEASURE 2.4
**Subcategory:** The functionality and behavior of the AI system are monitored
**BERU Evidence Required:**
- MLflow inference tracking via `JADE-AI/mlops/inference_tracker.py` — every inference call logs model version, latency, RAG context IDs, output fingerprint
- Prometheus + Grafana monitoring stack (`GP-INFRA/LinkOps-Manifests/helm/monitoring/`) with 9 PromQL alert rules
- Drift-detection rule mapped to CM-3 in lineage manifest

---

### MEASURE 2.5
**Subcategory:** AI system trustworthiness — validity, accuracy, reliability — is evaluated
**In plain English:** The model does what it says it does, consistently
**BERU Evidence Required:**
- Knowledge-brain eval measures BERU's accuracy on compliance questions (current baseline 29.4%, gate ≥70%)
- Reliability tested via repeated inference on the same input — same question must produce the same control citation
- 9-field output schema enforces structural validity; downstream parsing fails fast if the model deviates

---

### MEASURE 2.6
**Subcategory:** AI system safety — robustness against unintended outputs — is evaluated
**BERU Evidence Required:**
- Pentest suite includes safety-adjacent scenarios (refusal of unauthorized actions, refusal of S-rank approvals at the analyst tier)
- Hard stops in BERU system prompt: never hallucinate IDs, never approve B/S-rank, never skip EVIDENCE GAP
- Safety regression tests in `8-tests/test_beru_training_data.py` enforce the 30% adversarial floor in the training corpus

**Auditor Question:** "What evidence do you have that BERU refuses to act outside its authority?"

---

### MEASURE 2.7
**Subcategory:** AI system security and resilience are evaluated and documented
**In plain English:** You tested whether attackers can make BERU misbehave
**BERU Evidence Required:**
- Pentest brain eval covers all 10 OWASP LLM categories; current baseline 40.3% with RAG, gate ≥70%
- Training corpus has 100+ LLM01 (prompt injection) examples, 76 LLM06 (sensitive disclosure) examples, 150 LLM08 (excessive agency) examples
- Garak + promptfoo integrated in test pipeline (`8-tests/test_beru_evals.py`)
- AI-system-targeted MITRE ATLAS techniques mapped in `frameworks/mitre-atlas/` (16 distinct AML.T techniques)

**Auditor Question:** "Show me the prompt-injection scenarios you tested and what BERU's refusal rate is."

---

### MEASURE 2.8
**Subcategory:** Risks associated with transparency and accountability are documented
**BERU Evidence Required:**
- Every BERU finding cites a specific NIST 800-53 control AND (if AI in scope) an AI RMF subcategory — this is the dual-citation pattern from D-007
- 9-field output forces explanation: FINDING, CONTROL, EVIDENCE REVIEWED, EVIDENCE GAP, RISK justification, CONTROL OWNER, POA&M, CISO SUMMARY
- Transparency by design — model card at `6-model-cards/challenger/beru-v1.md` documents intended use, limits, and known failure modes

---

### MEASURE 2.9
**Subcategory:** AI system fairness and bias are evaluated
**In plain English:** You checked whether BERU treats similar findings consistently across system types and contexts
**BERU Evidence Required:**
- Bias detection scripts in `4-eval-clarify/2-test-data/evaluation/bias-detection/detect_training_bias.py`
- Fairness audit script: `GP-CONSULTING/AI-SEC-LENS/10-AI-SECURITY/06-MODEL-GOVERNANCE/01-auditors/audit-bias-fairness.sh`
- Break-scenario at `06-MODEL-GOVERNANCE/scenarios/break-GOVERN1-bias-regression.md`
- Crosswalk at `frameworks/crosswalk/800-53-to-ai-rmf.md` maps "MEASURE 2.9 (fairness/bias) → BERU should classify risk consistently across system types"

**Auditor Question:** "How would you know if BERU consistently ranks findings on AI systems higher than equivalent findings on traditional IT systems?"

---

### MEASURE 2.10
**Subcategory:** AI system privacy risk is examined
**BERU Evidence Required:**
- D-005 (synthetic-only training data) is the structural defense: no real client SSPs, no real scanner output, no PII ever enters the training corpus
- PII filter as part of the corpus quality gate
- BERU does not retain prior-session content (architecture-level privacy control)
- Privacy mapping documented in lineage manifest under PT-1 (Policy and Procedures for PII)

**Auditor Question:** "If I asked BERU to repeat a customer's name from training data, what would happen?"

---

### MEASURE 2.11
**Subcategory:** AI system fairness and bias evaluation results are documented
**BERU Evidence Required:**
- Bias-detection runs append results to the experiment register (`5-experiments/`) — every run produces a logged metric
- Fairness regression flagged automatically when a per-system-type rank distribution deviates beyond threshold
- Documented results feed back into the corpus-quality gate (`8-tests/test_beru_training_data.py`)

---

### MEASURE 2.12
**Subcategory:** Effectiveness of existing AI risk management is evaluated
**BERU Evidence Required:**
- Quarterly CA-7 governance review covers AI-system-specific controls
- Eval-gate trends tracked across versions in `5-experiments/`
- HITL routing log audited monthly to confirm the C-rank ceiling is honored (every B/S finding hit HITL, zero auto-approved)

---

## MEASURE 3 — Tracking Identified Risks

### MEASURE 3.1
**Subcategory:** Approaches, personnel, and documentation are in place for risks not measured or insufficiently measured
**BERU Evidence Required:**
- Risk-register entry RA-AI-001 (BERU) lists known measurement gaps (e.g., production-traffic drift detection deferred to Q3)
- For each gap: documented owner, target date, compensating control during the gap
- Quarterly review of the risk register catches measurement debt before it accumulates

**Auditor Question:** "What AI risks do you know exist but cannot yet measure, and how are you tracking them?"

---

### MEASURE 3.2
**Subcategory:** Risk tracking approaches considered for both pre-deployment and post-deployment AI risks
**BERU Evidence Required:**
- Pre-deployment: eval gates (knowledge + pentest) block promotion below 70%
- Post-deployment: MLflow tracks every inference call; PromQL alerts trigger on latency, error rate, drift indicators
- Synthetic-event tests (e.g., quarterly LLM01 injection drill) confirm the post-deployment monitoring is alive

---

### MEASURE 3.3
**Subcategory:** Feedback gathered from operators and users about negative AI impact
**BERU Evidence Required:**
- Feedback endpoint in `GP-INFRA/GP-API/routes/feedback.py` collects user-reported BERU errors
- Feedback loop in `1-local-pipeline/feedback_loop.py` identifies categories where BERU underperforms
- HITL approver disagreement rates tracked; sustained disagreement triggers a re-evaluation of the rank assignment logic

---

## MEASURE 4 — Feedback Efficacy

### MEASURE 4.1
**Subcategory:** Measurement approaches for identifying AI risks are connected to deployment context(s)
**BERU Evidence Required:**
- Eval suites are scoped to BERU's actual deployment context (GRC analysis, not general-purpose chat)
- Pentest scenarios reflect real adversarial framings BERU would encounter in scanner-ingestion paths
- Knowledge questions reflect the 800-53 + AI RMF + ATLAS + OWASP LLM landscape BERU is trained to operate in

---

### MEASURE 4.2
**Subcategory:** Measurement results are documented and reviewed
**BERU Evidence Required:**
- Every eval run appends to `5-experiments/` with params.yaml + metrics.json + notes.md
- Results reviewed at the CA-7 quarterly governance meeting
- Champion/challenger comparison documented in `6-model-cards/` with eval-result tables

---

### MEASURE 4.3
**Subcategory:** Measurable performance improvements are documented based on consultations with relevant AI actors
**BERU Evidence Required:**
- Each model version (v1.0, v1.1, v2.0) has a documented improvement narrative tied to specific eval-suite deltas
- Performance improvements traceable: training-data change → corpus-quality test → fine-tune → eval lift → promotion gate
- Negative results also documented (failed challengers stay in `6-model-cards/challenger/` archive, not deleted)

---

## Quick Reference: MEASURE → 800-53 Controls

| AI RMF Subcategory | Maps to 800-53 | Why |
|---|---|---|
| MEASURE 1.1 (select methods) | CA-2, SA-11 | Security assessment, developer testing |
| MEASURE 1.2 (assess appropriateness) | CA-7, SI-4 | Continuous monitoring, system monitoring |
| MEASURE 2.1 (test documentation) | CA-2, SA-11 | Assessment plans, developer testing |
| MEASURE 2.4 (functionality monitoring) | SI-4, AU-2 | System monitoring, event logging |
| MEASURE 2.5 (validity / reliability) | SA-11, CA-2 | Developer testing, security assessment |
| MEASURE 2.6 (safety) | SI-2, SI-7 | Flaw remediation, integrity verification |
| MEASURE 2.7 (security / resilience) | RA-5, SI-4, IR-4 | Vulnerability scanning, monitoring, incident handling |
| MEASURE 2.8 (transparency) | AU-3, AU-6 | Audit-record content, audit review |
| MEASURE 2.9 (fairness / bias eval) | RA-3, CA-2 | Risk assessment, security assessment |
| MEASURE 2.10 (privacy) | PT-1, PT-2 | PII policy, authority to process PII |
| MEASURE 2.11 (fairness results documented) | CA-5, AU-12 | POA&M, audit logging |
| MEASURE 2.12 (effectiveness) | CA-7, PM-31 | Continuous monitoring, continuous improvement |
| MEASURE 3.1 (unmeasured risks) | RA-3, CA-5 | Risk assessment, POA&M |
| MEASURE 3.2 (pre/post-deployment) | CA-2, SI-4 | Security assessment, system monitoring |
| MEASURE 3.3 (operator feedback) | IR-4, SI-4 | Incident handling, monitoring |
| MEASURE 4.2 (results documented) | CA-5, AU-12 | POA&M, audit logging |
| MEASURE 4.3 (performance improvements) | CA-7, SI-2 | Continuous monitoring, flaw remediation |
