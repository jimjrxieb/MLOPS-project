# GP-MODEL-OPS — Current State and Future Direction

This is an active learning and build artifact. It is not presented as a finished enterprise MLOps platform. It is a working end-to-end pipeline that I built to demonstrate how I think about the full model lifecycle — from raw data to production serving — while also studying for roles in MLOps, ML engineering, and AI security.

Fifteen training experiments completed. One model in production serving (BERU v1.6). One challenger in evaluation (BERU v1.7). Gates are real. Nothing ships without passing them.

---

## What Is Here Right Now

### Data Layer (`0-data-lab/`)

A synthetic data generation pipeline using a 3-agent CrewAI crew: Orchestrator → Quality Auditor → Report Generator. Takes JSA security findings and converts them to ChatML training examples. Output is validated against JSON Schema before any training run. A generation manifest tracks what was generated, when, and the SHA256 of each output file.

### Training Pipeline (`1-FineTuning-Pipeline/`)

Seven-step closed loop: ETL → chunk → LoRA fine-tune → merge → GGUF conversion → eval → feedback. LoRA with r=64/alpha=128, 4-bit quantized base (Unsloth), 2 epochs per chunk, cosine LR scheduler. Runs on a local RTX 5080. MLflow tracks every training run. The feedback loop reads eval results and routes weak categories back to data generation.

### RAG Pipeline (`2-RagIngestion-Pipeline/`)

Seven-stage prep factory (discover → preprocess → sanitize → format → label → validate → embed) plus a 4-agent CrewAI crew for quality review, semantic labeling, routing, and reporting. ChromaDB at 33k+ documents across 7 collections. Zero-vector policy: failed embeddings go to quarantine, never into the collection. Embedding model fixed at `nomic-embed-text` (768 dimensions) with explicit function passing to ChromaDB to prevent silent dimension mismatch.

### Model Registry (`3-model-registry/`)

Version-controlled artifact store with champion/challenger pattern. Every version that loads into Ollama is registered here first. Weights are gitignored; the tracked artifacts are `training_state.json` (corpus SHA, eval scores, promotion decision) and Modelfiles. Current champion: BERU v1.6 (KB 20.0% / PB 68.2%). Current challenger: BERU v1.7 (KB 34.1% / PB 63.0%).

### Eval Engine (`4-eval-clarify/`)

Three active eval suites:
- **knowledge_brain** — 30 questions across 6 GRC reasoning types (finding accuracy, POA&M drafting, tool output interpretation, evidence gap detection, dual citation, ATLAS-mapped AI risk). Positive scoring: validation keywords must appear.
- **pentest_brain** — 22 questions mapped to OWASP LLM Top 10, framed as evidence-in/finding-out to match BERU's production context. Negative scoring: fail indicators must be absent.
- **workflow_brain** — End-to-end scenarios: given scanner output, produce a complete 9-field structured finding.

Promotion gate: ≥70% overall on both suites, ≥60% per question type, zero hallucinated control IDs.

### Experiment Tracking (`5-experiments/`)

Every training run has a directory: `params.yaml` (what was configured), `metrics.json` (eval results), `notes.md` (what was tried, what happened, what was decided). Fifteen experiments. Decisions logged with dates. A `COMPARISON.md` tracks the full progression side by side.

### Model Cards (`6-model-cards/`)

Champion and challenger documentation. Tracks model version, base model, training corpus, eval scores, known limitations, and intended use. Connects each model to the experiment that produced it.

### Data Contracts (`7-data-schemas/`)

JSON Schema definitions for every structured format in the system: training examples, eval questions, eval results, scanner findings, classification results, generation manifests. Validated in CI and in the data quality test suite.

### Quality Gates (`8-tests/`)

89 pytest tests running in CI on every push to main. Data quality gates check ChatML format, scope keywords, content minimums, dedup, and schema compliance. Model behavior tests validate serving health and output structure. CI also runs gitleaks, pip-audit, and Trivy.

### MLOps Toolkit (`9-mlops-deploy/`)

Operational scripts and GitHub Actions for deploying and operating this pipeline at scale: Kubeflow and SageMaker tracks, KServe + vLLM serving, drift detection via Prometheus metrics, and a model CI/CD workflow that chains data validation → training submission → promotion → rollout.

### Production Runtime (`BERU-AI/`)

FastAPI service on port 8088 with LangGraph routing. Routes: `/audit` (full 9-field finding), `/assess` (SSP + evidence → PASS/PARTIAL/FAIL), `/grade-ssp` (narrative quality tier), `/ask` (freeform GRC question), `/ciso-brief` (executive summary), `/hitl/*` (human-in-the-loop escalation). MLflow inference tracking logs every call: model, latency, RAG usage, rank decision. Degrades gracefully if MLflow is not running.

### CrewAI Orchestration (`10-crewai-mlops/`)

Three production crews: `synthetic_pipeline` (data generation, port 8001), `rag_ingestion` (RAG prep, port 8002), `beru` (7 GRC sub-crews across NIST control families, port 8089). Pattern across all three: deterministic Python collects and prepares data; LLM agents do judgment. Token cost is kept low. Failures are diagnosable.

---

## What This Demonstrates

I understand the practical shape of an MLOps system beyond model calls and notebooks.

Specifically, this project shows that I can think about:

- **Data quality before training** — format validation, scope enforcement, dedup, content minimums, SHA256 tracking. The 85% garbage-removal lesson from exp-001 is documented and encoded in the pipeline.
- **Experiment reproducibility** — every run is a directory with params, metrics, and notes. You can reconstruct what was trained and why.
- **Promotion gates** — models do not move to production because they trained successfully. They move because they passed a defined eval threshold on a test suite that was designed to match the production task.
- **Eval design** — the pentest brain v2 rewrite (evidence-in/finding-out framing) came from recognizing that the original suite was testing the wrong threat model. BERU never receives direct user prompts in production. The eval was wrong. It was replaced.
- **Domain depth** — NIST 800-53 Rev 5 control families, NIST AI RMF / AI 600-1 subcategories, MITRE ATLAS technique IDs, OWASP LLM Top 10. The model is trained to operate inside these frameworks, not just mention them.
- **Security-aware AI** — gitleaks, Trivy, pip-audit in CI. OWASP LLM Top 10 in the eval suite. HITL routing for B/S-rank findings. The security posture is architectural, not bolted on.
- **Governance from day one** — every artifact traces back to a training run. Every finding cites a control. Every design decision has a documented reason.

---

## Known Gaps

This is a working prototype built by one person. It is not production-hardened at enterprise scale.

**Eval gates not met yet.** BERU v1.7 is at KB 34.1% / PB 63.0%. Neither clears 70/70. Fifteen experiments in and the trajectory is real — 70% relative KB gain from v1.6 to v1.7 — but the gate has not been passed. This is an honest statement about where the model is.

**No GPU CI runner.** Training runs locally on an RTX 5080. The GitHub Actions workflows exist and are wired correctly, but a self-hosted GPU runner is not connected. Tests run in CI; training does not.

**ChromaDB not production-hardened.** No corpus versioning, no backup/restore procedure, no rebuild documentation. A model's retrieval behavior cannot be reproduced from source because the vector DB state is not snapshotted.

**Retrieval evaluation is missing.** The knowledge brain eval tests BERU's reasoning. There is no golden-question test set that validates retrieval quality — whether the right chunks are actually being returned.

**Single-node training only.** LoRA on one GPU. No distributed training, no gradient checkpointing tuning, no multi-GPU setup.

**Model cards are incomplete.** The governance structure exists. Filling in intended use, failure modes, and bias analysis for each version is still in progress.

---

## Real-World Direction

As I continue building, these are the improvements that matter most for enterprise readiness:

**1. Clear the 70/70 promotion gate**

exp-016 targets `dual_citation` (0% → 60% target) and `atlas_mapped_ai_risk` (24% → 50% target) with dedicated generators producing explicit 800-53 ↔ AI RMF pairing examples and MITRE ATLAS technique → control mapping scenarios. The corpus goes from 1,832 to 5,000+ examples. This is the next concrete milestone.

**2. Corpus versioning**

Every ingest run should produce a corpus snapshot: source hashes, document counts, embedding model version, collection names, timestamp. Model eval results should record which corpus version was active during that run. Right now an answer cannot be traced back to the exact corpus that produced it.

**3. Retrieval evaluation**

Build a golden-question test set with expected source documents. Track recall, citation accuracy, and bad-context rate over time. This closes the loop between the RAG corpus and BERU's eval scores.

**4. Connect GPU runner to CI**

Wire the self-hosted GPU runner to the GitHub Actions training workflow. Training triggered by data merges, not manual runs. Promotion decisions automated by the eval gate.

**5. MLflow model registry integration**

Move from file-based `training_state.json` to the MLflow model registry. Every eval run is an MLflow run with metrics. Model promotion creates a registered model version with lineage back to the training run and the corpus SHA.

**6. BERU serving on KServe**

Move BERU from Ollama on a local machine to a KServe InferenceService with vLLM backend, KEDA autoscaling on queue depth, and a canary rollout path for version transitions. The KServe configs exist in `9-mlops-deploy/` and are ready to apply.

**7. Pentest brain to 70%**

The PB v2 framing was correct but the score dropped from 68.2% (PB v1) to 63.0% (PB v2) because the new evidence-in framing is harder. Closing the gap requires more adversarial evidence examples where the embedded attack is more subtle.

**8. JADE and Katie**

BERU is the CAPSTONE focus. JADE and Katie are designed and scaffolded but not actively being trained right now. As BERU clears its gates and serving is stable, the same pipeline runs JADE (8B DevSecOps toolchain reasoning) and Katie (3B K8s operations) through the same promotion gate discipline.

---

## How This Adds Team Value Today

Most ML work that gets into production fails between the model and the pipeline, not in the model itself. Bad data, no eval discipline, no lineage, no governance, no monitoring. Those failures are expensive and invisible until something breaks in production.

I built this project specifically to understand the hard parts:

- I can contribute to **data quality pipelines** — format validation, curation, dedup, schema enforcement, generation tracking.
- I can contribute to **eval design** — designing questions that match the production task, not just generic benchmarks. Recognizing when the eval is wrong and rebuilding it.
- I can contribute to **experiment discipline** — structured tracking, reproducible configs, documented decisions. Not just "I ran it and it worked."
- I can contribute to **governance and auditability** — tracing an output back to a control, a training run, a corpus version, a design decision.
- I can contribute to **security-aware AI systems** — OWASP LLM Top 10, HITL routing, prompt injection eval, CI security scanning.
- I can contribute to **domain-specific AI** — not just general assistants, but models built for a defined professional task with measurable eval criteria.

I am still learning. The gates are not all cleared. The production hardening is not complete. But the foundation is real, the direction is practical, and every gap is documented honestly rather than hidden.

The next step is to clear the BERU 70/70 gate, get serving stable on KServe, and bring the same discipline to JADE and Katie. After that, this becomes a three-model production system with full lifecycle management — data, training, eval, serving, monitoring, and governance — running on infrastructure an engineer at any serious shop would recognize.
