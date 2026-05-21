"""
ICAM collectors -- Step 1 of M-24-04 ICAM compliance assessment.

Encodes evidence collection for:
  GP-CONSULTING/07-OMB-LENS/playbooks/M-24-04-playbooks/01-implement-icam-authentication.md

Standalone module -- no CrewAI dependency, no LLM. Pure kubectl + AWS CLI.

M-24-04 ICAM service mandate summary:
  Authentication:     Phishing-resistant MFA (FIDO2/WebAuthn or PIV/CAC) by FY2024
  Identity Proofing:  IAL2 required before privileged account creation (cannot be assessed via API)
  Credentialing:      No long-lived static credentials; automated rotation required
  Authorization:      Full account lifecycle; least privilege; quarterly privileged review
  Federation:         OIDC/SAML federation; TLS-only auth flows
"""

import base64
import csv
import io
import json
import subprocess
from datetime import datetime, timezone


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


def _days_since(date_str: str | None) -> int | None:
    """Return days elapsed since an ISO date string, or None if unparseable."""
    if not date_str or date_str in ("N/A", "not_supported", "no_information"):
        return None
    try:
        # AWS credential report dates: "2024-01-15T10:00:00+00:00" or "2024-01-15"
        for fmt in ("%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str[:19], fmt[:len(date_str[:19])])
                dt = dt.replace(tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - dt).days
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _get_credential_report_rows() -> list[dict] | dict:
    """
    Generate and retrieve AWS IAM credential report as parsed CSV rows.
    Returns list of row dicts on success, or {"skipped"/"error": ...} on failure.
    """
    # Trigger generation -- may already be fresh
    _aws(["iam", "generate-credential-report"])
    report = _aws(["iam", "get-credential-report"])
    if "skipped" in report or "error" in report:
        return report
    content_b64 = report.get("Content", "")
    if not content_b64:
        return {"error": "credential report Content field is empty"}
    try:
        content = base64.b64decode(content_b64).decode()
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    except Exception as e:
        return {"error": f"credential report parse failed: {e}"}


# ── IA-2: Authentication / MFA ────────────────────────────────────────────────

def collect_mfa_configuration() -> dict:
    """
    IA-2: Assess MFA configuration signals.
    M-24-04 requires phishing-resistant MFA -- TOTP/SMS do NOT satisfy the mandate.
    Virtual MFA (TOTP) has SerialNumber prefix: arn:...:mfa/
    FIDO2/U2F hardware tokens: SerialNumber prefix: arn:...:u2f/ or contains "FIDO"

    Returns:
      oidc_configured (bool), oidc_issuer (str|None),
      aws_mfa_enabled_users (int), aws_mfa_disabled_users (int),
      mfa_device_types (list), phishing_resistant_detected (bool),
      compliance_assessment: "compliant"|"partial"|"non_compliant"
    """
    # Check if cluster OIDC is configured (authentication signal for k8s)
    oidc_raw = _kubectl(["get", "--raw", "/.well-known/openid-configuration"])
    if "skipped" in oidc_raw or "error" in oidc_raw:
        oidc_configured = False
        oidc_issuer = None
    else:
        oidc_issuer = oidc_raw.get("issuer")
        oidc_configured = bool(oidc_issuer)

    # Parse credential report for MFA status
    rows = _get_credential_report_rows()
    if isinstance(rows, dict):
        # skipped or error
        return {
            "oidc_configured": oidc_configured,
            "oidc_issuer": oidc_issuer,
            **rows,
            "compliance_assessment": "cannot_assess",
        }

    mfa_enabled_count = 0
    mfa_disabled_count = 0
    console_users = 0
    for row in rows:
        if row.get("user") == "<root_account>":
            continue
        if row.get("password_enabled") == "true":
            console_users += 1
            if row.get("mfa_active") == "true":
                mfa_enabled_count += 1
            else:
                mfa_disabled_count += 1

    # Check MFA device types for phishing resistance
    mfa_devices_raw = _aws(["iam", "list-virtual-mfa-devices",
                             "--assignment-status", "Assigned"])
    virtual_mfa_count = 0
    fido2_count = 0
    mfa_device_types = []

    if "skipped" not in mfa_devices_raw and "error" not in mfa_devices_raw:
        for device in mfa_devices_raw.get("VirtualMFADevices", []):
            serial = device.get("SerialNumber", "")
            if "u2f" in serial.lower() or "fido" in serial.upper():
                fido2_count += 1
                mfa_device_types.append("FIDO2/U2F (phishing-resistant)")
            else:
                virtual_mfa_count += 1
                mfa_device_types.append("VIRTUAL/TOTP (non-compliant with M-24-04)")

    phishing_resistant_detected = fido2_count > 0 and virtual_mfa_count == 0

    # Assessment logic
    if mfa_disabled_count > 0:
        compliance = "non_compliant"
    elif virtual_mfa_count > 0 and fido2_count == 0:
        # MFA enabled but only TOTP -- partial (MFA present, not phishing-resistant)
        compliance = "partial"
    elif fido2_count > 0 and virtual_mfa_count == 0 and mfa_disabled_count == 0:
        compliance = "compliant"
    elif console_users == 0:
        # No console users -- not applicable via this signal
        compliance = "compliant"
    else:
        compliance = "partial"

    return {
        "oidc_configured": oidc_configured,
        "oidc_issuer": oidc_issuer,
        "aws_mfa_enabled_users": mfa_enabled_count,
        "aws_mfa_disabled_users": mfa_disabled_count,
        "console_users_assessed": console_users,
        "virtual_mfa_devices": virtual_mfa_count,
        "fido2_devices": fido2_count,
        "mfa_device_types": list(set(mfa_device_types)),
        "phishing_resistant_detected": phishing_resistant_detected,
        "compliance_assessment": compliance,
    }


# ── IA-5: Credentialing / Key Ages ────────────────────────────────────────────

def collect_iam_key_ages() -> dict:
    """
    IA-5: Long-lived static credentials are a mandate violation.
    M-24-04 prohibits long-term IAM access keys for privileged access.
    Best practice: 90-day rotation; keys older than 365 days are critical violations.

    Returns:
      users_with_keys (list of {username, key_age_days, last_used_days, compliant: bool}),
      keys_over_90_days (int), keys_over_365_days (int),
      keys_never_used (int), highest_privilege_with_key (str|None)
    """
    rows = _get_credential_report_rows()
    if isinstance(rows, dict):
        return rows

    users_with_keys = []
    keys_over_90 = 0
    keys_over_365 = 0
    keys_never_used = 0

    for row in rows:
        username = row.get("user", "")
        if username == "<root_account>":
            continue

        for key_num in ("1", "2"):
            active_field = f"access_key_{key_num}_active"
            rotated_field = f"access_key_{key_num}_last_rotated"
            used_field = f"access_key_{key_num}_last_used_date"

            if row.get(active_field) != "true":
                continue

            rotated_str = row.get(rotated_field)
            used_str = row.get(used_field)

            key_age_days = _days_since(rotated_str)
            last_used_days = _days_since(used_str)

            never_used = (
                used_str in (None, "N/A", "no_information", "")
                or last_used_days is None
            )
            if never_used:
                keys_never_used += 1

            compliant = key_age_days is not None and key_age_days <= 90
            entry = {
                "username": username,
                "key_number": key_num,
                "key_age_days": key_age_days,
                "last_used_days": last_used_days,
                "never_used": never_used,
                "compliant": compliant,
            }
            users_with_keys.append(entry)

            if key_age_days is not None:
                if key_age_days > 365:
                    keys_over_365 += 1
                if key_age_days > 90:
                    keys_over_90 += 1

    # Identify highest-privilege user with a key (admin-group membership check)
    highest_privilege_with_key = None
    admin_groups_raw = _aws(["iam", "list-groups",
                              "--query", "Groups[*].GroupName"])
    admin_groups = []
    if "skipped" not in admin_groups_raw and "error" not in admin_groups_raw:
        all_groups = admin_groups_raw if isinstance(admin_groups_raw, list) else []
        admin_groups = [g for g in all_groups
                        if any(kw in g.lower()
                               for kw in ("admin", "power", "devops", "root", "sre"))]

    for entry in users_with_keys:
        uname = entry["username"]
        groups_raw = _aws(["iam", "list-groups-for-user", "--user-name", uname,
                           "--query", "Groups[*].GroupName"])
        if "skipped" in groups_raw or "error" in groups_raw:
            continue
        user_groups = groups_raw if isinstance(groups_raw, list) else []
        if any(g in admin_groups for g in user_groups):
            highest_privilege_with_key = uname
            break

    return {
        "users_with_keys": users_with_keys,
        "total_active_keys": len(users_with_keys),
        "keys_over_90_days": keys_over_90,
        "keys_over_365_days": keys_over_365,
        "keys_never_used": keys_never_used,
        "highest_privilege_with_key": highest_privilege_with_key,
    }


# ── IA-5: Service Account Credentials ─────────────────────────────────────────

def collect_service_account_credentials() -> dict:
    """
    IA-5: Kubernetes service account static token usage.
    M-24-04: workload identity (IRSA/Workload Identity) required -- no long-lived SA tokens.
    IRSA detection: eks.amazonaws.com/role-arn annotation on the service account.
    Long-lived static tokens: secrets of type kubernetes.io/service-account-token
    (projected tokens from BoundServiceAccountTokenVolume are short-lived and acceptable).

    Returns:
      total_service_accounts (int),
      automount_true (int), automount_false (int), automount_default (int),
      irsa_annotated (int), long_lived_secret_tokens (int),
      compliance_assessment: "compliant"|"partial"|"non_compliant"
    """
    sa_data = _kubectl(["get", "serviceaccounts", "-A", "-o", "json"])
    if "skipped" in sa_data or "error" in sa_data:
        return sa_data

    total = 0
    automount_true = 0
    automount_false = 0
    automount_default = 0
    irsa_annotated = 0

    for item in sa_data.get("items", []):
        total += 1
        annotations = item.get("metadata", {}).get("annotations", {})
        has_irsa = "eks.amazonaws.com/role-arn" in annotations
        if has_irsa:
            irsa_annotated += 1

        automount = item.get("automountServiceAccountToken")
        if automount is True:
            automount_true += 1
        elif automount is False:
            automount_false += 1
        else:
            automount_default += 1

    # Count long-lived static service account token secrets
    secret_data = _kubectl(["get", "secrets", "-A", "-o", "json"])
    long_lived_count = 0
    if "skipped" not in secret_data and "error" not in secret_data:
        for secret in secret_data.get("items", []):
            if secret.get("type") == "kubernetes.io/service-account-token":
                long_lived_count += 1

    # Assessment
    if long_lived_count > 0 and automount_true > 0:
        compliance = "non_compliant"
    elif long_lived_count > 0:
        compliance = "partial"
    elif automount_false + automount_default == total or irsa_annotated > 0:
        compliance = "compliant"
    else:
        compliance = "partial"

    return {
        "total_service_accounts": total,
        "automount_true": automount_true,
        "automount_false": automount_false,
        "automount_default": automount_default,
        "irsa_annotated": irsa_annotated,
        "long_lived_secret_tokens": long_lived_count,
        "compliance_assessment": compliance,
    }


# ── AC-2: Account Lifecycle ────────────────────────────────────────────────────

def collect_account_lifecycle() -> dict:
    """
    AC-2: Account lifecycle management -- creation, review, deprovisioning.
    M-24-04 requires automated lifecycle and periodic review for privileged accounts.
    Stale threshold: 90 days without use.

    Returns:
      stale_users (list), users_without_groups (list),
      console_users_without_mfa (list),
      service_accounts_in_default_ns (list),
      orphaned_rolebindings (list)
    """
    stale_users = []
    users_without_groups = []
    console_users_without_mfa = []

    rows = _get_credential_report_rows()
    if not isinstance(rows, dict):
        for row in rows:
            username = row.get("user", "")
            if username == "<root_account>":
                continue

            # Stale: password-enabled user not used in 90+ days
            last_used = row.get("password_last_used")
            days_since_use = _days_since(last_used)
            if row.get("password_enabled") == "true":
                if days_since_use is None or days_since_use > 90:
                    stale_users.append({
                        "username": username,
                        "last_used": last_used,
                        "days_inactive": days_since_use,
                    })

                # Console users without MFA
                if row.get("mfa_active") != "true":
                    console_users_without_mfa.append(username)

            # Users without group membership -- no lifecycle policy
            groups_raw = _aws(["iam", "list-groups-for-user",
                                "--user-name", username,
                                "--query", "Groups[*].GroupName"])
            if "skipped" not in groups_raw and "error" not in groups_raw:
                groups = groups_raw if isinstance(groups_raw, list) else []
                if not groups:
                    users_without_groups.append(username)

    # Service accounts in default namespace
    sa_data = _kubectl(["get", "serviceaccounts", "-n", "default", "-o", "json"])
    sa_in_default = []
    if "skipped" not in sa_data and "error" not in sa_data:
        for item in sa_data.get("items", []):
            name = item.get("metadata", {}).get("name", "")
            if name != "default":
                sa_in_default.append(name)

    # Orphaned rolebindings -- subjects that no longer exist
    orphaned = []
    for rb_resource in ["rolebindings", "clusterrolebindings"]:
        rb_data = _kubectl(["get", rb_resource, "-A", "-o", "json"])
        if "skipped" in rb_data or "error" in rb_data:
            continue
        for item in rb_data.get("items", []):
            rb_name = item.get("metadata", {}).get("name", "")
            rb_ns = item.get("metadata", {}).get("namespace", "cluster-wide")
            for subject in item.get("subjects", []):
                if subject.get("kind") != "ServiceAccount":
                    continue
                subj_name = subject.get("name", "")
                subj_ns = subject.get("namespace", "default")
                # Check if the SA still exists
                check = _kubectl(["get", "serviceaccount", subj_name,
                                  "-n", subj_ns, "--ignore-not-found"])
                if check.get("items") == [] or (
                    "error" in check and "not found" in check.get("error", "").lower()
                ):
                    orphaned.append({
                        "binding": rb_name,
                        "binding_namespace": rb_ns,
                        "subject": subj_name,
                        "subject_namespace": subj_ns,
                    })

    return {
        "stale_users": stale_users,
        "users_without_groups": users_without_groups,
        "console_users_without_mfa": console_users_without_mfa,
        "service_accounts_in_default_ns": sa_in_default,
        "orphaned_rolebindings": orphaned,
    }


# ── AC-6: Least Privilege ──────────────────────────────────────────────────────

def collect_least_privilege() -> dict:
    """
    AC-6: Least-privilege enforcement.
    M-24-04 Authorization: no standing privileged access, attribute-based where possible.

    Returns:
      admin_role_count (int), wildcard_permissions (list),
      broad_cluster_roles (list), privileged_pods (list), root_running_pods (list)
    """
    # ClusterRoles with wildcard verbs or resources (excluding system: prefix)
    cr_data = _kubectl(["get", "clusterroles", "-o", "json"])
    admin_role_count = 0
    wildcard_permissions = []
    broad_cluster_roles = []

    if "skipped" not in cr_data and "error" not in cr_data:
        for item in cr_data.get("items", []):
            name = item.get("metadata", {}).get("name", "")
            if name.startswith("system:"):
                continue
            if name == "cluster-admin":
                admin_role_count += 1
                continue

            rules = item.get("rules", [])
            for rule in rules:
                verbs = rule.get("verbs", [])
                resources = rule.get("resources", [])
                # Wildcard: * in verbs or resources
                if "*" in verbs or "*" in resources:
                    wildcard_permissions.append({
                        "role": name,
                        "rule": {"verbs": verbs, "resources": resources},
                    })
                # Broad: get/list/watch on all resources
                elif (set(verbs) >= {"get", "list", "watch"}
                      and "*" in resources):
                    broad_cluster_roles.append({
                        "role": name,
                        "rule": {"verbs": verbs, "resources": resources},
                    })

    # Privileged pods and root-running pods
    pod_data = _kubectl(["get", "pods", "-A", "-o", "json"])
    privileged_pods = []
    root_running_pods = []

    if "skipped" not in pod_data and "error" not in pod_data:
        for item in pod_data.get("items", []):
            ns = item.get("metadata", {}).get("namespace", "")
            pod_name = item.get("metadata", {}).get("name", "")
            pod_ctx = item.get("spec", {}).get("securityContext", {})
            pod_non_root = pod_ctx.get("runAsNonRoot", False)

            for container in item.get("spec", {}).get("containers", []):
                c_name = container.get("name", "")
                c_ctx = container.get("securityContext", {})

                if c_ctx.get("privileged") is True:
                    privileged_pods.append({
                        "namespace": ns,
                        "pod": pod_name,
                        "container": c_name,
                        "issue": "privileged: true",
                    })

                c_non_root = c_ctx.get("runAsNonRoot", False)
                if not pod_non_root and not c_non_root:
                    root_running_pods.append({
                        "namespace": ns,
                        "pod": pod_name,
                        "container": c_name,
                        "issue": "runAsNonRoot not set",
                    })

    return {
        "admin_role_count": admin_role_count,
        "wildcard_permissions": wildcard_permissions,
        "broad_cluster_roles": broad_cluster_roles,
        "privileged_pods": privileged_pods,
        "root_running_pods": root_running_pods,
    }


# ── AC-17 / SC-8: Federation and Remote Access ────────────────────────────────

def collect_federation_config() -> dict:
    """
    AC-17, SC-8: Federation and remote access configuration.
    M-24-04: OIDC/SAML federation required; no proprietary SSO silos.
    TLS required on all auth flows (SC-8 transmission confidentiality).

    Returns:
      oidc_providers (list), eks_oidc_configured (bool),
      tls_on_all_ingress (bool), ingress_without_tls (list),
      saml_provider_detected (bool)
    """
    # AWS IAM OIDC providers (federation endpoints)
    oidc_raw = _aws(["iam", "list-open-id-connect-providers"])
    oidc_providers = []
    if "skipped" not in oidc_raw and "error" not in oidc_raw:
        oidc_providers = [
            p.get("Arn", "") for p in oidc_raw.get("OpenIDConnectProviderList", [])
        ]

    # EKS OIDC -- at least one OIDC provider with eks.amazonaws.com indicates IRSA/federation
    eks_oidc_configured = any("oidc.eks" in p for p in oidc_providers)

    # SAML providers
    saml_raw = _aws(["iam", "list-saml-providers"])
    saml_provider_detected = False
    if "skipped" not in saml_raw and "error" not in saml_raw:
        saml_provider_detected = len(saml_raw.get("SAMLProviderList", [])) > 0

    # Ingress TLS check (SC-8 transmission confidentiality)
    ingress_data = _kubectl(["get", "ingress", "-A", "-o", "json"])
    ingress_without_tls = []
    total_ingress = 0

    if "skipped" not in ingress_data and "error" not in ingress_data:
        for item in ingress_data.get("items", []):
            total_ingress += 1
            ns = item.get("metadata", {}).get("namespace", "")
            name = item.get("metadata", {}).get("name", "")
            spec = item.get("spec", {})
            tls_entries = spec.get("tls", [])
            if not tls_entries:
                ingress_without_tls.append({"namespace": ns, "name": name})

    tls_on_all_ingress = total_ingress > 0 and len(ingress_without_tls) == 0

    return {
        "oidc_providers": oidc_providers,
        "eks_oidc_configured": eks_oidc_configured,
        "saml_provider_detected": saml_provider_detected,
        "total_ingress": total_ingress,
        "tls_on_all_ingress": tls_on_all_ingress,
        "ingress_without_tls": ingress_without_tls,
    }


# ── ICAM aggregate runner ──────────────────────────────────────────────────────

def _assess_credentialing(iam_keys: dict, sa_creds: dict) -> str:
    """Derive credentialing service compliance from key ages + SA token data."""
    if "skipped" in iam_keys and "skipped" in sa_creds:
        return "cannot_assess"

    violations = []
    if "skipped" not in iam_keys and "error" not in iam_keys:
        if iam_keys.get("keys_over_90_days", 0) > 0:
            violations.append("iam_keys_over_90_days")
        if iam_keys.get("keys_over_365_days", 0) > 0:
            violations.append("iam_keys_over_365_days")
        if iam_keys.get("keys_never_used", 0) > 0:
            violations.append("keys_never_used")

    if "skipped" not in sa_creds and "error" not in sa_creds:
        sa_compliance = sa_creds.get("compliance_assessment", "")
        if sa_compliance == "non_compliant":
            violations.append("sa_static_tokens")
        elif sa_compliance == "partial":
            violations.append("sa_mixed_token_posture")

    if not violations:
        return "compliant"
    critical = {"iam_keys_over_365_days", "sa_static_tokens"}
    if critical & set(violations):
        return "non_compliant"
    return "partial"


def _assess_authorization(lifecycle: dict, least_priv: dict) -> str:
    """Derive authorization service compliance from lifecycle + least-privilege data."""
    violations = []

    if "skipped" not in lifecycle and "error" not in lifecycle:
        if lifecycle.get("stale_users"):
            violations.append("stale_accounts")
        if lifecycle.get("users_without_groups"):
            violations.append("unmanaged_accounts")
        if lifecycle.get("console_users_without_mfa"):
            violations.append("console_no_mfa")

    if "skipped" not in least_priv and "error" not in least_priv:
        if least_priv.get("wildcard_permissions"):
            violations.append("wildcard_permissions")
        if least_priv.get("privileged_pods"):
            violations.append("privileged_pods")

    if not violations:
        return "compliant"
    critical = {"wildcard_permissions", "privileged_pods", "console_no_mfa"}
    if critical & set(violations):
        return "non_compliant"
    return "partial"


def _assess_federation(fed: dict) -> str:
    """Derive federation service compliance from federation config data."""
    if "skipped" in fed or "error" in fed:
        return "cannot_assess"

    if not fed.get("oidc_providers") and not fed.get("saml_provider_detected"):
        return "non_compliant"
    if fed.get("ingress_without_tls"):
        return "partial"
    if fed.get("tls_on_all_ingress") and (
        fed.get("eks_oidc_configured") or fed.get("saml_provider_detected")
    ):
        return "compliant"
    return "partial"


def run_icam_collectors() -> dict:
    """
    Aggregate all ICAM collectors. Step 1 of M-24-04 compliance assessment.

    Returns structured evidence keyed by ICAM service, plus icam_signals summary.

    IMPORTANT -- Identity Proofing (IA-4):
      IAL2 proofing requires review of onboarding process documentation,
      government ID verification records, and proofing workflow evidence.
      None of these are accessible via AWS CLI or kubectl API calls.
      This section is flagged as "requires process review" and must be assessed
      by a human auditor reviewing HR/onboarding records and proofing system logs.
    """
    print("  [icam] Collecting authentication signals (IA-2)...")
    mfa_config = collect_mfa_configuration()

    print("  [icam] Collecting IAM key ages (IA-5)...")
    iam_keys = collect_iam_key_ages()

    print("  [icam] Collecting service account credentials (IA-5)...")
    sa_creds = collect_service_account_credentials()

    print("  [icam] Collecting account lifecycle data (AC-2)...")
    lifecycle = collect_account_lifecycle()

    print("  [icam] Collecting least-privilege data (AC-6)...")
    least_priv = collect_least_privilege()

    print("  [icam] Collecting federation configuration (AC-17, SC-8)...")
    federation = collect_federation_config()

    # Derive per-service compliance assessments
    auth_compliance = mfa_config.get("compliance_assessment", "cannot_assess")
    cred_compliance = _assess_credentialing(iam_keys, sa_creds)
    authz_compliance = _assess_authorization(lifecycle, least_priv)
    fed_compliance = _assess_federation(federation)

    # Build critical violations list
    critical_violations = []

    if "skipped" not in iam_keys and "error" not in iam_keys:
        over_90 = iam_keys.get("keys_over_90_days", 0)
        over_365 = iam_keys.get("keys_over_365_days", 0)
        if over_365 > 0:
            critical_violations.append(
                f"{over_365} IAM access key(s) older than 365 days "
                f"(M-24-04 prohibits long-lived static credentials)"
            )
        elif over_90 > 0:
            critical_violations.append(
                f"{over_90} IAM access key(s) older than 90 days "
                f"(M-24-04 recommends automated rotation within 90 days)"
            )

    if "skipped" not in mfa_config and "error" not in mfa_config:
        disabled = mfa_config.get("aws_mfa_disabled_users", 0)
        if disabled > 0:
            critical_violations.append(
                f"{disabled} IAM console user(s) have no MFA configured "
                f"(M-24-04 Section 3 requires MFA for all users)"
            )
        virtual = mfa_config.get("virtual_mfa_devices", 0)
        if virtual > 0 and mfa_config.get("fido2_devices", 0) == 0:
            critical_violations.append(
                f"{virtual} user(s) using TOTP/virtual MFA -- M-24-04 requires "
                f"phishing-resistant MFA (FIDO2/WebAuthn or PIV/CAC)"
            )

    if "skipped" not in sa_creds and "error" not in sa_creds:
        static_tokens = sa_creds.get("long_lived_secret_tokens", 0)
        if static_tokens > 0:
            critical_violations.append(
                f"{static_tokens} long-lived kubernetes.io/service-account-token secret(s) "
                f"detected (M-24-04 requires workload identity -- IRSA or equivalent)"
            )

    if "skipped" not in lifecycle and "error" not in lifecycle:
        stale = len(lifecycle.get("stale_users", []))
        if stale > 0:
            critical_violations.append(
                f"{stale} IAM user(s) inactive for 90+ days with no deprovisioning evidence "
                f"(M-24-04 requires automated account lifecycle management)"
            )

    if "skipped" not in federation and "error" not in federation:
        no_tls = len(federation.get("ingress_without_tls", []))
        if no_tls > 0:
            critical_violations.append(
                f"{no_tls} ingress resource(s) without TLS "
                f"(M-24-04/SC-8 requires encrypted auth flows)"
            )

    # Mandate satisfied only if all assessable services are compliant
    assessable_statuses = [
        auth_compliance, cred_compliance, authz_compliance, fed_compliance,
    ]
    mandate_satisfied = all(
        s == "compliant"
        for s in assessable_statuses
        if s not in ("cannot_assess",)
    )

    return {
        "authentication": {
            "mfa_configuration": mfa_config,
        },
        "identity_proofing": {
            "note": (
                "IAL2 identity proofing cannot be assessed via API calls. "
                "Assessment requires human review of: onboarding process documentation, "
                "government-issued ID verification records, and proofing workflow audit logs. "
                "Flag as 'requires process review' in the SAR."
            ),
            "api_assessment_possible": False,
        },
        "credentialing": {
            "iam_key_ages": iam_keys,
            "service_account_credentials": sa_creds,
        },
        "authorization": {
            "account_lifecycle": lifecycle,
            "least_privilege": least_priv,
        },
        "federation": {
            "federation_config": federation,
        },
        "icam_signals": {
            "service_compliance": {
                "Authentication": auth_compliance,
                "Identity_Proofing": "cannot_assess_via_api",
                "Credentialing": cred_compliance,
                "Authorization": authz_compliance,
                "Federation": fed_compliance,
            },
            "mandate_satisfied": mandate_satisfied,
            "critical_violations": critical_violations,
        },
    }
