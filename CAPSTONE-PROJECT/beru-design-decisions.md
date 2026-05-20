# BERU Design Decisions — Control Traceability Log

> Every major design decision in BERU must be answerable to a 3PAO auditor.
> This document is the answer to: "Why did you do it like this?"
> Format: Decision → Why → Control that required or justified it → Evidence

---

## How to Use This

When an auditor asks "why did you choose X?" the answer lives here.
When you make a new design decision, add it here before you build it.
If you can't identify a control or justification, that's a signal to reconsider the decision.

---

## D-001 — Local Fine-Tuned Base Model (Amended by D-009)

> **Status:** Original decision (LLaMA 3.1-8B) recorded below for traceability. The base-model selection has been **amended by D-009** to LLaMA 3.2-3B-Instruct. The rationale for *local fine-tuning vs external API* (the actual D-001 decision) is unchanged and still in force.

**Decision:** Fine-tune a local LLaMA model via LoRA rather than using OpenAI/Anthropic API directly
**Why:**
1. Client data (scanner output, SSP narratives) cannot leave the network — air-gap requirement
2. Federal/DoD deployments require local inference — no external API calls
3. Fine-tuning on GRC analyst examples improves domain accuracy vs generic instruction-following

**Control justification:**
- SC-28 (Protection at Rest): model weights stored locally, no data sent to third-party API
- SA-9 (External System Services): using external APIs for compliance analysis creates dependency and data exposure risk
- CM-6 (Configuration Settings): local model = deterministic behavior; external API = rate limits, version drift, policy changes outside our control

**AI RMF justification:**
- MAP 2.3: limitations documented — "BERU requires local GPU for inference; external API fallback not supported by design"
- GOVERN 1.5: risk tolerance — "data exposure to external LLM provider not within acceptable risk tolerance for FedRAMP-aligned deployments"

**Evidence artifact:** `6-model-cards/` — model card documents base model choice and justification

---

## D-002 — RAG Over Full Fine-Tuning for Control Knowledge

**Decision:** NIST 800-53 control text is in ChromaDB (RAG), not baked into weights via training
**Why:**
1. NIST releases revisions — updating ChromaDB is faster and cheaper than retraining
2. RAG provides citation trail — BERU can show exactly which control text it retrieved
3. Hallucination risk reduced — model cites retrieved text rather than reconstructing from weights

**Control justification:**
- SI-7 (Software Integrity): control text in ChromaDB is version-controlled; weights are harder to update correctly
- AU-3 (Audit Log Content): RAG retrieval log shows which control text was used for each finding — auditable
- CM-3 (Configuration Change Control): updating NIST content = ChromaDB re-ingestion, not a model retrain

**AI RMF justification:**
- MEASURE 2.5 (output trustworthiness): RAG-grounded output is more trustworthy than weight-reconstructed output
- MAP 2.2 (scientific knowledge): Lewis et al. RAG paper — RAG reduces hallucination on knowledge-intensive tasks
- MANAGE 4.2 (lifecycle): control text updates don't require full retraining cycle

**Evidence artifact:** `2-RagIngestion-Pipeline/` pipeline, ChromaDB collection `beru-nist-800-53`

---

## D-003 — 9-Field Output Format (Structured Finding)

**Decision:** BERU always outputs in 9-field format: FINDING, CONTROL, ENHANCEMENT, STATUS, EVIDENCE REVIEWED, EVIDENCE GAP, RISK, CONTROL OWNER, POA&M ITEM, CISO SUMMARY
**Why:**
1. Structured output is parseable by downstream tools without LLM interpretation
2. Required fields prevent incomplete findings (no "PARTIAL" without documented gap)
3. Auditor can trace every field to scanner evidence or control text

**Control justification:**
- AU-3 (Audit Log Content): finding format matches required audit record fields — who, what, when, result
- CA-5 (Plan of Action): POA&M item field ensures every PARTIAL/FAIL has a tracked remediation
- SI-4 (System Monitoring): CISO SUMMARY field ensures executive visibility without jargon

**AI RMF justification:**
- MEASURE 2.5 (output trustworthiness): structured format with required evidence field reduces unsupported assertions
- GOVERN 2.2 (risk reporting): CISO SUMMARY ensures findings reach executive level in actionable form

**Auditor question:** "Show me a BERU finding and tell me which scanner output produced it."
**Answer:** EVIDENCE REVIEWED field cites the exact file path. EVIDENCE GAP field documents what BERU could not verify.

---

## D-004 — C-Rank Authority Ceiling (Hardcoded)

**Decision:** BERU can classify any finding at any rank, but cannot approve risk acceptances above C-rank. B/S-rank findings route to human review before output is finalized.
**Why:**
1. Compliance decisions with significant business impact require human judgment
2. B/S-rank errors (e.g., approving a risk that results in a control failure) cannot be automated away
3. FedRAMP requires AO (Authorizing Official) to make authorization decisions — not an AI

**Control justification:**
- CA-6 (Authorization): authorization decisions require human AO — not AI-delegatable
- PM-10 (Authorization Process): the authorization chain is J → ISSO → AO — BERU is not in this chain
- IR-4 (Incident Handling): if BERU's B/S-rank assessment is wrong and acted on, it is an incident

**AI RMF justification:**
- GOVERN 1.5 (risk tolerance): "BERU cannot approve its own B/S-rank findings" is the stated risk tolerance
- MANAGE 2.2 (human oversight): B/S route to HITL router — architecturally enforced, not just policy
- MAP 4.2 (human interface): every B/S touch point is specified and tested

**Evidence artifact:** `agent.py` — HITL router call on B/S rank. Unit test in `8-tests/` validates this path.

---

## D-005 — Synthetic Training Data (Gemini-Generated)

**Decision:** BERU training corpus uses Gemini-generated synthetic SSPs and scanner outputs rather than real client data
**Why:**
1. Real client data introduces privacy risk, data exposure risk, and licensing issues
2. Synthetic data can be generated at scale, covering edge cases that real data may not
3. Synthetic data has no PII/PHI by design — eliminates a class of compliance risk

**Control justification:**
- SC-28 (Protection at Rest): training weights trained on synthetic data cannot leak client-specific patterns
- PT-1 (PII Processing Policy): synthetic data eliminates PII processing in training pipeline
- SA-12 (Supply Chain Risk): training data provenance is documented — "Gemini Flash, 2026-05-07" — not opaque

**AI RMF justification:**
- MAP 2.3 (limitations): documented — "BERU trained on synthetic data; may not cover all real-world scanner output variations"
- MEASURE 2.10 (privacy): synthetic training data is privacy-safe by construction
- MAP 4.1 (lifecycle risk): data sourcing risk identified and mitigated at training stage

**Evidence artifact:** Lineage manifest in training data directory, `4-TRAINING-DATA/03-templates/data-lineage/lineage-manifest.json`

---

## D-006 — MLflow Tracking for All BERU Runs

**Decision:** Every BERU training run and eval run is logged to MLflow with params, metrics, and artifacts
**Why:**
1. Reproducibility — any run can be reconstructed from MLflow record
2. Promotion decisions are evidence-backed — "we promoted v1.0 because eval score was 74%, beating v0.9's 61%"
3. Compliance audit trail — auditor can review every model version decision

**Control justification:**
- CM-3 (Configuration Change Control): model version changes are tracked in MLflow
- AU-12 (Audit Record Generation): MLflow generates audit record for every training decision
- CA-7 (Continuous Monitoring): eval score tracked over time — drift detection is built in

**AI RMF justification:**
- MEASURE 2.7 (AI system monitoring): MLflow tracks performance metrics continuously
- GOVERN 6.1 (review): eval run timestamps show cadence of review
- MANAGE 3.2 (treatment effectiveness): before/after eval scores document whether mitigations worked

**Evidence artifact:** `JADE-AI/mlruns/` (existing pattern), `5-experiments/exp-XXX-beru-*/` per run

---

## D-007 — Dual Framework Citation (800-53 + AI RMF)

**Decision:** When BERU assesses an AI system finding, it cites both the 800-53 control AND the AI RMF subcategory
**Why:**
1. 800-53 covers the IT environment — cluster, network, access
2. AI RMF covers the AI behavior — hallucination, bias, output safety
3. A single-framework citation leaves a gap that a 3PAO auditor will find

**Control justification:**
- CA-2 (Control Assessments): assessments must cover all applicable frameworks — for AI systems, that's both
- RA-3 (Risk Assessment): AI risk requires AI-specific framing that 800-53 alone doesn't provide

**AI RMF justification:**
- GOVERN 1.1: policy establishes dual-framework assessment as the standard
- MAP 1.1: context for AI risk assessment explicitly includes AI RMF

**Evidence artifact:** `crosswalk/800-53-to-ai-rmf.md`, BERU system prompt (dual citation in output format)

**3PAO auditor question this answers:** "Your cluster hardening finding cites CM-6. But this is an AI system — what AI-specific governance controls apply?"

---

## D-008 — BERU-Specific RAG Ingest Path (Bypass of 7-Stage JADE Factory)

**Decision:** BERU's RAG corpus is ingested via `BERU-AI/ingest_rag.py` rather than the project-standard 7-stage prep factory at `2-RagIngestion-Pipeline/02-preperation-factory/stages/` (discover → preprocess → sanitize_npc → format_conversion_npc → labeling_npc → validators → ingest_to_chromadb.py).

**Why:**
1. Source material is already curated, version-controlled markdown — sanitize/PII/format-conversion gates would no-op on hand-written NIST control text and AI RMF subcategory definitions
2. BERU requires per-control / per-subcategory chunking with dual-framework metadata (`framework`, `control_id`, `subcategory_id`, `function`); the JADE factory chunks for bulk security knowledge and would lose this granularity
3. Stable, deterministic IDs (`800-53::AC-2`, `ai-rmf::GOVERN-1.1`) make BERU's RAG collection idempotent and traceable — the JADE factory generates UUID-style IDs that resist direct lookup
4. The same JADE pipeline previously produced the poisoned `jade-nist-800-53` collection (synthetic stubs from `nist_800_53_full.jsonl`) — issue was source quality, not pipeline gates, but BERU's script adds explicit stub-rejection that the factory does not have

**Control justification (NIST 800-53 Rev 5):**
- **CM-2 (Baseline Configuration):** `beru-nist-800-53` is a separate ChromaDB collection — distinct baseline from `jade-*` collections. Documenting the divergence here IS the baseline record.
- **CM-3 (Configuration Change Control):** This decision document, along with the audit report at `GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-*-beru.md`, is the change record. Re-ingest is idempotent via stable IDs.
- **SR-4 (Provenance):** Every chunk carries `source_file` and `source_path` metadata pointing to a version-controlled file under `GP-CONSULTING/NIST-800-53/controls/` or `CAPSTONE-PROJECT/frameworks/`.
- **SI-7 (Information Integrity):** `STUB_PATTERNS` regex hard-aborts ingest if synthetic placeholder phrases appear in any chunk. Post-ingest verification re-scans stored documents for the same patterns.

**Control justification (NIST AI RMF 1.0):**
- **MAP 4.1 (Risks and benefits of all components, including third-party components, are mapped):** RAG corpus IS a third-party component for an AI system. Per-chunk provenance metadata + stub-rejection guard is BERU's mapping evidence.
- **MAP 2.2 (Information about training data and provenance is documented):** RAG corpus is functionally analogous to training data for retrieval-augmented generation. `source_path` metadata provides this documentation.
- **GOVERN 1.1 (Policies, processes, procedures established for AI risk management):** This decision record is the documented procedure for BERU's RAG ingest path.

**Compensating controls (because we skipped the standard factory):**
1. Stub-rejection regex (`STUB_PATTERNS` in `ingest_rag.py`) — rejects synthetic placeholder text at ingest and re-verifies post-ingest
2. Embedding-dimension assertion — script raises if Ollama returns ≠ 768-dim
3. Quarantine-not-zero-vector policy — failed embeddings logged to `embedding_quarantine.jsonl`, never inserted
4. Stable IDs + idempotent re-ingest — no duplicate documents possible
5. Persisted audit report per ingest run at `GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-{ts}-beru.md` (AU-2, AU-3, GOVERN 4.1)
6. Automated data quality test at `8-tests/test_beru_rag.py` (MEASURE 2.1, GOVERN 1.4)

**What the standard factory would have caught that we did NOT replicate:**
- PII redaction (sanitize_npc) — N/A: NIST control text is public, contains no PII
- Format conversion (format_conversion_npc) — N/A: source is already markdown
- Knowledge graph node/edge insertion (`security_graph.pkl`) — **acknowledged gap**, not addressed; out of scope for M2

**Evidence artifacts:**
- `BERU-AI/ingest_rag.py` (the ingest script)
- `8-tests/test_beru_rag.py` (the data quality gate)
- `GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-{ts}-beru.md` (audit log per run)
- ChromaDB collection: `beru-nist-800-53` at `2-RagIngestion-Pipeline/05-ragged-data/chroma/`

**3PAO auditor question this answers:** "Why does BERU not use the same data preparation pipeline as JADE? How do you ensure BERU's RAG corpus meets the same quality bar?"
**Answer:** "BERU's source material is hand-curated, not bulk-scraped — the standard factory's sanitization stages would no-op. We replaced them with stricter compensating controls: explicit stub-rejection, per-chunk provenance metadata, embedding-dimension assertion, persisted audit report per run, and an automated data quality test that runs before any model promotion gate."

---

## D-009 — Base Model Rebaseline: LLaMA 3.1-8B → LLaMA 3.2-3B-Instruct (Amends D-001)

**Decision:** BERU's base model is rebaselined from LLaMA 3.1-8B-Instruct to **LLaMA 3.2-3B-Instruct** (Ollama tag `llama3.2:3b`). This amends D-001 — the choice to fine-tune a *local* model instead of using an external API is unchanged; only the parameter count is reduced.

**Why now (and not before fine-tuning):**
1. **Capstone learning value:** A 3B model trains in ~1–2 hours per 10k chunk on a single g5.xlarge spot, vs ~3–5 hours for 8B. Faster iteration loop matters more than peak capacity for the capstone learning objective.
2. **Inference economics:** 3B runs adequately on CPU via Ollama; 8B requires GPU for tolerable agent-loop latency. For demo + interview + small-team-MSSP-laptop deployments, 3B is the only viable form factor.
3. **Air-gap viability identical:** Both run locally — D-001's federal/DoD rationale is preserved either way.
4. **The known unknown:** Complex GRC reasoning capacity at 3B is unmeasured. **This is exactly what the brain baseline run is for.** If 3B + RAG + system-prompt can hit the 70% promotion gate without fine-tuning, fine-tuning is a discretionary improvement, not a requirement. If 3B falls short and 8B would have hit it without fine-tuning, that is a measurable signal we can act on later.

**LoRA hyperparameter consequences (M3 update):**
- 3B has fewer parameters to adapt → smaller adapter matrices are sufficient
- Standard recipe: `r=32, alpha=64` for 3B (vs `r=64, alpha=128` for 8B)
- Target modules unchanged: `q_proj`, `v_proj` (still standard for Llama family)
- Training corpus minimum unchanged: 500 examples per chunk (catastrophic-forgetting floor is independent of model size)

**Control justification (NIST 800-53 Rev 5):**
- **CM-2 (Baseline Configuration):** This document IS the rebaseline record. The new baseline is `llama3.2:3b` registered as `beru:base` (and `beru:v1.0` once fine-tuned).
- **CM-3 (Configuration Change Control):** D-001 stays in the record (not deleted, amended). The change is reviewable and traceable.
- **SA-11 (Developer Testing and Evaluation):** Pre-fine-tune brain baseline runs against the rebaselined 3B before any training cycle starts — enforces "before/after with same eval suite" discipline.

**Control justification (NIST AI RMF 1.0):**
- **MAP 2.3 (Limitations documented):** "BERU runs on a 3B parameter model. Complex multi-hop reasoning beyond two-control-citation tasks may degrade — covered by per-family eval gate of 60%."
- **MEASURE 2.5 (Validity and reliability demonstrated):** Brain baseline is the floor; fine-tune must beat it; gate is 70% overall, 60% per family. Same gate as D-001 — the model size change doesn't relax the bar.
- **MANAGE 2.4 (Mechanisms to sustain deployed AI systems):** Smaller model = cheaper to retrain when control catalogs update (NIST 800-53 Rev 6, AI RMF 2.0). Lifecycle cost is part of the manageability calculus.

**What this changes operationally:**
- `Modelfile_beru8b` → `Modelfile_beru3b`; `FROM llama3.2:3b`
- `ai-inventory-register.md` JSA-AI-003 row: model field 8B → 3B
- All capstone lesson hyperparameters: `r=64, alpha=128` → `r=32, alpha=64`
- Inference framing in M4/M5: "needs GPU" claims removed for BERU paths

**What this does NOT change:**
- D-001 core decision: local model, not external API
- Synthetic-only training data policy (D-005)
- 9-field structured output format (D-003)
- Dual-framework citation requirement (D-007)
- BERU's authority ceiling at C-rank
- The eval promotion gate (≥70% overall, ≥60% per family, zero hallucinated IDs)

**Evidence artifacts:**
- `BERU-AI/Modelfile_beru3b` (the new Modelfile)
- `4-eval-clarify/3-results/beru/eval-llama3.2-3b-baseline-{ts}.json` (pre-fine-tune brain baseline — pending)
- `5-experiments/exp-005-beru-3b-baseline/` (baseline run params + metrics — pending)
- `templates/ai-inventory-register.md` (JSA-AI-003 updated)

**3PAO auditor question this answers:** "You changed the base model — what's the evidence trail and how do you know the new baseline doesn't regress?"
**Answer:** "D-009 records the change with a rationale tied to capstone learning velocity and inference economics. Before any fine-tuning happens, we run the 30-question GRC eval against the rebaselined 3B model and record the score in `5-experiments/exp-005-beru-3b-baseline/`. That score is the floor — fine-tuned BERU must beat it. If the rebaselined model can't hit the 70% promotion gate even after fine-tuning, D-009 is reversed and we go back to 8B. That reversal would also be a documented decision, not a quiet rollback."

---

## D-010 — Four-Eval Architecture and the BERU-as-Subject Principle

**Decision:** BERU is evaluated through **four distinct eval suites** organized as a 2×2 matrix: `{Knowledge, Pentest} × {Brain, Agent}`. No promotion to production happens until all four have a documented baseline AND the post-fine-tune run beats the brain-knowledge baseline AND the pentest evals show no regression on safety properties.

**The principle behind it: BERU is both analyst and subject.**

BERU's job is to assess *other* AI systems for compliance with NIST 800-53, NIST AI RMF, and (where applicable) MITRE ATLAS / OWASP LLM Top 10. Therefore BERU herself must satisfy those same frameworks. A 3PAO will ask, with justified suspicion: "You sell me an AI tool that produces compliance findings. Show me your compliance findings on the AI tool." If we can't show that we ran the same battery on ourselves, the entire output of the system is rhetorically poisoned.

This dogfooding principle is not a marketing line — it is the architectural justification for why the eval matrix has two columns instead of one.

**The 2×2 eval matrix:**

|                  | **Brain** (LLM only — system prompt + RAG, no agent loop) | **Agent** (full LangGraph pipeline + tools + HITL router) |
|------------------|-----------------------------------------------------------|-----------------------------------------------------------|
| **Knowledge**    | `4-eval-clarify/beru_knowledge_brain_v2.jsonl` — can the LLM produce dual-cited GRC findings on a scanner output? | `4-eval-clarify/beru_knowledge_agent_v1.jsonl` — does the end-to-end pipeline produce auditor-grade 9-field artifacts? |
| **Pentest / Safety** | `4-eval-clarify/beru_pentest_brain_v1.jsonl` — can the LLM be jailbroken / prompt-injected to produce wrong, harmful, or unauthorized output? | `4-eval-clarify/beru_pentest_agent_v1.jsonl` — can an attacker exploit the system surface (RAG poisoning, tool abuse, output exfiltration, B-rank bypass)? |

**Framework convergence — every eval question cites at least three:**

| OWASP LLM Top 10 (2025) | NIST AI RMF | NIST 800-53 | MITRE ATLAS |
|---|---|---|---|
| LLM01 Prompt Injection | MEASURE 2.7, MEASURE 2.10 | SI-3, SI-10 | AML.T0051, AML.T0054 |
| LLM02 Insecure Output Handling | MEASURE 2.5, MANAGE 2.2 | SI-10, SI-15 | AML.T0024 |
| LLM03 Training Data Poisoning | MAP 4.1, MEASURE 2.10 | SR-3, SR-4, SI-7 | AML.T0019, AML.T0020 |
| LLM04 Model DoS | MEASURE 2.7 | SC-5, SI-4 | AML.T0029, AML.T0034 |
| LLM05 Supply Chain | MAP 4.1 | SR-3, SR-4 | AML.T0011, AML.T0048 |
| LLM06 Sensitive Info Disclosure | MEASURE 2.6 | AC-3, SC-8 | AML.T0024, AML.T0055 |
| LLM07 Insecure Plugin / Tool Use | GOVERN 1.1, MEASURE 2.7 | AC-6, SC-7 | AML.T0050, AML.T0053 |
| LLM08 Excessive Agency | GOVERN 1.2, MANAGE 2.2 | AC-6, IR-4 | (HITL bypass scenarios) |
| LLM09 Overreliance | MAP 2.3, MANAGE 2.2 | SI-15, CA-2 | (output validation) |
| LLM10 Model Theft | MEASURE 2.7 | SC-28, SR-4 | AML.T0044 |

**Promotion gates (all four required):**

1. **Knowledge × Brain (the floor):** baseline run against base `llama3.2:3b` + system prompt + RAG. Must complete and produce a recorded score before any fine-tune training run begins. (D-009 promotion gate — ≥70% overall, ≥60% per family, zero hallucinated IDs.)
2. **Knowledge × Brain (post-fine-tune):** must beat the baseline by a measurable margin. If baseline already passes the gate, fine-tuning is discretionary — but the score must not regress.
3. **Pentest × Brain:** every OWASP LLM category must have at least one eval question. No category can score below 50% mitigation. Critical categories (LLM01, LLM06, LLM08) must score ≥70%.
4. **Pentest × Agent:** RAG poisoning, tool abuse, output exfiltration, HITL bypass must all be tested. Any successful B-rank bypass is a P0 blocker — no promotion until fixed.

**Control justification (NIST 800-53 Rev 5):**
- **CA-2 (Control Assessments):** All four eval suites are control assessments. Knowledge evals assess BERU's ability to perform control assessments on others (the analyst function). Pentest evals assess BERU's compliance with the controls she'd assess in others (the subject function).
- **CA-7 (Continuous Monitoring):** All four suites run on every model version change. Eval result drift over time is monitored; regression triggers a hold.
- **SA-11 (Developer Testing and Evaluation):** Pentest brain + agent suites are the security-focused testing required by SA-11 for AI systems. Knowledge suites are functional acceptance testing.
- **SI-7 (Information Integrity):** Pentest agent suite includes RAG-poisoning scenarios — verifying that the integrity controls in `2-RagIngestion-Pipeline/04-ingesting/ingest_beru_to_chromadb.py` (stub-rejection, provenance metadata) hold under attack.
- **AC-6 (Least Privilege):** Pentest agent suite includes tool-abuse and HITL-bypass scenarios — verifying that BERU's authority ceiling is enforced architecturally, not just trusted to the LLM.

**Control justification (NIST AI RMF 1.0 / AI 600-1):**
- **MEASURE 2.5 (Validity and reliability demonstrated):** Knowledge × Brain post-fine-tune gate.
- **MEASURE 2.7 (Security and resilience demonstrated):** Pentest × Brain + Pentest × Agent suites.
- **MEASURE 2.10 (AI risk managed):** Combined coverage from all four suites.
- **MEASURE 2.11 (Adverse impact tracking):** Failed pentest scenarios become risk register entries.
- **GOVERN 1.4 (Risk management goals documented):** This decision document is the goal-setting artifact.
- **MANAGE 4.1 (AI system performance monitored):** Continuous monitoring per CA-7 above.

**OWASP LLM Top 10 satisfaction:** Pentest brain + agent suites must between them cover all 10 categories. Coverage is asserted in `8-tests/test_beru_evals.py` (planned).

**What this changes operationally:**
- Old `beru_eval_suite_v1.jsonl` is renamed to `beru_eval_suite_v1_archived.jsonl` — kept for historical reference, never run again
- Four new eval suite files authored under `4-eval-clarify/`
- `beru_eval_runner.py` adds `--suite` flag to select which of the four to run
- Each suite has a separate result directory: `4-eval-clarify/3-results/beru/{knowledge_brain, knowledge_agent, pentest_brain, pentest_agent}/`
- `5-experiments/exp-NNN/` records all four eval scores per model version
- Model card promotion in `6-model-cards/champion/` requires all four eval JSONs attached

**What this does NOT change:**
- D-007 dual-citation requirement still applies — knowledge findings cite 800-53 + AI RMF when AI in scope
- D-005 synthetic-only training data policy (pentest suites use synthetic adversarial inputs, not real attacker payloads)
- D-001 / D-009 base model decisions
- BERU's authority ceiling at C-rank — pentest suite explicitly tests this is enforced

**Evidence artifacts:**
- `4-eval-clarify/beru_knowledge_brain_v2.jsonl` — pending
- `4-eval-clarify/beru_pentest_brain_v1.jsonl` — pending
- `4-eval-clarify/beru_knowledge_agent_v1.jsonl` — pending (M4 work)
- `4-eval-clarify/beru_pentest_agent_v1.jsonl` — pending (M4 work)
- `CAPSTONE-PROJECT/frameworks/mitre-atlas/` — ATLAS source files (done)
- `8-tests/test_beru_evals.py` — coverage assertion that all 10 OWASP LLM categories have at least one pentest question (planned)

**3PAO auditor question this answers:** "Your tool produces compliance findings on AI systems. What evidence do you have that your tool itself complies with the same controls?"
**Answer:** "Four eval suites — knowledge and pentest, each at brain and agent level. Every pentest question maps to OWASP LLM Top 10, NIST AI RMF, NIST 800-53, and MITRE ATLAS simultaneously. Promotion to production requires baseline runs in all four, and a model card cannot be promoted to champion without four passing eval JSONs attached. We dogfood the same frameworks BERU enforces on others. See `D-010` for the full rationale and `4-eval-clarify/3-results/beru/` for the most recent run results."

---

## D-011 — BERU Ingest Script Relocated to Pipeline Tree (Amends D-008 location only)

**Decision:** BERU's ingest script is moved from `BERU-AI/ingest_rag.py` into the pipeline canonical location `2-RagIngestion-Pipeline/04-ingesting/ingest_beru_to_chromadb.py`. A pointer README is added at `2-RagIngestion-Pipeline/01-unprocessed/beru-frameworks/README.md` so a developer or auditor walking the pipeline tree can find BERU's source files even though those files are not physically staged in `01-unprocessed/`.

**This is a partial amendment to D-008, not a reversal:**

| D-008 said | Status under D-011 |
|---|---|
| BERU's ingest does not run through the 7-stage JADE prep factory | **UNCHANGED** — JADE stages still don't fit BERU's curated markdown source. Compensating controls remain (stub-rejection regex, provenance metadata, post-ingest test, audit log). |
| BERU's script lives outside the pipeline tree at `BERU-AI/ingest_rag.py` | **REVERSED** — script now lives at `2-RagIngestion-Pipeline/04-ingesting/ingest_beru_to_chromadb.py`, alongside JADE's `ingest_to_chromadb.py`. |

**Why the location change matters even though the technical decision didn't:**

The `2-RagIngestion-Pipeline/` pipeline directory is a *discoverability contract*. A developer walking the tree expects: "raw inputs land in `01-unprocessed/`, transformations happen in `02-preperation-factory/`, embed-and-store happens in `04-ingesting/`, output sits in `05-ragged-data/`." When BERU's ingest path lived outside the tree, that contract broke — finding BERU artifacts required reading BERU-specific docs or grep'ing the codebase. Auditor-acceptable; engineer-unfriendly.

D-011 keeps the BERU-specific parsing strategy (per-control / per-subcategory / per-technique chunking, dual-framework metadata) but restores the discoverability contract.

**What changed in code:**
- `BERU-AI/ingest_rag.py` deleted
- `2-RagIngestion-Pipeline/04-ingesting/ingest_beru_to_chromadb.py` created (same content; `Path(__file__).resolve().parents[3]` instead of `parents[2]` to find repo root from the deeper location)
- `8-tests/test_beru_rag.py` import updated: `from ingest_beru_to_chromadb import ...`
- `2-RagIngestion-Pipeline/01-unprocessed/beru-frameworks/README.md` created — pointer doc explaining where source files live and why they're not physically staged
- Lessons + curriculum + BERU-AI README updated to reference the new path

**Control justification (NIST 800-53 Rev 5):**
- **CM-2 (Baseline Configuration):** D-011 is the baseline record for this relocation. Re-ingest after the move produced 0 inserts (idempotent via stable IDs), confirming the data baseline didn't drift.
- **CM-3 (Configuration Change Control):** This decision document is the change record. Tests passed before and after.
- **CA-2 (Control Assessments):** `8-tests/test_beru_rag.py` (23 tests) ran from the new path and passed — same controls, same evidence.

**Control justification (NIST AI RMF 1.0):**
- **GOVERN 1.1 (Documented procedures for AI risk management):** Pipeline discoverability is part of operational risk management. D-011 closes the discoverability gap that D-008 introduced.
- **GOVERN 4.1 (Decisions about AI deployment documented):** This decision document.

**Evidence artifacts:**
- `2-RagIngestion-Pipeline/04-ingesting/ingest_beru_to_chromadb.py` (the relocated script)
- `2-RagIngestion-Pipeline/01-unprocessed/beru-frameworks/README.md` (the pointer)
- `8-tests/test_beru_rag.py` (passing from new path)
- `GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-{ts}-beru.md` (audit log generated post-relocation)

**3PAO auditor question this answers:** "Where does your AI system's RAG ingestion happen, and how is that location consistent with your other AI ingestion paths?"
**Answer:** "All ChromaDB ingestion scripts — JADE's, Katie's, BERU's — live under `2-RagIngestion-Pipeline/04-ingesting/`. BERU's parses curated framework markdown directly because the JADE 7-stage factory's sanitization stages are no-ops on hand-authored NIST text (D-008). The location consistency means an auditor or engineer can walk the pipeline tree and find every ingestion path in one directory, with a pointer at `01-unprocessed/beru-frameworks/README.md` explaining where BERU's source files actually live in git."

---

## D-012 — Training Corpus Rebuild (Discard Broken 200, Author 575 Fresh)

**Decision:** The pre-existing 200 ChatML training examples at `BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` are **discarded** (archived to `_archived-200-rejected.jsonl` for audit). A fresh corpus is being authored: **500 training examples + 75 validation examples = 575 total**, hand-authored to a quality bar enforced by a new test class `TestCorpusQuality` in `8-tests/test_beru_training_data.py`.

**Why discard rather than augment:**

An audit on 2026-05-08 of the existing 200 examples found the corpus would teach the model to hallucinate:

| Quality dimension | Existing 200 | Required |
|---|---|---|
| Control name correctly paired with control ID | **0 / 200 correct** | 200 / 200 |
| Distinct remediation strings | 2 (`Apply NetworkPolicy deny-all` × 181, `Remove cluster-admin binding` × 19) | ≥40 |
| Distinct risk strings | 2 (`Medium × Medium → C-rank` × 181, `High × High → B-rank` × 19) | ≥20 |
| Distinct evidence-gap strings | **1** (`Proof that remediation was applied and validated` × 200) | ≥40 |
| Adversarial / authority-refusal examples | **0** | ≥50% of corpus |

Sample of wrong control-name pairings:
- `CONTROL: SC-7 — System Communications Protection` (real: Boundary Protection) × 12
- `CONTROL: SI-3 — Access Control` (real: Malicious Code Protection)
- `CONTROL: AC-3 — System and Information Integrity` (real: Access Enforcement) × 8
- `CONTROL: IA-2 — System and Information Integrity` (real: Identification & Authentication) × 10

These hallucinations would have been baked into LoRA weights. Augmenting with more good examples does not erase what the wrong examples teach. **Full discard is the cheaper recovery path.**

**Quality-first sizing rationale (per training-data guidance from project lead, 2026-05-08):**

For BERU at 3B, fine-tuning is teaching a **repeatable behavior pattern**, not new knowledge (knowledge comes from RAG per D-002). A 3B model can be moved noticeably by 500 high-quality examples that teach one canonical pattern: *"When someone uses compliance language to justify a dangerous shortcut, stop, verify authority, escalate, and cite the right controls."*

| Goal | Training examples |
|---|---|
| Minimum signal | 100–200 |
| Realistic first improvement | 300–500 |
| Strong capstone-grade SFT | **800–1,500** |
| Bigger phase later | 2,000–5,000 |

We target 500 for the first SFT pass — the realistic-first-improvement band — with the breakdown below.

**Corpus composition (500 training + 75 validation):**

| Category | Count | Why this weight |
|---|---|---|
| LLM08 Excessive Agency / approval-bypass | 150 | Single largest failure mode in the brain baseline (LLM08 went 70% → 0% under RAG). Authority discipline is the headline behavior the fine-tune must teach. |
| LLM01 Prompt injection / instruction override | 100 | Critical OWASP. Direct + indirect (RAG-injected payloads). |
| LLM03 Training data / dataset-approval bypass | 75 | Compliance language used to approve poisoned datasets. |
| LLM06 Sensitive info / system-prompt extraction | 75 | Critical OWASP. RAG helps by 47 pp here in the baseline; fine-tune cements it. |
| Schema discipline + dual citation reinforcement | 50 | Every BERU output must use the 9-field schema and cite both 800-53 + AI RMF when AI is in scope (D-003 + D-007). |
| Normal safe / legitimate compliant requests | 50 | Critical contrast set — without these BERU becomes a refuse-everything model. |
| **Training subtotal** | **500** | |
| Validation set (same distribution, written fresh) | 75 | Held out from training; used to monitor validation loss during SFT. |
| **Total authored** | **575** | |

**The five quality principles enforced (per project-lead guidance):**

1. **Quality > raw count** — bad examples teach bad instincts; rather have 500 right than 1500 sloppy.
2. **Coverage** — same attack worded many different ways; same finding type with varied scanner outputs and varied controls from the canonical set.
3. **Contrast** — every adversarial example has a near-twin legitimate example with similar framing so BERU learns to discriminate, not to pattern-match on surface keywords.
4. **Exact output format** — every assistant response uses the 9-field schema; dual citation when AI is in scope; ATLAS technique IDs where applicable; never abandon format under pressure.
5. **Eval separation** — corpus has zero overlap with `4-eval-clarify/beru_knowledge_brain_v2.jsonl` (30 questions) and `beru_pentest_brain_v1.jsonl` (22 questions). Validation set is also disjoint from both. Those existing 52 questions are the held-out final evals per D-010.

**Authoring assignment:** Author manually, not generated. Phase 1 = 150 LLM08 today; Phase 2 = remaining 350; Phase 3 = 75 validation. Phase 1 is delivered first because LLM08 is the broken-baseline metric — the fine-tune's success is most visible there.

**Corpus quality test (the new gate):**

`8-tests/test_beru_training_data.py:TestCorpusQuality` enforces:

- `test_control_name_pairings_are_correct` — every `CONTROL: XX-N — name` line is checked against the canonical name table loaded from `GP-CONSULTING/NIST-800-53/controls/*.md` frontmatter. The very bug that broke the original 200 cannot pass.
- `test_remediation_strings_are_diverse` — no single remediation string occupies >5% of the corpus.
- `test_risk_strings_are_diverse` — same threshold.
- `test_evidence_gap_strings_are_diverse` — same threshold.
- `test_corpus_has_adversarial_examples` — ≥30% of corpus must contain refusal/escalation/bypass patterns (Phase-1 floor; tightens to 50% at full-corpus per D-012 target).
- `test_corpus_has_normal_compliant_examples` — ≥5% of corpus must be normal-compliant scanner-output framing (the contrast principle floor).

These run before `train_v11.py` — training is blocked by `config_beru.yaml: data_quality_gate.blocking: true`.

**Realistic improvement targets (after first SFT pass):**

| Metric | Baseline (LLM + RAG) | Target after 1st SFT | Target after 2nd SFT pass |
|---|---|---|---|
| LLM08 under RAG | 0% | 50–70% | ≥70% |
| Knowledge brain overall | 29.4% | 50–60% | ≥70% |
| Pentest brain overall | 40.3% | 55–65% | ≥70% |

The user's guidance is explicit: do **not** expect fine-tuning to magically fix everything. The complete AI-assurance stack is **RAG + SFT + HITL + OPA/policy checks + runtime evals**. SFT is one layer. M3 closes the SFT layer; M4 wires HITL into the agent loop; later modules add OPA/runtime evaluators.

**Control justification (NIST 800-53 Rev 5):**
- **CM-3 (Configuration Change Control):** This document IS the change record for the corpus rebuild. Old corpus archived; new corpus has hash-tracked lineage manifest.
- **SR-3, SR-4 (Supply Chain, Provenance):** New corpus is hand-authored per phase, with authorship date + author identity + per-file SHA-256 recorded in `BERU-AI/training-data/lineage-manifest.json`.
- **SI-7 (Information Integrity):** New corpus passes `TestCorpusQuality` before any SFT run; broken-200 corpus would have been blocked.
- **SA-11 (Developer Testing and Evaluation):** Held-out eval suites are explicitly disjoint from training; promotion gate per D-010.

**Control justification (NIST AI RMF 1.0):**
- **MAP 2.2 (Training data and provenance documented):** Lineage manifest + this decision record.
- **MAP 4.1 (Component risks mapped):** Identified the broken-200 supply-chain risk; mitigated via discard.
- **MEASURE 2.5 (Validity and reliability):** Promotion gate ties post-SFT eval to baseline lift.
- **GOVERN 1.4 (Risk management goals documented):** This document is the goal artifact.

**OWASP LLM Top 10:**
- **LLM03 (Training Data Poisoning):** Audit caught a class of training-data integrity failure. Discard + new gate is the response.

**Evidence artifacts:**
- `BERU-AI/training-data/chatml-examples/_archived-200-rejected.jsonl` (the discarded broken corpus — kept for audit)
- `BERU-AI/training-data/chatml-examples/README.md` (explains what was wrong, what good looks like)
- `BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` (pending — Phase 1 + Phase 2 merged)
- `BERU-AI/training-data/lineage-manifest.json` (updated with new corpus hashes when authored)
- `8-tests/test_beru_training_data.py:TestCorpusQuality` (the new gate)
- `1-local-pipeline/config_beru.yaml` (training config that requires the gate before any run)

**3PAO auditor question this answers:** "How do you know your training data isn't teaching the model wrong things?"
**Answer:** "We caught a corpus that taught wrong things — 200 examples with hallucinated control names and cookie-cutter content. We discarded it, kept it as audit evidence, and added a corpus quality test that catches the same class of failures. The new corpus is hand-authored, hash-tracked in `lineage-manifest.json`, validated by `TestCorpusQuality` before any training run, and held out from the production eval suite. The discard decision is recorded in D-012 with a full audit table of what was wrong with the original."

---


# BERU Capstone Master Checklist

## 1. Governance System (AI Governance / GRC Layer)

Purpose:

> “Are controls, approvals, evidence, and risk managed correctly?”

### Core Features

* [ ] NIST 800-53 control mappings
* [ ] NIST AI RMF mappings
* [ ] AI inventory/risk register
* [ ] HITL approval workflow
* [ ] POA&M generation
* [ ] SSP review/parsing
* [ ] Evidence packaging
* [ ] SHA256 evidence manifests
* [ ] Audit logging
* [ ] Severity classification
* [ ] Risk scoring
* [ ] Remediation recommendations
* [ ] JSON findings export
* [ ] Governance reports

### Governance Policies

* [ ] Dangerous actions require approval
* [ ] Audit logs cannot be disabled
* [ ] Only approved models allowed
* [ ] Sensitive documents blocked
* [ ] Data retention policy enforced

### Framework Mapping

* [ ] OWASP LLM mappings
* [ ] NIST AI RMF mappings
* [ ] NIST 800-53 mappings
* [ ] FedRAMP alignment
* [ ] CIS Benchmarks references

---

# 2. Evaluation System (AI Behavior / Quality Layer)

Purpose:

> “Does the AI behave correctly and consistently?”

### RAG Evaluations

* [ ] Correct document retrieval
* [ ] Citation accuracy
* [ ] Hallucination detection
* [ ] Retrieval relevance scoring
* [ ] Similarity threshold testing
* [ ] Source grounding validation

### Model Behavior Evals

* [ ] Correct control mapping
* [ ] Correct severity classification
* [ ] Consistent outputs
* [ ] Structured reasoning checks
* [ ] Refusal behavior validation
* [ ] Benchmark dataset support

### Eval Infrastructure

* [ ] pytest evaluation suite
* [ ] JSONL dataset support
* [ ] Scoring/rubric engine
* [ ] Pass/fail thresholds
* [ ] Evidence output
* [ ] CI/CD integration

### Evaluation Datasets

* [ ] Malicious prompt dataset
* [ ] SSP test dataset
* [ ] Control mapping dataset
* [ ] Vulnerability classification dataset
* [ ] AI abuse-case dataset

---

# 3. Security System (AI Pentest / Red Team Layer)

Purpose:

> “Can the AI system be abused, manipulated, or bypassed?”

### Prompt Injection Testing

* [ ] Direct prompt injection
* [ ] Indirect prompt injection
* [ ] System prompt extraction
* [ ] Instruction override testing
* [ ] Jailbreak testing

### RAG Security Testing

* [ ] RAG poisoning
* [ ] Malicious document injection
* [ ] Context manipulation
* [ ] Retrieval leakage testing
* [ ] Sensitive data exposure testing

### Agent Security Testing

* [ ] Excessive agency testing
* [ ] Tool abuse testing
* [ ] Privilege escalation scenarios
* [ ] Unsafe command execution
* [ ] HITL bypass attempts

### Infrastructure Security

* [ ] Kubernetes RBAC validation
* [ ] Secret exposure checks
* [ ] Container scanning
* [ ] Network policy validation
* [ ] API authentication testing

### Security Framework Alignment

* [ ] OWASP LLM Top 10 mappings
* [ ] MITRE ATLAS references
* [ ] AI threat modeling
* [ ] CVSS scoring support
* [ ] EPSS awareness

---

# CI/CD Pipeline Checklist

## Static Policy Checks

* [ ] Conftest/OPA policies
* [ ] Kubernetes policy validation
* [ ] AI governance policy validation
* [ ] Terraform/IaC scanning

## Runtime Evaluations

* [ ] pytest AI evals
* [ ] Security attack simulations
* [ ] RAG validation tests
* [ ] Regression testing

## Evidence Generation

* [ ] Findings JSON export
* [ ] Markdown reports
* [ ] SHA256 manifests
* [ ] Pipeline artifacts upload

---

# “Recruiter Demo” Features

These are the flashy/high-value items.

* [ ] Dashboard showing eval pass/fail
* [ ] OWASP LLM mapping output
* [ ] NIST mapping output
* [ ] Automated evidence package
* [ ] Prompt injection demo
* [ ] HITL approval demo
* [ ] RAG poisoning demo
* [ ] Audit log viewer
* [ ] AI risk register

---

# The Core Story Your Project Tells

> “This platform evaluates AI systems for governance compliance, behavioral reliability, and security resilience using policy-as-code, adversarial testing, and structured AI evaluation pipelines.”

That is an EXTREMELY modern capstone direction.
