"""
AC-family collectors — Step 1 of 02-access-control-hardening.md encoded as Python.

Mirrors GP-SECLAB/SecLAB-setup/03-n8n/crewai-runner/crew/collectors.py (AC section).
Standalone module — no CrewAI dependency, no LLM. Pure kubectl + AWS CLI.
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


# ── AC-2: Account Management ──────────────────────────────────────────────────

def collect_cluster_admin_bindings() -> list[dict]:
    """Who has cluster-admin? Each binding requires a business justification (B-rank)."""
    data = _kubectl(["get", "clusterrolebindings", "-o", "json"])
    return [
        {
            "binding": item["metadata"]["name"],
            "role": item["roleRef"]["name"],
            "subjects": [
                {"kind": s.get("kind"), "name": s.get("name"), "namespace": s.get("namespace")}
                for s in item.get("subjects", [])
            ],
            "is_cluster_admin": item["roleRef"]["name"] == "cluster-admin",
        }
        for item in data.get("items", [])
    ]


def collect_all_role_bindings() -> list[dict]:
    """All RoleBindings per namespace — who has what scoped access."""
    crbs = _kubectl(["get", "clusterrolebindings", "-o", "json"])
    rbs = _kubectl(["get", "rolebindings", "-A", "-o", "json"])
    bindings = []
    for item in crbs.get("items", []):
        for subject in item.get("subjects", []):
            bindings.append({
                "type": "ClusterRoleBinding",
                "binding": item["metadata"]["name"],
                "role": item["roleRef"]["name"],
                "subject_kind": subject.get("kind"),
                "subject_name": subject.get("name"),
                "subject_namespace": subject.get("namespace", "cluster-wide"),
            })
    for item in rbs.get("items", []):
        for subject in item.get("subjects", []):
            bindings.append({
                "type": "RoleBinding",
                "binding": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "role": item["roleRef"]["name"],
                "subject_kind": subject.get("kind"),
                "subject_name": subject.get("name"),
            })
    return bindings


def collect_service_accounts() -> list[dict]:
    """Full service account inventory — namespace, name, token automount status."""
    data = _kubectl(["get", "serviceaccounts", "-A", "-o", "json"])
    return [
        {
            "name": item["metadata"]["name"],
            "namespace": item["metadata"]["namespace"],
            "created": item["metadata"].get("creationTimestamp"),
            "automount_token": item.get("automountServiceAccountToken", True),
        }
        for item in data.get("items", [])
    ]


def collect_iam_users() -> dict:
    return _aws(["iam", "list-users", "--query",
                 "Users[*].{UserName:UserName,Created:CreateDate,PasswordLastUsed:PasswordLastUsed}"])


def collect_iam_credential_report() -> dict:
    _aws(["iam", "generate-credential-report"])
    report = _aws(["iam", "get-credential-report"])
    if "skipped" in report or "error" in report:
        return report
    import base64, csv, io
    content = base64.b64decode(report.get("Content", "")).decode()
    reader = csv.DictReader(io.StringIO(content))
    users = []
    for row in reader:
        users.append({
            "user": row.get("user"),
            "mfa_active": row.get("mfa_active") == "true",
            "password_last_used": row.get("password_last_used"),
            "access_key_1_active": row.get("access_key_1_active") == "true",
            "access_key_1_last_used": row.get("access_key_1_last_used_date"),
            "access_key_2_active": row.get("access_key_2_active") == "true",
            "access_key_2_last_used": row.get("access_key_2_last_used_date"),
        })
    return {"users": users}


# ── AC-3: Access Enforcement ──────────────────────────────────────────────────

def collect_rbac_enforcement() -> dict:
    """Verify RBAC is active and anonymous/unauthenticated access is blocked."""
    rbac_enabled = _kubectl(["api-versions"])
    has_rbac = "rbac.authorization.k8s.io" in rbac_enabled.get("raw", "")

    anon_check = subprocess.run(
        ["kubectl", "auth", "can-i", "list", "pods", "--as=system:anonymous"],
        capture_output=True, text=True, timeout=10,
    )
    unauth_check = subprocess.run(
        ["kubectl", "auth", "can-i", "list", "pods", "--as=system:unauthenticated"],
        capture_output=True, text=True, timeout=10,
    )

    return {
        "rbac_api_enabled": has_rbac,
        "anonymous_access_allowed": anon_check.stdout.strip() == "yes",
        "unauthenticated_access_allowed": unauth_check.stdout.strip() == "yes",
    }


# ── AC-6: Least Privilege ─────────────────────────────────────────────────────

def collect_root_pods() -> list[dict]:
    """Pods not explicitly configured to run as non-root — AC-6 violation."""
    data = _kubectl(["get", "pods", "-A", "-o", "json"])
    violations = []
    for item in data.get("items", []):
        pod_ctx = item.get("spec", {}).get("securityContext", {})
        pod_non_root = pod_ctx.get("runAsNonRoot", False)
        for container in item.get("spec", {}).get("containers", []):
            c_ctx = container.get("securityContext", {})
            c_non_root = c_ctx.get("runAsNonRoot", False)
            if not pod_non_root and not c_non_root:
                violations.append({
                    "namespace": item["metadata"]["namespace"],
                    "pod": item["metadata"]["name"],
                    "container": container["name"],
                    "issue": "runAsNonRoot not set",
                })
    return violations


def collect_privileged_containers() -> list[dict]:
    """Containers running with privileged:true — highest severity AC-6 finding."""
    data = _kubectl(["get", "pods", "-A", "-o", "json"])
    violations = []
    for item in data.get("items", []):
        for container in item.get("spec", {}).get("containers", []):
            if container.get("securityContext", {}).get("privileged") is True:
                violations.append({
                    "namespace": item["metadata"]["namespace"],
                    "pod": item["metadata"]["name"],
                    "container": container["name"],
                    "issue": "privileged: true",
                })
    return violations


def collect_wildcard_roles() -> list[dict]:
    """ClusterRoles with wildcard verbs or resources outside system: prefix."""
    data = _kubectl(["get", "clusterroles", "-o", "json"])
    wildcards = []
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        if name.startswith("system:"):
            continue
        for rule in item.get("rules", []):
            if "*" in rule.get("verbs", []) or "*" in rule.get("resources", []):
                wildcards.append({"name": name, "rule": rule})
    return wildcards


# ── AC-17: Remote Access ──────────────────────────────────────────────────────

def collect_remote_access_posture() -> dict:
    """Check TLS on API server and find exposed LoadBalancer/NodePort services."""
    try:
        cluster_info = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        cluster_info = type("r", (), {"stdout": ""})()

    api_server_tls = "https://" in cluster_info.stdout

    svc_data = _kubectl(["get", "svc", "-A", "-o", "json"])
    exposed_services = [
        {
            "namespace": svc["metadata"]["namespace"],
            "name": svc["metadata"]["name"],
            "type": svc["spec"]["type"],
        }
        for svc in svc_data.get("items", [])
        if svc["spec"]["type"] in ("LoadBalancer", "NodePort")
    ]

    eks_endpoint = _aws([
        "eks", "describe-cluster", "--name", "seclab",
        "--query", "cluster.resourcesVpcConfig.{publicAccess:endpointPublicAccess,publicCidrs:publicAccessCidrs}",
    ])

    return {
        "api_server_tls": api_server_tls,
        "exposed_services": exposed_services,
        "eks_public_endpoint": eks_endpoint,
    }


# ── AC family runner ──────────────────────────────────────────────────────────

def run_ac_collectors() -> dict:
    """Full AC-family audit pass — Step 1 of 02-access-control-hardening.md."""
    return {
        "ac2_account_management": {
            "cluster_admin_bindings": collect_cluster_admin_bindings(),
            "all_role_bindings": collect_all_role_bindings(),
            "service_accounts": collect_service_accounts(),
            "iam_users": collect_iam_users(),
            "iam_credential_report": collect_iam_credential_report(),
        },
        "ac3_access_enforcement": {
            "rbac_enforcement": collect_rbac_enforcement(),
        },
        "ac6_least_privilege": {
            "root_pods": collect_root_pods(),
            "privileged_containers": collect_privileged_containers(),
            "wildcard_roles": collect_wildcard_roles(),
        },
        "ac17_remote_access": {
            "remote_access_posture": collect_remote_access_posture(),
        },
    }
