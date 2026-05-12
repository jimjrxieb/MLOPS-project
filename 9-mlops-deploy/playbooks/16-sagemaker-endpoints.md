# Playbook 16 — SageMaker Endpoints (Model Serving)

> Deploy models as managed SageMaker endpoints instead of self-hosted KServe + vLLM.
> **When:** Client wants managed inference with autoscaling
> **Time:** 1-2 hours

---

## Prerequisites

- [ ] Model registered in SageMaker Model Registry (Playbook 15)
- [ ] Or model artifacts in S3

---

## Phase 1: Create Model

```python
import sagemaker
from sagemaker.huggingface import HuggingFaceModel

role = "arn:aws:iam::123456789:role/SageMakerEndpointRole"

model = HuggingFaceModel(
    model_data="s3://your-bucket/model-output/model.tar.gz",
    role=role,
    transformers_version="4.37",
    pytorch_version="2.1",
    py_version="py310",
    env={
        "HF_TASK": "text-generation",
    }
)
```

---

## Phase 2: Deploy Endpoint

```python
# Real-time endpoint
predictor = model.deploy(
    initial_instance_count=1,
    instance_type="ml.g5.xlarge",       # A10G for 3B model
    endpoint_name="katie-3b-prod",
)

# Test it
response = predictor.predict({
    "inputs": "A pod has CrashLoopBackOff. Exit code 137. Diagnose and fix.",
    "parameters": {"max_new_tokens": 500, "temperature": 0.3}
})
print(response)
```

---

## Phase 3: Autoscaling

```python
# Scale based on invocations per instance
client = boto3.client("application-autoscaling")

client.register_scalable_target(
    ServiceNamespace="sagemaker",
    ResourceId="endpoint/katie-3b-prod/variant/AllTraffic",
    ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    MinCapacity=1,
    MaxCapacity=3,
)

client.put_scaling_policy(
    PolicyName="katie-scaling",
    ServiceNamespace="sagemaker",
    ResourceId="endpoint/katie-3b-prod/variant/AllTraffic",
    ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    PolicyType="TargetTrackingScaling",
    TargetTrackingScalingPolicyConfiguration={
        "TargetValue": 10.0,             # 10 invocations per instance
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
        },
        "ScaleInCooldown": 300,
        "ScaleOutCooldown": 60,
    }
)
```

---

## Phase 4: Scale to Zero (Cost Optimization)

SageMaker Serverless Inference won't work for LLMs (cold start too long). But you can schedule scale-down:

```python
# Scale to 0 at night (if not 24/7)
# Use EventBridge + Lambda to set DesiredInstanceCount=0 at 10pm, back to 1 at 6am
```

Or use **SageMaker Inference Components** (pack multiple models on one endpoint):

```python
# Serve both Katie 3B and JADE 8B on one instance
# SageMaker routes traffic to the right model
# Saves cost vs 2 separate endpoints
```

---

## Self-Hosted vs SageMaker Comparison

| Feature | KServe + vLLM on K8s | SageMaker Endpoint |
|---------|---------------------|-------------------|
| Setup | kubectl apply (InferenceService) | model.deploy() |
| Autoscaling | KEDA (custom vLLM metrics) | Built-in (invocations/instance) |
| Cost (idle) | Node cost (Karpenter scales nodes) | ~$1.41/hr minimum |
| Cost (active) | Same instance cost | Same + SageMaker markup (~15%) |
| Multi-model | Multiple InferenceServices | Inference Components |
| API format | OpenAI-compatible (native) | SageMaker SDK |
| Monitoring | Prometheus + vLLM metrics | CloudWatch built-in |
| FedRAMP | You manage compliance | AWS manages infrastructure compliance |
| Best for | K8s-native, portability, custom metrics | High QPS, managed, compliance-required |

**Honest take:** KServe + vLLM gives you OpenAI-compatible API, custom autoscaling on GPU metrics, and zero vendor lock-in. SageMaker endpoints make sense when you need fully managed infrastructure, compliance artifacts, or you're serving many clients.

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Endpoint running | `17-sagemaker-model-monitor.md` |
| Need cost optimization | `11-optimize-ml-costs.md` |
