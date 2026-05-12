# Playbook 10 — Setup Drift Detection

> Monitor model performance in production via KServe + vLLM metrics. Detect data drift, model degradation, and trigger retraining.
> **When:** After model is serving via KServe (Playbook 08)
> **Time:** 3-4 hours

---

## Prerequisites

- [ ] KServe + vLLM serving live (Playbook 08)
- [ ] Prometheus deployed (or deploy via 02-CLUSTER-HARDEN)
- [ ] Eval benchmark baseline scores

---

## Phase 1: vLLM Metrics Collection

vLLM exposes Prometheus metrics natively. KServe + vLLM gives you these out of the box:

```
# Request metrics
vllm:num_requests_running          # Active requests
vllm:num_requests_waiting          # Queued requests
vllm:request_success_total         # Successful completions
vllm:request_failure_total         # Failed requests

# Latency metrics
vllm:e2e_request_latency_seconds   # End-to-end latency (histogram)
vllm:time_to_first_token_seconds   # TTFT (histogram)
vllm:time_per_output_token_seconds # TPOT (histogram)

# GPU metrics
vllm:gpu_cache_usage_perc          # KV cache utilization
vllm:cpu_cache_usage_perc          # CPU cache utilization

# Token metrics
vllm:prompt_tokens_total           # Input tokens processed
vllm:generation_tokens_total       # Output tokens generated
```

```bash
# Deploy ServiceMonitor for Prometheus scraping
kubectl apply -f 07-monitoring/drift-detection/servicemonitor.yaml -n ml-serving
```

---

## Phase 2: ServiceMonitor for vLLM

```yaml
# 07-monitoring/drift-detection/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: ml-serving
  labels:
    release: prometheus  # Match your Prometheus operator label
spec:
  selector:
    matchLabels:
      component: model-serving
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

---

## Phase 3: Data Drift Detection

Monitor input distribution shifts via a scheduled KFP pipeline:

```python
from kfp import dsl

@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["prometheus-api-client", "scipy"],
)
def check_data_drift(
    prometheus_url: str,
    training_dist: dict,
    drift_threshold: float,
) -> bool:
    """Query Prometheus for production request distribution, compare to training."""
    from prometheus_api_client import PrometheusConnect
    from scipy import stats

    prom = PrometheusConnect(url=prometheus_url)

    # Get request distribution over last 7 days
    # (Assumes your app labels requests by category)
    query = 'sum by (category) (increase(vllm:request_success_total{namespace="ml-serving"}[7d]))'
    results = prom.custom_query(query)

    production_dist = {}
    for r in results:
        category = r["metric"].get("category", "unknown")
        production_dist[category] = float(r["value"][1])

    # Normalize
    total = sum(production_dist.values()) or 1
    production_dist = {k: v / total for k, v in production_dist.items()}

    # Chi-squared test
    categories = sorted(set(list(training_dist.keys()) + list(production_dist.keys())))
    observed = [production_dist.get(c, 0) for c in categories]
    expected = [training_dist.get(c, 0) for c in categories]

    chi2, p_value = stats.chisquare(observed, expected)
    drifted = p_value < drift_threshold

    if drifted:
        print(f"DRIFT DETECTED (p={p_value:.4f})")
        print(f"Training: {training_dist}")
        print(f"Production: {production_dist}")

    return drifted
```

**Drift triggers:**
- Input category distribution shifts >15% from training
- Average prompt length changes >25%
- `vllm:request_failure_total` spikes
- `vllm:e2e_request_latency_seconds` p95 degrades

---

## Phase 4: Model Quality Monitoring

Run eval suite on a schedule against the production model:

```python
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["requests", "jsonlines"],
)
def check_model_quality(
    kserve_endpoint: str,
    eval_suite_path: str,
    baseline_score: float,
) -> bool:
    """Run eval suite against production model. Returns True if degraded."""
    import requests
    import jsonlines

    correct = 0
    total = 0

    with jsonlines.open(eval_suite_path) as reader:
        for example in reader:
            question = example["question"]
            expected = example["expected_answer"]

            response = requests.post(
                f"{kserve_endpoint}/v1/chat/completions",
                json={
                    "model": "katie-3b",
                    "messages": [{"role": "user", "content": question}],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
            )

            answer = response.json()["choices"][0]["message"]["content"]
            # Simple keyword match (real eval is more sophisticated)
            if any(kw in answer.lower() for kw in expected):
                correct += 1
            total += 1

    score = (correct / max(total, 1)) * 100
    degraded = score < (baseline_score - 10)  # Alert if >10% drop

    print(f"Eval score: {score:.1f}% (baseline: {baseline_score:.1f}%)")
    if degraded:
        print(f"MODEL DEGRADATION DETECTED")

    return degraded
```

**Alert thresholds:**
- Any category drops >10% from baseline → WARNING
- Any category drops below 50% → CRITICAL (retrain trigger)
- Weighted total drops below 55% → CRITICAL (rollback + retrain)

---

## Phase 5: Scheduled Monitoring Pipeline

```python
from kfp import Client

client = Client(host="http://kfp.mlops.svc:8888")

# Schedule daily drift check
client.create_recurring_run(
    experiment_id=experiment.experiment_id,
    job_name="daily-drift-check",
    pipeline_id=drift_pipeline.pipeline_id,
    cron_expression="0 6 * * *",  # 6am UTC daily
    parameters={
        "prometheus_url": "http://prometheus.monitoring.svc:9090",
        "kserve_endpoint": "http://katie-3b.ml-serving.svc.cluster.local",
    },
)

# Schedule weekly full eval
client.create_recurring_run(
    experiment_id=experiment.experiment_id,
    job_name="weekly-eval",
    pipeline_id=eval_pipeline.pipeline_id,
    cron_expression="0 2 * * 0",  # Sunday 2am UTC
)
```

---

## Phase 6: Grafana Dashboard

**Dashboard panels (Prometheus queries):**

```promql
# Request rate
rate(vllm:request_success_total{namespace="ml-serving"}[5m])

# P95 latency
histogram_quantile(0.95, rate(vllm:e2e_request_latency_seconds_bucket[5m]))

# Time to first token (P50)
histogram_quantile(0.50, rate(vllm:time_to_first_token_seconds_bucket[5m]))

# GPU cache utilization
vllm:gpu_cache_usage_perc{namespace="ml-serving"}

# Queue depth
vllm:num_requests_waiting{namespace="ml-serving"}

# Error rate
rate(vllm:request_failure_total{namespace="ml-serving"}[5m])
/ rate(vllm:request_success_total{namespace="ml-serving"}[5m])
```

---

## Phase 7: Automated Retraining Trigger

When drift or degradation is detected, trigger retraining via KFP:

```python
@dsl.pipeline(name="drift-response-pipeline")
def drift_response(drift_detected: bool, quality_degraded: bool):
    with dsl.If(quality_degraded == True):  # noqa: E712
        # Critical: rollback first, then retrain
        rollback_model(model_name="katie-3b")
        trigger_retrain(model_name="katie-3b")

    with dsl.If(drift_detected == True):  # noqa: E712
        # Non-critical: just schedule retraining
        trigger_retrain(model_name="katie-3b")
```

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Monitoring live | `11-optimize-ml-costs.md` |
| Drift detected | Trigger retrain via KFP pipeline |
| Want SageMaker monitoring | `17-sagemaker-model-monitor.md` |
