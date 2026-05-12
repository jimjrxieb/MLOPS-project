# 07-Monitoring

Model drift detection and observability dashboards.

## Contents

### drift-detection/
- `metrics-exporter.yaml` — K8s deployment for inference metrics collection
- `servicemonitor.yaml` — Prometheus ServiceMonitor for ML metrics
- `compare-eval.py` — Compare current eval scores against baseline

### dashboards/
- `mlops-dashboard.json` — Grafana dashboard (inference latency, request rate, eval trends)

## Metrics Collected

| Metric | Type | Description |
|--------|------|-------------|
| `ml_inference_latency_seconds` | Histogram | Time per inference request |
| `ml_inference_total` | Counter | Total inference requests by model version |
| `ml_inference_errors_total` | Counter | Failed inference requests |
| `ml_prompt_category` | Counter | Requests by domain (CKS/CKA/CKAD/CNPA/OPS) |
| `ml_eval_score` | Gauge | Latest eval benchmark score |
| `ml_data_drift_score` | Gauge | Chi-squared drift detection score |

## Related

- Playbook `10-setup-drift-detection.md`
