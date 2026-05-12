#!/bin/bash
# JADE Training Cluster Setup
#
# Creates a Kind cluster with intentionally vulnerable workloads
# for jsa-infrasec training data collection.
#
# Usage:
#   ./setup_training_cluster.sh           # Create cluster and deploy
#   ./setup_training_cluster.sh --destroy # Tear down cluster
#   ./setup_training_cluster.sh --status  # Check cluster status

set -e

# Configuration
CLUSTER_NAME="${JADE_CLUSTER_NAME:-jade-training}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BROKEN_APP_DIR="${SCRIPT_DIR}/../deployments/training/broken-app"
TRAINING_DATA_DIR="${HOME}/GP-Copilot/training-data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check for kind
    if ! command -v kind &> /dev/null; then
        log_error "kind is not installed. Install from: https://kind.sigs.k8s.io/"
        exit 1
    fi

    # Check for kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check for docker
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed"
        exit 1
    fi

    # Check if docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        exit 1
    fi

    log_info "All prerequisites met"
}

create_cluster() {
    log_info "Checking for existing cluster..."

    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_warn "Cluster '${CLUSTER_NAME}' already exists"
        log_info "Use --destroy to remove it first, or continue with existing cluster"
        return 0
    fi

    log_info "Creating Kind cluster '${CLUSTER_NAME}'..."

    # Create cluster with config
    cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      extraArgs:
        # Disable admission plugins that would block our vulnerable pods
        enable-admission-plugins: "NodeRestriction"
- role: worker
EOF

    log_info "Cluster created successfully"
}

set_context() {
    log_info "Setting kubectl context..."
    kubectl config use-context "kind-${CLUSTER_NAME}"

    # Verify connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Failed to connect to cluster"
        exit 1
    fi

    log_info "Connected to cluster"
}

deploy_broken_app() {
    log_info "Deploying intentionally vulnerable application..."

    if [ ! -d "${BROKEN_APP_DIR}" ]; then
        log_error "Broken app manifests not found at: ${BROKEN_APP_DIR}"
        exit 1
    fi

    # Apply manifests
    kubectl apply -f "${BROKEN_APP_DIR}/namespace.yaml"
    kubectl apply -f "${BROKEN_APP_DIR}/configmap.yaml"
    kubectl apply -f "${BROKEN_APP_DIR}/service.yaml"
    kubectl apply -f "${BROKEN_APP_DIR}/deployment.yaml"

    log_info "Vulnerable application deployed"

    # Wait for pods (they might fail due to security issues, which is expected)
    log_info "Waiting for pods (may show errors - this is expected)..."
    kubectl wait --for=condition=ready pod -l app=vulnerable-app -n broken-app --timeout=30s 2>/dev/null || true

    log_info "Deployment complete (pods may be in error state intentionally)"
}

setup_training_dir() {
    log_info "Setting up training data directory..."

    mkdir -p "${TRAINING_DATA_DIR}"

    # Create empty log files if they don't exist
    touch "${TRAINING_DATA_DIR}/fix-attempts.jsonl"

    log_info "Training data will be written to: ${TRAINING_DATA_DIR}"
}

print_status() {
    log_info "Cluster Status:"
    echo ""

    # Cluster info
    echo "=== Cluster ==="
    kubectl cluster-info
    echo ""

    # Nodes
    echo "=== Nodes ==="
    kubectl get nodes
    echo ""

    # Namespaces
    echo "=== Namespaces ==="
    kubectl get namespaces
    echo ""

    # Broken app pods
    echo "=== Broken App Pods ==="
    kubectl get pods -n broken-app -o wide 2>/dev/null || echo "Namespace not found"
    echo ""

    # Events (last 10)
    echo "=== Recent Events (broken-app) ==="
    kubectl get events -n broken-app --sort-by='.lastTimestamp' 2>/dev/null | tail -10 || echo "No events"
}

destroy_cluster() {
    log_warn "Destroying cluster '${CLUSTER_NAME}'..."

    if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_warn "Cluster '${CLUSTER_NAME}' does not exist"
        return 0
    fi

    kind delete cluster --name "${CLUSTER_NAME}"
    log_info "Cluster destroyed"
}

run_scanners() {
    log_info "Running security scanners on broken-app..."

    # Check for scanners
    local has_scanner=false

    if command -v checkov &> /dev/null; then
        log_info "Running Checkov..."
        checkov -d "${BROKEN_APP_DIR}" --quiet --compact || true
        has_scanner=true
    fi

    if command -v trivy &> /dev/null; then
        log_info "Running Trivy..."
        trivy config "${BROKEN_APP_DIR}" --severity HIGH,CRITICAL || true
        has_scanner=true
    fi

    if command -v polaris &> /dev/null; then
        log_info "Running Polaris..."
        polaris audit --audit-path "${BROKEN_APP_DIR}" --format pretty || true
        has_scanner=true
    fi

    if [ "$has_scanner" = false ]; then
        log_warn "No security scanners found. Install checkov, trivy, or polaris to scan."
        log_info "Install with:"
        log_info "  pip install checkov"
        log_info "  brew install trivy"
        log_info "  brew install fairwindsops/tap/polaris"
    fi
}

show_help() {
    cat <<EOF
JADE Training Cluster Setup

Usage: $(basename "$0") [OPTIONS]

Options:
    --create      Create cluster and deploy (default)
    --destroy     Destroy the cluster
    --status      Show cluster status
    --scan        Run security scanners
    --help        Show this help

Environment Variables:
    JADE_CLUSTER_NAME   Cluster name (default: jade-training)

Examples:
    # Full setup
    ./setup_training_cluster.sh

    # Check status
    ./setup_training_cluster.sh --status

    # Run scanners
    ./setup_training_cluster.sh --scan

    # Clean up
    ./setup_training_cluster.sh --destroy
EOF
}

# Main
main() {
    case "${1:-}" in
        --destroy)
            destroy_cluster
            ;;
        --status)
            set_context
            print_status
            ;;
        --scan)
            run_scanners
            ;;
        --help|-h)
            show_help
            ;;
        --create|"")
            check_prerequisites
            create_cluster
            set_context
            setup_training_dir
            deploy_broken_app
            echo ""
            print_status
            echo ""
            log_info "Training cluster ready!"
            log_info ""
            log_info "Next steps:"
            log_info "  1. Deploy jsa-infrasec to scan the cluster"
            log_info "  2. Run: ./setup_training_cluster.sh --scan"
            log_info "  3. Fix attempts will be logged to: ${TRAINING_DATA_DIR}"
            log_info ""
            log_info "To tear down: ./setup_training_cluster.sh --destroy"
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
