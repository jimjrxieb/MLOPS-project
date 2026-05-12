# Playbook 08 — Deploy KServe + vLLM (Model Serving)

> Deploy production model serving via KServe with vLLM backend. Autoscaling via KEDA. OpenAI-compatible API.
> **When:** After model passes promotion gates (Playbook 07)
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] Promoted model in S3 (`s3://ml-artifacts/models/katie-3b/v2.0/`)
- [ ] K8s cluster with GPU nodes (required for vLLM)
- [ ] KEDA installed (for autoscaling)

---

## Phase 1: Install KServe

```bash
# Deploy KServe standalone via the deploy script
bash tools/deploy-kserve.sh --namespace kserve

# Or manually:
kubectl create namespace kserve

helm repo add kserve https://kserve.github.io/charts
helm repo update

helm install kserve kserve/kserve \
  --namespace kserve \
  --values 01-kubeflow-platform/manifests/kserve-values.yaml \
  --wait \
  --timeout 10m
```

---

## Phase 2: Deploy vLLM ServingRuntime

The ServingRuntime defines HOW models are served. InferenceService references it.

```bash
# Deploy the vLLM runtime (cluster-wide — all namespaces can use it)
kubectl apply -f 04-model-serving/kserve/servingruntime-vllm.yaml

# Verify
kubectl get clusterservingruntime vllm-runtime
```

**What vLLM gives you over Ollama:**
- Concurrent request handling (PagedAttention)
- Continuous batching (higher throughput)
- OpenAI-compatible API (drop-in for existing clients)
- KV cache management (predictable latency)
- Prometheus metrics (request queue, GPU util, TTFT, TPOT)

---

## Phase 3: Deploy InferenceService

```bash
# Create serving namespace
kubectl create namespace ml-serving

# Deploy Katie 3B
kubectl apply -f 04-model-serving/kserve/inferenceservice-vllm.yaml -n ml-serving

# Watch rollout
kubectl get inferenceservice -n ml-serving -w
```

**The InferenceService does:**
1. Pulls model from S3 (`storageUri`)
2. Spins up vLLM container with the model loaded
3. Creates a Service + Ingress for inference
4. Monitors health via probes
5. Scales replicas based on KEDA triggers

---

## Phase 4: Configure Autoscaling (KEDA)

```bash
# Deploy KEDA ScaledObject (scales based on vLLM queue depth + GPU util)
kubectl apply -f 04-model-serving/kserve/keda-scaledobject.yaml -n ml-serving
```

**Scaling behavior:**
| Metric | Threshold | Action |
|--------|-----------|--------|
| `vllm:num_requests_waiting` > 5 | Queue building up | Scale out |
| `vllm:gpu_cache_usage_perc` > 80% | KV cache pressure | Scale out |
| All metrics below threshold for 5min | Idle | Scale in (min 1 replica) |

**Why not scale-to-zero for LLMs:** Loading a 3B model takes 30-60 seconds, 8B takes 2+ minutes. Unacceptable cold start. Keep `minReplicas: 1`.

---

## Phase 5: Test Inference

```bash
# Get the inference endpoint
ENDPOINT=$(kubectl get inferenceservice katie-3b -n ml-serving \
  -o jsonpath='{.status.url}')

# Test with OpenAI-compatible API (vLLM native format)
curl -X POST "${ENDPOINT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "katie-3b",
    "messages": [
      {"role": "system", "content": "You are a Kubernetes security expert."},
      {"role": "user", "content": "A pod has runAsNonRoot: false. Fix it."}
    ],
    "max_tokens": 500,
    "temperature": 0.3
  }'

# Health check
curl "${ENDPOINT}/health"

# Model info
curl "${ENDPOINT}/v1/models"

# Check latency
time curl -s -X POST "${ENDPOINT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"katie-3b","messages":[{"role":"user","content":"What is a NetworkPolicy?"}],"max_tokens":200}' > /dev/null
```

---

## Phase 6: Canary Rollout (A/B Testing)

Deploy a new model version alongside production:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: katie-3b
  namespace: ml-serving
spec:
  predictor:
    # Production: 90% traffic
    model:
      modelFormat:
        name: vllm
      runtime: vllm-runtime
      storageUri: "s3://ml-artifacts/models/katie-3b/v2.0/"
    canaryTrafficPercent: 10
  # Canary: 10% traffic
  canary:
    model:
      modelFormat:
        name: vllm
      runtime: vllm-runtime
      storageUri: "s3://ml-artifacts/models/katie-3b/v2.1/"
```

Monitor canary metrics → if good, promote to 100%.

---

## KServe vs SageMaker Endpoints

| Feature | KServe + vLLM (this playbook) | SageMaker Endpoints |
|---------|------------------------------|---------------------|
| Setup | kubectl apply | model.deploy() |
| Autoscaling | KEDA (custom metrics) | Built-in (invocations/instance) |
| Scale to zero | Possible but impractical for LLMs | Not for real-time endpoints |
| Cost (idle) | Node cost (Karpenter scales nodes) | ~$1.41/hr minimum |
| API format | OpenAI-compatible (native) | Custom (SageMaker SDK) |
| Canary | Built-in traffic split | Shadow/canary variants |
| Monitoring | Prometheus + Grafana | CloudWatch |
| Vendor lock-in | None | AWS |

---

## Success Criteria

- [ ] InferenceService running in `ml-serving` namespace
- [ ] vLLM responds to OpenAI-compatible API requests
- [ ] Health checks passing
- [ ] Response time < 5s for 3B model
- [ ] KEDA autoscaling configured
- [ ] Prometheus metrics visible (vLLM queue, GPU util)

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Model serving live | `09-deploy-model-cicd.md` |
| Need monitoring | `10-setup-drift-detection.md` |
| Want SageMaker instead | `16-sagemaker-endpoints.md` |
