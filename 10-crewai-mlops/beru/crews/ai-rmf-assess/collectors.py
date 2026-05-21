"""
NIST AI RMF 1.0 evidence collectors — filesystem + kubectl + AWS CLI.

Focuses on what can be verified without process interviews:
- AI system deployment security posture (kubectl/AWS)
- Existence of required artifacts (filesystem checks)
- Technical control implementation signals (code grep, config checks)

API-assessable subcategories:
  GOVERN-5.1: HITL enforcement code signals
  GOVERN-6.1: AI system inventory / model registry
  MEASURE-2.5: Red-team / eval artifacts (dated test result files)
  MEASURE-2.6: Adversarial testing artifacts (garak, pyrit)
  MANAGE-4.1: AI incident log existence

Process-only subcategories (28 of 52):
  Most GOVERN-1.x through GOVERN-2.x, all MAP-1.x through MAP-3.x and MAP-5.x,
  MANAGE-1.x through MANAGE-3.x — require document review and stakeholder interviews.
"""

import json
import os
import subprocess
from datetime import datetime, timezone


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _kubectl(args: list) -> dict:
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        return {"skipped": "kubectl not installed or not in PATH"}
    if result.returncode != 0:
        err = result.stderr.strip()
        if "no configuration has been provided" in err or "kubeconfig" in err.lower():
            return {"skipped": "kubeconfig not configured"}
        return {"error": err}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def _aws(args: list) -> dict:
    try:
        result = subprocess.run(
            ["aws"] + args + ["--output", "json"],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        return {"skipped": "AWS CLI not installed"}
    if result.returncode != 0:
        err = result.stderr.strip()
        if "Unable to locate credentials" in err or "NoCredentialsError" in err:
            return {"skipped": "AWS credentials not configured"}
        return {"error": err}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def _shell(cmd: str) -> str:
    """Run a shell command and return stdout, or empty string on any error."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── GOVERN-1.1, GOVERN-6.1: AI System Inventory ───────────────────────────────

def collect_ai_system_inventory() -> dict:
    """
    Check for AI system inventory artifacts and model registry entries.

    Covers: GOVERN-1.1 (AI risk policies — existence of inventory signals policy
    awareness), GOVERN-6.1 (AI system inventory — registered AI systems).
    """
    # Check for inventory file in current directory tree
    inventory_raw = _shell(
        "find . -name 'ai-inventory*' -o -name '*ai-register*' -o -name '*model-inventory*' 2>/dev/null"
    )
    inventory_paths = [p for p in inventory_raw.splitlines() if p.strip()]
    inventory_file_found = bool(inventory_paths)
    inventory_path = inventory_paths[0] if inventory_paths else ""

    # Check GP-MODEL-OPS model registry for registered model YAML/JSON entries
    registry_raw = _shell(
        "find . -path '*/model-registry/*' \\( -name '*.yaml' -o -name '*.json' \\) 2>/dev/null | head -20"
    )
    registry_entries = [p for p in registry_raw.splitlines() if p.strip()]
    model_registry_entries = len(registry_entries)

    # Check for model cards
    model_cards_raw = _shell(
        "find . \\( -name 'model-card*' -o -name '*modelcard*' \\) 2>/dev/null | head -10"
    )
    model_card_paths = [p for p in model_cards_raw.splitlines() if p.strip()]
    model_cards_found = len(model_card_paths)

    return {
        "inventory_file_found": inventory_file_found,
        "inventory_path": inventory_path,
        "model_registry_entries": model_registry_entries,
        "model_cards_found": model_cards_found,
        "available": True,
    }


# ── GOVERN-5.1: HITL Enforcement ──────────────────────────────────────────────

def collect_hitl_enforcement() -> dict:
    """
    Search for human-in-the-loop enforcement patterns in Python source.

    Covers: GOVERN-5.1 — organizational teams in place to implement, assess,
    and inform AI risk decisions with HITL enforcement as the primary control.
    """
    # Search for HITL enforcement patterns in Python source
    hitl_raw = _shell(
        "grep -r 'B_rank\\|S_rank\\|hitl\\|human.*review\\|escalate' src/ "
        "--include='*.py' -l 2>/dev/null"
    )
    hitl_files = [p for p in hitl_raw.splitlines() if p.strip()]
    hitl_code_found = bool(hitl_files)

    # Check for rank gating logic anywhere in the project
    rank_gating_raw = _shell(
        "grep -r 'rank.*[BS]\\|[BS].*rank\\|require.*human\\|block.*auto' . "
        "--include='*.py' -l 2>/dev/null | head -10"
    )
    rank_gating_files = [p for p in rank_gating_raw.splitlines() if p.strip()]
    rank_gating_found = bool(rank_gating_files)

    # Check for max authority / C-rank boundary in Python or YAML
    max_rank_raw = _shell(
        "grep -r 'C.rank\\|c_rank\\|max_authority' . "
        "--include='*.py' --include='*.yaml' -l 2>/dev/null"
    )
    max_rank_files = [p for p in max_rank_raw.splitlines() if p.strip()]
    max_rank_defined = "C-rank" if max_rank_files else "not found"

    return {
        "hitl_code_found": hitl_code_found,
        "hitl_files": hitl_files[:10],
        "rank_gating_found": rank_gating_found,
        "max_rank_defined": max_rank_defined,
        "available": True,
    }


# ── MEASURE-2.5, MEASURE-2.6: Red-Team Artifacts ─────────────────────────────

def collect_red_team_artifacts() -> dict:
    """
    Check for red-team, adversarial testing, and evaluation result artifacts.

    Covers: MEASURE-2.5 (AI risk and impacts from testing evaluated — evidence
    of red-team runs), MEASURE-2.6 (AI risks tracked using established metrics —
    adversarial testing artifacts demonstrate metric collection).
    """
    # Check for garak output files
    garak_raw = _shell(
        "find . \\( -name 'garak*.json' -o -name 'garak*.html' \\) 2>/dev/null"
    )
    garak_paths = [p for p in garak_raw.splitlines() if p.strip()]
    garak_results_found = bool(garak_paths)

    # Check for PyRIT results
    pyrit_raw = _shell(
        "find . \\( -name 'pyrit*' -o -path '*/red-team*' -name '*.json' \\) 2>/dev/null"
    )
    pyrit_paths = [p for p in pyrit_raw.splitlines() if p.strip()]
    pyrit_results_found = bool(pyrit_paths)

    # Check for eval / benchmark result files
    eval_raw = _shell(
        "find . \\( -path '*/eval*' -name '*.json' -o -path '*/benchmark*' -name '*.json' \\) "
        "2>/dev/null | head -20"
    )
    eval_paths = [p for p in eval_raw.splitlines() if p.strip()]
    eval_artifacts_found = len(eval_paths)

    # Check MEASURE-2.5 evidence directory
    measure_raw = _shell(
        "find . \\( -path '*/MEASURE-2*' -name '*.json' -o -path '*/MEASURE-2*' -name '*.html' \\) "
        "2>/dev/null"
    )
    measure_paths = [p for p in measure_raw.splitlines() if p.strip()]

    # Compute days since last red-team artifact across all found artifact paths
    all_artifact_paths = garak_paths + pyrit_paths + eval_paths + measure_paths
    days_since_last_redteam = None
    if all_artifact_paths:
        most_recent_mtime = None
        for path in all_artifact_paths:
            try:
                mtime = os.path.getmtime(path)
                if most_recent_mtime is None or mtime > most_recent_mtime:
                    most_recent_mtime = mtime
            except OSError:
                continue
        if most_recent_mtime is not None:
            now = datetime.now(timezone.utc).timestamp()
            days_since_last_redteam = int((now - most_recent_mtime) / 86400)

    # Classify coverage cadence
    if days_since_last_redteam is None:
        redteam_coverage = "No artifacts found"
    elif days_since_last_redteam < 30:
        redteam_coverage = "< 30 days"
    elif days_since_last_redteam <= 90:
        redteam_coverage = "30-90 days"
    else:
        redteam_coverage = "> 90 days"

    return {
        "garak_results_found": garak_results_found,
        "pyrit_results_found": pyrit_results_found,
        "eval_artifacts_found": eval_artifacts_found,
        "days_since_last_redteam": days_since_last_redteam,
        "redteam_coverage": redteam_coverage,
        "available": True,
    }


# ── MANAGE-4.1: AI Incident Log ───────────────────────────────────────────────

def collect_ai_incident_log() -> dict:
    """
    Check for AI incident records and incident response procedure documents.

    Covers: MANAGE-4.1 — post-deployment AI risk and benefits monitored and
    documented, including incident tracking.
    """
    # Check for AI incident record files
    incident_raw = _shell(
        "find . \\( -name 'AI-INC*' -o -path '*/MANAGE-4.1*' -name '*.json' \\) 2>/dev/null"
    )
    incident_paths = [p for p in incident_raw.splitlines() if p.strip()]

    # Check for incident response procedure documents
    ir_proc_raw = _shell(
        "find . \\( -name '*incident*response*' -o -name '*ir-playbook*' \\) "
        "-name '*.md' 2>/dev/null | head -5"
    )
    ir_proc_paths = [p for p in ir_proc_raw.splitlines() if p.strip()]
    incident_procedure_found = bool(ir_proc_paths)

    # Count open vs closed incidents by inspecting JSON incident files
    total_incidents_logged = len(incident_paths)
    open_incidents = 0
    for path in incident_paths:
        try:
            with open(path) as fh:
                content = fh.read()
            if '"resolved_at": null' in content or "'resolved_at': None" in content:
                open_incidents += 1
        except OSError:
            continue

    incident_log_path = incident_paths[0] if incident_paths else ""

    return {
        "incident_procedure_found": incident_procedure_found,
        "total_incidents_logged": total_incidents_logged,
        "open_incidents": open_incidents,
        "incident_log_path": incident_log_path,
        "available": True,
    }


# ── MEASURE-2.6, MAP-5.2: Monitoring Coverage ─────────────────────────────────

def collect_monitoring_coverage() -> dict:
    """
    Check for AI workload monitoring infrastructure via kubectl and filesystem.

    Covers: MEASURE-2.6 (AI risks tracked via monitoring metrics),
    MAP-5.2 (practices in place to monitor AI risks — monitoring infrastructure
    existence is an observable proxy signal).
    """
    # Prometheus
    prom_pods = _kubectl(["get", "pods", "-A", "-l", "app=prometheus", "-o", "json"])
    prometheus_found = False
    if "skipped" not in prom_pods and "error" not in prom_pods:
        prometheus_found = bool(prom_pods.get("items"))

    # Grafana
    grafana_pods = _kubectl(["get", "pods", "-A", "-l", "app=grafana", "-o", "json"])
    grafana_found = False
    if "skipped" not in grafana_pods and "error" not in grafana_pods:
        grafana_found = bool(grafana_pods.get("items"))

    # Falco (runtime anomaly detection covers MANAGE-4.1 proxy)
    falco_pods = _kubectl(["get", "pods", "-A", "-l", "app=falco", "-o", "json"])
    falco_found = False
    if "skipped" not in falco_pods and "error" not in falco_pods:
        falco_found = bool(falco_pods.get("items"))
    if not falco_found:
        # Try namespace-based lookup
        falco_ns_pods = _kubectl(["get", "pods", "-n", "falco", "-o", "json"])
        if "skipped" not in falco_ns_pods and "error" not in falco_ns_pods:
            falco_found = bool(falco_ns_pods.get("items"))

    # MLflow experiment tracking (MEASURE-2.5 proxy)
    mlflow_raw = _shell("find . -name 'mlruns' -type d 2>/dev/null | head -3")
    mlflow_paths = [p for p in mlflow_raw.splitlines() if p.strip()]
    mlflow_found = bool(mlflow_paths)

    # AI-specific monitoring deployments (drift, eval, observe)
    all_deployments = _kubectl(["get", "deployments", "-A", "-o", "json"])
    ai_monitoring_deployments = []
    if "skipped" not in all_deployments and "error" not in all_deployments:
        for deploy in all_deployments.get("items", []):
            name = deploy.get("metadata", {}).get("name", "").lower()
            if any(kw in name for kw in ["monitor", "observe", "drift", "eval"]):
                ai_monitoring_deployments.append(
                    deploy.get("metadata", {}).get("name", "")
                )

    return {
        "prometheus_found": prometheus_found,
        "grafana_found": grafana_found,
        "falco_found": falco_found,
        "mlflow_found": mlflow_found,
        "ai_monitoring_deployments": ai_monitoring_deployments,
        "available": True,
    }


# ── GOVERN-5.1, MEASURE-2.6: AI Workload Security ────────────────────────────

def collect_ai_workload_security() -> dict:
    """
    Check AI pod security posture via kubectl.

    Covers: GOVERN-5.1 (AI systems are subject to access control — security
    context on AI pods is an observable proxy), MEASURE-2.6 (AI risk metrics —
    exposed AI endpoints represent measurable risk).
    """
    all_pods = _kubectl(["get", "pods", "-A", "-o", "json"])

    ai_pods_found = []
    pods_without_security_context = 0
    gpu_pods_without_limits = 0

    # AI workload signals: GPU resource requests or AI-related image names
    ai_image_keywords = [
        "pytorch", "tensorflow", "triton", "ollama", "vllm", "llm",
        "transformers", "inference", "sagemaker", "huggingface",
    ]

    if "skipped" not in all_pods and "error" not in all_pods:
        for pod in all_pods.get("items", []):
            ns = pod.get("metadata", {}).get("namespace", "")
            if ns.startswith("kube-"):
                continue

            spec = pod.get("spec", {})
            containers = spec.get("containers", []) + spec.get("initContainers", [])
            is_ai_pod = False

            for container in containers:
                image = container.get("image", "").lower()
                if any(kw in image for kw in ai_image_keywords):
                    is_ai_pod = True

                # GPU resource request detection
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})
                has_gpu_request = any("gpu" in k.lower() or "nvidia" in k.lower()
                                      for k in list(requests.keys()) + list(limits.keys()))
                if has_gpu_request:
                    is_ai_pod = True

            if is_ai_pod:
                pod_name = pod.get("metadata", {}).get("name", "")
                ai_pods_found.append({"name": pod_name, "namespace": ns})

                # Security context check
                has_security_context = False
                for container in containers:
                    c_sec = container.get("securityContext", {})
                    if c_sec.get("runAsNonRoot") or c_sec.get("readOnlyRootFilesystem"):
                        has_security_context = True
                        break
                if not has_security_context:
                    pods_without_security_context += 1

                # GPU pods without resource limits
                for container in containers:
                    resources = container.get("resources", {})
                    limits = resources.get("limits", {})
                    requests = resources.get("requests", {})
                    has_gpu = any(
                        "gpu" in k.lower() or "nvidia" in k.lower()
                        for k in list(requests.keys()) + list(limits.keys())
                    )
                    if has_gpu and (not limits.get("memory") or not limits.get("cpu")):
                        gpu_pods_without_limits += 1

    # AI services exposed as LoadBalancer (public exposure risk)
    all_services = _kubectl(["get", "services", "-A", "-o", "json"])
    ai_services_exposed = []
    if "skipped" not in all_services and "error" not in all_services:
        for svc in all_services.get("items", []):
            svc_type = svc.get("spec", {}).get("type", "")
            svc_name = svc.get("metadata", {}).get("name", "").lower()
            ns = svc.get("metadata", {}).get("namespace", "")
            if svc_type == "LoadBalancer" and any(
                kw in svc_name for kw in ["inference", "llm", "model", "ai", "vllm", "triton"]
            ):
                ai_services_exposed.append({"name": svc_name, "namespace": ns})

    return {
        "ai_pods_found": ai_pods_found[:20],
        "pods_without_security_context": pods_without_security_context,
        "ai_services_exposed": ai_services_exposed,
        "gpu_pods_without_limits": gpu_pods_without_limits,
        "available": True,
    }


# ── MAP-4.1, MANAGE-2.4: RAG Security ────────────────────────────────────────

def collect_rag_security() -> dict:
    """
    Check RAG pipeline security posture via filesystem inspection.

    Covers: MAP-4.1 (approaches for mapping AI risk — RAG data provenance
    tracking is a proxy for context risk mapping), MANAGE-2.4 (risk treatment
    approaches are in place — hash verification signals active data integrity
    controls).
    """
    # Check for ChromaDB directory and collection count
    chroma_raw = _shell("find . -name 'chroma' -type d 2>/dev/null | head -3")
    chroma_dirs = [p for p in chroma_raw.splitlines() if p.strip()]
    chroma_found = bool(chroma_dirs)

    # Count collection entries by finding .parquet or sqlite files under chroma dir
    collection_count = 0
    if chroma_found:
        parquet_raw = _shell(
            f"find {chroma_dirs[0]} -name '*.parquet' 2>/dev/null | wc -l"
        )
        try:
            collection_count = int(parquet_raw.strip())
        except ValueError:
            collection_count = 0

    # Check for ingestion audit logs
    ingest_log_raw = _shell(
        "find . \\( -path '*/ingest*log*' -o -path '*/rag*log*' \\) 2>/dev/null | head -5"
    )
    ingest_log_paths = [p for p in ingest_log_raw.splitlines() if p.strip()]
    ingest_logs_found = bool(ingest_log_paths)

    # Check for document hash verification (poisoning protection)
    hash_raw = _shell(
        "grep -r 'hash\\|sha256\\|checksum\\|integrity' "
        "GP-MODEL-OPS/2-rag-ingestion/ --include='*.py' -l 2>/dev/null"
    )
    hash_files = [p for p in hash_raw.splitlines() if p.strip()]
    hash_verification_found = bool(hash_files)

    # Check for provenance fields in ingestion pipeline
    provenance_raw = _shell(
        "grep -r 'provenance\\|source_url\\|document_source\\|origin' . "
        "--include='*.py' -l 2>/dev/null | head -5"
    )
    provenance_files = [p for p in provenance_raw.splitlines() if p.strip()]
    provenance_tracking_found = bool(provenance_files)

    return {
        "chroma_found": chroma_found,
        "collection_count": collection_count,
        "ingest_logs_found": ingest_logs_found,
        "hash_verification_found": hash_verification_found,
        "provenance_tracking_found": provenance_tracking_found,
        "available": True,
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def run_ai_rmf_collectors() -> dict:
    """Run all AI RMF 1.0 API-assessable collectors. Returns structured evidence dict."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    run_id = timestamp.replace(":", "").replace("-", "").replace(".", "")[:16] + "Z"

    evidence = {
        "run_id": run_id,
        "timestamp": timestamp,
        "framework": "NIST AI RMF 1.0",
        "supplement": "NIST AI 600-1",
        "requires_process_review": [
            "GOVERN-1.1: AI risk policies — requires document review",
            "GOVERN-1.2 through GOVERN-2.2: Accountability and organizational processes — "
            "require interviews and documentation review",
            "MAP-1.1 through MAP-5.2 (most): Context, scientific basis, stakeholder engagement "
            "— require documentation review",
            "MANAGE-1.x through MANAGE-3.x: Risk treatment approaches and resource alignment "
            "— require governance documentation review",
        ],
        "ai_inventory": collect_ai_system_inventory(),
        "hitl_enforcement": collect_hitl_enforcement(),
        "redteam_artifacts": collect_red_team_artifacts(),
        "incident_management": collect_ai_incident_log(),
        "monitoring": collect_monitoring_coverage(),
        "ai_workload_security": collect_ai_workload_security(),
        "rag_security": collect_rag_security(),
    }

    return evidence
