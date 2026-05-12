#!/usr/bin/env bash
# run-ml-audit.sh — Assess current MLOps maturity
# Usage: bash tools/run-ml-audit.sh [--target /path/to/ml-project]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${PACKAGE_DIR}/outputs"
mkdir -p "$OUTPUT_DIR"

TARGET="${1:-.}"
REPORT="${OUTPUT_DIR}/maturity-assessment-$(date +%Y%m%d).md"

echo "=== MLOps Maturity Assessment ==="
echo "Target: ${TARGET}"
echo "Report: ${REPORT}"
echo ""

cat > "$REPORT" << 'HEADER'
# MLOps Maturity Assessment

Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

## Infrastructure Inventory
HEADER

echo "## Infrastructure Inventory" >> "$REPORT"
echo "" >> "$REPORT"

# Check for ML namespaces
echo "### Kubernetes ML Infrastructure" >> "$REPORT"
echo '```' >> "$REPORT"
if command -v kubectl &>/dev/null; then
    echo "--- Namespaces ---" >> "$REPORT"
    kubectl get namespaces 2>/dev/null | grep -iE 'ml|model|train|serving|mlflow|kubeflow|ollama' >> "$REPORT" || echo "No ML-related namespaces found" >> "$REPORT"

    echo "" >> "$REPORT"
    echo "--- GPU Nodes ---" >> "$REPORT"
    kubectl get nodes -l nvidia.com/gpu.present=true -o wide 2>/dev/null >> "$REPORT" || echo "No GPU nodes found" >> "$REPORT"

    echo "" >> "$REPORT"
    echo "--- ML Pods ---" >> "$REPORT"
    kubectl get pods --all-namespaces 2>/dev/null | grep -iE 'ollama|vllm|triton|tgi|seldon|mlflow|wandb' >> "$REPORT" || echo "No ML serving pods found" >> "$REPORT"
else
    echo "kubectl not available — skipping cluster checks" >> "$REPORT"
fi
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# Check for training scripts
echo "### Training Scripts" >> "$REPORT"
echo '```' >> "$REPORT"
find "$TARGET" -name "*.py" -path "*/train*" -o -name "*.py" -path "*/fine*tune*" 2>/dev/null | head -20 >> "$REPORT" || echo "None found" >> "$REPORT"
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# Check for model files
echo "### Model Files" >> "$REPORT"
echo '```' >> "$REPORT"
find "$TARGET" -name "*.gguf" -o -name "*.safetensors" -o -name "*.bin" -o -name "Modelfile*" 2>/dev/null | head -20 >> "$REPORT" || echo "None found" >> "$REPORT"
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# Check for experiment tracking
echo "### Experiment Tracking" >> "$REPORT"
echo '```' >> "$REPORT"
if [ -d "$TARGET/mlruns" ]; then
    echo "MLflow local tracking found: $TARGET/mlruns" >> "$REPORT"
elif command -v mlflow &>/dev/null; then
    echo "MLflow CLI available" >> "$REPORT"
else
    echo "No experiment tracking detected" >> "$REPORT"
fi
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# Check for data quality
echo "### Data Quality" >> "$REPORT"
echo '```' >> "$REPORT"
find "$TARGET" -name "*.jsonl" -path "*/train*" -o -name "*.jsonl" -path "*/data*" 2>/dev/null | head -10 >> "$REPORT" || echo "No training data found" >> "$REPORT"
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# Maturity scoring template
cat >> "$REPORT" << 'SCORING'

---

## Maturity Scoring (Manual — fill in after review)

| Dimension | Score (0-4) | Notes |
|-----------|-------------|-------|
| Data Management | | |
| Experiment Tracking | | |
| Training Pipeline | | |
| Evaluation | | |
| Model Registry | | |
| Serving | | |
| Monitoring | | |
| CI/CD | | |
| **Average** | | |

---

## Recommendations

| Priority | Gap | Playbook | Effort |
|----------|-----|----------|--------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

SCORING

echo ""
echo "Assessment written to: ${REPORT}"
echo "Fill in maturity scores manually after reviewing the inventory."
