# 04-Model Serving

KServe + vLLM deployment configs for production LLM serving on Kubernetes.

## Contents

```
04-model-serving/
├── kserve/
│   ├── inferenceservice-vllm.yaml   ← InferenceService for Katie 3B + JADE 8B
│   ├── servingruntime-vllm.yaml     ← ClusterServingRuntime (vLLM with OpenAI API)
│   └── keda-scaledobject.yaml       ← Autoscaling on vLLM queue depth + GPU util
└── vllm/
    ├── deployment.yaml              ← Raw vLLM deployment (non-KServe fallback)
    └── service.yaml
```

## Serving Stack

| Component | Role |
|-----------|------|
| **KServe** | InferenceService CRD — model lifecycle, canary, routing |
| **vLLM** | LLM engine — PagedAttention, continuous batching, OpenAI API |
| **KEDA** | Autoscaler — scales on vLLM Prometheus metrics |

## Deployed by

- `tools/deploy-kserve.sh`
- Playbook `08-deploy-kserve.md`
