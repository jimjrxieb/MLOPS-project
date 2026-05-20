# 9-MLOPS-DEPLOY Engagement Guide

> Source of truth for MLOps deployment engagements. This is the agent brain — playbook reader, not implementation.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │        MLOps Platform (K8s / AWS)        │
                    │                                         │
  Raw Data ──►  ┌──┴───────┐   ┌───────────┐   ┌──────────┐ │
                │ KFP       │──►│  Model     │──►│  KServe  │ │
                │ Pipeline  │   │  Registry  │   │  + vLLM  │ │
                └──┬───────┘   └───────────┘   └──────────┘ │
                   │                │                │        │
                ┌──┴───────┐   ┌───┴───────┐   ┌───┴──────┐ │
                │ Data      │   │ Experiment│   │ Monitoring│ │
                │ Quality   │   │ Tracking  │   │ & Drift  │ │
                └──────────┘   └───────────┘   └──────────┘ │
                    │                                         │
                    │   ┌───────────┐   ┌───────────────┐    │
                    │   │ RAG       │   │ Model CI/CD   │    │
                    │   │ Pipeline  │   │ (GHA → KFP)   │    │
                    │   └───────────┘   └───────────────┘    │
                    └─────────────────────────────────────────┘
```

---

## Phase 1: Assess (Week 1)

**Goal:** Understand current ML maturity, identify gaps, establish baseline.
**Playbook:** `01-assess-ml-maturity.md`

### Summary
1. Inventory existing models, training scripts, data sources
2. Score against MLOps maturity model (L0-L4)
3. Identify highest-impact gaps
4. Create remediation roadmap

### What We Deliver
| Deliverable | Location |
|-------------|----------|
| Maturity assessment | `outputs/maturity-assessment.md` |
| Gap analysis | `outputs/gap-analysis.md` |
| Roadmap | `outputs/mlops-roadmap.md` |

---

## Phase 2: Foundation (Weeks 2-3)

**Goal:** Deploy pipeline orchestration, model registry, data quality gates.
**Playbooks:** `02-deploy-kubeflow.md`, `03-setup-model-registry.md`, `04-setup-data-quality-gates.md`

### Summary
1. Deploy KFP standalone on K8s (MySQL metadata + S3 artifacts)
2. Configure S3-based model registry with versioning and promotion workflow
3. Implement data quality gates (format validation, dedup, scope check)
4. Integrate with existing training scripts via KFP components

### Rank Classification
| Finding | Rank | Action |
|---------|------|--------|
| No experiment tracking | D | Deploy KFP standalone (pattern NPC) |
| No model versioning | D | Configure S3 registry (pattern NPC) |
| Training on uncurated data | C | Quality gate pipeline (JADE reviews) |
| No reproducibility | C | KFP pipelines (config + artifact tracking) |

### What We Deliver
| Deliverable | Location |
|-------------|----------|
| KFP instance | `mlops` namespace |
| Model registry | S3 + `registry.json` |
| Data quality pipeline | `tools/validate-training-data.py` |

---

## Phase 3: Pipeline (Weeks 3-4)

**Goal:** Automated KFP training pipeline with eval gates and model promotion.
**Playbooks:** `05-setup-kfp-pipeline.md`, `06-setup-rag-pipeline.md`, `07-setup-model-eval.md`

### Summary
1. Build KFP v2 training pipeline (validate → ETL → train → merge → convert → eval → promote)
2. Deploy RAG ingestion pipeline (preprocess → embed → ingest → validate)
3. Set up evaluation benchmarks with promotion gates
4. Wire feedback loop (weak categories → targeted data generation)

### Decision Tree
```
Pipeline submitted
  ├── validate FAILS → Stop. Fix data quality.
  ├── train OOM → Reduce batch_size. KFP retries.
  ├── eval ≥ 60% → Promote: upload to S3, update registry, rollout KServe
  ├── eval 40-60% → Generate targeted training data → re-run pipeline
  └── eval < 40% → Review training data quality → manual inspection
```

### What We Deliver
| Deliverable | Location |
|-------------|----------|
| KFP training pipeline | `02-training-pipeline/kfp/training_pipeline.py` |
| RAG pipeline | `2-RagIngestion-Pipeline/` (7-stage NPC factory) |
| Eval benchmark | `4-eval-clarify/` |
| Promotion gates | Automated in KFP pipeline |

---

## Phase 4: Serving (Week 5)

**Goal:** Deploy model serving via KServe with vLLM backend, autoscaling, canary rollouts.
**Playbook:** `08-deploy-kserve.md`

### Summary
1. Deploy KServe standalone + vLLM ServingRuntime
2. Create InferenceService for each model (Katie 3B, JADE 8B)
3. Configure KEDA autoscaling (vLLM queue depth + GPU utilization)
4. Set up canary rollout for model version transitions

### Serving Stack
| Component | Role |
|-----------|------|
| KServe | Model serving orchestration (InferenceService CRD) |
| vLLM | LLM inference engine (PagedAttention, continuous batching) |
| KEDA | Autoscaling on custom vLLM Prometheus metrics |
| Karpenter | GPU node provisioning (spot g5.xlarge, scale to zero) |

### What We Deliver
| Deliverable | Location |
|-------------|----------|
| KServe + vLLM deployment | `ml-serving` namespace |
| OpenAI-compatible API | `{endpoint}/v1/chat/completions` |
| Autoscaling | KEDA ScaledObject on vLLM metrics |

---

## Phase 5: CI/CD + Monitoring (Week 6)

**Goal:** Model CI/CD pipeline, drift detection, production monitoring.
**Playbooks:** `09-deploy-model-cicd.md`, `10-setup-drift-detection.md`

### Summary
1. GitHub Actions: data push → quality gate → submit KFP pipeline → wait → rollout KServe
2. Drift detection via vLLM Prometheus metrics + scheduled eval pipeline
3. Alerting on eval score degradation and request distribution shifts
4. Automated retraining triggers via KFP recurring runs

### CI/CD Flow
```
Push to data branch
  → validate-training-data (GHA quality gate)
  → Upload data to S3
  → Submit KFP pipeline (GPU training, eval, promotion)
  → IF pass: S3 model updated → KServe InferenceService patched → smoke test
  → IF fail: GitHub issue with eval scores
```

### What We Deliver
| Deliverable | Location |
|-------------|----------|
| Model CI/CD workflows | `.github/workflows/` |
| Drift detection | KFP scheduled pipeline + Prometheus |
| Grafana dashboards | vLLM metrics (latency, queue, GPU) |

---

## Phase 6: Optimize + Report (Week 7)

**Goal:** Cost optimization, compliance documentation, handoff.
**Playbooks:** `11-optimize-ml-costs.md`, `12-mlops-compliance-report.md`

### Summary
1. Right-size GPU nodes (Karpenter NodePools for ML workloads, spot instances)
2. Schedule training during off-peak
3. Generate compliance report (model lineage, data provenance, eval history)
4. Handoff documentation

### What We Deliver
| Deliverable | Location |
|-------------|----------|
| Cost optimization report | `outputs/ml-cost-report.md` |
| Compliance report | `outputs/mlops-compliance-report.md` |
| Runbook | `outputs/operational-runbook.md` |

---

## Rank Classification for MLOps Findings

| Finding | Rank | Automation |
|---------|------|------------|
| Missing experiment tracking | D | Deploy KFP standalone (scripted) |
| Unpinned dependencies | D | Pin + audit (scripted) |
| No data quality gates | C | Deploy KFP pipeline (JADE reviews config) |
| No model versioning | D | S3 registry setup (scripted) |
| Training on raw/uncurated data | C | Curation pipeline (JADE reviews) |
| No eval benchmarks | C | Deploy eval suite (JADE reviews thresholds) |
| No model CI/CD | C | Deploy GH Actions → KFP (JADE reviews) |
| Model serving without health checks | D | KServe probes (scripted) |
| No drift detection | B | Design detection strategy (human decides) |
| Model compliance/audit gap | B | Human reviews lineage + provenance |
| Novel architecture decision | S | Human only |

---

*Ghost Protocol — MLOps / Model Lifecycle Management*
