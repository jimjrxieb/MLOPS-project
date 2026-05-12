# Playbook 11 — Optimize ML Costs

> Right-size GPU nodes, schedule training off-peak, minimize serving costs.
> **When:** After ML infrastructure is running (Playbooks 08, 09)
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] ML workloads running on K8s
- [ ] Cost data available (AWS Cost Explorer or kubectl top)
- [ ] Karpenter deployed (Playbook 04-OPTIMIZE/03)

---

## Phase 1: Audit Current ML Spend

```bash
# Check GPU node utilization
kubectl top nodes -l nvidia.com/gpu.present=true

# Check ML pod resource usage vs requests
kubectl top pods -n ml-serving
kubectl top pods -n mlops

# Check for idle GPU allocation
kubectl describe nodes -l nvidia.com/gpu.present=true | grep -A5 "Allocated resources"
```

**Common waste patterns:**
| Pattern | Waste | Fix |
|---------|-------|-----|
| GPU allocated 24/7, training runs 2h/week | ~97% idle GPU | Spot + scale-to-zero |
| 8B model on GPU, only serves 10 req/hr | Over-provisioned | CPU serving or smaller quant |
| Training on on-demand instances | 3x spot price | Spot with checkpointing |
| Embedding model on GPU | Unnecessary | CPU is fine for nomic-embed-text |

---

## Phase 2: Karpenter NodePools for ML

```yaml
# Separate NodePool for training (spot, scale-to-zero)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g6.xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m   # Scale down fast when training completes
  limits:
    gpu: 2
```

```yaml
# Separate NodePool for serving (on-demand, always-on for 3B)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-serving
spec:
  template:
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.2xlarge", "m6i.2xlarge"]  # CPU-only for 3B
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30m
```

---

## Phase 3: Training Scheduling

Schedule training during off-peak hours for lower spot prices:

```yaml
# CronJob for nightly training
apiVersion: batch/v1
kind: CronJob
metadata:
  name: nightly-training
  namespace: mlops
spec:
  schedule: "0 2 * * *"   # 2 AM UTC
  jobTemplate:
    spec:
      template:
        spec:
          tolerations:
            - key: nvidia.com/gpu
              operator: Exists
          containers:
            - name: trainer
              image: ghcr.io/your-org/ml-trainer:latest
              command: ["python3", "1-data-pipeline/train_v11.py"]
              resources:
                limits:
                  nvidia.com/gpu: 1
                  memory: "16Gi"
                requests:
                  cpu: "4"
                  memory: "12Gi"
          restartPolicy: OnFailure
```

---

## Phase 4: Serving Right-Sizing

```bash
# Profile actual serving memory usage
kubectl exec -n ml-serving deploy/katie-3b-predictor -- cat /proc/meminfo | head -5

# Check vLLM GPU cache usage (if low, model may fit on CPU)
curl http://katie-3b.ml-serving.svc.cluster.local/metrics | grep gpu_cache_usage

# Right-size the InferenceService resources
kubectl edit inferenceservice katie-3b -n ml-serving
```

**Model size guide:**
| Model | GGUF (Q4_K_M) | RAM Needed | GPU Needed? |
|-------|---------------|------------|-------------|
| 3B | ~2GB | ~6GB | No |
| 8B | ~5GB | ~10GB | Recommended |
| 13B | ~8GB | ~16GB | Yes |
| 70B | ~40GB | ~48GB | Yes (A100) |

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Costs optimized | `12-mlops-compliance-report.md` |
| Need more optimization | 04-OPTIMIZE package |
