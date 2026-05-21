# 07-Monitoring

Model drift detection and observability for production ML serving.

## Contents

### drift-detection/

| File | What it does |
|------|-------------|
| `servicemonitor.yaml` | Prometheus ServiceMonitor — scrapes vLLM inference metrics from the serving namespace |
| `compare-eval.py` | Compares current eval scores against a saved baseline; exits non-zero if degradation exceeds threshold |

## Metrics Collected

| Metric | Type | What it signals |
|--------|------|----------------|
| `ml_inference_latency_seconds` | Histogram | Serving degradation |
| `ml_inference_total` | Counter | Request volume by model version |
| `ml_inference_errors_total` | Counter | Error rate spikes |
| `ml_prompt_category` | Counter | Domain shift in production traffic |
| `ml_eval_score` | Gauge | Benchmark score trending down → retrain trigger |
| `ml_data_drift_score` | Gauge | Chi-squared drift score across input distribution |

## Usage

```bash
# Apply Prometheus ServiceMonitor
kubectl apply -f 07-monitoring/drift-detection/servicemonitor.yaml

# Compare latest eval scores against baseline (run after weekly-eval.yml)
python3 07-monitoring/drift-detection/compare-eval.py \
  --baseline 5-experiments/exp-015-beru-v1.7/metrics.json \
  --current 4-eval-clarify/3-results/beru/knowledge_brain/latest.json \
  --threshold 0.05
```

## Related

- `06-model-cicd/github-actions/weekly-eval.yml` — scheduled eval that feeds this
- `5-experiments/` — baseline metrics for comparison
