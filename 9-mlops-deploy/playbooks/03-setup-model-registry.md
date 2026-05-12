# Playbook 03 — Setup Model Registry

> Configure model versioning with promotion workflows. File-based registry for K8s track, SageMaker Model Registry for AWS track.
> **When:** After KFP deployed (Playbook 02)
> **Time:** 1-2 hours

---

## Prerequisites

- [ ] KFP deployed (Playbook 02) or SageMaker configured
- [ ] S3 bucket for model storage
- [ ] At least one trained model checkpoint

---

## Phase 1: Registry Directory Structure

Models are versioned in S3 and tracked via KFP artifacts. The file-based registry defines what's promoted:

```
s3://ml-artifacts/models/
├── katie-3b/
│   ├── v1.1/
│   │   ├── model.gguf            ← GGUF for vLLM serving
│   │   ├── config.yaml           ← Training config snapshot
│   │   ├── eval_results.json     ← Benchmark scores
│   │   └── training_state.json   ← What data was used
│   └── v2.0/
│       ├── model.gguf
│       ├── config.yaml
│       ├── eval_results.json
│       └── training_state.json
├── jade-8b/
│   └── v1.1/
│       └── ...
└── registry.json                  ← Version manifest (which version is production)
```

---

## Phase 2: Version Manifest

The `registry.json` file tracks which model version is active:

```json
{
  "models": {
    "katie-3b": {
      "production": "v2.0",
      "staging": null,
      "archived": ["v1.0", "v1.1"],
      "last_promoted": "2026-03-25T10:00:00Z",
      "promotion_score": 65.2,
      "promotion_threshold": 60.0
    },
    "jade-8b": {
      "production": "v1.1",
      "staging": null,
      "archived": ["v1.0"],
      "last_promoted": "2026-03-10T08:00:00Z",
      "promotion_score": 62.8,
      "promotion_threshold": 60.0
    }
  }
}
```

---

## Phase 3: Promotion Workflow

Models move through stages: **Training** → **Staging** → **Production** → **Archived**

```python
import boto3
import json
from datetime import datetime

s3 = boto3.client("s3")
BUCKET = "ml-artifacts"
REGISTRY_KEY = "models/registry.json"

def promote_model(model_name: str, version: str, eval_score: float, threshold: float = 60.0):
    """Promote a model version to production."""
    if eval_score < threshold:
        raise ValueError(f"Score {eval_score}% below threshold {threshold}%")

    # Load current registry
    obj = s3.get_object(Bucket=BUCKET, Key=REGISTRY_KEY)
    registry = json.loads(obj["Body"].read())

    model = registry["models"].get(model_name, {})

    # Archive current production
    current_prod = model.get("production")
    if current_prod:
        archived = model.get("archived", [])
        archived.append(current_prod)
        model["archived"] = archived

    # Promote new version
    model["production"] = version
    model["staging"] = None
    model["last_promoted"] = datetime.utcnow().isoformat() + "Z"
    model["promotion_score"] = eval_score
    model["promotion_threshold"] = threshold

    registry["models"][model_name] = model

    # Write back
    s3.put_object(
        Bucket=BUCKET,
        Key=REGISTRY_KEY,
        Body=json.dumps(registry, indent=2),
    )
    print(f"Promoted {model_name} {version} (score: {eval_score}%)")


def rollback_model(model_name: str):
    """Rollback to previous production version."""
    obj = s3.get_object(Bucket=BUCKET, Key=REGISTRY_KEY)
    registry = json.loads(obj["Body"].read())

    model = registry["models"][model_name]
    archived = model.get("archived", [])
    if not archived:
        raise ValueError("No archived version to rollback to")

    previous = archived.pop()
    model["production"] = previous
    model["archived"] = archived

    registry["models"][model_name] = model
    s3.put_object(
        Bucket=BUCKET,
        Key=REGISTRY_KEY,
        Body=json.dumps(registry, indent=2),
    )
    print(f"Rolled back {model_name} to {previous}")
```

---

## Phase 4: KFP Integration

The training pipeline's `register_model` component uploads to S3 and updates the registry automatically. KFP tracks the full lineage:

```
KFP Experiment → Run → Training Artifact → Eval Metrics → Promoted Model
                                                            ↓
                                              registry.json updated
                                                            ↓
                                              KServe InferenceService picks up new model
```

---

## Phase 5: Verify

```bash
# Check registry
aws s3 cp s3://ml-artifacts/models/registry.json - | python3 -m json.tool

# List model versions
aws s3 ls s3://ml-artifacts/models/katie-3b/ --recursive | head -20

# Check KFP artifacts for a specific run
# → KFP UI: Experiments → katie-3b-training → (latest run) → Artifacts tab
```

**Success criteria:**
- [ ] registry.json in S3 with model entries
- [ ] Each version has config + eval results + training state
- [ ] Promotion/rollback functions work
- [ ] KFP pipeline automatically registers promoted models

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Registry configured | `04-setup-data-quality-gates.md` |
| Ready to build pipeline | `05-setup-kfp-pipeline.md` |
| Want SageMaker registry | `15-sagemaker-model-registry.md` |
