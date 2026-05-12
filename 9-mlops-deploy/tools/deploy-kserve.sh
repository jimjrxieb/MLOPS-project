#!/usr/bin/env bash
# deploy-kserve.sh — Deploy KServe + vLLM ServingRuntime + KEDA on Kubernetes
# Usage: bash tools/deploy-kserve.sh [--namespace kserve]
set -euo pipefail

NAMESPACE="kserve"
SERVING_NS="ml-serving"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace) NAMESPACE="$2"; shift 2 ;;
        --serving-namespace) SERVING_NS="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

echo "=== Deploying KServe + vLLM ==="
echo "KServe namespace: ${NAMESPACE}"
echo "Serving namespace: ${SERVING_NS}"
echo ""

# --- Step 1: Install KEDA (autoscaling) ---
echo "--- Installing KEDA ---"
helm repo add kedacore https://kedacore.github.io/charts 2>/dev/null || true
helm repo update
kubectl create namespace keda --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install keda kedacore/keda \
  --namespace keda \
  --wait \
  --timeout 5m
echo "KEDA installed."
echo ""

# --- Step 2: Install KServe ---
echo "--- Installing KServe ---"
helm repo add kserve https://kserve.github.io/charts 2>/dev/null || true
helm repo update
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install kserve kserve/kserve \
  --namespace "$NAMESPACE" \
  --values "${PACKAGE_DIR}/01-kubeflow-platform/manifests/kserve-values.yaml" \
  --wait \
  --timeout 10m
echo "KServe installed."
echo ""

# --- Step 3: Deploy vLLM ServingRuntime ---
echo "--- Deploying vLLM ServingRuntime ---"
kubectl apply -f "${PACKAGE_DIR}/04-model-serving/kserve/servingruntime-vllm.yaml"
echo "vLLM runtime registered."
echo ""

# --- Step 4: Create serving namespace ---
echo "--- Creating serving namespace ---"
kubectl create namespace "$SERVING_NS" --dry-run=client -o yaml | kubectl apply -f -
echo ""

echo "=== KServe + vLLM Deployed ==="
echo ""
echo "--- Verification ---"
kubectl get pods -n "$NAMESPACE"
kubectl get clusterservingruntime
echo ""

echo "--- Next Steps ---"
echo "1. Deploy a model:"
echo "   kubectl apply -f 04-model-serving/kserve/inferenceservice-vllm.yaml -n ${SERVING_NS}"
echo ""
echo "2. Configure autoscaling:"
echo "   kubectl apply -f 04-model-serving/kserve/keda-scaledobject.yaml -n ${SERVING_NS}"
echo ""
echo "3. Test inference:"
echo "   ENDPOINT=\$(kubectl get inferenceservice katie-3b -n ${SERVING_NS} -o jsonpath='{.status.url}')"
echo "   curl \${ENDPOINT}/v1/models"
