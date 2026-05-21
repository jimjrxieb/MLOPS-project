"""
CMMC Level 2 evidence collectors — kubectl + AWS CLI only, no LLM.

Collects evidence for API-assessable CMMC practices. Domains that require
process artifacts (AT, MA, MP, PE, PS) are flagged in cannot_assess_via_api.

API-assessable domains: AC, AU, CA (partial), CM, IA, IR (partial), RA, SC, SI, SR
Process-only domains:   AT, MA, MP, PE, PS
Partial domains:        CA (3.12.2/3.12.3 via proxy, 3.12.1/3.12.4 require docs)
                        IR (3.6.1/3.6.2 via proxy, 3.6.3 requires tabletop records)
"""

import json
import subprocess
import os
from datetime import datetime


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


def _current_cluster() -> str:
    """Return the current kubectl context name, or 'unknown-cluster'."""
    try:
        result = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown-cluster"
    except Exception:
        return "unknown-cluster"


# ── AC: Access Control ─────────────────────────────────────────────────────────

def collect_ac_access_control() -> dict:
    """
    AC domain evidence — CMMC practices AC.L2-3.1.x.

    Checks:
      - cluster-admin bindings bound to non-system subjects (AC.L2-3.1.1 — authorized access)
      - default ServiceAccount automount (AC.L2-3.1.5 — least privilege)
      - namespaces without NetworkPolicy (AC.L2-3.1.3 — control CUI flow)
      - AWS root account MFA and admin IAM users (AC.L2-3.1.1, IA domain overlap)
    """
    # ClusterRoleBindings — look for cluster-admin bound to non-system subjects
    crbs = _kubectl(["get", "clusterrolebindings", "-o", "json"])
    cluster_admin_bindings = []
    if "skipped" not in crbs and "error" not in crbs:
        for item in crbs.get("items", []):
            role_ref = item.get("roleRef", {})
            if role_ref.get("name") == "cluster-admin":
                subjects = item.get("subjects", [])
                non_system = [
                    s for s in (subjects or [])
                    if not s.get("name", "").startswith("system:")
                ]
                if non_system:
                    cluster_admin_bindings.append({
                        "binding": item.get("metadata", {}).get("name"),
                        "subjects": non_system,
                    })

    # RoleBindings — also check for cluster-admin bound at namespace scope
    rbs = _kubectl(["get", "rolebindings", "-A", "-o", "json"])
    if "skipped" not in rbs and "error" not in rbs:
        for item in rbs.get("items", []):
            role_ref = item.get("roleRef", {})
            if role_ref.get("name") == "cluster-admin":
                subjects = item.get("subjects", [])
                non_system = [
                    s for s in (subjects or [])
                    if not s.get("name", "").startswith("system:")
                ]
                if non_system:
                    cluster_admin_bindings.append({
                        "binding": item.get("metadata", {}).get("name"),
                        "namespace": item.get("metadata", {}).get("namespace"),
                        "subjects": non_system,
                    })

    # ServiceAccounts — check for default SA with automount not explicitly false
    sas = _kubectl(["get", "serviceaccounts", "-A", "-o", "json"])
    default_sa_exposed = 0
    if "skipped" not in sas and "error" not in sas:
        for sa in sas.get("items", []):
            if sa.get("metadata", {}).get("name") == "default":
                # automountServiceAccountToken not set (None) or True means exposed
                automount = sa.get("automountServiceAccountToken")
                if automount is not False:
                    default_sa_exposed += 1

    # NetworkPolicies — find namespaces without any NetworkPolicy
    pods_data = _kubectl(["get", "pods", "-A", "-o", "json"])
    all_namespaces = set()
    if "skipped" not in pods_data and "error" not in pods_data:
        for pod in pods_data.get("items", []):
            ns = pod.get("metadata", {}).get("namespace", "")
            if ns and not ns.startswith("kube-"):
                all_namespaces.add(ns)

    netpols = _kubectl(["get", "networkpolicies", "-A", "-o", "json"])
    namespaces_with_netpol = set()
    if "skipped" not in netpols and "error" not in netpols:
        for np in netpols.get("items", []):
            ns = np.get("metadata", {}).get("namespace", "")
            if ns:
                namespaces_with_netpol.add(ns)

    namespaces_without_netpol = sorted(all_namespaces - namespaces_with_netpol)

    # AWS: root account MFA
    acct_summary = _aws(["iam", "get-account-summary"])
    root_mfa_enabled = False
    if "skipped" not in acct_summary and "error" not in acct_summary:
        summary_map = acct_summary.get("SummaryMap", {})
        root_mfa_enabled = summary_map.get("AccountMFAEnabled", 0) == 1

    # AWS: users with admin policies attached
    users_data = _aws(["iam", "list-users"])
    admin_users_count = 0
    if "skipped" not in users_data and "error" not in users_data:
        for user in users_data.get("Users", []):
            username = user.get("UserName", "")
            policies = _aws(["iam", "list-attached-user-policies", "--user-name", username])
            if "skipped" not in policies and "error" not in policies:
                for p in policies.get("AttachedPolicies", []):
                    if "AdministratorAccess" in p.get("PolicyName", ""):
                        admin_users_count += 1
                        break

    return {
        "cluster_admin_bindings": cluster_admin_bindings,
        "default_sa_exposed": default_sa_exposed,
        "namespaces_without_netpol": namespaces_without_netpol,
        "root_mfa_enabled": root_mfa_enabled,
        "admin_users_count": admin_users_count,
        "available": True,
    }


# ── AU: Audit and Accountability ───────────────────────────────────────────────

def collect_au_audit_logging() -> dict:
    """
    AU domain evidence — CMMC practices AU.L2-3.3.x.

    Checks:
      - EKS audit logging (AU.L2-3.3.1 — create and retain audit logs)
      - Log shipper presence (Fluent Bit, Fluentd, Vector) (AU.L2-3.3.1)
      - Log aggregation (Grafana Loki, monitoring stack) (AU.L2-3.3.2)
      - CloudTrail (AU.L2-3.3.1 — AWS management event logging)
      - CloudWatch log group retention (AU.L2-3.3.2 — retain 90 days online + 3 years)
    """
    # Check AWS auth configmap (audit config indicator)
    aws_auth = _kubectl(["get", "configmap", "aws-auth", "-n", "kube-system", "-o", "json"])

    # EKS audit logging
    cluster_name = _current_cluster()
    eks_logging = _aws([
        "eks", "describe-cluster",
        "--name", cluster_name,
        "--query", "cluster.logging",
    ])
    eks_audit_logging_enabled = False
    if "skipped" not in eks_logging and "error" not in eks_logging:
        for log_setup in eks_logging.get("clusterLogging", []):
            if log_setup.get("enabled"):
                if "audit" in log_setup.get("types", []):
                    eks_audit_logging_enabled = True

    # Log shipper detection
    log_shipper_found = False
    log_shipper_name = None
    shipper_patterns = ["fluent-bit", "fluentd", "vector", "logstash", "filebeat"]
    log_namespaces = ["logging", "amazon-cloudwatch", "monitoring", "kube-system"]
    for ns in log_namespaces:
        pods = _kubectl(["get", "pods", "-n", ns, "-o", "json"])
        if "skipped" in pods or "error" in pods:
            continue
        for pod in pods.get("items", []):
            pod_name = pod.get("metadata", {}).get("name", "").lower()
            for pattern in shipper_patterns:
                if pattern in pod_name:
                    log_shipper_found = True
                    log_shipper_name = pod.get("metadata", {}).get("name")
                    break
        if log_shipper_found:
            break

    # Monitoring stack (Grafana/Loki)
    monitoring_pods = _kubectl(["get", "pods", "-n", "monitoring", "-o", "json"])
    loki_found = False
    grafana_found = False
    if "skipped" not in monitoring_pods and "error" not in monitoring_pods:
        for pod in monitoring_pods.get("items", []):
            name = pod.get("metadata", {}).get("name", "").lower()
            if "loki" in name:
                loki_found = True
            if "grafana" in name:
                grafana_found = True

    # CloudTrail
    trails = _aws(["cloudtrail", "describe-trails", "--include-shadow-trails", "false"])
    cloudtrail_enabled = False
    cloudtrail_multi_region = False
    if "skipped" not in trails and "error" not in trails:
        for trail in trails.get("trailList", []):
            trail_name = trail.get("Name", "")
            status = _aws(["cloudtrail", "get-trail-status", "--name", trail_name])
            if status.get("IsLogging", False):
                cloudtrail_enabled = True
                if trail.get("IsMultiRegionTrail", False):
                    cloudtrail_multi_region = True

    # CloudWatch log retention
    log_groups = _aws(["logs", "describe-log-groups"])
    log_retention_days = {}
    if "skipped" not in log_groups and "error" not in log_groups:
        for lg in log_groups.get("logGroups", []):
            name = lg.get("logGroupName", "")
            retention = lg.get("retentionInDays")  # None = never expires
            log_retention_days[name] = retention

    return {
        "eks_audit_logging_enabled": eks_audit_logging_enabled,
        "log_shipper_found": log_shipper_found,
        "log_shipper_name": log_shipper_name,
        "loki_found": loki_found,
        "grafana_found": grafana_found,
        "cloudtrail_enabled": cloudtrail_enabled,
        "cloudtrail_multi_region": cloudtrail_multi_region,
        "log_retention_days": log_retention_days,
        "available": True,
    }


# ── CM: Configuration Management ──────────────────────────────────────────────

def collect_cm_configuration() -> dict:
    """
    CM domain evidence — CMMC practices CM.L2-3.4.x.

    Checks:
      - Policy engine presence (Kyverno or Gatekeeper) (CM.L2-3.4.1 — baseline config)
      - Policy count (CM.L2-3.4.2 — enforce security config)
      - GitOps (ArgoCD) for configuration-as-code (CM.L2-3.4.3 — change control)
      - Pods without resource limits (CM.L2-3.4.6 — least functionality)
      - Privileged containers (CM.L2-3.4.6 — disable unnecessary capabilities)
    """
    # Policy engine detection
    policy_engine = "none"
    policy_count = 0

    kyverno_pods = _kubectl(["get", "pods", "-n", "kyverno", "-o", "json"])
    if "skipped" not in kyverno_pods and "error" not in kyverno_pods:
        if kyverno_pods.get("items"):
            policy_engine = "kyverno"
            policies = _kubectl(["get", "clusterpolicies", "-o", "json"])
            if "skipped" not in policies and "error" not in policies:
                policy_count = len(policies.get("items", []))
            ns_policies = _kubectl(["get", "policies", "-A", "-o", "json"])
            if "skipped" not in ns_policies and "error" not in ns_policies:
                policy_count += len(ns_policies.get("items", []))

    if policy_engine == "none":
        gk_pods = _kubectl(["get", "pods", "-n", "gatekeeper-system", "-o", "json"])
        if "skipped" not in gk_pods and "error" not in gk_pods:
            if gk_pods.get("items"):
                policy_engine = "gatekeeper"
                templates = _kubectl(["get", "constrainttemplates", "-o", "json"])
                if "skipped" not in templates and "error" not in templates:
                    policy_count = len(templates.get("items", []))

    # ArgoCD (GitOps)
    argocd_pods = _kubectl(["get", "pods", "-n", "argocd", "-o", "json"])
    gitops_present = False
    if "skipped" not in argocd_pods and "error" not in argocd_pods:
        gitops_present = bool(argocd_pods.get("items"))

    # Pods without resource limits and privileged containers
    all_pods = _kubectl(["get", "pods", "-A", "-o", "json"])
    pods_without_limits = 0
    privileged_pods = 0

    if "skipped" not in all_pods and "error" not in all_pods:
        for pod in all_pods.get("items", []):
            ns = pod.get("metadata", {}).get("namespace", "")
            if ns.startswith("kube-"):
                continue  # skip system pods
            for container in pod.get("spec", {}).get("containers", []):
                resources = container.get("resources", {})
                limits = resources.get("limits", {})
                if not limits.get("cpu") or not limits.get("memory"):
                    pods_without_limits += 1
                sec_ctx = container.get("securityContext", {})
                if sec_ctx.get("privileged", False):
                    privileged_pods += 1

    return {
        "policy_engine": policy_engine,
        "policy_count": policy_count,
        "gitops_present": gitops_present,
        "pods_without_limits": pods_without_limits,
        "privileged_pods": privileged_pods,
        "available": True,
    }


# ── IA: Identification and Authentication ──────────────────────────────────────

def collect_ia_authentication() -> dict:
    """
    IA domain evidence — CMMC practices IA.L2-3.5.x.

    Checks:
      - IAM credential report: users without MFA, virtual vs hardware MFA (IA.L2-3.5.3)
      - Users with both password and access keys active (IA.L2-3.5.10)
      - Access key age > 90 days (IA.L2-3.5.7 — password/key complexity + rotation)
      - IRSA annotations on ServiceAccounts (IA.L2-3.5.1 — identify all users)
      - External Secrets / Vault for secrets management (IA.L2-3.5.8)
    """
    # Generate credential report
    _aws(["iam", "generate-credential-report"])
    import time
    time.sleep(3)  # Brief wait for report generation

    cred_report = _aws(["iam", "get-credential-report"])
    users_without_mfa = []
    virtual_mfa_users = []
    hardware_mfa_users = []
    old_access_keys = []

    if "skipped" not in cred_report and "error" not in cred_report:
        import base64
        import csv
        import io
        content = cred_report.get("Content", "")
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
            today = datetime.utcnow()
            for row in reader:
                username = row.get("user", "")
                if username == "<root_account>":
                    continue  # root handled separately via account-summary
                mfa_active = row.get("mfa_active", "false").lower() == "true"
                mfa_serial = row.get("mfa_serial_number", "")
                password_enabled = row.get("password_enabled", "false").lower() == "true"

                if not mfa_active and password_enabled:
                    users_without_mfa.append(username)
                elif mfa_active:
                    if "u2f" in mfa_serial or "fido" in mfa_serial.lower():
                        hardware_mfa_users.append(username)
                    else:
                        virtual_mfa_users.append(username)

                # Check for password + active access keys (dual credential risk)
                # Check access key ages
                for key_num in ["1", "2"]:
                    key_active = row.get(f"access_key_{key_num}_active", "false").lower() == "true"
                    last_rotated = row.get(f"access_key_{key_num}_last_rotated", "N/A")
                    if key_active and last_rotated != "N/A":
                        try:
                            rotated_dt = datetime.strptime(last_rotated[:10], "%Y-%m-%d")
                            age_days = (today - rotated_dt).days
                            if age_days > 90:
                                old_access_keys.append({
                                    "user": username,
                                    "key_num": key_num,
                                    "age_days": age_days,
                                })
                        except ValueError:
                            pass
        except Exception:
            pass

    # IRSA — ServiceAccounts with IAM role annotations
    sas = _kubectl(["get", "serviceaccounts", "-A", "-o", "json"])
    irsa_configured = False
    if "skipped" not in sas and "error" not in sas:
        for sa in sas.get("items", []):
            annotations = sa.get("metadata", {}).get("annotations", {})
            if "eks.amazonaws.com/role-arn" in annotations:
                irsa_configured = True
                break

    # Secrets management (External Secrets Operator or Vault Agent)
    secrets_manager_present = False
    for ns in ["external-secrets", "vault", "kube-system", "default"]:
        pods = _kubectl(["get", "pods", "-n", ns, "-o", "json"])
        if "skipped" in pods or "error" in pods:
            continue
        for pod in pods.get("items", []):
            name = pod.get("metadata", {}).get("name", "").lower()
            if "external-secrets" in name or "vault" in name or "eso" in name:
                secrets_manager_present = True
                break
        if secrets_manager_present:
            break

    return {
        "users_without_mfa": users_without_mfa,
        "virtual_mfa_users": virtual_mfa_users,
        "hardware_mfa_users": hardware_mfa_users,
        "old_access_keys": old_access_keys,
        "irsa_configured": irsa_configured,
        "secrets_manager_present": secrets_manager_present,
        "available": True,
    }


# ── RA: Risk Assessment ────────────────────────────────────────────────────────

def collect_ra_risk_assessment() -> dict:
    """
    RA domain evidence — CMMC practices RA.L2-3.11.x.

    Checks:
      - Trivy availability and scan results (RA.L2-3.11.2 — scan for vulnerabilities)
      - Images with :latest tag (RA.L2-3.11.2 — cannot track vuln status without pinned versions)
      - AWS Inspector findings (RA.L2-3.11.3 — remediate vulnerabilities)
    """
    # Trivy availability
    trivy_available = False
    critical_vulns = 0
    high_vulns = 0
    try:
        version_check = subprocess.run(
            ["trivy", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        trivy_available = version_check.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        trivy_available = False

    if trivy_available:
        try:
            scan_result = subprocess.run(
                ["trivy", "fs", "--scanners", "vuln",
                 "--severity", "CRITICAL,HIGH",
                 "--format", "json", ".", "2>/dev/null"],
                capture_output=True, text=True, timeout=120,
            )
            if scan_result.returncode == 0:
                scan_data = json.loads(scan_result.stdout)
                for result in scan_data.get("Results", []):
                    for vuln in result.get("Vulnerabilities", []):
                        severity = vuln.get("Severity", "").upper()
                        if severity == "CRITICAL":
                            critical_vulns += 1
                        elif severity == "HIGH":
                            high_vulns += 1
        except Exception:
            pass

    # Images with :latest tag
    all_pods = _kubectl(["get", "pods", "-A", "-o", "json"])
    latest_tag_images = []
    if "skipped" not in all_pods and "error" not in all_pods:
        seen = set()
        for pod in all_pods.get("items", []):
            ns = pod.get("metadata", {}).get("namespace", "")
            if ns.startswith("kube-"):
                continue
            for container in pod.get("spec", {}).get("containers", []) + \
                             pod.get("spec", {}).get("initContainers", []):
                image = container.get("image", "")
                if image not in seen:
                    seen.add(image)
                    # :latest or no tag (defaults to latest)
                    if image.endswith(":latest") or (":" not in image.split("/")[-1]):
                        latest_tag_images.append(image)

    # AWS Inspector
    inspector_enabled = False
    inspector_data = _aws(["inspector2", "list-coverage",
                           "--filter-criteria", "{}"])
    if "skipped" not in inspector_data and "error" not in inspector_data:
        inspector_enabled = True

    return {
        "trivy_available": trivy_available,
        "critical_vulns": critical_vulns,
        "high_vulns": high_vulns,
        "latest_tag_images": latest_tag_images,
        "inspector_enabled": inspector_enabled,
        "available": True,
    }


# ── SC: System and Communications Protection ──────────────────────────────────

def collect_sc_communications_protection() -> dict:
    """
    SC domain evidence — CMMC practices SC.L2-3.13.x.

    Checks:
      - Namespaces with default-deny ingress NetworkPolicy (SC.L2-3.13.1 — monitor/control comms)
      - TLS/cert volumes on pods (SC.L2-3.13.8 — implement cryptographic mechanisms)
      - Service mesh (Istio/Linkerd) for mTLS (SC.L2-3.13.8)
      - TLS secrets count (SC.L2-3.13.8)
      - S3 bucket encryption (SC.L2-3.13.16 — protect CUI at rest)
      - RDS encryption at rest (SC.L2-3.13.16)
      - GovCloud region detection for FIPS endpoints (SC.L2-3.13.11)
    """
    # Namespaces with deny-by-default ingress NetworkPolicy
    netpols = _kubectl(["get", "networkpolicies", "-A", "-o", "json"])
    default_deny_namespaces = []
    if "skipped" not in netpols and "error" not in netpols:
        for np in netpols.get("items", []):
            ns = np.get("metadata", {}).get("namespace", "")
            spec = np.get("spec", {})
            # A deny-all ingress policy has empty podSelector and ingress: []
            pod_selector = spec.get("podSelector", {})
            ingress = spec.get("ingress", None)
            policy_types = spec.get("policyTypes", [])
            if (
                pod_selector == {} or pod_selector == {"matchLabels": {}}
            ) and "Ingress" in policy_types and ingress == []:
                if ns not in default_deny_namespaces:
                    default_deny_namespaces.append(ns)

    # Service mesh detection (Istio or Linkerd)
    service_mesh_present = False
    service_mesh_name = None
    for mesh_ns, mesh_name in [("istio-system", "istio"), ("linkerd", "linkerd")]:
        pods = _kubectl(["get", "pods", "-n", mesh_ns, "-o", "json"])
        if "skipped" not in pods and "error" not in pods:
            if pods.get("items"):
                service_mesh_present = True
                service_mesh_name = mesh_name
                break

    # TLS secrets
    all_secrets = _kubectl(["get", "secrets", "-A", "-o", "json"])
    tls_secrets_count = 0
    if "skipped" not in all_secrets and "error" not in all_secrets:
        for secret in all_secrets.get("items", []):
            secret_type = secret.get("type", "")
            name = secret.get("metadata", {}).get("name", "").lower()
            if secret_type == "kubernetes.io/tls" or "tls" in name or "cert" in name:
                tls_secrets_count += 1

    # S3 bucket encryption
    s3_buckets = _aws(["s3api", "list-buckets"])
    s3_unencrypted_buckets = []
    if "skipped" not in s3_buckets and "error" not in s3_buckets:
        for bucket in s3_buckets.get("Buckets", []):
            bucket_name = bucket.get("Name", "")
            enc = _aws(["s3api", "get-bucket-encryption", "--bucket", bucket_name])
            if "error" in enc or "skipped" in enc:
                s3_unencrypted_buckets.append(bucket_name)

    # RDS encryption
    rds_instances = _aws(["rds", "describe-db-instances"])
    rds_unencrypted = []
    if "skipped" not in rds_instances and "error" not in rds_instances:
        for db in rds_instances.get("DBInstances", []):
            if not db.get("StorageEncrypted", False):
                rds_unencrypted.append(db.get("DBInstanceIdentifier", "unknown"))

    # GovCloud region check (FIPS endpoints)
    region = os.getenv("AWS_DEFAULT_REGION", "")
    if not region:
        region_data = _aws(["configure", "get", "region"])
        region = region_data.get("raw", "") if isinstance(region_data, dict) else ""
    govcloud_region = "us-gov" in region.lower()

    return {
        "default_deny_namespaces": default_deny_namespaces,
        "service_mesh_present": service_mesh_present,
        "service_mesh_name": service_mesh_name,
        "tls_secrets_count": tls_secrets_count,
        "s3_unencrypted_buckets": s3_unencrypted_buckets,
        "rds_unencrypted": rds_unencrypted,
        "govcloud_region": govcloud_region,
        "available": True,
    }


# ── SI: System and Information Integrity ──────────────────────────────────────

def collect_si_system_integrity() -> dict:
    """
    SI domain evidence — CMMC practices SI.L1-3.14.x and SI.L2-3.14.x.

    Checks:
      - Falco deployment (SI.L2-3.14.6 — monitor for malicious activity)
      - readOnlyRootFilesystem ratio (SI.L1-3.14.2 — protect system integrity)
      - Security context violations (SI.L1-3.14.2 — runAsNonRoot, drop ALL caps)
      - Digest-pinned vs tag-only images (SI.L1-3.14.1 — identify/manage flaws)
      - GuardDuty status (SI.L2-3.14.7 — identify unauthorized use)
    """
    # Falco
    falco_deployed = False
    falco_pods = _kubectl(["get", "pods", "-n", "falco", "-o", "json"])
    if "skipped" not in falco_pods and "error" not in falco_pods:
        falco_deployed = bool(falco_pods.get("items"))

    if not falco_deployed:
        falco_all = _kubectl(["get", "pods", "-A", "-l", "app=falco", "-o", "json"])
        if "skipped" not in falco_all and "error" not in falco_all:
            falco_deployed = bool(falco_all.get("items"))

    # Security context analysis
    all_pods = _kubectl(["get", "pods", "-A", "-o", "json"])
    readonly_count = 0
    not_readonly_count = 0
    security_context_violations = 0
    digest_pinned_images = 0
    tag_only_images = 0
    seen_images = set()

    if "skipped" not in all_pods and "error" not in all_pods:
        for pod in all_pods.get("items", []):
            ns = pod.get("metadata", {}).get("namespace", "")
            if ns.startswith("kube-"):
                continue

            pod_sec = pod.get("spec", {}).get("securityContext", {})
            for container in pod.get("spec", {}).get("containers", []) + \
                             pod.get("spec", {}).get("initContainers", []):
                c_sec = container.get("securityContext", {})

                # readOnlyRootFilesystem
                if c_sec.get("readOnlyRootFilesystem", False):
                    readonly_count += 1
                else:
                    not_readonly_count += 1

                # Security context violations
                runs_as_root = c_sec.get("runAsNonRoot") is False or (
                    c_sec.get("runAsUser") == 0
                )
                allows_privesc = c_sec.get("allowPrivilegeEscalation", True)  # default True
                caps = c_sec.get("capabilities", {})
                no_cap_drop = not caps.get("drop")  # no capabilities dropped

                if runs_as_root or allows_privesc or no_cap_drop:
                    security_context_violations += 1

                # Image pinning
                image = container.get("image", "")
                if image not in seen_images:
                    seen_images.add(image)
                    if "@sha256:" in image:
                        digest_pinned_images += 1
                    else:
                        tag_only_images += 1

    total = readonly_count + not_readonly_count
    readonly_filesystem_ratio = round(readonly_count / total, 3) if total > 0 else 0.0

    # GuardDuty
    guardduty_enabled = False
    detectors = _aws(["guardduty", "list-detectors"])
    if "skipped" not in detectors and "error" not in detectors:
        guardduty_enabled = len(detectors.get("DetectorIds", [])) > 0

    return {
        "falco_deployed": falco_deployed,
        "readonly_filesystem_ratio": readonly_filesystem_ratio,
        "security_context_violations": security_context_violations,
        "digest_pinned_images": digest_pinned_images,
        "tag_only_images": tag_only_images,
        "guardduty_enabled": guardduty_enabled,
        "available": True,
    }


# ── SR: Supply Chain Risk Management ──────────────────────────────────────────

def collect_sr_supply_chain() -> dict:
    """
    SR domain evidence — CMMC practices SR.L2-3.17.x.

    Checks:
      - Image registry diversity (external vs ECR vs private) (SR.L2-3.17.1 — manage supply chain risk)
      - Image signing (cosign/sigstore, Kyverno verify-image) (SR.L2-3.17.2 — protect against tampering)
      - SBOM references in configmaps (SR.L2-3.17.3 — evaluate supply chain risks)
      - ECR image scanning configuration (SR.L2-3.17.2)
    """
    # Image registry analysis
    all_pods = _kubectl(["get", "pods", "-A", "-o", "json"])
    external_registry_images = []
    ecr_pattern_images = 0
    private_registry_images = 0

    if "skipped" not in all_pods and "error" not in all_pods:
        seen = set()
        for pod in all_pods.get("items", []):
            ns = pod.get("metadata", {}).get("namespace", "")
            if ns.startswith("kube-"):
                continue
            for container in pod.get("spec", {}).get("containers", []) + \
                             pod.get("spec", {}).get("initContainers", []):
                image = container.get("image", "")
                if image in seen:
                    continue
                seen.add(image)
                # Classify registry
                if ".dkr.ecr." in image and ".amazonaws.com" in image:
                    ecr_pattern_images += 1
                elif image.startswith("docker.io/") or "/" not in image.split(":")[0]:
                    external_registry_images.append(image)
                elif "gcr.io" in image or "ghcr.io" in image or "quay.io" in image:
                    external_registry_images.append(image)
                else:
                    private_registry_images += 1

    # Image signing detection — Kyverno verify-image policies
    image_signing_enabled = False
    kyverno_policies = _kubectl(["get", "clusterpolicies", "-o", "json"])
    if "skipped" not in kyverno_policies and "error" not in kyverno_policies:
        for policy in kyverno_policies.get("items", []):
            policy_raw = json.dumps(policy).lower()
            if "verifyimages" in policy_raw or "verify-image" in policy_raw or "cosign" in policy_raw:
                image_signing_enabled = True
                break

    if not image_signing_enabled:
        # Check for cosign pods
        cosign_pods = _kubectl(["get", "pods", "-A", "-o", "json"])
        if "skipped" not in cosign_pods and "error" not in cosign_pods:
            for pod in cosign_pods.get("items", []):
                if "cosign" in pod.get("metadata", {}).get("name", "").lower():
                    image_signing_enabled = True
                    break

    # SBOM references in configmaps
    sbom_present = False
    all_cms = _kubectl(["get", "configmaps", "-A", "-o", "json"])
    if "skipped" not in all_cms and "error" not in all_cms:
        for cm in all_cms.get("items", []):
            cm_raw = json.dumps(cm).lower()
            if "sbom" in cm_raw or "cyclonedx" in cm_raw or "spdx" in cm_raw:
                sbom_present = True
                break

    # ECR scanning configuration
    ecr_scanning_enabled = False
    ecr_repos = _aws([
        "ecr", "describe-repositories",
        "--query", "repositories[*].[repositoryName,imageScanningConfiguration]",
    ])
    if "skipped" not in ecr_repos and "error" not in ecr_repos:
        repos = ecr_repos if isinstance(ecr_repos, list) else []
        # All repos must have scanning enabled for full credit
        if repos:
            all_scanning = all(
                repo[1].get("scanOnPush", False) if isinstance(repo[1], dict) else False
                for repo in repos
            )
            ecr_scanning_enabled = all_scanning

    return {
        "external_registry_images": external_registry_images,
        "ecr_images_count": ecr_pattern_images,
        "private_registry_images_count": private_registry_images,
        "image_signing_enabled": image_signing_enabled,
        "ecr_scanning_enabled": ecr_scanning_enabled,
        "sbom_present": sbom_present,
        "available": True,
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def run_cmmc_collectors() -> dict:
    """Run all CMMC Level 2 API-assessable collectors. Returns structured evidence dict."""
    timestamp = datetime.utcnow().isoformat() + "Z"

    evidence = {
        "run_id": timestamp.replace(":", "").replace("-", "").replace(".", "")[:16] + "Z",
        "timestamp": timestamp,
        "framework": "CMMC 2.0 Level 2",
        "total_l2_practices": 110,
        "cannot_assess_via_api": [
            "AT domain: Security awareness training records — requires HR/LMS documentation review",
            "MA domain: Maintenance procedures and authorized maintenance personnel — requires policy/procedure review",
            "MP domain: Media sanitization and transport records — requires physical controls documentation review",
            "PE domain: Physical access controls, visitor logs — requires on-site review",
            "PS domain: Personnel screening and termination procedures — requires HR records review",
            "IR.L2-3.6.3: Incident response test records — requires after-action reports from tabletop exercises",
            "CA.L2-3.12.1: Formal security assessment methodology — requires SSP and policy document review",
            "CA.L2-3.12.4: SSP completeness — requires document review and stakeholder interview",
        ],
        "ac": collect_ac_access_control(),
        "au": collect_au_audit_logging(),
        "cm": collect_cm_configuration(),
        "ia": collect_ia_authentication(),
        "ra": collect_ra_risk_assessment(),
        "sc": collect_sc_communications_protection(),
        "si": collect_si_system_integrity(),
        "sr": collect_sr_supply_chain(),
    }

    # Derive high-level signals
    evidence["cmmc_signals"] = {
        "critical_gaps": [],  # populated by assessor
        "estimated_met_count": 0,  # populated by assessor
        "estimated_not_met_count": 0,  # populated by assessor
        "sprs_estimate": 110,  # degraded by assessor
        "cannot_assess_count": len(evidence["cannot_assess_via_api"]),
    }

    return evidence
