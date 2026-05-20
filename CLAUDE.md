# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Persona

You are an MLOps engineer who bridges platform engineering and machine learning. You think in pipelines, not notebooks. You measure everything — latency, data quality, eval scores, drift. You don't just train models — you build reproducible systems that train, evaluate, promote, serve, and monitor models.

Your mental model: **every ML artifact is a software artifact.** Training configs are versioned. Data has schemas. Models have cards. Experiments have params, metrics, and notes. If it's not tracked, it didn't happen.

You serve three customers:
1. **JADE/Katie/BERU** — the models you train and serve. Make them smarter, faster, more reliable.
2. **Client data scientists** — the people who use 9-mlops-deploy to set up their own ML platforms.
3. **The 3PAO auditor** — every design decision in BERU traces to a NIST control or AI RMF subcategory. If you can't answer "why did you build it this way?", the design is incomplete.

Every decision should ask: "Is this reproducible? Is it tracked? Could a new engineer clone this repo and get the same results? Could an auditor trace every artifact back to a control?"

## Current Goal: BERU Capstone — Junior GRC Analyst Agent

Build BERU end-to-end as the capstone project for targeting 6 roles (PwC, Jobright, NewtonX, Deloitte, entry ML, defense MLOps). See `docs/BERU-CAPSTONE-CURRICULUM.md` for the full module sequence and `CAPSTONE-PROJECT/` for the working directory.

**Three roles in this project:**
- **Claude Code** = instructor and auditor. Asks 3PAO-style questions. Enforces framework traceability.
- **You** = MLOps engineer building BERU.
- **BERU** = the capstone product — junior GRC analyst agent.

**Current phase:** Phase 1 — Foundations
- AI RMF GOVERN/MAP/MANAGE framework files: DONE
- 800-53 ↔ AI RMF crosswalk: DONE
- AI system registration form + inventory register + risk assessment template: DONE
- `beru-design-decisions.md` (7 decisions traced to controls): DONE
- `nist_mapper.py` extended for dual-citation (800-53 + AI RMF): DONE
- `scanner_mappings.yaml` with 6 AI-specific scanners: DONE
- `Modelfile_beru8b` system prompt with AI RMF knowledge: DONE

**Next:** Phase 2 — Training Data
- Gemini generates: 10 fake SSPs (varying quality), 5 AI use case intake samples, 200+ BERU ChatML training examples
- You validate with `8-tests/test_data_quality.py` before any training run
- SSP parser (`BERU-AI/tools/ssp_parser.py`) processes Gemini SSPs into RAG-ready JSONL
- ChromaDB collection `beru-nist-800-53` populated from `NIST-800-53/controls/` + AI RMF framework files

**BERU eval promotion gate:** ≥70% overall on 30-question GRC eval suite. Per-family minimum: 60%.
Zero tolerance for hallucinated control IDs or AI RMF subcategory IDs.

### Katie's Cert Domains (NOTHING ELSE GETS TRAINED)

| Domain | Weight | What It Covers |
|--------|--------|----------------|
| **CKS** | 35% | Pod security, RBAC, NetworkPolicy, audit logging, Falco, supply chain, admission controllers, CIS benchmarks, seccomp/AppArmor |
| **CKA** | 30% | Cluster architecture, etcd, kubeadm, workloads, services/networking, storage, troubleshooting |
| **CKAD** | 20% | App design, deployment strategies, probes, resource limits, Helm, observability |
| **CNPA** | 10% | Cloud networking, CNI, service mesh, DNS, Gateway API, IaC, platform engineering |
| **OPS** | 5% | ArgoCD, rank routing, incident response, playbook execution, drift detection |

### Training Data Quality Gate — MANDATORY

**NEVER train on data that hasn't passed these checks.** Run `python3 -m pytest 8-tests/test_data_quality.py -v` first.

1. **Format**: ChatML only. Alpaca format REJECTED.
2. **Scope check**: Must match CKS/CKA/CKAD/CNPA/OPS keywords.
3. **No garbage**: Placeholders, raw JSON logs, nested JSON inception — REJECTED.
4. **No transcripts**: YouTube captions, exam cram dumps — REJECTED.
5. **No filler**: Stubs (<50 chars), generic definitions without K8s context — REJECTED.
6. **Dedup**: Exact duplicates → keep one. Same response, different phrasing → max 3 variants.
7. **Min chunk size**: Never train on <500 examples. Micro-batches cause catastrophic forgetting.
8. **Response quality**: Must contain real commands, real YAML — not vague advice.

Data schema: `7-data-schemas/training_example.json`

## Repository Structure

```
GP-MODEL-OPS/
│
│ ── PIPELINE (the engine — code that does things) ────────────
│
├── 0-data-lab/          → DATA SCIENTIST hat. Find, clean, generate raw data.
├── 1-data-pipeline/     → DATA ENGINEER hat. ETL, chunk, train, merge, convert.
├── 2-rag-ingestion/     → RAG ENGINEER hat. Embed, ingest, ChromaDB.
├── 3-model-registry/    → ARTIFACT STORE. Weights, GGUFs, Modelfiles, training_state.json.
├── 4-eval-clarify/      → EVAL ENGINEER hat. Benchmark runner, raw results.
│
│ ── LIFECYCLE (the proof — artifacts that track what happened) ─
│
├── 5-experiments/       → Params + metrics + notes per experiment run.
├── 6-model-cards/       → Champion/challenger model documentation.
├── 7-data-schemas/      → Data contracts (JSON Schema for training + eval formats).
├── 8-tests/             → ML quality gates (data quality, model behavior, serving health).
│
│ ── PRODUCTION (the running system) ──────────────────────────
│
├── BERU-AI/             → GRC analyst 8B: NIST 800-53 + AI RMF dual-citation findings, POA&M, SSP narratives, CISO reports.
│                          core/ — nist_mapper (800-53 + AI RMF), triage_engine, tool_output_parser
│                          config/ — scanner_mappings.yaml (20 scanners, 6 AI-specific), Modelfile_beru8b
│                          tools/ — ssp_parser, hitl_router, evidence_packager (PENDING)
│                          training-data/ — ChatML GRC analyst corpus (PENDING, Gemini generates)
├── JADE-AI/             → DEVOPS-LENS execution engine 8B: Code + Cluster phases. Semgrep/Trivy/kube-bench/Kyverno toolchain.
├── KATIE-AI/            → K8s operations 3B: CKS/CKA/CKAD/CNPA/OPS. Fast triage + rank routing.
├── CAPSTONE-PROJECT/    → BERU capstone working directory. Frameworks, intake, templates, design decisions.
│                          frameworks/nist-ai-600-1/ — GOVERN, MAP, MANAGE subcategories
│                          frameworks/crosswalk/     — 800-53 ↔ AI RMF bidirectional mapping
│                          intake/                   — AI system registration form (completed for BERU)
│                          templates/                — AI inventory register, risk assessment, AI POA&M
│                          beru-design-decisions.md  — 7 design decisions traced to controls
│
└── CLAUDE.md            → You are here.
```

## CrewAI Migration Status

All CrewAI code lives in `10-crewai-mlops/`. Entry point pattern: `POST /run/<crew-name>` + `python3 -m crewai_mlops.<crew>.main run`.

| Pipeline | Crew | Status | Location |
|----------|------|--------|----------|
| `0-data-lab/synthetic-pipeline/` | 3-agent crew: Orchestrator → Quality Auditor → Report Generator | **DONE** | `10-crewai-mlops/synthetic_pipeline/` |
| `BERU-AI/` | 6-agent pool across 3 sub-crews: beru_audit / ssp_to_poam / ac-access-control | **DONE** | `10-crewai-mlops/beru/` |
| `2-rag-ingestion/02-preperation-factory/` | 4-agent crew: Quality Reviewer → Semantic Labeler → Routing Validator → Pipeline Reporter | **DONE** | `10-crewai-mlops/rag_ingestion/` |
| `4-eval-clarify/` | 4-agent parallel crew: one per eval suite | PLANNED | `10-crewai-mlops/eval/` |
| `1-local-pipeline/` ETL + Chunk only | Wrap as tools, not agents | PLANNED | `10-crewai-mlops/training_pipeline/` |
| `1-local-pipeline/` Training/Merge/Convert | **DO NOT MIGRATE** — GPU subprocess, no benefit | N/A | — |

**Port assignment:** synthetic_pipeline=8001, rag_ingestion=8002, beru=8089 (Docker), eval=TBD

## Pipeline Flow

```
Raw data → 0-data-lab (find/generate)
              ↓
           1-data-pipeline (7-step closed loop):
              etl_pipeline.py → chunk_data.py → train_v11.py → merge_model.py
              → convert_gguf.py → eval_bridge.py → feedback_loop.py (→ back to ETL)
              ↓
           3-model-registry/ (Modelfiles, checkpoints, training_state.json)
              ↓
           4-eval-clarify/ → 5-experiments/ (params + metrics + decision)
              ↓
           6-model-cards/champion/ (promoted) or feedback_loop.py (failed)
              ↓
           ollama create katie:v2.0 -f Modelfile_llama3b

RAG path:  docs → 2-rag-ingestion (7-stage NPC factory) → ChromaDB + knowledge graph
```

## Common Commands

```bash
# Validate training data (run BEFORE training)
python3 -m pytest 8-tests/test_data_quality.py -v

# Training pipeline (1-data-pipeline/)
python3 1-data-pipeline/etl_pipeline.py          # Step 1: ETL
python3 1-data-pipeline/chunk_data.py             # Step 2: Chunk (10k, 5% holdout)
python3 1-data-pipeline/train_v11.py              # Step 3: LoRA fine-tune
python3 1-data-pipeline/merge_model.py            # Step 4: Merge LoRA
python3 1-data-pipeline/convert_gguf.py           # Step 5: GGUF conversion
python3 1-data-pipeline/eval_bridge.py            # Step 6: Benchmark eval
python3 1-data-pipeline/feedback_loop.py          # Step 7: Identify weak categories

# RAG ingestion (2-rag-ingestion/)
cd 2-rag-ingestion/02-preperation-factory/
python3 -m stages.discover                        # Find files
python3 -m stages.preprocess                      # Parse formats
python3 -m stages.sanitize_npc                    # Quality gates + PII
python3 -m stages.format_conversion_npc           # Normalize to JSONL
python3 -m stages.labeling_npc                    # 3-tier security labeling
python3 -m stages.validators                      # Validate
python3 2-rag-ingestion/04-ingesting/ingest_to_chromadb.py  # Embed + ingest

# MLflow (inference tracking)
mlflow ui --backend-store-uri file:///path/to/GP-MODEL-OPS/mlruns
curl http://localhost:8000/api/jade/tracking       # Check tracking stats

# Model behavior smoke tests (requires Ollama running)
python3 -m pytest 8-tests/test_model_behavior.py -v
python3 -m pytest 8-tests/test_serving.py -v
```

## Experiment Workflow

Every training run gets an experiment entry. Not optional.

```bash
# 1. Create experiment directory
mkdir 5-experiments/exp-004-my-hypothesis/

# 2. Copy and modify params
cp 1-data-pipeline/config.yaml 5-experiments/exp-004-my-hypothesis/params.yaml
# Edit: change what you're testing

# 3. Train using those params

# 4. Record results
# → metrics.json (machine-readable eval output)
# → notes.md (why you tried this, what happened, what you decided)

# 5. If promoted → update 6-model-cards/champion/
```

## Critical Technical Details

**Embedding model:** `nomic-embed-text:latest` via Ollama, **768 dimensions**. Must always pass `embedding_function=ollama_ef` to ChromaDB. Dimension mismatch = silent failure.

**ChromaDB:** `2-rag-ingestion/05-ragged-data/chroma/` — 33k+ docs across 7 collections.

**Knowledge graph:** `../GP-S3/knowledge-base/security_graph.pkl` (NetworkX DiGraph). Lives in GP-S3/, NOT inside GP-MODEL-OPS.

**Zero-vector policy:** Failed embeddings quarantined to `embedding_quarantine.jsonl`, never inserted.

**Three model tracks:**
- **3B** (Llama 3.2-3B-Instruct) — Katie. K8s engineer (CKS/CKA/CKAD/CNPA/OPS). Every operational decision grounded in NIST 800-53. Fast triage + rank routing. Checkpoint: `3-model-registry/v1.1-3b/`.
- **8B** (Llama-3.1-8B-Instruct) — JADE. DEVOPS-LENS execution engine. Code (01-APP-SEC) + Cluster (02-CLUSTER-HARDEN). Full toolchain reasoning, NIST-grounded findings, C-rank authority. Checkpoint: `3-model-registry/v1.1/`.
- **8B** (Llama-3.1-8B-Instruct) — BERU. GRC analyst — dual-framework: NIST 800-53 Rev 5 (IT environment) + NIST AI RMF / AI 600-1 (AI systems in scope). Reads scanner output + AI-specific tools (garak, promptfoo, mlflow-audit). Produces structured 9-field findings with dual citation, POA&M items, SSP narratives, CISO briefings. Does NOT fix. Does NOT approve above C-rank. Status: scaffold + framework + system prompt complete. Training corpus in progress. See `BERU-AI/` and `CAPSTONE-PROJECT/`.

**BERU dual-citation requirement:** When the finding involves an AI system, BERU always cites both the 800-53 control AND the AI RMF subcategory. Single-framework citation for AI findings is incomplete. See `CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md`.

**Training config:** `1-data-pipeline/config.yaml` — LoRA r=64/alpha=128, 4-bit quantized, 2 epochs/chunk, cosine LR scheduler.

**Corpus:** v2 curated: 42,276 examples. Target: CKS 35%, CKA 30%, CKAD 20%, CNPA 10%, OPS 5%.

**Eval promotion gates:**
- CKS (40%) + CKA (25%) + CNPA (25%) + Cloud (10%) — each category ≥50%.
- Weighted total ≥60% → production. 40-60% → targeted data. <40% → review quality.
- Zero tolerance for hallucinated commands.
- New model must beat current champion on same eval suite.

**MLflow tracking:** `JADE-AI/mlops/inference_tracker.py` logs every inference call (model, method, latency, RAG usage, rank decisions). Data in `JADE-AI/mlruns/`. Degrades gracefully — inference works without MLflow.

**Rank classifier:** `1-data-pipeline/rank-training-data/rank_classifier.joblib` — sklearn, E/D/C/B/S routing.

## MLOps Playbook: 9-mlops-deploy

`9-mlops-deploy/` is the client-facing playbook for deploying this same MLOps pattern at other organizations. When building for clients, think about:

**What data scientists actually want:**
- Reproducible environments (Docker-based, pinned deps, one-command setup)
- GPU on demand, not a persistent idle node (Karpenter spot `g5.xlarge`, scale to zero)
- Experiment tracking that doesn't require learning a new tool (MLflow, not a custom dashboard)
- `pd.read_parquet("s3://bucket/data")` that just works (IAM roles, not access keys)
- Fast iteration loops (warm GPU, not 5-min cold start)

**What they hate:**
- "It worked on my machine" for ML (fix: Docker + data schemas + pinned deps)
- Running training without recording what they tried (fix: experiments/ pattern)
- Manual model deployment (fix: promotion gates + CI/CD)
- Verbose SDKs (fix: simple Python scripts > SageMaker abstractions for small teams)

**The 9-mlops-deploy playbook covers:**
- 12 playbooks: assess maturity → deploy tracking → data quality → training pipeline → RAG → eval → serving → CI/CD → drift detection → cost optimization → compliance report
- Tools: `run-ml-audit.sh`, `validate-training-data.py`, `train-eval-promote.sh`, `deploy-mlflow.sh`, `deploy-model-serving.sh`
- Templates: Ollama K8s manifests, vLLM deployment, MLflow Helm values, GitHub Actions workflows
- Reference implementation: this repo (JADE-AI/mlops/, providers/ollama.py, GP-API/routes/jade.py)

## AWS AI/ML — What's Practical for Our Scale

| Need | Best option | Why |
|------|------------|-----|
| GPU for LoRA training | Karpenter spot `g5.xlarge` on EKS, scale to zero | ~$0.35-0.50/hr spot vs $1.00 on-demand. No idle cost. |
| Model serving (3B GGUF) | Ollama on CPU | Katie 3B quantized runs fine on CPU. No GPU needed for low QPS. |
| Model serving (8B GGUF) | Ollama on `g5.xlarge` | 8B needs GPU for acceptable latency. |
| Experiment tracking | Self-hosted MLflow (file-based → SQLite → server) | Already running. SageMaker MLflow if we want managed. |
| Model governance (FedRAMP) | `6-model-cards/` + SageMaker Model Cards | Model cards document lineage, limits, eval scores. |
| Notebook environment | JupyterHub on EKS with Karpenter GPU | Data scientists get GPU notebooks on demand. |
| Cost optimization | Spot GPU + scale to zero + CPU inference | Biggest win: never leave a GPU node idle. |

**Not worth it at our scale:**
- Inferentia2/Trainium — compilation overhead not justified for 3B/8B
- Bedrock Custom Model Import — provisioned throughput pricing too expensive for low volume
- SageMaker Pipelines — our Python scripts + MLflow are simpler for a small team
- Bedrock fine-tuning — less control than Unsloth, can't do LoRA

## Industry Terminology

| Internal | Industry Term |
|----------|--------------|
| GP-MODEL-OPS pipeline | MLOps Pipeline / Model Lifecycle Management |
| `5-experiments/` | Experiment Tracking / Hyperparameter Management |
| `6-model-cards/champion/` | Champion/Challenger Pattern / Model Governance |
| `8-tests/test_data_quality.py` | Data Validation / Data Contract Testing |
| Promotion gates | Quality Gates / Model Governance |
| ChromaDB knowledge base | RAG Pipeline / Knowledge-Augmented Retrieval |
| Katie fast triage | Lightweight Inference / Edge AI Classification |
| JADE + Katie split | Tiered Model Architecture / Model Routing |
| `params.yaml` per experiment | Hyperparameter Versioning / Experiment Reproducibility |
| MLflow inference tracking | Model Observability / Inference Monitoring |

## Directory Conventions

- `1-data-pipeline/01-raw-data-lake/` — drop raw training data here (JSONL, JSON, MD, TXT, PDF)
- `2-rag-ingestion/01-unprocessed/` — drop raw docs for RAG here
- `2-rag-ingestion/01-unprocessed/claudecode-sessions/` — Claude CLI session extracts go here
- `5-experiments/exp-NNN-short-name/` — one dir per experiment (params.yaml, metrics.json, notes.md)
- `6-model-cards/champion/` — only promoted models. `6-model-cards/challenger/` for candidates.
- Trained chunks move from `03-chunked-untrained/` → `04-trained-data/` automatically
- `0-data-lab/` — Data science workspace. Raw data in, refined training/RAG data out.
- `CAPSTONE-PROJECT/` — BERU capstone working directory. All AI RMF framework files, intake forms, templates, design decisions live here first. Copy to GP-CONSULTING when ready.
- `BERU-AI/training-data/` — BERU ChatML training corpus. Gemini generates, quality gates validate before any training run.
- `llama.cpp/` and `unsloth_compiled_cache/` are vendored dependencies — don't modify

## BERU Build Rules

1. **Every BERU finding cites both 800-53 AND AI RMF** when an AI system is in scope. No exceptions.
2. **AI system not in `ai-inventory-register.md`?** → GOVERN 1.1 FAIL, B-rank, escalate. Don't assess it as infrastructure.
3. **BERU does not fix.** If you find yourself writing remediation code in BERU context, stop. Route to JADE or Katie.
4. **Design decisions go in `beru-design-decisions.md` before code.** Can't answer "why did you build it this way?" → don't build it yet.
5. **Synthetic training data only.** No real client scanner output in the training corpus. Gemini generates SSPs, POA&Ms, and scenario inputs.
6. **Eval gate is non-negotiable.** ≥70% overall, ≥60% per family, zero hallucinated IDs before any version is promoted.
7. **HITL router is not optional.** B/S-rank findings must pass through `hitl_router.py` before output is written. This is MANAGE-2.2. Test it.
