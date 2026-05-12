#!/usr/bin/env bash
# train-eval-promote.sh — Submit training pipeline to KFP, wait for completion
# Usage: bash tools/train-eval-promote.sh --model katie-3b --data s3://bucket/corpus.jsonl
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
KFP_ENDPOINT="${KFP_ENDPOINT:-http://localhost:8887}"
PROMOTION_THRESHOLD=60

# Parse args
MODEL=""
DATA=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift 2 ;;
        --data) DATA="$2"; shift 2 ;;
        --endpoint) KFP_ENDPOINT="$2"; shift 2 ;;
        --threshold) PROMOTION_THRESHOLD="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

if [[ -z "$MODEL" || -z "$DATA" ]]; then
    echo "Usage: $0 --model <model-name> --data <s3-path-to-data>"
    echo ""
    echo "Options:"
    echo "  --endpoint  KFP API endpoint (default: http://localhost:8887)"
    echo "  --threshold Promotion threshold (default: 60)"
    exit 1
fi

echo "=== Train → Eval → Promote (via KFP) ==="
echo "Model: ${MODEL}"
echo "Data: ${DATA}"
echo "KFP endpoint: ${KFP_ENDPOINT}"
echo "Promotion threshold: ${PROMOTION_THRESHOLD}%"
echo ""

# Step 0: Local data validation (fast, before submitting to KFP)
echo "--- Step 0: Local Data Quality Check ---"
if [[ "$DATA" == s3://* ]]; then
    echo "Data is in S3 — KFP pipeline will validate in-cluster"
else
    python3 "${PACKAGE_DIR}/tools/validate-training-data.py" \
        --input "$DATA" \
        --check all \
        --strict
    echo "Data quality: PASS"
fi
echo ""

# Step 1: Submit KFP pipeline
echo "--- Step 1: Submitting KFP Pipeline ---"
VERSION="v$(date +%Y%m%d-%H%M%S)"

RUN_ID=$(python3 -c "
from kfp import Client
import sys

client = Client(host='${KFP_ENDPOINT}')
run = client.create_run_from_pipeline_func(
    pipeline_func=__import__('sys').path.insert(0, '${PACKAGE_DIR}/02-training-pipeline/kfp') or __import__('training_pipeline').training_pipeline,
    experiment_name='${MODEL}-training',
    run_name='${MODEL}-${VERSION}',
    arguments={
        'data_path': '${DATA}',
        'model_name': '${MODEL}',
        'model_version': '${VERSION}',
        'promotion_threshold': ${PROMOTION_THRESHOLD},
    },
)
print(run.run_id)
")

echo "Pipeline submitted: ${RUN_ID}"
echo "View at: ${KFP_ENDPOINT}/#/runs/details/${RUN_ID}"
echo ""

# Step 2: Wait for completion
echo "--- Step 2: Waiting for Pipeline Completion ---"
python3 -c "
from kfp import Client
import time
import sys

client = Client(host='${KFP_ENDPOINT}')
run_id = '${RUN_ID}'

while True:
    run = client.get_run(run_id)
    state = run.state
    print(f'  Status: {state}', flush=True)
    if state in ('SUCCEEDED', 'FAILED', 'SKIPPED', 'ERROR'):
        break
    time.sleep(30)

if state != 'SUCCEEDED':
    print(f'Pipeline failed: {state}')
    sys.exit(1)
print('Pipeline completed successfully')
"

echo ""
echo "=== Complete ==="
echo "Model ${MODEL} ${VERSION} trained and evaluated via KFP."
echo "Check KFP UI for metrics and artifacts."
