# Playbook 13 — SageMaker Experiment Tracking

> Use SageMaker Experiments for managed experiment tracking. No infrastructure to deploy.
> **When:** Client is AWS-native and wants managed experiment tracking
> **Time:** 1-2 hours

---

## Prerequisites

- [ ] AWS account with SageMaker access
- [ ] IAM role with `sagemaker:*` and `s3:*` permissions
- [ ] S3 bucket for artifacts
- [ ] AWS CLI configured (`aws sts get-caller-identity` works)

---

## Phase 1: SageMaker Experiments

Built into SageMaker — no separate server. Tighter integration with SageMaker Training Jobs.

```python
from sagemaker.experiments import Run

with Run(experiment_name="katie-3b-training", run_name="chunk_001") as run:
    run.log_parameter("model", "llama-3.2-3b-instruct")
    run.log_parameter("lora_r", 64)
    run.log_parameter("learning_rate", 2e-5)

    # Training happens here...

    run.log_metric("train_loss", 0.42)
    run.log_metric("eval_accuracy", 0.65)
    run.log_file("config.yaml", is_output=True)
```

**Cost:** Free (included with SageMaker).

---

## Phase 2: Organize Experiments

```python
import boto3

sm = boto3.client("sagemaker")

# Create experiment
sm.create_experiment(
    ExperimentName="katie-3b-training",
    Description="Katie 3B LoRA fine-tuning runs",
    Tags=[
        {"Key": "model", "Value": "katie-3b"},
        {"Key": "team", "Value": "platform"},
    ],
)

# Each training run is a "Trial"
sm.create_trial(
    TrialName="katie-3b-v2-chunk01",
    ExperimentName="katie-3b-training",
)
```

---

## Phase 3: Query Experiment Results

```python
# List all experiments
experiments = sm.list_experiments()
for exp in experiments["ExperimentSummaries"]:
    print(f"{exp['ExperimentName']} — created {exp['CreationTime']}")

# List runs in an experiment
trials = sm.list_trials(ExperimentName="katie-3b-training")
for trial in trials["TrialSummaries"]:
    print(f"  {trial['TrialName']} — {trial['CreationTime']}")

# Get metrics from SageMaker Studio UI or via search
from sagemaker.analytics import ExperimentAnalytics

analytics = ExperimentAnalytics(experiment_name="katie-3b-training")
df = analytics.dataframe()
print(df[["TrialName", "train_loss", "eval_accuracy"]].sort_values("eval_accuracy", ascending=False))
```

---

## Phase 4: Verify

```bash
# List experiments via CLI
aws sagemaker list-experiments --query 'ExperimentSummaries[].ExperimentName'

# List trials
aws sagemaker list-trials \
  --experiment-name katie-3b-training \
  --query 'TrialSummaries[].TrialName'
```

---

## KFP vs SageMaker Comparison

| Feature | KFP (Playbook 02) | SageMaker Experiments |
|---------|-------------------|-----------------------|
| Infrastructure | Self-hosted on K8s | Managed by AWS |
| Pipeline orchestration | Yes (DAGs, caching) | Yes (SageMaker Pipelines) |
| Cost | Free (infra cost only) | Free (included) |
| UI | KFP UI | SageMaker Studio |
| Portability | Any K8s cluster | AWS only |
| Best for | K8s-native, multi-cloud | AWS-native, compliance |

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Tracking running | `14-sagemaker-training-jobs.md` |
| Need model registry | `15-sagemaker-model-registry.md` |
