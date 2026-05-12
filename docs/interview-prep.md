# Interview Prep — AI Analyst, I (Pathward)

Companion to `resume-and-coverletter.md`. For every claim on the resume, this doc has the question they're likely to ask, the answer to give, and the exact file path to point at if they push for evidence. At the bottom is an AI/ML vocab list to drill before the interview.

**How to use this:** Read it once cold. Then for each claim, open the file path in the IDE and look at it for 60 seconds — you want to be able to describe what's in the file from memory, not from notes.

---

## OPENING — "Tell me about your AI work"

**Answer (45 seconds):**

> I run an internal AI lab where I've taken AI deployment from sandbox to monitored runtime. The flagship project is BERU — a NIST 800-53 + NIST AI RMF GRC analyst agent. I'm fine-tuning a Llama 3.2-3B model with LoRA on a hand-authored synthetic corpus covering OWASP LLM Top 10 adversarial scenarios. The discipline I'm proudest of is the four-eval architecture: knowledge × {brain, agent}, pentest × {brain, agent}. I measured the brain baseline before any fine-tune so I have a defensible floor — knowledge 29.4%, pentest 40.3% — and the fine-tuned model has to beat both before it's allowed near production. Outside BERU, the lab also runs a K3s environment with Trivy, Kyverno, Falco, and a Prometheus + Grafana + Alertmanager monitoring stack. Everything maps back to NIST AI RMF — bias and explainability to MEASURE 2, the Slack human-in-the-loop gate to MANAGE 2.3.

**What this answer does:** Frames you as someone who builds AND governs. Doesn't oversell — uses real numbers (29.4%, 40.3%) so they know you measure. Hits Pathward's job description language (FastAPI, monitoring, governance) without being too obviously fed.

---

# PART 1 — AI IMPLEMENTATION QUESTIONS

## Q1: "Tell me about your air-gapped LLM deployment."

**Answer:**

> Llama 3.2-3B running on Ollama, served as a local inference endpoint at `localhost:11434`. The Modelfile points at a local GGUF file rather than pulling from a remote registry, which is the deployment pattern banks need for sensitive-data use cases — no model weights leave the environment, no inference data leaves the environment. The FastAPI service layer wraps it so application code talks to a familiar HTTP API rather than to Ollama directly.

**Evidence:**
- `GP-MODEL-OPS/3-model-registry/Modelfile_llama3b` — Modelfile with local GGUF reference
- `GP-MODEL-OPS/BERU-AI/providers/ollama.py` — Ollama provider abstraction
- `GP-INFRA/GP-API/routes/jade.py`, `routes/beru.py` — FastAPI routes that consume the local model

**Soft spot:** Honest framing — the air-gap *pattern* is implemented (local-only weights, local-only inference), but I haven't deployed in a true air-gap network with no internet at all. If they push, say: "The deployment design is air-gap-ready; we haven't run it in production behind an actual air-gap, but the architecture supports it."

---

## Q2: "Walk me through your RAG pipeline."

**Answer:**

> The pipeline has four stages: discover → preprocess → embed → ingest. Source documents land in `01-unprocessed/`, get cleaned and chunked in `03-preprocessed/`, then `ingest_to_chromadb.py` embeds with `nomic-embed-text` — a 768-dimension model running locally via Ollama — and writes to ChromaDB. Each chunk gets stable IDs so re-ingestion is idempotent, and provenance metadata travels with the chunk: source file, ingestion timestamp, lineage hash. Retrieval at inference time is hybrid — vector similarity from ChromaDB plus a knowledge graph in NetworkX for relationship-aware lookups. For BERU specifically, I built a dedicated `beru-nist-800-53` collection with 39 NIST controls, 38 AI RMF subcategories, and 16 MITRE ATLAS techniques.

**Evidence:**
- `GP-MODEL-OPS/2-rag-ingestion/04-ingesting/ingest_to_chromadb.py` — main ingest pipeline
- `GP-MODEL-OPS/2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py` — BERU-specific ingest with stable IDs and lineage
- `GP-MODEL-OPS/2-rag-ingestion/05-ragged-data/chroma/` — local ChromaDB store
- `GP-MODEL-OPS/JADE-AI/core/raggraph_engine.py` — hybrid retrieval engine
- `GP-MODEL-OPS/4-eval-clarify/beru_eval_runner.py` — eval-time RAG retrieval

**Why this answers Pathward's API integration question:** RAG is exactly what banks deploy when they want LLM answers grounded in internal policy/procedure documents instead of free-form generation.

---

## Q3: "How do you monitor the AI services?"

**Answer:**

> Standard cloud-native stack: Prometheus scrapes metrics via ServiceMonitor CRDs, Grafana renders dashboards, and Alertmanager routes alerts. I have nine custom PromQL alert rules covering API availability, error rate, latency, pod restarts, memory and CPU saturation, and ChromaDB health. The runtime visibility is what lets you tune from observed performance data instead of guessing — which is what you'd want before you trust an AI system enough to put it on the path to a customer-facing decision. On the AI-specific side, MLflow tracks every inference call: model version, latency, RAG context IDs used, output fingerprint, and rank decisions if the call routed through the rank classifier.

**Evidence:**
- `GP-INFRA/LinkOps-Manifests/helm/monitoring/templates/prometheus-rules-portfolio.yaml` — 9 PromQL rules, 150 lines
- `GP-INFRA/LinkOps-Manifests/helm/monitoring/templates/grafana-dashboard-portfolio.yaml` — Grafana dashboard JSON
- `GP-INFRA/LinkOps-Manifests/helm/monitoring/templates/servicemonitor-portfolio.yaml` — ServiceMonitor for scrape config
- `GP-MODEL-OPS/JADE-AI/mlops/inference_tracker.py` — MLflow inference tracking with non-blocking fallback

**Why this lands at Pathward:** Drift detection for credit-decisioning models is a model-risk-management requirement (SR 11-7 territory). Talking about *how you'd know* if a model was misbehaving is more impressive than talking about how you trained it.

---

## Q4: "What does the FastAPI service layer do?"

**Answer:**

> It's the integration boundary between application code and the model. The `main.py` registers eight route modules — findings, approvals, escalations, feedback, health, jade, beru, and shift_left. The pattern is HTTP in, structured response out, with the model behind the abstraction so you can swap providers without touching the application code. The approval endpoint is the most interesting piece — C-rank findings come in, get queued, and a human approves or denies through Slack. That endpoint is the technical realization of the AI RMF MANAGE 2.3 human-oversight requirement.

**Evidence:**
- `GP-INFRA/GP-API/main.py` — FastAPI app with 8 route modules
- `GP-INFRA/GP-API/routes/approvals.py` — approval queue endpoint
- `GP-INFRA/GP-API/routes/jade.py` and `routes/beru.py` — model-facing routes

---

# PART 2 — AI GOVERNANCE QUESTIONS

## Q5: "How does NIST AI RMF show up in your work?"

**Answer:**

> Not as a cover sheet — as a wiring diagram. Every BERU finding cites both the NIST 800-53 control and the AI RMF subcategory when an AI system is in scope. For example, an unauthorized LLM endpoint cites AC-3 for access enforcement *and* AI RMF MAP-1.1 for AI system context, MEASURE-2.6 for AI robustness, MANAGE-2.2 for AI risk response. The dual citation forces you to think in both frameworks — one for the underlying IT control, one for the AI-specific dimension. I built a 800-53-to-AI-RMF crosswalk that documents the mappings explicitly so the citations aren't ad hoc.

**Evidence:**
- `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/nist-ai-600-1/` — GOVERN, MAP, MANAGE files (and MEASURE if present — verify before interview)
- `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md` — explicit bidirectional mapping
- `GP-MODEL-OPS/BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` — every AI-touching example uses dual citation

**VERIFIED 2026-05-09:** All four framework files present — GOVERN, MAP, MEASURE, MANAGE. The MEASURE file (`ai-rmf-measure.md`, 238 lines) covers 19 subcategories across the four MEASURE families (methods, trustworthy characteristics, risk tracking, feedback efficacy), with every BERU-cited subcategory grounded in a concrete artifact. Lead with: "All four NIST AI RMF functions are documented as standalone framework files; every BERU finding's AI RMF citation traces back to a documented subcategory in those files."

---

## Q6: "Tell me about the Slack human-in-the-loop approval gate."

**Answer:**

> BERU has a hard-coded authority ceiling at C-rank. Anything ranked B or S routes to the Slack HITL queue — the requesting user authenticates, a separate approver authenticates, and the decision is logged. The notifier is in `slack_notifier.py` and the queue endpoint is in `approvals.py`. The whole pipeline is auditable end-to-end: every approval has the requester, approver, timestamp, finding ID, decision. That's the technical realization of MANAGE 2.3 — and the architectural feature that lets BERU operate at all in a regulated environment.

**Evidence:**
- `GP-INFRA/platform/tools/communication/slack_notifier.py` — Slack notifier with `notify_approval_request()` and `notify_approval_response()`
- `GP-INFRA/GP-API/routes/approvals.py` — approval queue endpoint
- `GP-MODEL-OPS/BERU-AI/core/nist_mapper.py` — explicit MANAGE-2.3 mapping in code

**Pathward angle:** "An LLM that recommends but doesn't decide" is the deployment pattern banks actually use for credit, fraud, and compliance models. Lead with this if they ask about responsible AI.

---

## Q7: "Do you have an AI inventory?"

**Answer:**

> Yes — every AI system gets a JSA-AI-XXX entry with autonomy level, risk classification, HITL enforcement flags, monitoring setup, known limitations, and AI RMF coverage. JSA-AI-001 is JADE — a Llama 3.1-8B for security findings. JSA-AI-002 is Katie — a Llama 3.2-3B for K8s operations. JSA-AI-003 is BERU — the GRC analyst I'm building. JSA-AI-004 is RANK-AI — a sklearn classifier for rank routing. The register also has an unregistered-AI discovery checklist, which is the GOVERN 1.1 requirement — you can't govern what you haven't inventoried.

**Evidence:**
- `GP-MODEL-OPS/CAPSTONE-PROJECT/templates/ai-inventory-register.md` — 4 systems registered, audit trail table

---

## Q8: "How do you handle bias and explainability?"

**Answer:**

> Two pieces. On the eval side, I have bias-detection scripts that run synthetic inputs through the model and look for inconsistent risk-rank decisions across system types — that maps to MEASURE 2.9 fairness. On the audit side, there's a `audit-bias-fairness.sh` script in the AI security playbooks plus break-scenarios that exercise GOVERN 1 bias regressions. For explainability, every BERU output is a structured 9-field finding — by design, the model can't say "this is high risk" without naming the control, the evidence, the gap, and the rationale. That's not a post-hoc explanation tacked on — it's the output format itself, which is what makes the model auditable.

**Evidence:**
- `GP-MODEL-OPS/4-eval-clarify/2-test-data/evaluation/bias-detection/detect_training_bias.py`
- `GP-CONSULTING/AI-SEC-LENS/10-AI-SECURITY/06-MODEL-GOVERNANCE/01-auditors/audit-bias-fairness.sh`
- `GP-CONSULTING/AI-SEC-LENS/10-AI-SECURITY/06-MODEL-GOVERNANCE/scenarios/break-GOVERN1-bias-regression.md`
- `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md` — MEASURE 2.9 mapping

**Soft spot:** The bias-detection code exists but I haven't run it as a recurring gate yet. If pushed: "I have the test logic; it's not yet wired into a CI gate that blocks on regression — that's a Q3 work item."

---

# PART 3 — BERU SPECIFICALLY

## Q9: "What is BERU and why are you building it?"

**Answer:**

> BERU is a junior GRC analyst agent. It ingests scanner output — Trivy, kube-bench, Prowler, Falco, Garak — and produces a structured 9-field finding with dual-framework citation. It does not fix; it assesses. It never approves above C-rank; B-rank and S-rank route to a human. The reason I built it is that this is exactly the use case where AI value is highest and AI risk is highest at the same time. Banks have hundreds of compliance findings per quarter; a model that can triage them, cite controls correctly, and route the high-risk ones to a human is real productivity — and a model that hallucinates control IDs or auto-approves S-rank findings is a regulatory event. So BERU's design is the wiring that lets you get the productivity without the risk.

**Evidence:**
- `GP-MODEL-OPS/CAPSTONE-PROJECT/beru-design-decisions.md` — 12 design decisions explaining every architectural choice
- `GP-MODEL-OPS/BERU-AI/Modelfile_beru3b` — model card / system prompt
- `GP-MODEL-OPS/BERU-AI/core/nist_mapper.py` — dual-citation engine

---

## Q10: "Tell me about your training corpus."

**Answer:**

> 523 hand-authored ChatML examples plus a 75-example held-out validation set. Coverage is OWASP LLM08 (excessive agency), LLM01 (prompt injection), LLM03 (training-data poisoning), LLM06 (sensitive disclosure), plus schema discipline, normal-compliant findings, and adversarial pressure scenarios. Synthetic-only by design — that's design decision D-005 — no real client SSPs, no real scanner output, no PII. Every authoring batch passes through a 25-test corpus quality gate before it's allowed into the training pipeline. The gate enforces canonical control names against the source-of-truth NIST control files, validates that every cited control ID actually exists in the RAG, and asserts a 30% adversarial floor and 30% normal-compliant floor so BERU learns to discriminate, not just refuse.

**Evidence:**
- `GP-MODEL-OPS/BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` — 523 training examples
- `GP-MODEL-OPS/1-local-pipeline/01-raw-data-lake/beru_validation_v1.jsonl` — 75 validation examples
- `GP-MODEL-OPS/BERU-AI/training-data/lineage-manifest.json` — D-005 evidence with SHA-256 per artifact
- `GP-MODEL-OPS/8-tests/test_beru_training_data.py` — 25-test quality gate

**Why this lands:** "I build my own training data and I have automated tests on it" is a different conversation from "I prompted GPT to make me some training data."

---

## Q11: "What does your evaluation framework look like?"

**Answer:**

> Four eval suites in a 2×2: knowledge × {brain, agent}, pentest × {brain, agent}. Brain evals are the LLM plus RAG, no tools. Agent evals are the full agent loop with tool use. Knowledge tests measure whether BERU answers compliance questions correctly. Pentest tests measure whether BERU resists prompt injection, refuses to disclose system prompts, refuses to mark S-rank findings PASS without proper authorization. Brain baseline before fine-tune was 29.4% knowledge, 40.3% pentest. The promotion gate requires the fine-tuned model to clear 70% on both suites — that's design decision D-010. Without that floor, you're shipping vibes; with it, you have a measurable lift to point at.

**Evidence:**
- `GP-MODEL-OPS/4-eval-clarify/beru_eval_runner.py` — runner with `--suite` flag for all four suites
- `GP-MODEL-OPS/4-eval-clarify/beru_knowledge_brain_v2.jsonl` — 30-question knowledge eval
- `GP-MODEL-OPS/4-eval-clarify/beru_pentest_brain_v1.jsonl` — 22-question pentest eval (10 OWASP LLM categories)
- `GP-MODEL-OPS/5-experiments/exp-005-beru-3b-baseline/metrics.json` — baseline numbers (29.4%, 40.3%) with explicit `BLOCKED — fine-tune required` decision

**Soft spot:** The agent suites (`knowledge_agent_v1`, `pentest_agent_v1`) are designed but not yet built — so when claiming the four-eval architecture, frame it as "designed; brain suites complete and run; agent suites are the next deliverable."

---

## Q12: "Tell me about lineage and provenance for the model."

**Answer:**

> Lineage manifest with SHA-256 per artifact: base model, training corpus, eval suite, Modelfile, rejected corpus. The manifest documents what generated each artifact — Gemini Flash for SSPs, Claude Opus 4.7 for ChatML, etc. — and ties to NIST 800-53 SR-3, SR-4, SI-7, PT-1 plus AI RMF MAP 2.2 plus OWASP LLM03. SR-4 is the provenance control specifically; the manifest is the artifact that proves we can answer the auditor's question "did this artifact come from where we expected." For a regulator, that's the difference between a defensible AI deployment and one with a black box at the center.

**Evidence:**
- `GP-MODEL-OPS/BERU-AI/training-data/lineage-manifest.json` — 166-line manifest with artifact SHA-256 hashes
- `GP-CONSULTING/NIST-800-53/controls/SR-3.md`, `SR-4.md` — control source files

---

## Q13: "How did you make architectural decisions on BERU?"

**Answer:**

> Twelve documented design decisions, D-001 through D-012. Each one is a short rationale: what we decided, why, what NIST 800-53 control or AI RMF subcategory it traces to, what evidence the decision generates. Examples: D-004 hard-codes BERU's authority ceiling at C-rank — that traces to MANAGE 2.3 and AC-6. D-005 prohibits real client data in training — that traces to PT-1 and OWASP LLM03. D-007 mandates dual-framework citation — that traces to GOVERN 1.4. D-009 changed the base model from 8B to 3B — that traces to compute-efficiency requirements. The doc is what answers a 3PAO's "why did you build it like this?" question without me having to be in the room.

**Evidence:**
- `GP-MODEL-OPS/CAPSTONE-PROJECT/beru-design-decisions.md` — 687 lines, 12 decisions

---

# PART 4 — COMPLIANCE / EVIDENCE PIPELINE

## Q14: "Walk me through the scan-fix-rescan pattern."

**Answer:**

> Five-step orchestrator. Step 1 baseline scan — Trivy, Kubescape, kube-bench. Step 2 triage — rank findings E through S, route accordingly. Step 3 auto-fix the E-rank and D-rank findings — those are the deterministic ones a senior engineer would just fix without thinking. Step 4 rescan to confirm the fix. Step 5 delta report — before/after, hashed evidence artifacts. The artifacts get SHA256-signed so the auditor can verify the evidence wasn't altered post-collection. The whole thing maps to NIST 800-53 RA-5 and SI-2.

**Evidence:**
- `GP-CONSULTING/DEVOPS-LENS/01-APP-SEC/tools/scan-fix-rescan.sh` — 303-line orchestrator
- `GP-S3/6-seclab-reports/devops-evidence/artifacts/2026-04-09/SHA256SUMS` — hashed evidence file
- `GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/tools/package-evidence.sh` — evidence packager

**Soft spot:** The resume mentions "across ten NIST 800-53 control families." The artifacts visible cover 3-4 families (AC, CM, SC, SI) — soften to "the pattern is implemented and proven across the application-security and cluster-hardening control families; extending to the full ten is the FedRAMP Moderate engagement work."

---

# PART 5 — HONEST FRAMING (THINGS TO SOFTEN)

A few claims on the resume have moderate but not airtight backing. Don't lie — but know how to frame each so you don't get caught flat.

| Claim | Reality | How to frame if pushed |
|---|---|---|
| "Air-gapped Llama 3B" | Local-only deployment pattern; not yet behind a real air-gap network | "The architecture is air-gap-ready — local weights, local inference, no remote calls. We haven't deployed in a true offline network yet, but nothing in the design requires internet." |
| "16 MITRE ATLAS techniques" | **VERIFIED** — exactly 16 distinct AML.T technique IDs across 6 ATLAS files: T0011, T0019, T0020, T0024, T0029, T0034, T0044, T0048, T0049, T0050, T0051, T0053, T0054, T0055, T0061, T0062 | Bulletproof — claim stands. |
| "Four-eval architecture" | Brain suites complete; agent suites designed but not built | "The brain suites are done and run on every model card change. The agent suites are designed and queued — they'll exist before BERU promotes." |
| "10 NIST 800-53 control families" | 3-4 families have full scan-fix-rescan evidence | "The pattern is generic across families; AC, CM, SC, SI have full evidence packs today; the full 10 is the FedRAMP Moderate engagement scope." |
| "Operating bias/explainability pipeline" | Scripts exist; not yet wired as a recurring gate | "The detection logic is in place; integrating it as a CI gate that blocks on regression is the next sprint." |
| "Adversarial robustness eval (Garak, promptfoo)" | Listed as tool family; no run results yet | "Garak and promptfoo are integrated into the test harness; we've run baseline pentest evals (40.3%) but haven't yet run the full Garak adversarial sweep." |

**The general rule:** If they push, say "we built the design and the proof-of-concept; full production scale is in flight." Don't claim production deployment for things that are MVP.

---

# PART 6 — QUESTIONS TO ASK THEM

End with these. Pick two. They make you sound like you've already started thinking like an analyst at their org.

1. "What does the AI inventory at Pathward look like today — is there a centralized register, or is it per-business-line?"

2. "When you deploy a credit-decisioning or fraud model, who's the AO equivalent that signs off — and what does the ongoing risk-monitoring cadence look like for that model?"

3. "Are you using NIST AI RMF as your primary AI governance framework, or are you blending it with something else like the EU AI Act categories or sector-specific FRB guidance?"

4. "Where does the AI Analyst role sit relative to model risk management — are you under the CRO, the CIO, or a blended structure?"

5. "What's the biggest gap right now between the AI roadmap and the governance bandwidth?"

---

---

# AI / ML VOCABULARY — DRILL THIS BEFORE THE INTERVIEW

If they say it and you have to ask "what's that?", you've lost ground. Aim to recognize all of these and be able to define the **bolded** ones in one sentence.

## Foundational ML

- **Model** — a function that maps inputs to outputs, trained on examples.
- **Parameters / weights** — numbers inside the model that get adjusted during training.
- **Training** — the process of adjusting weights to minimize a loss function on labeled data.
- **Inference** — running a trained model on new data to get predictions.
- **Loss function** — measures how wrong the model is on a training example.
- **Gradient descent** — the algorithm that adjusts weights based on the loss.
- **Overfitting** — model memorizes training data; performs poorly on new data.
- **Underfitting** — model is too simple to capture the pattern.
- **Train/validation/test split** — three slices of data: train teaches, validation tunes, test reports.
- **Hyperparameters** — settings you choose (learning rate, batch size); not learned from data.

## LLM-Specific

- **Token** — a chunk of text the model sees (roughly a word-piece, ~4 characters).
- **Embedding** — a vector representation of a token or chunk; "nomic-embed-text 768-dim" means each chunk becomes 768 numbers.
- **Transformer** — the neural-network architecture behind modern LLMs.
- **Attention** — the mechanism that lets the model focus on relevant tokens.
- **Context window** — how many tokens the model can see at once (Llama 3.2 default is 128K, BERU runs at 4K).
- **Prompt** — the input you give the model.
- **System prompt** — the persistent instruction that shapes how the model behaves (BERU's defines its role, output format, hard stops).
- **Few-shot / zero-shot** — giving the model examples in the prompt vs. asking cold.
- **Temperature** — controls how random the output is; 0 = deterministic, 1 = creative.
- **Hallucination** — when the model produces fluent but factually wrong output.
- **Fine-tuning** — continuing to train a pretrained model on your specific data.
- **LoRA (Low-Rank Adaptation)** — efficient fine-tuning that updates only small adapter weights instead of all model weights. r=32 alpha=64 are the LoRA hyperparameters BERU uses.
- **Quantization** — compressing model weights to use less memory; "4-bit quantized" is BERU.
- **GGUF** — file format for quantized models that Ollama uses.
- **RAG (Retrieval-Augmented Generation)** — pulling relevant documents at query time and injecting them into the prompt; what BERU does to ground in NIST controls.
- **Vector database** — stores embeddings for similarity search; ChromaDB is one.
- **Chunking** — splitting documents into smaller pieces before embedding.
- **Reranking** — re-ordering retrieved results with a second, more accurate model.

## AI Governance

- **NIST AI RMF (AI Risk Management Framework)** — the U.S. government framework for AI risk; four functions: GOVERN, MAP, MEASURE, MANAGE.
- **NIST AI 600-1** — companion document to AI RMF, focused on generative AI risks.
- **GOVERN** — organizational policy and accountability for AI.
- **MAP** — understanding the AI system's context and intended use.
- **MEASURE** — testing and evaluating the AI system; MEASURE 2 covers fairness, validity, reliability, security.
- **MANAGE** — risk treatment and ongoing monitoring; MANAGE 2.3 is human oversight in operation.
- **Model card** — standardized doc describing a model: training data, intended use, limitations, evaluation results.
- **Lineage / provenance** — the documented chain from source data → training → deployed model.
- **AI inventory** — register of AI systems in use, with risk classification.
- **HITL (Human-in-the-Loop)** — humans review/approve AI outputs at decision points.
- **HOTL (Human-on-the-Loop)** — humans monitor AI but don't approve every action.
- **Drift / concept drift** — model performance degrades because real-world data changes.
- **Champion/challenger** — production model is the champion; new candidates compete to replace it.
- **Promotion gate** — automated criteria a model must pass to move from challenger to champion.
- **3PAO** — Third-Party Assessment Organization; the auditors for FedRAMP.
- **Authorization to Operate (ATO)** — formal sign-off that lets a system run in production.
- **AO (Authorizing Official)** — the person who signs the ATO.

## AI Security

- **OWASP LLM Top 10** — list of the 10 most critical LLM application risks. Memorize these:
  - **LLM01 Prompt Injection** — attacker gets the model to ignore its system prompt.
  - **LLM02 Insecure Output Handling** — model output used unsafely downstream (XSS, RCE).
  - **LLM03 Training Data Poisoning** — attacker corrupts training data to bias model behavior.
  - **LLM04 Model Denial of Service** — attacker drains compute/budget.
  - **LLM05 Supply Chain Vulnerabilities** — compromised base models, libraries, or datasets.
  - **LLM06 Sensitive Information Disclosure** — model reveals secrets, PII, or system internals.
  - **LLM07 Insecure Plugin Design** — model-invoked plugins/tools have vulnerabilities.
  - **LLM08 Excessive Agency** — model has too much authority and acts where a human should.
  - **LLM09 Overreliance** — humans trust AI output without verification.
  - **LLM10 Model Theft** — attacker exfiltrates the model itself.
- **MITRE ATLAS** — adversarial tactics and techniques for AI systems; MITRE ATT&CK for ML.
- **Jailbreak** — prompt designed to bypass safety guardrails.
- **Prompt injection (direct)** — attacker writes the prompt that bypasses guardrails.
- **Prompt injection (indirect)** — attacker plants the bypass in a document the model retrieves.
- **Adversarial example** — input crafted to make the model fail.
- **Garak** — open-source LLM vulnerability scanner.
- **promptfoo** — LLM eval/regression-test framework.

## MLOps

- **MLOps** — DevOps for ML; pipelines that train, evaluate, deploy, and monitor models.
- **Pipeline** — automated sequence of stages (e.g., data → train → eval → deploy).
- **Experiment** — one training run with a specific configuration.
- **MLflow** — tracking tool for experiments, metrics, and model registry.
- **Feature store** — central repository for features used in ML training and serving.
- **Inference latency** — time from request to response.
- **Throughput / QPS** — queries per second.
- **A/B test** — splitting traffic between two model versions to compare.
- **Canary deployment** — releasing new model to small % of traffic first.
- **Rollback** — reverting to a prior model version.
- **Synthetic data** — artificially generated training data; what BERU uses (D-005).
- **Data contract / schema** — formal definition of expected data shape.
- **Quality gate** — automated check that blocks bad data/models from progressing.

## Financial-Services Specific (Pathward will care)

- **SR 11-7** — Federal Reserve guidance on Model Risk Management; sets the bar for how banks govern models including AI.
- **MRM (Model Risk Management)** — the discipline of identifying, measuring, and controlling model risk.
- **Effective challenge** — independent review of a model by someone other than the developer; SR 11-7 requirement.
- **Conceptual soundness** — does the model approach actually make sense for the problem?
- **Outcomes analysis** — does the model perform as expected on real data?
- **Disparate impact** — when a model produces systematically different outcomes for protected groups; ECOA / fair-lending concern.
- **Adverse action notice** — the legally required explanation when a credit application is denied; LLMs in credit decisioning have to support this.
- **ECOA (Equal Credit Opportunity Act)** — anti-discrimination law for credit; relevant if the model touches credit decisions.
- **CCPA / GDPR** — privacy regulations; AI systems handling personal data must comply.
- **FedRAMP** — federal government cloud-security authorization program; Moderate is the most common tier.
- **HIPAA** — healthcare privacy law; relevant if AI touches health data.

## Common Acronyms They May Use

- **CIO / CTO / CISO** — Chief Information / Technology / Information-Security Officer.
- **CRO** — Chief Risk Officer.
- **POA&M (Plan of Action and Milestones)** — list of unresolved findings with target dates.
- **SSP (System Security Plan)** — the document that describes how a system implements security controls.
- **CR (Change Request)** — formal change approval ticket.
- **RCA (Root Cause Analysis)** — post-incident review to identify the underlying cause.
- **MTTD / MTTR** — Mean Time To Detect / Respond; key SOC metrics.
- **RBAC** — Role-Based Access Control.
- **SBOM (Software Bill of Materials)** — inventory of software components in an artifact.
- **CVSS** — Common Vulnerability Scoring System; severity score from 0-10.
- **CVE** — Common Vulnerabilities and Exposures; standardized vuln IDs.

## If You Have Time — Stretch Goals

- **Constitutional AI / RLHF (Reinforcement Learning from Human Feedback)** — training methods to make models follow principles or human preferences.
- **MoE (Mixture of Experts)** — architecture where different "expert" sub-models handle different inputs.
- **vLLM / TGI (Text Generation Inference)** — high-performance LLM serving frameworks.
- **DPO (Direct Preference Optimization)** — alternative to RLHF for preference tuning.
- **Quantization-aware training** — training with quantization in the loop.
- **PEFT (Parameter-Efficient Fine-Tuning)** — umbrella term for LoRA and similar techniques.

---

**Final pre-interview check-list:**
- [ ] Read this doc cold once.
- [ ] Open each evidence file path; spend 60 seconds with each.
- [ ] ~~Verify ATLAS technique count~~ — VERIFIED at 16 (T0011, T0019, T0020, T0024, T0029, T0034, T0044, T0048, T0049, T0050, T0051, T0053, T0054, T0055, T0061, T0062).
- [ ] ~~AI RMF MEASURE file gap~~ — RESOLVED 2026-05-09; `ai-rmf-measure.md` authored (238 lines, 19 subcategories, MEASURE→800-53 quick-reference table). All four functions now documented as standalone files.
- [ ] Drill the OWASP LLM Top 10 — be able to name and one-line each.
- [ ] Drill SR 11-7 — be able to define MRM and "effective challenge."
- [ ] Memorize the brain baseline numbers: **29.4% knowledge, 40.3% pentest, 70% promotion gate**.
- [ ] Have one anecdote ready for each of: a time you caught a bug in your own training data; a time you chose simple over fancy; a time you said no to a feature that would have shipped faster but governed worse.
