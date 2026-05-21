"""
ZT Zero Trust collectors -- Step 1 of M-22-09 assessment encoded as Python.

Mirrors GP-SECLAB/SecLAB-setup/03-n8n/crewai-runner/crew/collectors.py (ZT section).
Standalone module -- no CrewAI dependency, no LLM. Pure kubectl + AWS CLI.

Controls assessed across ZT pillars:
  Networks:      SC-7 (NetworkPolicy), SC-8 (TLS/mTLS), AC-17 (remote access)
  Identity:      AC-2, AC-6 (RBAC), IA-2 (MFA/OIDC), IA-5 (workload identity)
  Devices:       IA-3, CM-8 (node inventory)
  Applications:  AC-3 (access enforcement), SI-4 (monitoring)
  Data:          SC-28 (encryption at rest)
  Cross-pillar:  CA-7 (continuous monitoring)
"""

import json
import subprocess


def _kubectl(args: list[str]) -> dict:
    result = subprocess.run(
        ["kubectl"] + args,
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
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


# ── SC-7: Boundary Protection (Networks pillar) ───────────────────────────────

def collect_network_policies() -> dict:
    """
    SC-7: Check NetworkPolicy coverage across all namespaces.
    ZT Networks pillar -- Initial requires deny-all default + allow-listed traffic.
    Returns:
      total_namespaces, namespaces_with_netpol, namespaces_without_netpol (list),
      has_default_deny (bool), coverage_pct (float)
    """
    netpols = _kubectl(["get", "networkpolicies", "-A", "-o", "json"])
    namespaces_data = _kubectl(["get", "namespaces", "-o", "json"])

    if "error" in netpols or "error" in namespaces_data:
        return {"skipped": "kubectl not available or cluster unreachable"}

    all_namespaces = [
        item["metadata"]["name"]
        for item in namespaces_data.get("items", [])
    ]
    total_namespaces = len(all_namespaces)

    # Map namespace -> list of policies
    ns_policies: dict[str, list] = {ns: [] for ns in all_namespaces}
    has_default_deny = False

    for item in netpols.get("items", []):
        ns = item["metadata"]["namespace"]
        pod_selector = item.get("spec", {}).get("podSelector", {})
        policy_types = item.get("spec", {}).get("policyTypes", [])

        if ns in ns_policies:
            ns_policies[ns].append(item["metadata"]["name"])

        # Default-deny-all: empty podSelector + both Ingress and Egress in policyTypes
        if (
            pod_selector == {} or pod_selector == {"matchLabels": {}}
        ) and "Ingress" in policy_types and "Egress" in policy_types:
            has_default_deny = True

    namespaces_with_netpol = [ns for ns, policies in ns_policies.items() if policies]
    namespaces_without_netpol = [ns for ns, policies in ns_policies.items() if not policies]
    coverage_pct = (
        round(len(namespaces_with_netpol) / total_namespaces * 100, 1)
        if total_namespaces > 0 else 0.0
    )

    return {
        "total_namespaces": total_namespaces,
        "namespaces_with_netpol": len(namespaces_with_netpol),
        "namespaces_without_netpol": namespaces_without_netpol,
        "has_default_deny": has_default_deny,
        "coverage_pct": coverage_pct,
    }


# ── SC-8: Transmission Confidentiality/Integrity (Networks + Data pillars) ────

def collect_tls_enforcement() -> dict:
    """
    SC-8: Check TLS enforcement on ingress resources.
    ZT Networks+Data -- Initial requires TLS on all ingress; Advanced requires mTLS.
    Returns:
      ingress_resources (list with tls: bool per ingress),
      tls_enforced_pct (float), mtls_detected (bool)
    """
    ingress_data = _kubectl(["get", "ingress", "-A", "-o", "json"])

    if "error" in ingress_data:
        return {"skipped": "kubectl not available or cluster unreachable"}

    ingress_resources = []
    for item in ingress_data.get("items", []):
        spec = item.get("spec", {})
        has_tls = bool(spec.get("tls"))
        ingress_resources.append({
            "namespace": item["metadata"]["namespace"],
            "name": item["metadata"]["name"],
            "tls": has_tls,
        })

    total = len(ingress_resources)
    tls_count = sum(1 for r in ingress_resources if r["tls"])
    tls_enforced_pct = round(tls_count / total * 100, 1) if total > 0 else 0.0

    # Detect Istio (mTLS) -- check for istio-system namespace pods
    istio_pods = _kubectl(["get", "pods", "-n", "istio-system", "-o", "json"])
    istio_detected = bool(istio_pods.get("items"))

    # Detect Linkerd (mTLS)
    linkerd_pods = _kubectl(["get", "pods", "-n", "linkerd", "-o", "json"])
    linkerd_detected = bool(linkerd_pods.get("items"))

    mtls_detected = istio_detected or linkerd_detected

    return {
        "ingress_resources": ingress_resources,
        "tls_enforced_pct": tls_enforced_pct,
        "mtls_detected": mtls_detected,
        "istio_detected": istio_detected,
        "linkerd_detected": linkerd_detected,
    }


# ── AC-2, AC-6: Account Management + Least Privilege (Identity pillar) ────────

def collect_rbac_privilege() -> dict:
    """
    AC-2, AC-6: Cluster-admin bindings, wildcard roles, over-provisioned service accounts.
    ZT Identity pillar -- no standing cluster-admin outside kube-system.
    Returns:
      cluster_admin_count, non_system_cluster_admins (list),
      wildcard_roles (list), privileged_pods (list)
    """
    crbs = _kubectl(["get", "clusterrolebindings", "-o", "json"])
    if "error" in crbs:
        return {"skipped": "kubectl not available or cluster unreachable"}

    cluster_admin_count = 0
    non_system_cluster_admins = []

    for item in crbs.get("items", []):
        if item["roleRef"]["name"] != "cluster-admin":
            continue
        for subject in item.get("subjects", []):
            cluster_admin_count += 1
            name = subject.get("name", "")
            namespace = subject.get("namespace", "")
            # Flag anything outside system: prefix or kube-system namespace
            if not name.startswith("system:") and namespace not in ("kube-system", ""):
                non_system_cluster_admins.append({
                    "binding": item["metadata"]["name"],
                    "kind": subject.get("kind"),
                    "name": name,
                    "namespace": namespace,
                })
            elif not name.startswith("system:") and namespace == "":
                # ClusterRoleBinding with no namespace (user/group not in kube-system)
                non_system_cluster_admins.append({
                    "binding": item["metadata"]["name"],
                    "kind": subject.get("kind"),
                    "name": name,
                    "namespace": "cluster-wide",
                })

    # Wildcard ClusterRoles outside system: prefix
    clusterroles = _kubectl(["get", "clusterroles", "-o", "json"])
    wildcard_roles = []
    for item in clusterroles.get("items", []):
        name = item["metadata"]["name"]
        if name.startswith("system:"):
            continue
        for rule in item.get("rules", []):
            if "*" in rule.get("verbs", []) or "*" in rule.get("resources", []):
                wildcard_roles.append({"name": name, "rule": rule})

    # Privileged pods
    pods = _kubectl(["get", "pods", "-A", "-o", "json"])
    privileged_pods = []
    for item in pods.get("items", []):
        for container in item.get("spec", {}).get("containers", []):
            if container.get("securityContext", {}).get("privileged") is True:
                privileged_pods.append({
                    "namespace": item["metadata"]["namespace"],
                    "pod": item["metadata"]["name"],
                    "container": container["name"],
                })

    return {
        "cluster_admin_count": cluster_admin_count,
        "non_system_cluster_admins": non_system_cluster_admins,
        "wildcard_roles": wildcard_roles,
        "privileged_pods": privileged_pods,
    }


# ── IA-2: MFA / OIDC Signals (Identity pillar) ───────────────────────────────

def collect_mfa_signals() -> dict:
    """
    IA-2: Detect MFA/OIDC configuration signals.
    ZT Identity -- Initial requires MFA; Advanced requires phishing-resistant.
    Returns:
      oidc_issuer_detected (bool), oidc_issuer (str|None),
      aws_sso_detected (bool), service_account_tokens_expiring (bool)
    """
    # Check OIDC discovery on the cluster API
    oidc_raw = subprocess.run(
        ["kubectl", "get", "--raw", "/.well-known/openid-configuration"],
        capture_output=True, text=True, timeout=15,
    )
    oidc_issuer = None
    oidc_issuer_detected = False
    if oidc_raw.returncode == 0:
        try:
            oidc_data = json.loads(oidc_raw.stdout)
            oidc_issuer = oidc_data.get("issuer")
            oidc_issuer_detected = bool(oidc_issuer)
        except json.JSONDecodeError:
            pass

    # AWS SSO / IAM Identity Center
    sso_instances = _aws(["sso-admin", "list-instances"])
    aws_sso_detected = bool(sso_instances.get("Instances"))

    # Virtual MFA devices
    mfa_devices = _aws(["iam", "list-virtual-mfa-devices"])
    mfa_unassigned = 0
    mfa_enabled = 0
    if "skipped" not in mfa_devices and "error" not in mfa_devices:
        devices = mfa_devices.get("VirtualMFADevices", [])
        for d in devices:
            if d.get("User"):
                mfa_enabled += 1
            else:
                mfa_unassigned += 1

    # Service account token expiry -- detect if BoundServiceAccountToken feature used
    # Check for projected service account tokens (short-lived) vs old long-lived secrets
    sa_secrets = _kubectl(["get", "secrets", "-A", "-o", "json"])
    long_lived_token_count = 0
    if "error" not in sa_secrets:
        for item in sa_secrets.get("items", []):
            if item.get("type") == "kubernetes.io/service-account-token":
                long_lived_token_count += 1

    service_account_tokens_expiring = long_lived_token_count == 0

    return {
        "oidc_issuer_detected": oidc_issuer_detected,
        "oidc_issuer": oidc_issuer,
        "aws_sso_detected": aws_sso_detected,
        "mfa_enabled_count": mfa_enabled,
        "mfa_unassigned_count": mfa_unassigned,
        "long_lived_sa_token_count": long_lived_token_count,
        "service_account_tokens_expiring": service_account_tokens_expiring,
    }


# ── IA-3, CM-8: Device Identification + Inventory (Devices pillar) ───────────

def collect_device_inventory() -> dict:
    """
    CM-8, IA-3: Node inventory -- are all nodes managed/identified?
    ZT Devices pillar -- Initial requires complete inventory.
    Returns:
      node_count, nodes (list with name, role, os, kernel),
      unmanaged_node_detected (bool)
    """
    nodes_data = _kubectl(["get", "nodes", "-o", "json"])
    if "error" in nodes_data:
        return {"skipped": "kubectl not available or cluster unreachable"}

    nodes = []
    unmanaged_node_detected = False

    for item in nodes_data.get("items", []):
        labels = item["metadata"].get("labels", {})
        node_info = item.get("status", {}).get("nodeInfo", {})

        # Determine role
        role = "worker"
        if "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels:
            role = "control-plane"

        # Check for managed identity signal -- EKS nodes have eks.amazonaws.com/nodegroup label
        managed_labels = [
            "eks.amazonaws.com/nodegroup",
            "cloud.google.com/gke-nodepool",
            "kubernetes.azure.com/agentpool",
            "k3s.io/hostname",
        ]
        is_managed = any(label in labels for label in managed_labels)
        if not is_managed:
            unmanaged_node_detected = True

        nodes.append({
            "name": item["metadata"]["name"],
            "role": role,
            "os": node_info.get("operatingSystem", "unknown"),
            "kernel": node_info.get("kernelVersion", "unknown"),
            "kubelet_version": node_info.get("kubeletVersion", "unknown"),
            "managed": is_managed,
        })

    return {
        "node_count": len(nodes),
        "nodes": nodes,
        "unmanaged_node_detected": unmanaged_node_detected,
    }


# ── AC-3, IA-5: Workload Identity / IRSA (Applications + Identity pillars) ───

def collect_workload_identity() -> dict:
    """
    AC-3, IA-5: IRSA / Workload Identity -- are service accounts using managed identity?
    ZT Applications + Identity -- no long-lived static credentials for workloads.
    Returns:
      service_accounts_with_irsa (int), service_accounts_without_irsa (int),
      long_lived_tokens_detected (bool), automount_default_on (bool)
    """
    sa_data = _kubectl(["get", "serviceaccounts", "-A", "-o", "json"])
    if "error" in sa_data:
        return {"skipped": "kubectl not available or cluster unreachable"}

    sa_with_irsa = 0
    sa_without_irsa = 0
    automount_default_on = False

    for item in sa_data.get("items", []):
        annotations = item["metadata"].get("annotations", {})
        irsa_annotation = "eks.amazonaws.com/role-arn"

        if irsa_annotation in annotations:
            sa_with_irsa += 1
        else:
            sa_without_irsa += 1

        # automountServiceAccountToken defaults to True if not set
        if item.get("automountServiceAccountToken", True) is True:
            automount_default_on = True

    # Check for long-lived static credentials in AWS IAM
    iam_users = _aws(["iam", "list-users", "--query", "Users[*].{UserName:UserName}"])
    long_lived_access_keys = 0

    if "skipped" not in iam_users and "error" not in iam_users:
        users = iam_users if isinstance(iam_users, list) else []
        for user in users:
            username = user.get("UserName", "")
            keys = _aws([
                "iam", "list-access-keys",
                "--user-name", username,
                "--query", "AccessKeyMetadata[?Status=='Active']",
            ])
            if "skipped" not in keys and "error" not in keys:
                active_keys = keys if isinstance(keys, list) else []
                long_lived_access_keys += len(active_keys)

    long_lived_tokens_detected = long_lived_access_keys > 0

    return {
        "service_accounts_with_irsa": sa_with_irsa,
        "service_accounts_without_irsa": sa_without_irsa,
        "long_lived_tokens_detected": long_lived_tokens_detected,
        "long_lived_access_key_count": long_lived_access_keys,
        "automount_default_on": automount_default_on,
    }


# ── SC-28: Protection of Information at Rest (Data pillar) ───────────────────

def collect_encryption_at_rest() -> dict:
    """
    SC-28: Encryption at rest for etcd, secrets, S3.
    ZT Data pillar -- Initial requires encryption at rest for sensitive data.
    Returns:
      etcd_encryption_detected (bool), k8s_secrets_kms (bool),
      s3_default_encryption (list of {bucket, encrypted: bool})
    """
    # Check for EncryptionConfiguration -- presence of encryption-provider-config
    # On EKS, this is surfaced via the cluster describe API
    eks_encryption = _aws([
        "eks", "describe-cluster", "--name", "seclab",
        "--query", "cluster.encryptionConfig",
    ])
    etcd_encryption_detected = False
    k8s_secrets_kms = False

    if "skipped" not in eks_encryption and "error" not in eks_encryption:
        # eks_encryption is a list of encryption config objects
        configs = eks_encryption if isinstance(eks_encryption, list) else []
        for cfg in configs:
            resources = cfg.get("resources", [])
            provider = cfg.get("provider", {})
            if "secrets" in resources:
                etcd_encryption_detected = True
                if provider.get("keyArn") or provider.get("kmsKeyId"):
                    k8s_secrets_kms = True

    # S3 bucket encryption
    buckets_resp = _aws(["s3api", "list-buckets", "--query", "Buckets[*].Name"])
    s3_encryption_results = []

    if "skipped" not in buckets_resp and "error" not in buckets_resp:
        bucket_names = buckets_resp if isinstance(buckets_resp, list) else []
        for bucket in bucket_names[:20]:  # cap at 20 to avoid timeout
            enc = _aws(["s3api", "get-bucket-encryption", "--bucket", bucket])
            if "skipped" in enc or "error" in enc:
                s3_encryption_results.append({"bucket": bucket, "encrypted": False})
            else:
                s3_encryption_results.append({"bucket": bucket, "encrypted": True})

    return {
        "etcd_encryption_detected": etcd_encryption_detected,
        "k8s_secrets_kms": k8s_secrets_kms,
        "s3_default_encryption": s3_encryption_results,
    }


# ── SI-4, CA-7: Monitoring Coverage (Applications + cross-pillar) ─────────────

def collect_monitoring_coverage() -> dict:
    """
    SI-4, CA-7: Continuous monitoring presence.
    ZT Applications + cross-pillar -- Advanced requires runtime monitoring.
    Returns:
      falco_running (bool), prometheus_running (bool),
      grafana_running (bool), security_hub_enabled (bool)
    """
    pods_data = _kubectl(["get", "pods", "-A", "-o", "json"])

    falco_running = False
    prometheus_running = False
    grafana_running = False

    if "error" not in pods_data:
        for item in pods_data.get("items", []):
            name = item["metadata"]["name"].lower()
            labels = item["metadata"].get("labels", {})
            label_str = " ".join(f"{k}={v}" for k, v in labels.items()).lower()

            if "falco" in name or "falco" in label_str:
                falco_running = True
            if "prometheus" in name or "prometheus" in label_str:
                prometheus_running = True
            if "grafana" in name or "grafana" in label_str:
                grafana_running = True

    # AWS Security Hub
    hub = _aws(["securityhub", "describe-hub"])
    security_hub_enabled = "skipped" not in hub and "error" not in hub and bool(hub)

    return {
        "falco_running": falco_running,
        "prometheus_running": prometheus_running,
        "grafana_running": grafana_running,
        "security_hub_enabled": security_hub_enabled,
    }


# ── ZT runner ─────────────────────────────────────────────────────────────────

def _determine_pillar_stage(
    network_policies: dict,
    tls_enforcement: dict,
    rbac_privilege: dict,
    mfa_signals: dict,
    workload_identity: dict,
    device_inventory: dict,
    monitoring_coverage: dict,
    encryption_at_rest: dict,
) -> dict:
    """Derive ZT pillar maturity stages from collected evidence."""

    # ── Identity stage ────────────────────────────────────────────────────────
    oidc = mfa_signals.get("oidc_issuer_detected", False)
    mfa_count = mfa_signals.get("mfa_enabled_count", 0)
    non_system_admins = rbac_privilege.get("non_system_cluster_admins", [])
    wildcard_count = len(rbac_privilege.get("wildcard_roles", []))
    long_lived = workload_identity.get("long_lived_tokens_detected", False)

    identity_stage = "Traditional"
    if oidc or mfa_count > 0:
        identity_stage = "Initial"
    if oidc and not non_system_admins and wildcard_count == 0 and not long_lived:
        identity_stage = "Advanced"

    # ── Devices stage ─────────────────────────────────────────────────────────
    node_count = device_inventory.get("node_count", 0)
    unmanaged = device_inventory.get("unmanaged_node_detected", False)

    devices_stage = "Traditional"
    if node_count > 0 and not unmanaged:
        devices_stage = "Initial"
    # Advanced: would need endpoint compliance enforcement signals (not detectable via kubectl alone)

    # ── Networks stage ────────────────────────────────────────────────────────
    coverage_pct = network_policies.get("coverage_pct", 0.0)
    has_default_deny = network_policies.get("has_default_deny", False)
    tls_pct = tls_enforcement.get("tls_enforced_pct", 0.0)
    mtls = tls_enforcement.get("mtls_detected", False)

    networks_stage = "Traditional"
    if coverage_pct >= 50 and tls_pct > 0:
        networks_stage = "Initial"
    if has_default_deny and coverage_pct == 100 and mtls:
        networks_stage = "Advanced"

    # ── Applications stage ───────────────────────────────────────────────────
    falco = monitoring_coverage.get("falco_running", False)
    prom = monitoring_coverage.get("prometheus_running", False)
    sa_with_irsa = workload_identity.get("service_accounts_with_irsa", 0)
    sa_without_irsa = workload_identity.get("service_accounts_without_irsa", 0)
    total_sa = sa_with_irsa + sa_without_irsa

    applications_stage = "Traditional"
    if prom or falco:
        applications_stage = "Initial"
    if falco and prom and total_sa > 0 and sa_with_irsa > 0:
        applications_stage = "Advanced"

    # ── Data stage ────────────────────────────────────────────────────────────
    etcd_enc = encryption_at_rest.get("etcd_encryption_detected", False)
    kms = encryption_at_rest.get("k8s_secrets_kms", False)
    s3_buckets = encryption_at_rest.get("s3_default_encryption", [])
    s3_all_encrypted = all(b.get("encrypted") for b in s3_buckets) if s3_buckets else True

    data_stage = "Traditional"
    if etcd_enc or s3_all_encrypted:
        data_stage = "Initial"
    if etcd_enc and kms and s3_all_encrypted:
        data_stage = "Advanced"

    return {
        "Identity": identity_stage,
        "Devices": devices_stage,
        "Networks": networks_stage,
        "Applications": applications_stage,
        "Data": data_stage,
    }


def _stage_rank(stage: str) -> int:
    """Map stage name to numeric rank for min() comparison."""
    return {"Traditional": 0, "Initial": 1, "Advanced": 2, "Optimal": 3}.get(stage, 0)


def _compute_critical_gaps(
    pillar_stages: dict,
    network_policies: dict,
    tls_enforcement: dict,
    rbac_privilege: dict,
    mfa_signals: dict,
    workload_identity: dict,
    device_inventory: dict,
    monitoring_coverage: dict,
    encryption_at_rest: dict,
) -> list[str]:
    """Build a human-readable list of the most blocking ZT gaps."""
    gaps = []

    # Networks
    ns_without = network_policies.get("namespaces_without_netpol", [])
    if ns_without:
        count = len(ns_without)
        total = network_policies.get("total_namespaces", count)
        gaps.append(
            f"SC-7: {count} of {total} namespaces have no NetworkPolicy "
            f"(namespaces: {', '.join(ns_without[:5])}{'...' if count > 5 else ''})"
        )
    if not network_policies.get("has_default_deny"):
        gaps.append("SC-7: No default-deny-all NetworkPolicy detected in any namespace")
    tls_pct = tls_enforcement.get("tls_enforced_pct", 0.0)
    if tls_pct < 100:
        non_tls = [r["name"] for r in tls_enforcement.get("ingress_resources", []) if not r["tls"]]
        gaps.append(
            f"SC-8: TLS not enforced on {len(non_tls)} ingress resources "
            f"({tls_pct}% coverage)"
        )
    if not tls_enforcement.get("mtls_detected"):
        gaps.append("SC-8: No mTLS service mesh detected (Istio or Linkerd not found)")

    # Identity
    non_sys = rbac_privilege.get("non_system_cluster_admins", [])
    if non_sys:
        names = [a["name"] for a in non_sys]
        gaps.append(f"AC-6: {len(non_sys)} non-system cluster-admin binding(s): {names}")
    if not mfa_signals.get("oidc_issuer_detected"):
        gaps.append("IA-2: No OIDC issuer detected -- centralized IdP/MFA not configured on cluster")
    if workload_identity.get("long_lived_tokens_detected"):
        count = workload_identity.get("long_lived_access_key_count", 0)
        gaps.append(f"IA-5: {count} long-lived IAM access key(s) detected -- workload identity not migrated to IRSA")

    # Devices
    if device_inventory.get("unmanaged_node_detected"):
        gaps.append("CM-8: Unmanaged node(s) detected -- not enrolled in managed node group")

    # Applications
    if not monitoring_coverage.get("falco_running"):
        gaps.append("SI-4: Falco runtime detection not running -- no runtime threat monitoring")

    # Data
    if not encryption_at_rest.get("etcd_encryption_detected"):
        gaps.append("SC-28: Kubernetes secrets encryption at rest not detected")
    s3_buckets = encryption_at_rest.get("s3_default_encryption", [])
    unencrypted_s3 = [b["bucket"] for b in s3_buckets if not b.get("encrypted")]
    if unencrypted_s3:
        gaps.append(
            f"SC-28: {len(unencrypted_s3)} S3 bucket(s) without default encryption: "
            f"{', '.join(unencrypted_s3[:5])}{'...' if len(unencrypted_s3) > 5 else ''}"
        )

    return gaps


def run_zt_collectors() -> dict:
    """
    Aggregate all ZT collectors. Full M-22-09 evidence pass.
    Returns pillar-structured evidence with zt_signals summary.
    """
    # Collect all pillars
    network_policies = collect_network_policies()
    tls_enforcement = collect_tls_enforcement()
    rbac_privilege = collect_rbac_privilege()
    mfa_signals = collect_mfa_signals()
    workload_identity = collect_workload_identity()
    device_inventory = collect_device_inventory()
    monitoring_coverage = collect_monitoring_coverage()
    encryption_at_rest = collect_encryption_at_rest()

    # Derive pillar stages -- use empty dicts if collectors skipped
    _netpol = network_policies if "skipped" not in network_policies else {}
    _tls = tls_enforcement if "skipped" not in tls_enforcement else {}
    _rbac = rbac_privilege if "skipped" not in rbac_privilege else {}
    _mfa = mfa_signals if "skipped" not in mfa_signals else {}
    _wi = workload_identity if "skipped" not in workload_identity else {}
    _dev = device_inventory if "skipped" not in device_inventory else {}
    _mon = monitoring_coverage if "skipped" not in monitoring_coverage else {}
    _enc = encryption_at_rest if "skipped" not in encryption_at_rest else {}

    pillar_stages = _determine_pillar_stage(
        _netpol, _tls, _rbac, _mfa, _wi, _dev, _mon, _enc
    )

    # Overall stage = min across all pillars
    lowest_rank = min(_stage_rank(s) for s in pillar_stages.values())
    stage_names = {0: "Traditional", 1: "Initial", 2: "Advanced", 3: "Optimal"}
    overall_stage = stage_names[lowest_rank]

    m22_09_compliant = lowest_rank >= 1  # Initial or better

    critical_gaps = _compute_critical_gaps(
        pillar_stages, _netpol, _tls, _rbac, _mfa, _wi, _dev, _mon, _enc
    )

    return {
        "networks_pillar": {
            "network_policies": network_policies,
            "tls_enforcement": tls_enforcement,
        },
        "identity_pillar": {
            "rbac_privilege": rbac_privilege,
            "mfa_signals": mfa_signals,
            "workload_identity": workload_identity,
        },
        "devices_pillar": {
            "device_inventory": device_inventory,
        },
        "applications_pillar": {
            "monitoring_coverage": monitoring_coverage,
        },
        "data_pillar": {
            "encryption_at_rest": encryption_at_rest,
        },
        "zt_signals": {
            "pillar_stages": pillar_stages,
            "overall_stage": overall_stage,
            "m22_09_compliant": m22_09_compliant,
            "critical_gaps": critical_gaps,
        },
    }
