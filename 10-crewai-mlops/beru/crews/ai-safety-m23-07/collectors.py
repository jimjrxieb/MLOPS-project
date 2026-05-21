"""
AI Safety collectors — Step 1 of M-23-07 / EO 14110 AI safety assessment.

Encodes the evidence collection phase of:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-23-07-playbooks/01-assess-ai-security-baseline.md

Standalone module — no CrewAI dependency, no LLM. Pure kubectl + AWS CLI.

Design constraint:
  EO 14110 requirements split into two categories:
    API-assessable  — infrastructure state (security context, monitoring, storage encryption)
    Process-review  — document artifacts (red-teaming records, AI use case inventory, risk docs)

  This module assesses only what kubectl and AWS CLI can verify.
  Items requiring process review are flagged explicitly — never hallucinated.
"""

import json
import subprocess


# ── AI workload detection signals ─────────────────────────────────────────────

_AI_IMAGE_PATTERNS = [
    "pytorch", "tensorflow", "huggingface", "transformers",
    "ollama", "vllm", "triton", "torchserve", "mlflow",
    "ray", "spark", "jupyter", "notebook", "cuda", "nvidia",
    "sagemaker", "bedrock", "langchain", "llamaindex",
]

_AI_PORT_SIGNALS = [8080, 8501, 8502, 11434, 8000]  # common inference serving ports

_AI_ENV_SIGNALS = [
    "MODEL_PATH", "MODEL_NAME", "HUGGING_FACE_HUB_TOKEN",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TRANSFORMERS_CACHE",
]

_MODEL_STORAGE_NAME_PATTERNS = [
    "model", "weights", "training", "checkpoint", "dataset",
    "embeddings", "artifacts", "onnx", "gguf", "safetensors",
]

_INFERENCE_PATH_PATTERNS = [
    "/v1/", "/predict", "/inference", "/generate", "/completions",
    "/chat", "/embeddings", "/score", "/classify",
]


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _kubectl(args: list[str]) -> dict:
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


def _aws(args: list[str]) -> dict:
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


def _image_has_ai_signal(image: str) -> list[str]:
    """Return list of matched AI patterns found in an image string."""
    image_lower = image.lower()
    return [pat for pat in _AI_IMAGE_PATTERNS if pat in image_lower]


def _name_has_model_signal(name: str) -> bool:
    """Return True if a resource name matches model storage patterns."""
    name_lower = name.lower()
    return any(pat in name_lower for pat in _MODEL_STORAGE_NAME_PATTERNS)


# ── EO 4.1: AI Safety and Security ───────────────────────────────────────────

def collect_ai_workloads() -> dict:
    """
    Detect AI/ML workloads in the cluster.
    EO 4.1/4.2: agencies must know what AI they're running before they can assess it.

    Returns:
      ai_pods (list of {namespace, pod, container, image, signals, gpu_requested}),
      ai_namespaces (list),
      gpu_node_count (int),
      model_serving_endpoints (list of pods with inference-typical ports exposed),
      ai_workload_count (int),
      inventory_exists (bool) — always False; can only be confirmed via process review
    """
    pods_data = _kubectl(["get", "pods", "-A", "-o", "json"])
    if "skipped" in pods_data or "error" in pods_data:
        return {
            "skipped": pods_data.get("skipped", pods_data.get("error")),
            "ai_pods": [],
            "ai_namespaces": [],
            "gpu_node_count": 0,
            "model_serving_endpoints": [],
            "ai_workload_count": 0,
            "inventory_exists": False,
        }

    ai_pods = []
    ai_namespaces = set()
    model_serving = []

    for item in pods_data.get("items", []):
        ns = item["metadata"]["namespace"]
        pod_name = item["metadata"]["name"]
        spec = item.get("spec", {})

        for container in spec.get("containers", []) + spec.get("initContainers", []):
            image = container.get("image", "")
            signals = _image_has_ai_signal(image)

            # Check env var names for AI signals
            env_vars = [e.get("name", "") for e in container.get("env", [])]
            env_signals = [e for e in env_vars if e in _AI_ENV_SIGNALS]
            signals += [f"env:{e}" for e in env_signals]

            # Check GPU resource requests
            resources = container.get("resources", {})
            requests = resources.get("requests", {})
            limits = resources.get("limits", {})
            gpu_requested = (
                "nvidia.com/gpu" in requests
                or "amd.com/gpu" in requests
                or "nvidia.com/gpu" in limits
                or "amd.com/gpu" in limits
            )
            if gpu_requested:
                signals.append("gpu:requested")

            if signals:
                pod_entry = {
                    "namespace": ns,
                    "pod": pod_name,
                    "container": container["name"],
                    "image": image,
                    "signals": signals,
                    "gpu_requested": gpu_requested,
                }
                ai_pods.append(pod_entry)
                ai_namespaces.add(ns)

                # Check for inference-typical ports
                ports = [p.get("containerPort") for p in container.get("ports", [])]
                if any(p in _AI_PORT_SIGNALS for p in ports):
                    model_serving.append({
                        "namespace": ns,
                        "pod": pod_name,
                        "container": container["name"],
                        "ports": ports,
                    })

    # Check GPU nodes
    nodes_data = _kubectl(["get", "nodes", "-o", "json"])
    gpu_node_count = 0
    if "items" in nodes_data:
        for node in nodes_data["items"]:
            labels = node.get("metadata", {}).get("labels", {})
            capacity = node.get("status", {}).get("capacity", {})
            if (
                "nvidia.com/gpu" in capacity
                or "amd.com/gpu" in capacity
                or "accelerator" in labels
                or "gpu" in " ".join(labels.keys()).lower()
            ):
                gpu_node_count += 1

    return {
        "ai_pods": ai_pods,
        "ai_namespaces": sorted(ai_namespaces),
        "gpu_node_count": gpu_node_count,
        "model_serving_endpoints": model_serving,
        "ai_workload_count": len(ai_pods),
        "inventory_exists": False,  # cannot be confirmed via API — requires process review
    }


def collect_inference_endpoint_exposure() -> dict:
    """
    AC-6, SA-11: Are inference endpoints exposed without authentication?
    EO 4.1: AI systems must have access control — unauthenticated inference = mandate gap.

    Returns:
      exposed_services (list of {namespace, service, type, port, ai_likely}),
      loadbalancer_inference_endpoints (list),
      ingress_ai_endpoints (list),
      unauthenticated_endpoints_detected (bool)
    """
    svc_data = _kubectl(["get", "svc", "-A", "-o", "json"])
    if "skipped" in svc_data or "error" in svc_data:
        return {
            "skipped": svc_data.get("skipped", svc_data.get("error")),
            "exposed_services": [],
            "loadbalancer_inference_endpoints": [],
            "ingress_ai_endpoints": [],
            "unauthenticated_endpoints_detected": False,
        }

    exposed_services = []
    loadbalancer_endpoints = []

    for svc in svc_data.get("items", []):
        svc_type = svc["spec"].get("type", "ClusterIP")
        if svc_type not in ("LoadBalancer", "NodePort"):
            continue
        ns = svc["metadata"]["namespace"]
        name = svc["metadata"]["name"]
        ports = [p.get("port") for p in svc["spec"].get("ports", [])]
        ai_likely = (
            _image_has_ai_signal(name)
            or any(p in _AI_PORT_SIGNALS for p in ports)
        )
        entry = {
            "namespace": ns,
            "service": name,
            "type": svc_type,
            "ports": ports,
            "ai_likely": bool(ai_likely),
        }
        exposed_services.append(entry)
        if svc_type == "LoadBalancer" and ai_likely:
            loadbalancer_endpoints.append(entry)

    # Check ingress for AI path patterns
    ingress_data = _kubectl(["get", "ingress", "-A", "-o", "json"])
    ingress_ai_endpoints = []
    if "items" in ingress_data:
        for ing in ingress_data.get("items", []):
            ns = ing["metadata"]["namespace"]
            name = ing["metadata"]["name"]
            for rule in ing.get("spec", {}).get("rules", []):
                for path_entry in rule.get("http", {}).get("paths", []):
                    path = path_entry.get("path", "")
                    if any(pat in path for pat in _INFERENCE_PATH_PATTERNS):
                        ingress_ai_endpoints.append({
                            "namespace": ns,
                            "ingress": name,
                            "host": rule.get("host", "*"),
                            "path": path,
                        })

    # Heuristic: unauthenticated detection requires process review for full assurance,
    # but externally exposed AI ports without annotation is a strong indicator.
    unauthenticated_detected = len(loadbalancer_endpoints) > 0 or len(ingress_ai_endpoints) > 0

    return {
        "exposed_services": exposed_services,
        "loadbalancer_inference_endpoints": loadbalancer_endpoints,
        "ingress_ai_endpoints": ingress_ai_endpoints,
        "unauthenticated_endpoints_detected": unauthenticated_detected,
    }


def collect_ai_security_context() -> dict:
    """
    AC-6, SA-11: AI workload security posture.
    EO 4.1 security evaluation includes checking AI runtime isolation.

    Returns:
      ai_pods_running_as_root (list),
      ai_pods_privileged (list),
      ai_pods_without_resource_limits (list),
      ai_pods_with_host_network (list),
      ai_pods_with_host_path (list)
    """
    pods_data = _kubectl(["get", "pods", "-A", "-o", "json"])
    if "skipped" in pods_data or "error" in pods_data:
        return {
            "skipped": pods_data.get("skipped", pods_data.get("error")),
            "ai_pods_running_as_root": [],
            "ai_pods_privileged": [],
            "ai_pods_without_resource_limits": [],
            "ai_pods_with_host_network": [],
            "ai_pods_with_host_path": [],
        }

    running_as_root = []
    privileged = []
    without_limits = []
    host_network = []
    host_path = []

    for item in pods_data.get("items", []):
        ns = item["metadata"]["namespace"]
        pod_name = item["metadata"]["name"]
        spec = item.get("spec", {})
        pod_ctx = spec.get("securityContext", {})

        # Determine if this pod has AI signals
        is_ai_pod = False
        for container in spec.get("containers", []) + spec.get("initContainers", []):
            if _image_has_ai_signal(container.get("image", "")):
                is_ai_pod = True
                break
            env_vars = [e.get("name", "") for e in container.get("env", [])]
            if any(e in _AI_ENV_SIGNALS for e in env_vars):
                is_ai_pod = True
                break

        if not is_ai_pod:
            continue

        pod_ref = {"namespace": ns, "pod": pod_name}

        # Host network check (model exfil risk)
        if spec.get("hostNetwork"):
            host_network.append(pod_ref)

        # Host path check (training data access risk)
        for vol in spec.get("volumes", []):
            if "hostPath" in vol:
                host_path.append({**pod_ref, "volume": vol["name"], "path": vol["hostPath"].get("path")})

        for container in spec.get("containers", []):
            if not _image_has_ai_signal(container.get("image", "")):
                # Re-check per-container for accuracy
                env_vars = [e.get("name", "") for e in container.get("env", [])]
                if not any(e in _AI_ENV_SIGNALS for e in env_vars):
                    continue

            c_name = container["name"]
            c_ctx = container.get("securityContext", {})
            container_ref = {**pod_ref, "container": c_name}

            # Root check
            pod_non_root = pod_ctx.get("runAsNonRoot", False)
            c_non_root = c_ctx.get("runAsNonRoot", False)
            run_as_user = c_ctx.get("runAsUser", pod_ctx.get("runAsUser", None))
            if not pod_non_root and not c_non_root and (run_as_user is None or run_as_user == 0):
                running_as_root.append(container_ref)

            # Privileged check
            if c_ctx.get("privileged") is True:
                privileged.append(container_ref)

            # Resource limits check
            resources = container.get("resources", {})
            limits = resources.get("limits", {})
            if not limits or ("cpu" not in limits and "memory" not in limits):
                without_limits.append(container_ref)

    return {
        "ai_pods_running_as_root": running_as_root,
        "ai_pods_privileged": privileged,
        "ai_pods_without_resource_limits": without_limits,
        "ai_pods_with_host_network": host_network,
        "ai_pods_with_host_path": host_path,
    }


def collect_cicd_ai_gates() -> dict:
    """
    SA-11: CI/CD security gates for AI code/models.
    EO 4.1: pre-deployment evaluation — are there automated gates before AI goes to prod?

    Note: CI/CD content cannot be fully assessed via K8s API — this collector is
    intentionally limited. It checks for CI/CD credential patterns and config refs
    as proxy signals only. Flag for process review.

    Returns:
      github_actions_detected (bool),
      security_scan_in_cicd (bool),
      ai_specific_tests_detected (bool),
      ci_credential_secrets_found (list),
      note (str)
    """
    # Look for CI/CD-related secrets (names only, never values)
    secrets_data = _kubectl(["get", "secrets", "-A", "-o", "json"])
    ci_credential_secrets = []
    ci_patterns = [
        "github", "gitlab", "jenkins", "circleci", "tekton",
        "argocd-image-updater", "registry", "docker-registry",
    ]

    if "items" in secrets_data:
        for secret in secrets_data.get("items", []):
            name = secret["metadata"]["name"].lower()
            if any(pat in name for pat in ci_patterns):
                ci_credential_secrets.append({
                    "namespace": secret["metadata"]["namespace"],
                    "name": secret["metadata"]["name"],
                    "type": secret.get("type", "Opaque"),
                })

    # Check configmaps for CI/CD references
    cms_data = _kubectl(["get", "configmaps", "-A", "-o", "json"])
    github_actions_detected = False
    security_scan_detected = False

    if "items" in cms_data:
        for cm in cms_data.get("items", []):
            name = cm["metadata"]["name"].lower()
            data_str = json.dumps(cm.get("data", {})).lower()
            if "github" in name or "github-actions" in data_str:
                github_actions_detected = True
            if any(scanner in data_str for scanner in ["semgrep", "bandit", "trivy", "snyk", "sonar"]):
                security_scan_detected = True

    return {
        "github_actions_detected": github_actions_detected,
        "security_scan_in_cicd": security_scan_detected,
        "ai_specific_tests_detected": False,  # cannot be determined via K8s API
        "ci_credential_secrets_found": ci_credential_secrets,
        "note": (
            "CI/CD content cannot be fully assessed via K8s API. "
            "Presence of CI credential secrets is a proxy signal only. "
            "Pre-deployment red-teaming and AI model evaluation records "
            "require direct repository and pipeline review."
        ),
    }


# ── EO 4.2: AI Risk Assessment ────────────────────────────────────────────────

def collect_model_storage() -> dict:
    """
    SC-28, RA-3: Model weights and training data protection.
    EO 4.2: model artifacts must be protected — encryption + access control.

    Returns:
      s3_buckets_with_model_signals (list of {bucket, encrypted, public, versioned}),
      pvc_with_model_signals (list of {name, namespace, storage_class, size}),
      unencrypted_model_storage (int),
      publicly_accessible_model_storage (int)
    """
    # S3 bucket scan
    buckets_resp = _aws(["s3api", "list-buckets", "--query", "Buckets[*].Name"])
    model_buckets = []
    unencrypted_count = 0
    public_count = 0

    if "skipped" not in buckets_resp and "error" not in buckets_resp:
        bucket_names = buckets_resp if isinstance(buckets_resp, list) else []
        for bucket_name in bucket_names:
            if not _name_has_model_signal(bucket_name):
                continue

            # Check encryption
            enc_resp = _aws(["s3api", "get-bucket-encryption", "--bucket", bucket_name])
            encrypted = "skipped" not in enc_resp and "error" not in enc_resp

            # Check public access block
            pub_resp = _aws(["s3api", "get-public-access-block", "--bucket", bucket_name])
            if "skipped" in pub_resp or "error" in pub_resp:
                is_public = False  # cannot determine; treat as unknown
            else:
                block = pub_resp.get("PublicAccessBlockConfiguration", {})
                is_public = not all([
                    block.get("BlockPublicAcls", False),
                    block.get("BlockPublicPolicy", False),
                    block.get("IgnorePublicAcls", False),
                    block.get("RestrictPublicBuckets", False),
                ])

            # Check versioning
            ver_resp = _aws(["s3api", "get-bucket-versioning", "--bucket", bucket_name])
            versioned = ver_resp.get("Status") == "Enabled"

            entry = {
                "bucket": bucket_name,
                "encrypted": encrypted,
                "public": is_public,
                "versioned": versioned,
            }
            model_buckets.append(entry)
            if not encrypted:
                unencrypted_count += 1
            if is_public:
                public_count += 1

    # PVC scan for model storage
    pvcs_data = _kubectl(["get", "pvc", "-A", "-o", "json"])
    pvc_model_signals = []

    if "items" in pvcs_data:
        for pvc in pvcs_data.get("items", []):
            name = pvc["metadata"]["name"]
            if not _name_has_model_signal(name):
                continue
            pvc_model_signals.append({
                "name": name,
                "namespace": pvc["metadata"]["namespace"],
                "storage_class": pvc["spec"].get("storageClassName", "unknown"),
                "size": pvc["spec"].get("resources", {}).get("requests", {}).get("storage", "unknown"),
                "phase": pvc.get("status", {}).get("phase", "unknown"),
            })

    return {
        "s3_buckets_with_model_signals": model_buckets,
        "pvc_with_model_signals": pvc_model_signals,
        "unencrypted_model_storage": unencrypted_count,
        "publicly_accessible_model_storage": public_count,
    }


def collect_aws_ai_services() -> dict:
    """
    RA-3, SC-28: AWS managed AI service usage and configuration.
    EO 4.2: AI risk assessment must cover managed AI services (Bedrock, SageMaker).

    Returns:
      sagemaker_domains (list of {name, status, kms_encrypted}),
      bedrock_model_access (list of enabled foundation models),
      bedrock_guardrails_configured (bool),
      sagemaker_vpc_only (bool),
      rekognition_in_use (bool),
      comprehend_in_use (bool)
    """
    # SageMaker domains
    sm_domains_resp = _aws(["sagemaker", "list-domains"])
    sagemaker_domains = []
    sagemaker_vpc_only = True  # assume compliant until proven otherwise

    if "skipped" not in sm_domains_resp and "error" not in sm_domains_resp:
        for domain in sm_domains_resp.get("Domains", []):
            domain_name = domain.get("DomainName", "")
            status = domain.get("Status", "")
            kms_key = domain.get("KmsKeyId", "")
            sagemaker_domains.append({
                "name": domain_name,
                "status": status,
                "kms_encrypted": bool(kms_key),
            })

        # Check notebook instances for direct internet access
        nb_resp = _aws(["sagemaker", "list-notebook-instances"])
        if "skipped" not in nb_resp and "error" not in nb_resp:
            for nb in nb_resp.get("NotebookInstances", []):
                if nb.get("DirectInternetAccess") == "Enabled":
                    sagemaker_vpc_only = False

    # Bedrock — list enabled foundation models
    bedrock_resp = _aws(["bedrock", "list-foundation-models"])
    bedrock_model_access = []
    if "skipped" not in bedrock_resp and "error" not in bedrock_resp:
        for model in bedrock_resp.get("modelSummaries", []):
            if model.get("modelLifecycle", {}).get("status") == "ACTIVE":
                bedrock_model_access.append({
                    "modelId": model.get("modelId"),
                    "provider": model.get("providerName"),
                })

    # Bedrock guardrails
    guardrails_resp = _aws(["bedrock", "list-guardrails"])
    bedrock_guardrails_configured = (
        "skipped" not in guardrails_resp
        and "error" not in guardrails_resp
        and len(guardrails_resp.get("guardrails", [])) > 0
    )

    # Rekognition — proxy: check if any policies reference rekognition
    # (Cannot enumerate usage without CloudTrail; mark as unknown)
    rekognition_resp = _aws(["rekognition", "describe-projects"])
    rekognition_in_use = (
        "skipped" not in rekognition_resp
        and "error" not in rekognition_resp
        and len(rekognition_resp.get("ProjectDescriptions", [])) > 0
    )

    # Comprehend — check for endpoints as proxy for active use
    comprehend_resp = _aws(["comprehend", "list-endpoints"])
    comprehend_in_use = (
        "skipped" not in comprehend_resp
        and "error" not in comprehend_resp
        and len(comprehend_resp.get("EndpointPropertiesList", [])) > 0
    )

    return {
        "sagemaker_domains": sagemaker_domains,
        "bedrock_model_access": bedrock_model_access,
        "bedrock_guardrails_configured": bedrock_guardrails_configured,
        "sagemaker_vpc_only": sagemaker_vpc_only,
        "rekognition_in_use": rekognition_in_use,
        "comprehend_in_use": comprehend_in_use,
    }


# ── EO 4.3: AI Transparency and Monitoring ────────────────────────────────────

def collect_monitoring_for_ai() -> dict:
    """
    SI-4, CA-7: Is there monitoring in place for AI workload behavior?
    EO 4.3: AI systems in consequential decisions must be monitored.

    Returns:
      falco_running (bool),
      falco_ai_rules_detected (bool),
      prometheus_running (bool),
      model_metrics_endpoints (list),
      behavioral_baseline_configured (bool),
      security_hub_enabled (bool),
      guardduty_enabled (bool)
    """
    # Falco
    falco_pods = _kubectl(["get", "pods", "-n", "falco", "-o", "json"])
    falco_running = False
    falco_ai_rules_detected = False

    if "items" in falco_pods:
        running_falco = [
            p for p in falco_pods["items"]
            if p.get("status", {}).get("phase") == "Running"
        ]
        falco_running = len(running_falco) > 0

    if falco_running:
        # Check Falco configmaps for AI-specific rules
        falco_cms = _kubectl(["get", "configmaps", "-n", "falco", "-o", "json"])
        if "items" in falco_cms:
            for cm in falco_cms.get("items", []):
                data_str = json.dumps(cm.get("data", {})).lower()
                if any(sig in data_str for sig in ["model", "inference", "llm", "ollama", "gpu"]):
                    falco_ai_rules_detected = True

    # Prometheus / monitoring stack
    monitoring_patterns = ["prometheus", "grafana", "datadog", "dynatrace", "newrelic"]
    all_pods = _kubectl(["get", "pods", "-A", "-o", "json"])
    prometheus_running = False
    model_metrics_endpoints = []

    if "items" in all_pods:
        for pod in all_pods.get("items", []):
            pod_name = pod["metadata"]["name"].lower()
            ns = pod["metadata"]["namespace"]

            if any(pat in pod_name for pat in monitoring_patterns):
                if "prometheus" in pod_name:
                    prometheus_running = True

            # Check for /metrics exposure on AI pods
            for container in pod.get("spec", {}).get("containers", []):
                if not _image_has_ai_signal(container.get("image", "")):
                    continue
                ports = [p.get("containerPort") for p in container.get("ports", [])]
                if 9090 in ports or 9091 in ports or 8000 in ports:
                    model_metrics_endpoints.append({
                        "namespace": ns,
                        "pod": pod["metadata"]["name"],
                        "container": container["name"],
                        "ports": ports,
                    })

    # AWS SecurityHub
    sh_resp = _aws(["securityhub", "describe-hub"])
    security_hub_enabled = (
        "skipped" not in sh_resp
        and "error" not in sh_resp
        and "HubArn" in sh_resp
    )

    # GuardDuty
    gd_resp = _aws(["guardduty", "list-detectors"])
    guardduty_enabled = (
        "skipped" not in gd_resp
        and "error" not in gd_resp
        and len(gd_resp.get("DetectorIds", [])) > 0
    )

    return {
        "falco_running": falco_running,
        "falco_ai_rules_detected": falco_ai_rules_detected,
        "prometheus_running": prometheus_running,
        "model_metrics_endpoints": model_metrics_endpoints,
        "behavioral_baseline_configured": falco_running and falco_ai_rules_detected,
        "security_hub_enabled": security_hub_enabled,
        "guardduty_enabled": guardduty_enabled,
    }


# ── Aggregate runner ───────────────────────────────────────────────────────────

def run_ai_safety_collectors() -> dict:
    """
    Aggregate all AI Safety collectors for M-23-07 / EO 14110 assessment.

    Returns evidence grouped by EO 14110 section, plus ai_signals summary.
    CRITICAL: cannot_assess_via_api list is always populated — agents must not
    hallucinate determinations for these items.
    """
    # Collect all sections
    ai_workloads = collect_ai_workloads()
    inference_exposure = collect_inference_endpoint_exposure()
    ai_security_ctx = collect_ai_security_context()
    cicd_gates = collect_cicd_ai_gates()
    model_storage = collect_model_storage()
    aws_ai_services = collect_aws_ai_services()
    monitoring = collect_monitoring_for_ai()

    # ── Derive ai_signals summary ──────────────────────────────────────────────

    ai_workload_count = ai_workloads.get("ai_workload_count", 0)
    ai_workloads_detected = ai_workload_count > 0

    aws_managed_ai_detected = (
        len(aws_ai_services.get("sagemaker_domains", [])) > 0
        or len(aws_ai_services.get("bedrock_model_access", [])) > 0
        or aws_ai_services.get("rekognition_in_use", False)
        or aws_ai_services.get("comprehend_in_use", False)
    )

    # Section 4.1 — EO AI Safety and Security
    # API-assessable proxy: security context + endpoint exposure + CI signals
    sec_ctx = ai_security_ctx
    has_root_ai = len(sec_ctx.get("ai_pods_running_as_root", [])) > 0
    has_privileged_ai = len(sec_ctx.get("ai_pods_privileged", [])) > 0
    has_exposed_unauthenticated = inference_exposure.get("unauthenticated_endpoints_detected", False)
    has_host_network_ai = len(sec_ctx.get("ai_pods_with_host_network", [])) > 0

    if has_root_ai or has_privileged_ai or has_exposed_unauthenticated or has_host_network_ai:
        section_4_1_status = "assessable_gap"
    elif ai_workloads_detected:
        section_4_1_status = "assessable_compliant"
    else:
        section_4_1_status = "requires_process_review"

    # Section 4.2 — Risk Assessment: model protection is API-assessable
    unencrypted_storage = model_storage.get("unencrypted_model_storage", 0)
    public_storage = model_storage.get("publicly_accessible_model_storage", 0)

    if unencrypted_storage > 0 or public_storage > 0:
        section_4_2_status = "assessable_gap"
    elif len(model_storage.get("s3_buckets_with_model_signals", [])) > 0 or aws_managed_ai_detected:
        section_4_2_status = "assessable_compliant"
    else:
        section_4_2_status = "requires_process_review"

    # Section 4.3 — Transparency and Monitoring: infrastructure is API-assessable
    monitoring_gap = (
        not monitoring.get("falco_running", False)
        and not monitoring.get("prometheus_running", False)
        and not monitoring.get("security_hub_enabled", False)
        and not monitoring.get("guardduty_enabled", False)
    )

    if monitoring_gap and ai_workloads_detected:
        section_4_3_status = "assessable_gap"
    elif monitoring.get("falco_running") or monitoring.get("security_hub_enabled"):
        section_4_3_status = "assessable_compliant"
    else:
        section_4_3_status = "requires_process_review"

    # Critical findings — API-assessable only
    critical_findings = []
    if has_privileged_ai:
        critical_findings.append(
            f"{len(sec_ctx['ai_pods_privileged'])} AI container(s) running privileged — "
            "EO 14110 §4.1 isolation requirement not met"
        )
    if public_storage > 0:
        critical_findings.append(
            f"{public_storage} model storage bucket(s) publicly accessible — "
            "EO 14110 §4.2 SC-28 protection at rest gap"
        )
    if unencrypted_storage > 0:
        critical_findings.append(
            f"{unencrypted_storage} model storage bucket(s) unencrypted — "
            "EO 14110 §4.2 SC-28 protection at rest gap"
        )
    if has_exposed_unauthenticated and ai_workloads_detected:
        critical_findings.append(
            "AI inference endpoints externally exposed — "
            "EO 14110 §4.1 AC-6 access control gap detected"
        )

    # Items that cannot be assessed via API — always present, never empty
    cannot_assess_via_api = [
        "AI use case inventory (EO 14110 §4.3) — requires process review",
        "Pre-deployment red-teaming records (EO 14110 §4.1) — requires process review",
        "AI risk documentation / NIST AI RMF artifacts (EO 14110 §4.2) — requires process review",
        "Dual-use AI designation and CBRN uplift assessment (EO 14110 §4.1) — requires process review",
        "AI system consequential-decision classification (EO 14110 §4.3) — requires process review",
    ]

    return {
        "eo_4_1_safety": {
            "ai_workloads": ai_workloads,
            "inference_endpoint_exposure": inference_exposure,
            "ai_security_context": ai_security_ctx,
            "cicd_gates": cicd_gates,
        },
        "eo_4_2_risk": {
            "model_storage": model_storage,
            "aws_ai_services": aws_ai_services,
        },
        "eo_4_3_monitoring": {
            "monitoring_for_ai": monitoring,
        },
        "ai_signals": {
            "ai_workloads_detected": ai_workloads_detected,
            "ai_workload_count": ai_workload_count,
            "aws_managed_ai_detected": aws_managed_ai_detected,
            "section_compliance": {
                "4.1": section_4_1_status,
                "4.2": section_4_2_status,
                "4.3": section_4_3_status,
            },
            "cannot_assess_via_api": cannot_assess_via_api,
            "critical_findings": critical_findings,
        },
    }
