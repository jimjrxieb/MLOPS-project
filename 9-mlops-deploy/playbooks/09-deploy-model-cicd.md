# Playbook 09 — Deploy Model CI/CD

> Automate the full model lifecycle: data change → quality gate → KFP pipeline → eval → promote → KServe rollout.
> **When:** After training pipeline + eval + serving are working (Playbooks 05, 07, 08)
> **Time:** 3-4 hours

---

## Prerequisites

- [ ] KFP training pipeline working end-to-end (Playbook 05)
- [ ] Eval benchmarks configured (Playbook 07)
- [ ] KServe model serving deployed (Playbook 08)
- [ ] GitHub repo with Actions enabled

---

## Phase 1: Data Validation Workflow

Triggers on any push to training data directories:

```yaml
# .github/workflows/validate-training-data.yml
name: Validate Training Data
on:
  push:
    paths:
      - '1-data-pipeline/01-raw-data-lake/**'
      - '1-data-pipeline/00-processed/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: pip install jsonlines pandas

      - name: Run quality gates
        run: |
          python3 tools/validate-training-data.py \
            --input 1-data-pipeline/01-raw-data-lake/ \
            --check all \
            --report > validation-report.md

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: data-validation-report
          path: validation-report.md

      - name: Fail on quality issues
        run: |
          python3 tools/validate-training-data.py \
            --input 1-data-pipeline/01-raw-data-lake/ \
            --check all \
            --strict  # Exit 1 on any quality violation
```

---

## Phase 2: Train + Eval via KFP Pipeline

Triggers after data validation passes. Submits a KFP pipeline run instead of running training directly on the GHA runner.

```yaml
# .github/workflows/train-eval-promote.yml
name: Train → Eval → Promote (KFP)
on:
  workflow_run:
    workflows: ["Validate Training Data"]
    types: [completed]
    branches: [main]

jobs:
  trigger-pipeline:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install KFP SDK
        run: pip install kfp==2.12.0

      - name: Upload data to S3
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          aws s3 sync 1-data-pipeline/01-raw-data-lake/ \
            s3://ml-artifacts/training-data/ \
            --exclude "*.tmp"

      - name: Submit KFP Pipeline
        env:
          KFP_ENDPOINT: ${{ secrets.KFP_ENDPOINT }}
        run: |
          python3 -c "
          from kfp import Client
          client = Client(host='${KFP_ENDPOINT}')
          run = client.create_run_from_pipeline_func(
              pipeline_func=__import__('training_pipeline').training_pipeline,
              experiment_name='katie-3b-training',
              run_name='gha-${GITHUB_SHA::8}',
              arguments={
                  'data_path': 's3://ml-artifacts/training-data/corpus.jsonl',
                  'model_name': 'katie-3b',
                  'model_version': 'v${GITHUB_RUN_NUMBER}',
              },
          )
          print(f'Pipeline run: {run.run_id}')
          "

      - name: Wait for Pipeline Completion
        env:
          KFP_ENDPOINT: ${{ secrets.KFP_ENDPOINT }}
        run: |
          python3 -c "
          from kfp import Client
          import time
          client = Client(host='${KFP_ENDPOINT}')
          # Poll for completion (KFP handles the heavy lifting)
          run_id = '...'  # From previous step
          while True:
              run = client.get_run(run_id)
              if run.state in ('SUCCEEDED', 'FAILED', 'SKIPPED', 'ERROR'):
                  break
              time.sleep(30)
          if run.state != 'SUCCEEDED':
              raise SystemExit(f'Pipeline failed: {run.state}')
          "
```

**Key difference from old approach:** Training runs on GPU nodes via KFP, not on the GHA runner. GHA just triggers and monitors.

---

## Phase 3: KServe Model Rollout

After KFP pipeline promotes a model to S3, update KServe to serve it:

```yaml
# .github/workflows/model-rollout.yml
name: Model Rollout (KServe)
on:
  workflow_run:
    workflows: ["Train → Eval → Promote (KFP)"]
    types: [completed]

jobs:
  rollout:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Update InferenceService
        run: |
          # Update the storageUri to point to the new model version
          kubectl patch inferenceservice katie-3b -n ml-serving \
            --type='json' \
            -p='[{"op":"replace","path":"/spec/predictor/model/storageUri","value":"s3://ml-artifacts/models/katie-3b/v'${GITHUB_RUN_NUMBER}'/"}]'

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/katie-3b-predictor -n ml-serving --timeout=300s

      - name: Smoke test
        run: |
          ENDPOINT=$(kubectl get inferenceservice katie-3b -n ml-serving \
            -o jsonpath='{.status.url}')
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${ENDPOINT}/health")
          if [ "$STATUS" != "200" ]; then
            echo "Health check failed: $STATUS"
            exit 1
          fi
```

---

## Phase 4: Rollback Workflow

```yaml
# .github/workflows/model-rollback.yml
name: Model Rollback
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Model version to rollback to (e.g., v2.0)'
        required: true
      reason:
        description: 'Reason for rollback'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - name: Rollback KServe InferenceService
        run: |
          echo "Rolling back to ${{ inputs.version }}: ${{ inputs.reason }}"
          kubectl patch inferenceservice katie-3b -n ml-serving \
            --type='json' \
            -p='[{"op":"replace","path":"/spec/predictor/model/storageUri","value":"s3://ml-artifacts/models/katie-3b/${{ inputs.version }}/"}]'
          kubectl rollout status deployment/katie-3b-predictor -n ml-serving --timeout=300s
```

---

## CI/CD Flow Summary

```
Push to data branch
  → validate-training-data.yml (quality gate)
  → Upload data to S3
  → Submit KFP pipeline (train → eval → promote on GPU nodes)
  → IF pass: model uploaded to S3 → KServe InferenceService updated → smoke test
  → IF fail: GitHub issue opened with eval scores
```

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| CI/CD working | `10-setup-drift-detection.md` |
| Need cost optimization | `11-optimize-ml-costs.md` |
