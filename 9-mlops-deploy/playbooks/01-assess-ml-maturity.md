# Playbook 01 — Assess ML Maturity

> Baseline the client's current MLOps state and score against the maturity model.
> **When:** Start of every MLOps engagement
> **Time:** 2-4 hours

---

## Prerequisites

- [ ] Cluster access (kubectl configured)
- [ ] Access to ML project repos
- [ ] List of models in production (or planned)

---

## Phase 1: Inventory

Catalog what exists today.

```bash
# Check for existing ML infrastructure
kubectl get namespaces | grep -iE 'ml|model|train|serving|mlflow|kubeflow'

# Check for GPU nodes
kubectl get nodes -l nvidia.com/gpu.present=true -o wide

# Check for existing model serving
kubectl get pods --all-namespaces | grep -iE 'ollama|vllm|triton|tgi|seldon'

# Check for experiment tracking
kubectl get pods --all-namespaces | grep -iE 'mlflow|wandb|neptune'
```

**Document:**
- [ ] Number of models in production
- [ ] Training frequency (ad-hoc, weekly, continuous)
- [ ] Data sources and formats
- [ ] Current serving infrastructure
- [ ] Experiment tracking (if any)
- [ ] Model versioning approach

---

## Phase 2: Score Maturity

Rate each dimension 0-4:

| Dimension | L0 (Manual) | L1 (Tracked) | L2 (Automated) | L3 (CI/CD) | L4 (Full Loop) |
|-----------|-------------|--------------|----------------|------------|----------------|
| **Data Management** | Files on laptop | Central storage | Quality gates | Versioned datasets | Auto-curation |
| **Experiment Tracking** | None | Spreadsheet | MLflow/W&B | Auto-logged | Compared + archived |
| **Training** | Manual scripts | Parameterized | Pipeline orchestrated | Triggered by data | Self-healing |
| **Evaluation** | Manual check | Benchmark suite | Promotion gates | A/B tested | Drift-triggered |
| **Model Registry** | Files on disk | Named versions | Stage transitions | Auto-promoted | Lineage tracked |
| **Serving** | Local only | Manual deploy | Health-checked | Canary rollout | Auto-scaled |
| **Monitoring** | None | Logs | Metrics + alerts | Drift detection | Auto-retrain |
| **CI/CD** | None | Manual trigger | On-push train | Full pipeline | Feedback loop |

**Overall Score:** Average across dimensions → L0-L4

---

## Phase 3: Gap Analysis

For each dimension below L2, create a remediation item:

```markdown
## Gap: [Dimension] — Currently L[X], Target L[Y]

**Impact:** [What breaks or is risky without this]
**Effort:** [Hours/days to implement]
**Playbook:** [Which playbook addresses this]
**Priority:** [1-5, where 1 = do first]
```

---

## Phase 4: Roadmap

Map gaps to playbooks and create a week-by-week plan:

| Week | Focus | Playbooks | Deliverables |
|------|-------|-----------|--------------|
| 1 | Assessment + Foundation | 01, 02 | Maturity report, KFP deployed |
| 2 | Foundation | 03, 04 | Registry, quality gates |
| 3-4 | Pipeline | 05, 06, 07 | Training + RAG + eval |
| 5 | Serving | 08 | Model endpoints live |
| 6 | Automation | 09, 10 | CI/CD + monitoring |
| 7 | Report | 11, 12 | Cost optimization + compliance |

---

## What Next

| Finding | Next Playbook |
|---------|---------------|
| No experiment tracking | `02-deploy-experiment-tracking.md` |
| No model versioning | `03-setup-model-registry.md` |
| No data quality | `04-setup-data-quality-gates.md` |
| No training pipeline | `05-setup-training-pipeline.md` |
| No RAG pipeline | `06-setup-rag-pipeline.md` |
| No eval/benchmarks | `07-setup-model-eval.md` |
| No serving infra | `08-deploy-model-serving.md` |
