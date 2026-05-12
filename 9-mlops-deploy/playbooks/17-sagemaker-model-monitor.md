# Playbook 17 — SageMaker Model Monitor

> Managed drift detection and model quality monitoring.
> **When:** Client serves models via SageMaker endpoints and needs automated monitoring
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] SageMaker endpoint deployed (Playbook 16)
- [ ] Data capture enabled on endpoint

---

## Phase 1: Enable Data Capture

Every inference request/response gets logged to S3 for analysis:

```python
from sagemaker.model_monitor import DataCaptureConfig

data_capture = DataCaptureConfig(
    enable_capture=True,
    sampling_percentage=100,              # Capture everything (adjust for high QPS)
    destination_s3_uri="s3://your-bucket/data-capture/",
    capture_options=["Input", "Output"],
)

# Apply to endpoint
predictor = model.deploy(
    instance_type="ml.g5.xlarge",
    data_capture_config=data_capture,
)
```

---

## Phase 2: Create Baseline (What "Normal" Looks Like)

```python
from sagemaker.model_monitor import DefaultModelMonitor

monitor = DefaultModelMonitor(
    role=role,
    instance_type="ml.m5.xlarge",
    instance_count=1,
)

# Generate baseline from training data statistics
monitor.suggest_baseline(
    baseline_dataset="s3://your-bucket/training-data/katie_v2_clean.jsonl",
    dataset_format={"json": {"header": False}},
    output_s3_uri="s3://your-bucket/baseline/",
)
```

---

## Phase 3: Schedule Monitoring

```python
from sagemaker.model_monitor import CronExpressionGenerator

monitor.create_monitoring_schedule(
    monitor_schedule_name="katie-quality-monitor",
    endpoint_input="katie-3b-prod",
    output_s3_uri="s3://your-bucket/monitoring-results/",
    schedule_cron_expression=CronExpressionGenerator.daily(),
    statistics=monitor.baseline_statistics(),
    constraints=monitor.suggested_constraints(),
)
```

**What it checks daily:**
- Input data drift (are queries changing from what the model was trained on?)
- Output quality (are responses degrading?)
- Missing values, data type changes
- Statistical distribution shifts

---

## Phase 4: Alerts

```python
# CloudWatch alarm on monitoring violations
import boto3

cw = boto3.client("cloudwatch")

cw.put_metric_alarm(
    AlarmName="katie-model-drift",
    MetricName="MonitoringScheduleViolationCount",
    Namespace="aws/sagemaker/Endpoints/data-metrics",
    Statistic="Sum",
    Period=86400,                          # Daily
    EvaluationPeriods=1,
    Threshold=1,
    ComparisonOperator="GreaterThanOrEqualToThreshold",
    AlarmActions=["arn:aws:sns:us-east-1:123456789:ml-alerts"],
    AlarmDescription="Katie model drift detected — review and consider retraining"
)
```

---

## Self-Hosted vs SageMaker Comparison

| Feature | Prometheus + compare-eval.py | SageMaker Model Monitor |
|---------|------------------------------|------------------------|
| Setup | Deploy ServiceMonitor + write rules | API call |
| Data capture | Custom (log to JSONL) | Built-in (S3 automatic) |
| Drift detection | Chi-squared in Python | Built-in statistical tests |
| Alerts | Grafana → PagerDuty | CloudWatch → SNS |
| Cost | Free (self-managed) | ~$0.10/hr per monitoring job |
| Customization | Full control | Limited to built-in checks |

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Monitoring running | `12-mlops-compliance-report.md` |
| Drift detected | Retrain via `14-sagemaker-training-jobs.md` |
