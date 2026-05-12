#!/usr/bin/env bash
# deploy-kubeflow.sh — Deploy standalone KFP (Kubeflow Pipelines) on Kubernetes
# Uses kustomize (official method — no Helm chart exists for KFP standalone)
# Usage: ./tools/deploy-kubeflow.sh [--namespace kubeflow] [--version 2.16.0]
set -euo pipefail

NAMESPACE="kubeflow"
PIPELINE_VERSION="2.16.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace) NAMESPACE="$2"; shift 2 ;;
        --version) PIPELINE_VERSION="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; echo "Usage: $0 [--namespace kubeflow] [--version 2.16.0]"; exit 1 ;;
    esac
done

KUSTOMIZE_BASE="github.com/kubeflow/pipelines/manifests/kustomize"

echo "=== Deploying KFP (Kubeflow Pipelines) Standalone ==="
echo "Version:   ${PIPELINE_VERSION}"
echo "Namespace: ${NAMESPACE} (KFP kustomize creates this automatically)"
echo ""

# --- Step 1: Deploy cluster-scoped resources (CRDs) ---
echo "--- Step 1: Applying cluster-scoped resources (CRDs) ---"
kubectl apply -k "${KUSTOMIZE_BASE}/cluster-scoped-resources?ref=${PIPELINE_VERSION}"

echo "Waiting for CRDs to be established..."
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io 2>/dev/null || true

# --- Step 2: Deploy KFP platform-agnostic (standalone, no Istio) ---
echo ""
echo "--- Step 2: Deploying KFP standalone (platform-agnostic) ---"
echo "This includes: API server, UI, Argo Workflows, MySQL, MinIO"
kubectl apply -k "${KUSTOMIZE_BASE}/env/platform-agnostic?ref=${PIPELINE_VERSION}"

# --- Step 3: Wait for pods ---
echo ""
echo "--- Step 3: Waiting for pods to be ready ---"
echo "(This can take 2-5 minutes on first deploy...)"
kubectl -n "$NAMESPACE" wait --for condition=ready pod -l app=ml-pipeline --timeout=300s 2>/dev/null || {
    echo "Warning: ml-pipeline pod not ready yet. Check: kubectl get pods -n ${NAMESPACE}"
}

echo ""
echo "=== KFP Deployed ==="
echo ""

# --- Verify ---
echo "--- Verification ---"
kubectl get pods -n "$NAMESPACE" 2>/dev/null || true
echo ""
kubectl get svc -n "$NAMESPACE" 2>/dev/null || true

echo ""
echo "--- Access ---"
echo "UI:  kubectl port-forward svc/ml-pipeline-ui -n ${NAMESPACE} 8888:80"
echo "     → http://localhost:8888"
echo "API: kubectl port-forward svc/ml-pipeline -n ${NAMESPACE} 8887:8888"
echo "     → http://localhost:8887/apis/v2beta1/healthz"
echo ""
echo "--- Python SDK ---"
echo "pip install kfp==${PIPELINE_VERSION}"
echo ""
echo "--- Next Steps ---"
echo "1. Access KFP UI at http://localhost:8888"
echo "2. Deploy KServe: ./tools/deploy-kserve.sh"
echo "3. Submit a pipeline: python3 02-training-pipeline/kfp/training_pipeline.py --submit"
