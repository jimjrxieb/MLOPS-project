# Target Roles — Skills Map

> Goal: Land one of these four roles by building BERU as the capstone project.
> BERU demonstrates every core requirement across all four. Read the curriculum: `BERU-CAPSTONE-CURRICULUM.md`

---

## Role 1 — AI Commercialization Associate (PwC)

**Level:** Associate | **Type:** Consulting | **Audience:** Business-facing

### What They Need

| Requirement | Type |
| --- | --- |
| 1+ year in consulting, digital transformation, AI enablement, or commercial strategy | Experience |
| Foundational understanding of Commercial AI strategy | Knowledge |
| Working knowledge of Generative AI tools | Technical |
| Evaluate business challenges through a strategic AI lens | Skill |
| Support quantitative analysis and data insights | Skill |
| Develop structured, executive-ready documents | Communication |
| Continuous learning mindset in AI and digital innovation | Soft skill |

### What Sets You Apart

- Commercial AI strategy literacy (deployment models, risk classification)
- Ability to translate AI capabilities into business outcomes
- Executive communication — no jargon, clear narrative

### GP-Copilot / BERU Evidence

| Requirement | Evidence |
| --- | --- |
| Commercial AI strategy | AI-SEC-LENS Part 6 — six deployment models A-F, EU AI Act, NIST AI 600-1 |
| GenAI tool knowledge | Built BERU on LLaMA 8B with Ollama, fine-tuned with LoRA, RAG with ChromaDB |
| Executive-ready documents | BERU `04-ciso-briefing.md` — no NIST IDs, plain-language risk tables |
| Strategic AI lens | GP-Copilot NIST-CONTROL-MAP.md, 3POA audit framework |
| Quantitative analysis | gap-analysis.py, POA&M gap tracking, kubescape risk scoring |

---

## Role 2 — AI Engineer (Jobright)

**Level:** Early-career (0-2 years) | **Type:** Product engineering | **Audience:** Production AI agents

### What They Need

| Requirement | Type |
| --- | --- |
| Python + FastAPI (or Flask/Django) | Technical |
| LLM deployment and autonomous agent infrastructure | Technical |
| RAG architecture implementation | Technical |
| ML monitoring, testing, and CI/CD for AI | MLOps |
| Docker + Kubernetes | Infrastructure |
| Vector databases (Pinecone, Milvus, Weaviate) | Technical |
| AWS / GCP / Azure | Cloud |

### What Sets You Apart

- Production AI agents end-to-end (not just notebooks)
- MLOps pipeline with experiment tracking
- RAG systems in production

### GP-Copilot / BERU Evidence

| Requirement | Evidence |
| --- | --- |
| Python + FastAPI | `GP-INFRA/GP-API/` — FastAPI on port 8000, `/api/jade`, `/api/beru` |
| LLM deployment | Ollama serving jade:v1.0, katie:v1.0, beru:v1.0 as Modelfiles |
| RAG architecture | ChromaDB 33k+ docs, 7 collections, nomic-embed-text 768-dim |
| MLOps | MLflow at `JADE-AI/mlruns/`, experiment tracking, eval promotion gates |
| Docker + Kubernetes | jsa-kubestar deployed on cluster, Helm charts, ArgoCD |
| Vector databases | ChromaDB collections, ingestion pipeline, zero-vector quarantine |
| Monitoring + CI/CD | 48 tests in `8-tests/`, data quality gates, eval bridge |

---

## Role 3 — LLM Infrastructure Engineer (NewtonX)

**Level:** 3-4 years | **Type:** Full-stack AI infra | **Audience:** Enterprise B2B research

### What They Need

| Requirement | Type |
| --- | --- |
| Production Python backend (3-4 years shipping code) | Technical |
| LLM integrations (OpenAI/Anthropic APIs or equivalent) | Technical |
| RAG systems, embeddings, semantic search | Technical |
| Full-stack: React/TypeScript + Python backend | Technical |
| AWS + Docker deployment | Infrastructure |
| Fusing structured and unstructured data | Technical |
| High code quality: testing, code reviews, CI/CD | Engineering |

### What Sets You Apart (Nice to Have)

- Real-time data processing or streaming
- Open-source contributions in AI/ML
- Demonstrated LLM project (side project, OSS, blog)

### GP-Copilot / BERU Evidence

| Requirement | Evidence |
| --- | --- |
| Production Python | GP-MODEL-OPS pipeline: ETL, chunking, LoRA training, GGUF conversion, eval |
| LLM integrations | Ollama provider at `JADE-AI/providers/ollama.py`, ChromaDB embedding |
| RAG systems | `2-RagIngestion-Pipeline/` — 7-stage NPC factory, 33k docs, semantic search |
| Structured + unstructured fusion | Scanner JSON output → NIST control mapping → structured POA&M |
| Open-source AI project | GP-Copilot itself — public MSSP framework with OSS tools |
| Testing + CI/CD | 48 tests, data quality gates, promotion criteria |

---

## Role 4 — GenAI Engineer (Deloitte)

**Level:** 2+ years | **Type:** Internal product engineering | **Audience:** Enterprise clients

### What They Need

| Requirement | Type |
| --- | --- |
| 2+ years AI/ML with GenAI focus | Experience |
| LangChain, Agents, Vector databases, Prompt engineering, fine-tuning | Technical |
| Python + cloud-native (AWS, Azure, GCP) | Technical |
| DevSecOps, CI/CD, full SDLC lifecycle | Engineering |
| OpenAI, Claude, Gemini API experience | Technical |
| Big data + SQL/NoSQL | Data |
| Agile/SAFe/XP methodologies | Process |
| Cross-functional collaboration, executive communication | Soft skills |

### What Sets You Apart

- End-to-end ownership from requirements to production
- Security-aware engineering (DevSecOps)
- Clear technical communication across org levels

### GP-Copilot / BERU Evidence

| Requirement | Evidence |
| --- | --- |
| GenAI fine-tuning | LoRA r=64/alpha=128 on LLaMA 3.1-8B and 3.2-3B via Unsloth |
| Agents | JADE + Katie + BERU agentic stack, LangGraph, rank routing |
| Vector databases | ChromaDB, 7 collections, embedding pipeline |
| Prompt engineering | BERU Modelfile_beru8b — system prompt engineering for audit persona |
| DevSecOps | GP-CONSULTING full DevSecOps framework — SAST, RBAC, Kyverno, Falco |
| Full SDLC | Model lifecycle: data → train → eval → promote → serve → monitor |
| Claude API | GP-API uses Claude Sonnet for B/S-rank decisions |
| Executive communication | CISO briefing templates, SSP narratives, POA&M writing |

---

## Cross-Role Skills Matrix

Skills that appear in 3+ of the 4 roles — these are the must-haves:

| Skill | PwC | Jobright | NewtonX | Deloitte | Capstone Module |
| --- | :---: | :---: | :---: | :---: | --- |
| Python (production) | | ✓ | ✓ | ✓ | M0, M3, M8 |
| LLM/GenAI fundamentals | ✓ | ✓ | ✓ | ✓ | M1 |
| RAG + vector databases | | ✓ | ✓ | ✓ | M2 |
| Fine-tuning | | ✓ | | ✓ | M3 |
| Agents / agentic architecture | ✓ | ✓ | | ✓ | M4 |
| MLOps + CI/CD | | ✓ | ✓ | ✓ | M5 |
| Docker + Kubernetes | | ✓ | ✓ | ✓ | M5 |
| AWS / cloud | | ✓ | ✓ | ✓ | M5 |
| Domain expertise (GRC/AI) | ✓ | | | ✓ | M6 |
| Commercial AI strategy | ✓ | | | ✓ | M7 |
| Executive communication | ✓ | | | ✓ | M7, M8 |
| Testing + code quality | | ✓ | ✓ | ✓ | M0, M5 |

**The capstone project (BERU) covers every checked box in this table.**
See `BERU-CAPSTONE-CURRICULUM.md` for the full learning path.

---

## Role 5 — AI/ML Engineer Entry-Level (Generic / Staffing)

**Level:** Entry-level (0–5 years, Master’s preferred) | **Type:** Client-facing placement | **Audience:** Data scientists + engineering teams

### What They Need

| Requirement | Type |
| --- | --- |
| Python (strong) | Technical |
| ML concepts — supervised/unsupervised, training/testing, overfitting | Knowledge |
| Pandas, NumPy, Scikit-learn | Technical |
| Statistics, probability, linear algebra | Knowledge |
| SQL and databases | Technical |
| SDLC and ML best practices | Engineering |
| Good communication for US clients | Soft skill |

### What Sets You Apart

- Working ML project (academic, OSS, or internship) — not just coursework
- Deep learning / NLP exposure (TensorFlow, PyTorch, Keras)
- Cloud ML services (AWS SageMaker, Azure ML, GCP Vertex)
- GitHub portfolio or Kaggle participation

### GP-Copilot / BERU Evidence

| Requirement | Evidence |
| --- | --- |
| Python | All core Python tools: `gap-to-poam.py`, `BERU-AI/core/`, `1-data-pipeline/` scripts |
| ML concepts | LoRA fine-tuning (supervised), rank classifier (sklearn), eval/train split, overfitting via chunk size |
| Pandas/NumPy | ETL pipeline (`etl_pipeline.py`), data preprocessing throughout `1-data-pipeline/` |
| Scikit-learn | `RANK-AI` sklearn classifier, `rank_classifier.joblib` |
| Deep learning / NLP | LLaMA 3.1-8B fine-tuning via Unsloth, HuggingFace PEFT |
| Cloud ML | SageMaker pipeline in `1c-sagemaker-pipeline/`, Prowler for AWS security |
| GitHub portfolio | GP-Copilot is public OSS — the whole repo is the portfolio |

**Gap to address:** No Pandas-heavy data analysis notebook visible as a standalone demo. Easy fix: add one Jupyter notebook in `5-experiments/` showing model eval results as a DataFrame.

---

## Role 6 — MLOps Engineer (Defense / Government, 3+ Years)

**Level:** Mid-senior (3+ years) | **Type:** Government-funded applied research | **Audience:** Data scientists + geophysicists + engineering teams | **Note:** U.S. citizenship required (security clearance eligible)

### What They Need

| Requirement | Type |
| --- | --- |
| 3+ years MLOps / ML Engineering / Data Engineering | Experience |
| Python data stack — Pandas/Polars, PyArrow, NumPy/SciPy | Technical |
| ML framework integration — PyTorch, TensorFlow, or Keras into pipelines | Technical |
| Full ML lifecycle — ingest → train → eval → inference → monitoring | MLOps |
| CI/CD for ML/data services (Git-based) | Engineering |
| AWS or cloud environment experience | Cloud |
| Containerized ML workloads on Kubernetes | Infrastructure |
| Collaboration with data scientists to operationalize algorithms | Engineering |
| U.S. Security Clearance eligible (citizenship required) | Compliance |

### What Sets You Apart (Nice to Have)

- KEDA or event-driven autoscaling for ML workloads
- Streaming pipelines (Kafka, Spark, Flink) feeding lakehouse formats (Iceberg, Delta)
- SQL engines (Trino, DuckDB, Athena)
- Orchestration (Airflow, Dask, Ray, Spark)
- Helm + GitOps (ArgoCD)
- Defense, cybersecurity, or mission-driven analytics background

### GP-Copilot / BERU Evidence

| Requirement | Evidence |
| --- | --- |
| 3+ years MLOps | GP-MODEL-OPS: full lifecycle — `0-data-lab` → train → eval → serve → monitor |
| Python data stack | `1-data-pipeline/etl_pipeline.py`, `chunk_data.py`, all pipeline scripts |
| PyTorch / HuggingFace into pipelines | Unsloth LoRA training (`train_v11.py`), PEFT/GGUF conversion |
| Full ML lifecycle | 9-step pipeline: ETL → chunk → train → merge → GGUF → eval → feedback → serve → monitor |
| CI/CD for ML | GitHub Actions eval gate (pending M5), `8-tests/` quality gates, eval promotion criteria |
| AWS / cloud | SageMaker pipeline (`1c-sagemaker-pipeline/`), Prowler 300+ checks, EKS deployment |
| K8s containerized ML | jsa-kubestar deployed on K8s cluster, Ollama served via K8s Deployment |
| Helm + GitOps | ArgoCD + Helm charts throughout `GP-CONSULTING/DEVOPS-LENS/` |
| Defense / cybersecurity background | GP-Copilot itself — FedRAMP, NIST 800-53, DoD-aligned security framework |
| Security clearance | U.S. citizenship — confirm eligibility separately |

**Key differentiator for this role:** The "government-funded applied research" context maps directly to GP-Copilot’s FedRAMP Moderate and DoD alignment. BERU’s AI RMF integration is exactly what defense AI programs require. Most candidates won’t have a publicly available example of responsible AI governance documentation.

---

## Updated Cross-Role Skills Matrix

Skills appearing in 3+ of the 6 roles — must-haves:

| Skill | PwC | Jobright | NewtonX | Deloitte | Entry ML | MLOps Defense | Capstone Module |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| Python (production) | | ✓ | ✓ | ✓ | ✓ | ✓ | M0, M3, M8 |
| LLM/GenAI fundamentals | ✓ | ✓ | ✓ | ✓ | | | M1 |
| RAG + vector databases | | ✓ | ✓ | ✓ | | | M2 |
| Fine-tuning (LoRA/QLoRA) | | ✓ | | ✓ | ✓ | ✓ | M3 |
| Agents / agentic architecture | ✓ | ✓ | | ✓ | | | M4 |
| MLOps + CI/CD | | ✓ | ✓ | ✓ | | ✓ | M5 |
| Docker + Kubernetes | | ✓ | ✓ | ✓ | | ✓ | M5 |
| AWS / cloud | | ✓ | ✓ | ✓ | ✓ | ✓ | M5 |
| ML lifecycle (ingest→serve) | | | | | ✓ | ✓ | M3, M5 |
| Domain expertise (GRC/AI sec) | ✓ | | | ✓ | | ✓ | M6 |
| AI governance (RMF/600-1) | ✓ | | | ✓ | | ✓ | M6 |
| Commercial AI strategy | ✓ | | | ✓ | | | M7 |
| Executive communication | ✓ | | | ✓ | | | M7, M8 |
| Testing + code quality | | ✓ | ✓ | ✓ | ✓ | ✓ | M0, M5 |
| Scikit-learn / ML frameworks | | | | | ✓ | ✓ | M3 |

**The capstone project (BERU) covers every checked box in this table.**
See `BERU-CAPSTONE-CURRICULUM.md` for the full learning path.
