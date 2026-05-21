"""
AU-family collectors — Step 1 of M-21-31 logging maturity assessment.

Mirrors the evidence collection phase of:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-21-31-playbooks/01-assess-logging-maturity.md

Standalone module — no CrewAI dependency, no LLM. Pure AWS CLI + kubectl.

EL determination thresholds:
  EL0: no CloudTrail active AND no EKS logging AND no K8s audit policy
  EL1: CloudTrail active + EKS logging enabled + retention >= 30 days
  EL2: EL1 + Fluent Bit running + Loki/SIEM detected + retention >= 90 days + log validation
  EL3: EL2 + SIEM detected + retention >= 365 days hot + cross-system correlation capability
"""

import json
import subprocess


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


# ── AU-2: Event Logging ────────────────────────────────────────────────────────

def collect_eks_logging_status() -> dict:
    """
    Check which EKS control plane log types are enabled. EL1 requires all 5.

    EKS log types: api, audit, authenticator, controllerManager, scheduler
    M-21-31 EL1: all five must be enabled.
    """
    cluster_name = _current_cluster()
    data = _aws([
        "eks", "describe-cluster",
        "--name", cluster_name,
        "--query", "cluster.logging",
    ])
    if "skipped" in data or "error" in data:
        return {**data, "cluster": cluster_name}

    required_types = {"api", "audit", "authenticator", "controllerManager", "scheduler"}
    enabled_types = set()

    cluster_logging = data if isinstance(data, dict) else {}
    for log_setup in cluster_logging.get("clusterLogging", []):
        if log_setup.get("enabled"):
            for t in log_setup.get("types", []):
                enabled_types.add(t)

    missing = sorted(required_types - enabled_types)
    return {
        "cluster": cluster_name,
        "enabled_types": sorted(enabled_types),
        "missing_types": missing,
        "all_five_enabled": len(missing) == 0,
        "el1_satisfied": len(missing) == 0,
    }


def collect_k8s_audit_policy() -> dict:
    """
    Check if kube-apiserver has an audit policy configured. EL1 requirement.

    Checks for --audit-policy-file flag in kube-apiserver pod command args.
    Also attempts to read the policy file path and log path.
    """
    data = _kubectl([
        "get", "pods", "-n", "kube-system",
        "-l", "component=kube-apiserver",
        "-o", "json",
    ])
    if "skipped" in data or "error" in data:
        return {**data, "audit_policy_found": False, "policy_file": None, "log_path": None}

    audit_policy_file = None
    audit_log_path = None

    for item in data.get("items", []):
        for container in item.get("spec", {}).get("containers", []):
            for arg in container.get("command", []) + container.get("args", []):
                if arg.startswith("--audit-policy-file="):
                    audit_policy_file = arg.split("=", 1)[1]
                if arg.startswith("--audit-log-path="):
                    audit_log_path = arg.split("=", 1)[1]

    # EKS manages the API server — audit policy is managed by AWS, not visible via kubectl
    # If no kube-system pods match, infer from EKS managed cluster context
    is_eks = "eks" in _current_cluster().lower() or not data.get("items")
    if is_eks and not audit_policy_file:
        return {
            "note": "EKS managed control plane — audit policy is AWS-managed, enable via EKS logging config",
            "audit_policy_found": False,
            "policy_file": None,
            "log_path": None,
            "is_eks_managed": True,
        }

    return {
        "audit_policy_found": audit_policy_file is not None,
        "policy_file": audit_policy_file,
        "log_path": audit_log_path,
        "is_eks_managed": False,
    }


# ── AU-11: Audit Record Retention ─────────────────────────────────────────────

_EL1_RETENTION_DAYS = 365   # 12 months
_EL2_HOT_RETENTION_DAYS = 90
_EL3_HOT_RETENTION_DAYS = 365


def collect_cloudwatch_log_groups() -> list[dict]:
    """
    List all CloudWatch log groups with retention settings.

    Retention thresholds (M-21-31):
      EL1: retentionInDays >= 365 (12 months total)
      EL2: retentionInDays >= 90 hot (S3 export satisfies cold tier)
      EL3: retentionInDays >= 365 hot

    retentionInDays == None means logs are kept forever (compliant for all ELs on retention).
    """
    data = _aws(["logs", "describe-log-groups"])
    if "skipped" in data or "error" in data:
        return [data]

    groups = []
    for lg in data.get("logGroups", []):
        name = lg.get("logGroupName", "")
        retention = lg.get("retentionInDays")  # None = never expires

        # None = indefinite = fully compliant; otherwise check thresholds
        if retention is None:
            el1_ok = el2_ok = el3_ok = True
        else:
            el1_ok = retention >= _EL1_RETENTION_DAYS
            el2_ok = retention >= _EL2_HOT_RETENTION_DAYS
            el3_ok = retention >= _EL3_HOT_RETENTION_DAYS

        groups.append({
            "name": name,
            "retention_days": retention,  # None = never expires
            "el_compliant": {
                "EL1": el1_ok,
                "EL2": el2_ok,
                "EL3": el3_ok,
            },
        })
    return groups


# ── AU-2 / CloudTrail ─────────────────────────────────────────────────────────

def collect_cloudtrail_status() -> dict:
    """
    Check CloudTrail configuration. EL1 requires centralized management event logging.

    Checks:
      - At least one trail active and logging
      - Multi-region trail present (broader coverage)
      - Log file validation enabled (AU-9)
    """
    trails_data = _aws(["cloudtrail", "describe-trails"])
    if "skipped" in trails_data or "error" in trails_data:
        return {**trails_data, "any_active": False, "multi_region_trail": False, "log_validation": False}

    trails = trails_data.get("trailList", [])
    any_active = False
    multi_region = False
    log_validation = False
    trail_details = []

    for trail in trails:
        trail_name = trail.get("Name", "")
        home_region = trail.get("HomeRegion", "")
        is_multi = trail.get("IsMultiRegionTrail", False)

        # Get trail status (logging yes/no)
        status = _aws(["cloudtrail", "get-trail-status", "--name", trail_name])
        is_logging = status.get("IsLogging", False) if "skipped" not in status else False

        if is_logging:
            any_active = True
        if is_multi and is_logging:
            multi_region = True
        if trail.get("LogFileValidationEnabled", False):
            log_validation = True

        trail_details.append({
            "name": trail_name,
            "home_region": home_region,
            "is_multi_region": is_multi,
            "is_logging": is_logging,
            "log_file_validation": trail.get("LogFileValidationEnabled", False),
            "s3_bucket": trail.get("S3BucketName", ""),
            "include_global_service_events": trail.get("IncludeGlobalServiceEvents", False),
        })

    return {
        "trails": trail_details,
        "any_active": any_active,
        "multi_region_trail": multi_region,
        "log_validation": log_validation,
        "el1_cloudtrail_satisfied": any_active,
    }


# ── AU-12: Audit Record Generation (pipeline health) ─────────────────────────

def collect_fluent_bit_status() -> dict:
    """
    Check if Fluent Bit DaemonSet is running on all nodes. EL2 pipeline requirement.

    Looks in common namespaces: logging, amazon-cloudwatch, monitoring, kube-system.
    """
    namespaces_to_check = ["logging", "amazon-cloudwatch", "monitoring", "kube-system"]
    for ns in namespaces_to_check:
        data = _kubectl(["get", "ds", "-n", ns, "-o", "json"])
        if "skipped" in data or "error" in data:
            continue
        for ds in data.get("items", []):
            name = ds.get("metadata", {}).get("name", "")
            if "fluent" in name.lower():
                status = ds.get("status", {})
                desired = status.get("desiredNumberScheduled", 0)
                ready = status.get("numberReady", 0)
                return {
                    "found": True,
                    "name": name,
                    "namespace": ns,
                    "desired": desired,
                    "ready": ready,
                    "all_nodes_covered": desired > 0 and ready == desired,
                }
    # Check for amazon-cloudwatch-agent as alternative
    data = _kubectl(["get", "ds", "-A", "-o", "json"])
    if "skipped" not in data and "error" not in data:
        for ds in data.get("items", []):
            name = ds.get("metadata", {}).get("name", "")
            if "cloudwatch" in name.lower() or "fluent" in name.lower():
                status = ds.get("status", {})
                desired = status.get("desiredNumberScheduled", 0)
                ready = status.get("numberReady", 0)
                return {
                    "found": True,
                    "name": name,
                    "namespace": ds.get("metadata", {}).get("namespace", ""),
                    "desired": desired,
                    "ready": ready,
                    "all_nodes_covered": desired > 0 and ready == desired,
                }
    return {
        "found": False,
        "desired": 0,
        "ready": 0,
        "all_nodes_covered": False,
    }


def collect_loki_status() -> dict:
    """
    Check if Loki is running. EL2 log storage requirement.

    Loki provides the hot-tier log storage that EL2 querying requires.
    """
    data = _kubectl([
        "get", "pods", "-A",
        "-l", "app.kubernetes.io/name=loki",
        "-o", "json",
    ])
    if "skipped" in data or "error" in data:
        return {**data, "found": False, "running_pods": 0, "total_pods": 0}

    pods = data.get("items", [])
    running = sum(
        1 for p in pods
        if p.get("status", {}).get("phase") == "Running"
    )
    return {
        "found": len(pods) > 0,
        "running_pods": running,
        "total_pods": len(pods),
    }


def collect_siem_status() -> dict:
    """
    Check for SIEM integration (Splunk/ELK forwarder). EL3 requirement.

    Scans for known SIEM forwarder patterns across all namespaces:
      - Splunk Universal Forwarder
      - Elasticsearch / OpenSearch beat or forwarder
      - Generic SIEM configmap labels
    """
    siem_patterns = [
        ("splunk", "splunk"),
        ("elastic", "elasticsearch"),
        ("filebeat", "elasticsearch"),
        ("logstash", "elasticsearch"),
        ("opensearch-forwarder", "opensearch"),
    ]

    # Check pod labels
    pods_data = _kubectl(["get", "pods", "-A", "-o", "json"])
    if "skipped" not in pods_data and "error" not in pods_data:
        for pod in pods_data.get("items", []):
            pod_name = pod.get("metadata", {}).get("name", "").lower()
            ns = pod.get("metadata", {}).get("namespace", "")
            for pattern, siem_type in siem_patterns:
                if pattern in pod_name:
                    return {
                        "siem_detected": True,
                        "type": siem_type,
                        "namespace": ns,
                        "pod_name": pod.get("metadata", {}).get("name"),
                    }

    # Check configmaps for SIEM references
    cm_data = _kubectl(["get", "configmaps", "-A", "-o", "json"])
    if "skipped" not in cm_data and "error" not in cm_data:
        for cm in cm_data.get("items", []):
            cm_name = cm.get("metadata", {}).get("name", "").lower()
            ns = cm.get("metadata", {}).get("namespace", "")
            for pattern, siem_type in siem_patterns:
                if pattern in cm_name:
                    return {
                        "siem_detected": True,
                        "type": siem_type,
                        "namespace": ns,
                        "configmap_name": cm.get("metadata", {}).get("name"),
                    }

    return {
        "siem_detected": False,
        "type": None,
        "namespace": None,
    }


def collect_falco_forwarding() -> dict:
    """
    Check if Falco is running and forwarding to log pipeline. EL2/EL3 runtime detection.

    Falco implements SI-4 (System Monitoring) and feeds AU-12 when configured
    to forward alerts to the log pipeline.
    """
    data = _kubectl(["get", "pods", "-n", "falco", "-o", "json"])
    if "skipped" in data or "error" in data:
        # Also check in default/monitoring namespaces
        data = _kubectl(["get", "pods", "-A", "-l", "app=falco", "-o", "json"])
        if "skipped" in data or "error" in data:
            return {
                "falco_running": False,
                "pod_count": 0,
                "expected_on_all_nodes": False,
            }

    pods = data.get("items", [])
    running_pods = [
        p for p in pods
        if p.get("status", {}).get("phase") == "Running"
    ]

    # Determine node count for coverage assessment
    nodes_data = _kubectl(["get", "nodes", "-o", "json"])
    node_count = len(nodes_data.get("items", [])) if "skipped" not in nodes_data else 0

    return {
        "falco_running": len(running_pods) > 0,
        "pod_count": len(running_pods),
        "expected_on_all_nodes": node_count > 0 and len(running_pods) == node_count,
        "node_count": node_count,
    }


# ── AU-9: Protection of Audit Information ─────────────────────────────────────

def collect_log_group_encryption() -> dict:
    """
    Check if CloudWatch log groups have KMS encryption. AU-9 protection requirement.
    """
    data = _aws(["logs", "describe-log-groups"])
    if "skipped" in data or "error" in data:
        return {**data, "encrypted_count": 0, "total_count": 0, "all_encrypted": False}

    groups = data.get("logGroups", [])
    encrypted = [g for g in groups if g.get("kmsKeyId")]
    return {
        "encrypted_count": len(encrypted),
        "total_count": len(groups),
        "all_encrypted": len(groups) > 0 and len(encrypted) == len(groups),
        "unencrypted_examples": [
            g.get("logGroupName") for g in groups if not g.get("kmsKeyId")
        ][:5],
    }


# ── EL signal computation ──────────────────────────────────────────────────────

def _compute_el_signals(
    eks_logging: dict,
    cloudtrail: dict,
    k8s_audit: dict,
    log_groups: list[dict],
    fluent_bit: dict,
    loki: dict,
    siem: dict,
    falco: dict,
) -> dict:
    """
    Derive EL0/EL1/EL2/EL3 signals from collected evidence.

    These are signals, not determinations — the assessor agent makes the final call.
    """
    indicators_el0 = []

    # EL1 checks
    cloudtrail_active = cloudtrail.get("any_active", False) and "skipped" not in cloudtrail
    eks_logging_ok = eks_logging.get("all_five_enabled", False) and "skipped" not in eks_logging
    eks_is_managed = eks_logging.get("skipped") or k8s_audit.get("is_eks_managed", False)

    # Retention check — worst case across all log groups
    worst_retention = None
    for lg in log_groups:
        if isinstance(lg, dict) and "retention_days" in lg:
            r = lg["retention_days"]
            if r is not None:
                if worst_retention is None or r < worst_retention:
                    worst_retention = r
    # None means never expires — treat as max retention
    if worst_retention is None and log_groups and not any("skipped" in lg for lg in log_groups if isinstance(lg, dict)):
        worst_retention = 99999  # indefinite

    el1_retention_ok = worst_retention is None or (worst_retention is not None and worst_retention >= _EL1_RETENTION_DAYS)
    el2_retention_ok = worst_retention is None or (worst_retention is not None and worst_retention >= _EL2_HOT_RETENTION_DAYS)
    el3_retention_ok = worst_retention is None or (worst_retention is not None and worst_retention >= _EL3_HOT_RETENTION_DAYS)

    if not cloudtrail_active:
        indicators_el0.append("No active CloudTrail trail detected")
    if not eks_logging_ok and not eks_is_managed:
        indicators_el0.append("EKS control plane logging not fully enabled (requires all 5 types)")
    if not cloudtrail_active and not eks_logging_ok:
        indicators_el0.append("No centralized event logging detected — likely EL0")

    # EL1: CloudTrail active + EKS logging + some retention
    el1_satisfied = cloudtrail_active and (eks_logging_ok or eks_is_managed) and el1_retention_ok

    # EL2: EL1 + Fluent Bit + Loki or SIEM + 90d retention + log validation
    fluent_bit_ok = fluent_bit.get("found", False) and fluent_bit.get("all_nodes_covered", False)
    log_aggregation_ok = loki.get("found", False) or siem.get("siem_detected", False)
    log_validation_ok = cloudtrail.get("log_validation", False)
    el2_satisfied = (
        el1_satisfied
        and fluent_bit_ok
        and log_aggregation_ok
        and el2_retention_ok
        and log_validation_ok
    )

    # EL3: EL2 + SIEM + 365d hot retention + Falco
    siem_ok = siem.get("siem_detected", False)
    falco_ok = falco.get("falco_running", False)
    el3_satisfied = el2_satisfied and siem_ok and el3_retention_ok and falco_ok

    if el3_satisfied:
        likely_el = "EL3"
    elif el2_satisfied:
        likely_el = "EL2"
    elif el1_satisfied:
        likely_el = "EL1"
    else:
        likely_el = "EL0"

    return {
        "likely_el": likely_el,
        "el0_indicators": indicators_el0,
        "el1_satisfied": el1_satisfied,
        "el2_satisfied": el2_satisfied,
        "el3_satisfied": el3_satisfied,
        "detail": {
            "cloudtrail_active": cloudtrail_active,
            "eks_logging_all_types": eks_logging_ok,
            "eks_is_managed": bool(eks_is_managed),
            "worst_retention_days": worst_retention if worst_retention != 99999 else "indefinite",
            "el1_retention_ok": el1_retention_ok,
            "el2_retention_ok": el2_retention_ok,
            "el3_retention_ok": el3_retention_ok,
            "fluent_bit_all_nodes": fluent_bit_ok,
            "log_aggregation_present": log_aggregation_ok,
            "cloudtrail_log_validation": log_validation_ok,
            "siem_present": siem_ok,
            "falco_running": falco_ok,
        },
    }


# ── AU family runner ───────────────────────────────────────────────────────────

def run_au_collectors() -> dict:
    """
    Full AU-family evidence pass — Step 1 of M-21-31 logging maturity assessment.

    Runs all collectors and aggregates into control-mapped evidence with EL signals.
    """
    # Collect raw data
    eks_logging = collect_eks_logging_status()
    k8s_audit = collect_k8s_audit_policy()
    cloudtrail = collect_cloudtrail_status()
    log_groups = collect_cloudwatch_log_groups()
    fluent_bit = collect_fluent_bit_status()
    loki = collect_loki_status()
    siem = collect_siem_status()
    falco = collect_falco_forwarding()
    log_encryption = collect_log_group_encryption()

    # Derive worst-case retention for reporting
    worst_retention = None
    for lg in log_groups:
        if isinstance(lg, dict) and "retention_days" in lg:
            r = lg["retention_days"]
            if r is not None:
                if worst_retention is None or r < worst_retention:
                    worst_retention = r

    # Determine query capability
    if siem.get("siem_detected"):
        query_capability = siem.get("type", "siem")
    elif loki.get("found"):
        query_capability = "loki"
    else:
        query_capability = "none"

    # Detect structured logging from audit policy level
    audit_policy_level = "None"
    if k8s_audit.get("audit_policy_found"):
        audit_policy_level = "RequestResponse"  # Assume full if explicitly configured
    elif k8s_audit.get("is_eks_managed"):
        audit_policy_level = "Metadata"  # EKS default audit level

    # Structured evidence mapped to NIST AU controls
    evidence = {
        "au2_event_logging": {
            "eks_logging": eks_logging,
            "k8s_audit_policy": k8s_audit,
            "cloudtrail": cloudtrail,
        },
        "au3_record_content": {
            "audit_policy_level": audit_policy_level,
            "structured_logging_detected": k8s_audit.get("audit_policy_found", False)
                or k8s_audit.get("is_eks_managed", False),
        },
        "au6_review_analysis": {
            "siem": siem,
            "alerting_configured": siem.get("siem_detected", False) or falco.get("falco_running", False),
        },
        "au7_reduction_reporting": {
            "log_query_capability": query_capability,
        },
        "au9_protection": {
            "cloudtrail_log_validation": cloudtrail.get("log_validation", False),
            "log_group_encryption": log_encryption,
        },
        "au11_retention": {
            "log_groups": log_groups,
            "worst_retention_days": worst_retention,  # None = indefinite
            "el1_compliant": worst_retention is None or (worst_retention is not None and worst_retention >= _EL1_RETENTION_DAYS),
            "el2_compliant": worst_retention is None or (worst_retention is not None and worst_retention >= _EL2_HOT_RETENTION_DAYS),
            "el3_compliant": worst_retention is None or (worst_retention is not None and worst_retention >= _EL3_HOT_RETENTION_DAYS),
        },
        "au12_generation": {
            "fluent_bit": fluent_bit,
            "loki": loki,
            "falco": falco,
            "pipeline_complete": fluent_bit.get("all_nodes_covered", False)
                and (loki.get("found", False) or siem.get("siem_detected", False)),
        },
        "el_signals": _compute_el_signals(
            eks_logging=eks_logging,
            cloudtrail=cloudtrail,
            k8s_audit=k8s_audit,
            log_groups=log_groups,
            fluent_bit=fluent_bit,
            loki=loki,
            siem=siem,
            falco=falco,
        ),
    }

    return evidence
