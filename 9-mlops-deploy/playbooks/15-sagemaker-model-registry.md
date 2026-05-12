# Playbook 15 — SageMaker Model Registry

> Managed model versioning with approval workflows and deployment stages.
> **When:** Client needs governed model promotion (especially FedRAMP/compliance)
> **Time:** 1-2 hours

---

## Prerequisites

- [ ] SageMaker Training Job completed (Playbook 14)
- [ ] Model artifacts in S3

---

## Phase 1: Create Model Package Group

```python
import boto3

sm = boto3.client("sagemaker")

# Create a model group (like a project — all versions of Katie go here)
sm.create_model_package_group(
    ModelPackageGroupName="katie-3b",
    ModelPackageGroupDescription="Katie 3B — CKA/CKS/CKAD platform engineer model"
)
```

---

## Phase 2: Register Model Version

```python
# After training completes, register the model
sm.create_model_package(
    ModelPackageGroupName="katie-3b",
    ModelPackageDescription="Katie v2.0 — trained on 42k curated examples",
    InferenceSpecification={
        "Containers": [{
            "Image": "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.1-transformers4.37-gpu-py310-cu121-ubuntu22.04",
            "ModelDataUrl": "s3://your-bucket/model-output/model.tar.gz",
        }],
        "SupportedContentTypes": ["application/json"],
        "SupportedResponseMIMETypes": ["application/json"],
    },
    ModelApprovalStatus="PendingManualApproval",
    CustomerMetadataProperties={
        "experiment": "exp-002-katie-v2-curated",
        "corpus_sha256": "0347e5e9df5aa0cf...",
        "eval_score": "pending",
        "training_examples": "42276",
        "base_model": "llama-3.2-3b-instruct",
    }
)
```

---

## Phase 3: Approval Workflow

```python
# List pending models
response = sm.list_model_packages(
    ModelPackageGroupName="katie-3b",
    ModelApprovalStatus="PendingManualApproval"
)

for pkg in response["ModelPackageSummaryList"]:
    print(f"Version: {pkg['ModelPackageVersion']}")
    print(f"Status: {pkg['ModelApprovalStatus']}")
    print(f"Created: {pkg['CreationTime']}")

# After eval passes promotion gate:
sm.update_model_package(
    ModelPackageArn="arn:aws:sagemaker:us-east-1:123456789:model-package/katie-3b/2",
    ModelApprovalStatus="Approved",
    ApprovalDescription="Eval score 65% — passes 60% threshold. CKS 52%, CKA 58%."
)

# Or reject:
sm.update_model_package(
    ModelPackageArn="arn:aws:sagemaker:us-east-1:123456789:model-package/katie-3b/2",
    ModelApprovalStatus="Rejected",
    ApprovalDescription="Eval score 45% — below 60% threshold. Needs more CNPA data."
)
```

---

## Phase 4: SageMaker Model Cards (Compliance)

For FedRAMP / audit compliance, attach a model card:

```python
sm.create_model_card(
    ModelCardName="katie-3b-v2",
    Content=json.dumps({
        "model_overview": {
            "model_name": "Katie v2.0 (3B)",
            "model_description": "CKA/CKS/CKAD-certified Kubernetes platform engineer",
            "model_owner": "LinkOps Industries",
        },
        "intended_uses": {
            "purpose_of_model": "Autonomous K8s troubleshooting and remediation",
            "intended_users": "JSA agents, k8sgpt, kubectl-ai",
            "out_of_scope_uses": "B/S rank decisions, architecture decisions",
        },
        "training_details": {
            "training_data": "42,276 curated examples (ChatML format)",
            "training_method": "LoRA fine-tuning (r=64, alpha=128, 4-bit quantized)",
        },
        "evaluation_details": {
            "evaluation_metrics": "Weighted eval: CKS 40%, CKA 25%, CNPA 25%, Cloud 10%",
            "promotion_threshold": "≥60% weighted, each category ≥50%",
        },
    }),
    ModelCardStatus="Draft",
)
```

---

## Self-Hosted vs SageMaker Comparison

| Feature | Self-hosted (`6-model-cards/`) | SageMaker Model Registry |
|---------|-------------------------------|--------------------------|
| Model cards | Markdown in git | SageMaker Model Cards (API) |
| Versioning | Directory-based (`v1.1-3b/`, `v2.0-3b/`) | Automatic version numbers |
| Approval | Manual (update model_card.md) | Built-in PendingApproval → Approved/Rejected |
| Audit trail | Git history | CloudTrail + SageMaker lineage |
| FedRAMP | Manual documentation | Native compliance artifacts |
| Cost | Free | Free (included with SageMaker) |

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Model registered | `16-sagemaker-endpoints.md` |
| Need drift monitoring | `17-sagemaker-model-monitor.md` |
