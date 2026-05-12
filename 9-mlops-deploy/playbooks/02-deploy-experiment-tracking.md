# Playbook 02 — Deploy Kubeflow Pipelines (Experiment Tracking + Orchestration)

> Deploy standalone KFP for pipeline orchestration, experiment tracking, and artifact lineage. No full Kubeflow platform — just KFP.
> **When:** After maturity assessment (Playbook 01)
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] K8s cluster running (EKS, Docker Desktop K8s, or any K8s 1.27+)
- [ ] Helm 3.x installed
- [ ] (Docker Desktop) Default StorageClass available (`hostpath` — comes out of the box)
- [ ] (Production) S3 bucket for pipeline artifacts
- [ ] (Production) RDS MySQL for metadata store

> **Docker Desktop note:** KFP standalone deploys SeaweedFS (S3-compatible) and MySQL in-cluster automatically. No external S3 or RDS needed for local dev.

---

## Phase 1: Install KFP Standalone

```bash
# Deploy KFP standalone via the deploy script (uses kustomize, not Helm)
bash tools/deploy-kubeflow.sh --namespace kubeflow

# The script applies two kustomize layers:
# 1. Cluster-scoped resources (CRDs for Argo Workflows, KFP)
# 2. Platform-agnostic deployment (no Istio, includes in-cluster storage)
#
# First deploy takes 5-10 min as images pull. Pods with CrashLoopBackOff
# during startup are normal — they recover once MySQL is ready.
```

**What gets deployed (14 pods):**
- KFP API server (REST + gRPC)
- KFP UI (pipeline visualization, run monitoring)
- Argo Workflow controller (executes pipeline steps as pods)
- MySQL (metadata store — experiments, runs, artifacts)
- SeaweedFS (S3-compatible artifact storage — replaces MinIO in KFP 2.16+)
- Metadata gRPC + envoy (ML Metadata service)
- Cache server (skip re-execution of identical pipeline steps)

---

## Phase 2: Verify KFP

```bash
# Check pods
kubectl get pods -n kubeflow

# Port-forward the UI
kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8888:80
# → http://localhost:8888

# Test API
kubectl port-forward svc/ml-pipeline -n kubeflow 8887:8888
curl http://localhost:8887/apis/v2beta1/healthz
```

---

## Phase 3: Create First Experiment

Experiments group related pipeline runs (like MLflow experiments).

```python
from kfp import Client

client = Client(host="http://localhost:8887")  # port-forward first

# Create experiment
experiment = client.create_experiment(
    name="katie-3b-training",
    description="Katie 3B LoRA fine-tuning runs",
)
print(f"Experiment: {experiment.experiment_id}")

# List experiments
experiments = client.list_experiments()
for exp in experiments.experiments:
    print(f"  {exp.display_name} ({exp.experiment_id})")
```

---

## Phase 4: Submit a Test Pipeline

```python
from kfp import dsl, Client

@dsl.component(base_image="python:3.11-slim")
def hello(name: str) -> str:
    msg = f"Hello {name} from KFP!"
    print(msg)
    return msg

@dsl.pipeline(name="test-pipeline")
def test_pipeline(name: str = "Katie"):
    hello(name=name)

client = Client(host="http://localhost:8887")  # port-forward first
run = client.create_run_from_pipeline_func(
    test_pipeline,
    experiment_name="test",
    arguments={"name": "Katie"},
)
print(f"Run: {run.run_id}")
```

---

## Phase 5: Production Config (RDS + S3)

For production, switch from in-cluster MySQL to RDS:

```yaml
# In 01-kubeflow-platform/manifests/kfp-values.yaml
mysql:
  enabled: false
  externalHost: kfp-db.xxxx.us-east-1.rds.amazonaws.com
  externalPort: 3306
  existingSecret: kfp-db-credentials
  existingSecretKey: password
```

And use IRSA for S3 access (no static credentials):

```bash
# Create IRSA for KFP service account
eksctl create iamserviceaccount \
  --name ml-pipeline \
  --namespace mlops \
  --cluster your-cluster \
  --attach-policy-arn arn:aws:iam::123456789:policy/KFPArtifactAccess \
  --approve
```

---

## KFP vs MLflow vs SageMaker

| Feature | KFP (this playbook) | SageMaker Experiments |
|---------|--------------------|-----------------------|
| Pipeline orchestration | Yes (DAGs, caching, parallelism) | Yes (SageMaker Pipelines) |
| Experiment tracking | Yes (runs, metrics, artifacts) | Yes (native) |
| Artifact lineage | Automatic | Automatic |
| UI | KFP UI (pipeline graphs) | SageMaker Studio |
| Cost | Free (self-hosted) | Included with SageMaker |
| Vendor lock-in | None (runs on any K8s) | AWS only |
| Best for | K8s-native teams, portability | AWS-native teams, compliance |

---

## Success Criteria

- [ ] KFP pods running in `mlops` namespace
- [ ] KFP UI accessible via port-forward
- [ ] Test pipeline completes successfully
- [ ] Experiment shows up in UI with run details
- [ ] (Production) RDS backend configured, S3 artifacts working

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| KFP deployed | `03-setup-model-registry.md` |
| Need serving too | `08-deploy-kserve.md` |
| Want SageMaker instead | `13-sagemaker-experiment-tracking.md` |
