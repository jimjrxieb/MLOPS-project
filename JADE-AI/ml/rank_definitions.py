"""
Rank Definitions for GP-Copilot Security Automation

This file defines what each rank means and provides patterns for classification.
Used by both rule-based and ML classifiers for consistency.

Philosophy:
- E-Rank: Trivial, no thought needed
- D-Rank: JSA agent specialties (they're trained for this)
- C-Rank: Junior engineer approval level
- B-Rank: Senior/architect review required
- S-Rank: Security incident, escalate immediately
"""

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class RankDefinition:
    """Definition of what a rank means and its patterns"""
    name: str
    automation_level: str  # "full", "high", "moderate", "low", "none"
    description: str
    action: str
    examples: List[str]
    scanner_patterns: Dict[str, List[str]]  # scanner -> rule patterns
    keywords: Set[str]  # Keywords that suggest this rank


# ═══════════════════════════════════════════════════════════════════════════════
# RANK DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

E_RANK = RankDefinition(
    name="E",
    automation_level="full",
    description="Trivial fixes - auto-fix immediately, no thought needed",
    action="auto_fix",
    examples=[
        "Formatting issues (black, eslint indent, prettier)",
        "Unused variables/imports",
        "Pin versions in Dockerfile (DL3008)",
        "Add .gitignore entries",
        "Trailing whitespace",
        "Missing newline at EOF",
        "Sort imports",
        "Quote style consistency",
    ],
    scanner_patterns={
        "eslint": ["no-unused-vars", "indent", "semi", "quotes", "eol-last"],
        "hadolint": ["DL3008", "DL3009", "DL3015", "DL3025"],
        "black": ["formatting", "line-length"],
        "isort": ["import-order"],
        "prettier": ["formatting"],
    },
    keywords={
        "format", "indent", "whitespace", "unused", "import", "newline",
        "trailing", "quote", "semicolon", "style", "lint"
    }
)

D_RANK = RankDefinition(
    name="D",
    automation_level="high",
    description="JSA agent specialties - domain expertise, agents trained for this",
    action="auto_fix",
    examples=[
        # jsa-devsecops specialties (CKA/CKS level)
        "OPA/Rego deny message fixes",
        "Pod security fixes (CKV_K8S_* checks)",
        "RBAC fixes (missing ClusterRole, RoleBinding)",
        "NetworkPolicy creation/fixes",
        "securityContext hardening (readOnlyRootFilesystem, runAsNonRoot)",
        "Gatekeeper constraint fixes",
        "Kyverno policy fixes",
        "Container resource limits/requests",
        "Image tag pinning (use SHA256 digest)",
        "Service account token automount disable",

        # jsa-ci specialties
        "GHA workflow fixes (pin actions to SHA)",
        "CI/CD pipeline security",
        "Docker build security (non-root user)",
        "Dependency upgrades (CVE fixes with known fix version)",
        "SAST fixes (SQL injection, command injection)",
        "Secrets detection remediation",
        "Bandit B602/B603 subprocess fixes",
        "Semgrep pattern fixes",
    ],
    scanner_patterns={
        # K8s security (jsa-devsecops domain)
        "checkov": [
            "CKV_K8S_8",   # liveness probe
            "CKV_K8S_9",   # readiness probe
            "CKV_K8S_20",  # runAsNonRoot
            "CKV_K8S_21",  # default namespace
            "CKV_K8S_22",  # readOnlyRootFilesystem
            "CKV_K8S_23",  # hostNetwork
            "CKV_K8S_25",  # capabilities drop
            "CKV_K8S_28",  # resource limits
            "CKV_K8S_29",  # resource requests
            "CKV_K8S_30",  # securityContext
            "CKV_K8S_31",  # seccomp
            "CKV_K8S_37",  # privilege escalation
            "CKV_K8S_38",  # hostPID
            "CKV_K8S_39",  # hostIPC
            "CKV_K8S_40",  # high UID
            "CKV_K8S_43",  # image digest
        ],
        "kubescape": [
            "C-0001",  # forbidden container registries
            "C-0004",  # resource limits
            "C-0013",  # non-root
            "C-0016",  # privileged container
            "C-0017",  # root container
            "C-0034",  # automount SA token
            "C-0038",  # host network
            "C-0041",  # hostPID
            "C-0042",  # hostIPC
            "C-0044",  # host path
            "C-0045",  # writable filesystem
            "C-0046",  # insecure capabilities
            "C-0055",  # linux hardening
            "C-0057",  # privilege escalation
        ],
        "polaris": [
            "hostNetwork", "hostPID", "hostIPC", "privileged",
            "runAsRootAllowed", "readOnlyRootFilesystem",
            "cpuLimitsMissing", "memoryLimitsMissing",
        ],

        # CI/CD (jsa-ci domain)
        "gitleaks": ["generic-api-key", "aws-access-key", "github-token", "slack-token"],
        "trivy": ["CVE-"],  # Any CVE with fixed version
        "grype": ["CVE-"],
        "snyk": ["SNYK-"],

        # SAST (jsa-ci domain)
        "bandit": [
            "B101",  # assert
            "B102",  # exec
            "B103",  # set_bad_file_permissions
            "B104",  # hardcoded_bind_all
            "B105",  # hardcoded_password_string
            "B106",  # hardcoded_password_funcarg
            "B107",  # hardcoded_password_default
            "B108",  # hardcoded_tmp_directory
            "B110",  # try_except_pass
            "B112",  # try_except_continue
            "B201",  # flask_debug
            "B301",  # pickle
            "B302",  # marshal
            "B303",  # MD5
            "B304",  # insecure cipher
            "B305",  # insecure cipher mode
            "B306",  # mktemp
            "B307",  # eval
            "B308",  # mark_safe
            "B310",  # urllib_urlopen
            "B311",  # random
            "B312",  # telnetlib
            "B313",  # xml_bad_cElementTree
            "B314",  # xml_bad_ElementTree
            "B320",  # xml_bad_lxml
            "B323",  # ssl_unverified
            "B324",  # hashlib
            "B501",  # request_with_no_cert_validation
            "B502",  # ssl_context
            "B503",  # ssl_no_validate
            "B504",  # ssl_no_version
            "B505",  # weak_cryptographic_key
            "B506",  # yaml_load
            "B507",  # ssh_no_host_key
            "B601",  # paramiko_calls
            "B602",  # subprocess_popen_with_shell
            "B603",  # subprocess_without_shell_equals_true
            "B604",  # any_other_function_with_shell
            "B605",  # start_process_with_shell
            "B606",  # start_process_with_no_shell
            "B607",  # start_process_with_partial_path
            "B608",  # hardcoded_sql
            "B609",  # wildcard_injection
            "B610",  # django_extra
            "B611",  # django_raw_sql
            "B701",  # jinja2_autoescape_false
            "B702",  # mako_templates
            "B703",  # django_mark_safe
        ],
        "semgrep": [
            "python.lang.security",
            "javascript.lang.security",
            "typescript.lang.security",
            "go.lang.security",
            "java.lang.security",
        ],

        # Dockerfile (jsa-ci domain)
        "hadolint": [
            "DL3000",  # WORKDIR absolute path
            "DL3001",  # command to clean cache
            "DL3002",  # last USER root
            "DL3003",  # WORKDIR + cd
            "DL3004",  # sudo
            "DL3006",  # tag version
            "DL3007",  # :latest
            "DL3010",  # ADD for archives
            "DL3011",  # valid port
            "DL3013",  # pip version
            "DL3018",  # apk version
            "DL3019",  # apk --no-cache
            "DL3020",  # ADD vs COPY
            "DL3022",  # COPY --from stage
            "DL4000",  # MAINTAINER deprecated
            "DL4006",  # SHELL pipefail
        ],
    },
    keywords={
        "securitycontext", "runasnonroot", "readonlyrootfilesystem", "rbac",
        "networkpolicy", "gatekeeper", "kyverno", "opa", "rego", "cve",
        "dependency", "upgrade", "injection", "xss", "sql", "subprocess",
        "shell", "dockerfile", "github-actions", "workflow", "secrets",
        "api-key", "credential", "token", "certificate", "tls", "ssl",
        "container", "pod", "deployment", "service", "ingress",
    }
)

C_RANK = RankDefinition(
    name="C",
    automation_level="moderate",
    description="Junior engineer approval level - can fix but human should verify",
    action="request_approval",
    examples=[
        "Helmify (convert raw manifests to Helm charts)",
        "Terraform/CloudFormation changes",
        "Multi-file refactors",
        "New resource creation (not just fixing)",
        "Cross-service changes",
        "Database schema changes",
        "API endpoint changes",
        "Configuration changes affecting multiple services",
        "New IAM roles/policies (non-admin)",
        "New S3 buckets/storage",
    ],
    scanner_patterns={
        "checkov": [
            "CKV_AWS_",    # AWS-specific (needs review)
            "CKV_GCP_",    # GCP-specific
            "CKV_AZURE_",  # Azure-specific
            "CKV2_",       # Cross-resource checks
        ],
        "tfsec": [
            "aws-",
            "azure-",
            "google-",
        ],
        "prowler": [
            "check1",  # IAM checks
            "check2",  # S3 checks
            "check3",  # CloudTrail
        ],
    },
    keywords={
        "helm", "helmify", "terraform", "cloudformation", "multi-file",
        "refactor", "create", "new", "migration", "schema", "database",
        "api", "endpoint", "configuration", "iam-role", "s3-bucket",
    }
)

B_RANK = RankDefinition(
    name="B",
    automation_level="low",
    description="Senior/architect review - major architecture impact",
    action="escalate",
    examples=[
        "Major architecture changes",
        "Multi-cluster modifications",
        "Cross-account IAM changes",
        "IAM wildcards (*) in policies",
        "Encryption strategy changes",
        "Network topology changes",
        "VPC/subnet changes",
        "Database replication changes",
        "Zero-trust boundary modifications",
        "Service mesh configuration",
    ],
    scanner_patterns={
        "prowler": [
            "iam-policy-too-permissive",
            "cross-account",
            "root-account",
            "mfa-disabled",
        ],
        "checkov": [
            "CKV_AWS_1",   # S3 versioning (data protection)
            "CKV_AWS_19",  # EBS encryption
            "CKV_AWS_23",  # security group rules
            "CKV_AWS_33",  # KMS key rotation
            "CKV_AWS_40",  # IAM policy wildcards
            "CKV_AWS_49",  # SSM parameter encryption
        ],
        "kubescape": [
            "C-0002",  # exec into container
            "C-0007",  # data destruction
            "C-0015",  # cluster admin
            "C-0035",  # cluster takeover
        ],
    },
    keywords={
        "architecture", "multi-cluster", "cross-account", "wildcard",
        "encryption", "network", "topology", "vpc", "subnet", "replication",
        "zero-trust", "service-mesh", "istio", "linkerd", "consul",
    }
)

S_RANK = RankDefinition(
    name="S",
    automation_level="none",
    description="Security incident or org-wide impact - escalate immediately",
    action="escalate",
    examples=[
        "Active security incidents",
        "Data exfiltration detection",
        "Root/admin credential exposure",
        "Zero-trust violations in production",
        "Compliance violations (SOC2, PCI, HIPAA)",
        "Active exploitation attempts",
        "Malware detection",
        "Unauthorized access patterns",
        "Critical CVEs under active exploitation",
    ],
    scanner_patterns={
        "gitleaks": [
            "aws-root",
            "gcp-service-account",
            "private-key",
        ],
        "prowler": [
            "root-login",
            "unusual-activity",
            "data-exfiltration",
        ],
        "kubescape": [
            "C-0035",  # cluster takeover vectors
        ],
    },
    keywords={
        "incident", "exfiltration", "breach", "root", "admin", "compromise",
        "exploit", "malware", "unauthorized", "violation", "compliance",
        "soc2", "pci", "hipaa", "gdpr", "active-exploit", "cisa-kev",
    }
)


# ═══════════════════════════════════════════════════════════════════════════════
# RANK LOOKUP
# ═══════════════════════════════════════════════════════════════════════════════

RANKS = {
    "E": E_RANK,
    "D": D_RANK,
    "C": C_RANK,
    "B": B_RANK,
    "S": S_RANK,
}


def get_rank_for_scanner_rule(scanner: str, rule_id: str) -> str:
    """
    Look up the appropriate rank for a scanner+rule combination.
    Returns the rank letter or None if not found.
    """
    scanner_lower = scanner.lower()
    rule_lower = rule_id.lower()

    # Check from most specific (S) to least specific (E)
    for rank_letter in ["S", "B", "C", "D", "E"]:
        rank_def = RANKS[rank_letter]
        patterns = rank_def.scanner_patterns.get(scanner_lower, [])

        for pattern in patterns:
            if pattern.lower() in rule_lower or rule_lower.startswith(pattern.lower()):
                return rank_letter

    return None


def get_rank_for_keywords(text: str) -> str:
    """
    Suggest rank based on keyword matching in description/title.
    Returns the rank letter or None if no strong match.
    """
    text_lower = text.lower()

    # Check S-rank keywords first (most critical)
    s_matches = sum(1 for kw in S_RANK.keywords if kw in text_lower)
    if s_matches >= 2:
        return "S"

    # Check B-rank
    b_matches = sum(1 for kw in B_RANK.keywords if kw in text_lower)
    if b_matches >= 2:
        return "B"

    # Check C-rank
    c_matches = sum(1 for kw in C_RANK.keywords if kw in text_lower)
    if c_matches >= 2:
        return "C"

    # D-rank and E-rank checked together, D takes precedence
    d_matches = sum(1 for kw in D_RANK.keywords if kw in text_lower)
    e_matches = sum(1 for kw in E_RANK.keywords if kw in text_lower)

    if d_matches > e_matches:
        return "D"
    if e_matches > 0:
        return "E"

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC DATA PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

SYNTHETIC_PATTERNS = {
    "E": [
        # Formatting
        {"scanner": "eslint", "severity": "info", "rule_id": "no-unused-vars",
         "description": "Unused variable 'temp' in line 42", "file": "src/utils.js"},
        {"scanner": "eslint", "severity": "info", "rule_id": "indent",
         "description": "Expected indentation of 2 spaces", "file": "src/app.js"},
        {"scanner": "black", "severity": "info", "rule_id": "formatting",
         "description": "Line too long (85 > 79 characters)", "file": "app.py"},
        {"scanner": "hadolint", "severity": "info", "rule_id": "DL3008",
         "description": "Pin versions in apt get install", "file": "Dockerfile"},
        {"scanner": "isort", "severity": "info", "rule_id": "import-order",
         "description": "Imports not sorted correctly", "file": "main.py"},
    ],

    "D": [
        # CKA/CKS level - jsa-devsecops specialty
        {"scanner": "checkov", "severity": "high", "rule_id": "CKV_K8S_22",
         "description": "Container does not have readOnlyRootFilesystem", "file": "deployment.yaml",
         "fix_suggestion": "Add securityContext.readOnlyRootFilesystem: true"},
        {"scanner": "checkov", "severity": "high", "rule_id": "CKV_K8S_40",
         "description": "Container is using UID < 10000", "file": "deployment.yaml",
         "fix_suggestion": "Add securityContext.runAsUser: 10001"},
        {"scanner": "checkov", "severity": "high", "rule_id": "CKV_K8S_43",
         "description": "Image does not use digest", "file": "deployment.yaml",
         "fix_suggestion": "Use image SHA256 digest instead of tag"},
        {"scanner": "kubescape", "severity": "high", "rule_id": "C-0017",
         "description": "Container running as root", "file": "pod.yaml",
         "fix_suggestion": "Add runAsNonRoot: true"},
        {"scanner": "polaris", "severity": "medium", "rule_id": "cpuLimitsMissing",
         "description": "Container does not have CPU limits", "file": "deployment.yaml"},
        {"scanner": "conftest", "severity": "high", "rule_id": "deny-privileged",
         "description": "OPA policy denies privileged containers", "file": "deployment.yaml"},

        # CI/CD - jsa-ci specialty
        {"scanner": "trivy", "severity": "high", "rule_id": "CVE-2024-1234",
         "description": "lodash < 4.17.21 has RCE vulnerability", "file": "package.json",
         "fixed_version": "4.17.21"},
        {"scanner": "bandit", "severity": "high", "rule_id": "B602",
         "description": "subprocess call with shell=True", "file": "deploy.py",
         "fix_suggestion": "Use shell=False and pass args as list"},
        {"scanner": "gitleaks", "severity": "high", "rule_id": "generic-api-key",
         "description": "API key detected in source code", "file": "config.py",
         "fix_suggestion": "Move to environment variable or secrets manager"},
        {"scanner": "semgrep", "severity": "high", "rule_id": "python.lang.security.injection.sql",
         "description": "SQL injection vulnerability", "file": "db/queries.py",
         "fix_suggestion": "Use parameterized queries"},
        {"scanner": "hadolint", "severity": "medium", "rule_id": "DL3002",
         "description": "Last USER should not be root", "file": "Dockerfile",
         "fix_suggestion": "Add USER nonroot at end of Dockerfile"},
    ],

    "C": [
        # Helm/Terraform changes
        {"scanner": "checkov", "severity": "medium", "rule_id": "CKV_AWS_21",
         "description": "S3 bucket does not have versioning enabled", "file": "main.tf"},
        {"scanner": "tfsec", "severity": "medium", "rule_id": "aws-s3-enable-bucket-logging",
         "description": "S3 bucket logging not enabled", "file": "s3.tf"},
        {"scanner": "kubescape", "severity": "medium", "rule_id": "C-0074",
         "description": "Missing Ingress controller configuration", "file": "ingress.yaml"},
        {"scanner": "checkov", "severity": "medium", "rule_id": "CKV2_AWS_6",
         "description": "S3 bucket should have public access block", "file": "storage.tf"},
        {"scanner": "helm", "severity": "medium", "rule_id": "values-schema",
         "description": "Helm values missing required schema validation", "file": "values.yaml"},
    ],

    "B": [
        # Architecture changes
        {"scanner": "prowler", "severity": "critical", "rule_id": "iam-policy-too-permissive",
         "description": "IAM policy allows * on all resources", "file": "iam.tf"},
        {"scanner": "checkov", "severity": "critical", "rule_id": "CKV_AWS_40",
         "description": "IAM policy uses wildcard actions", "file": "policies/admin.json"},
        {"scanner": "kubescape", "severity": "critical", "rule_id": "C-0015",
         "description": "ClusterAdmin role binding detected", "file": "rbac.yaml"},
        {"scanner": "prowler", "severity": "high", "rule_id": "cross-account-trust",
         "description": "IAM role has cross-account trust", "file": "iam-role.tf"},
        {"scanner": "checkov", "severity": "high", "rule_id": "CKV_AWS_23",
         "description": "Security group allows 0.0.0.0/0 ingress", "file": "security-groups.tf"},
    ],

    "S": [
        # Security incidents
        {"scanner": "gitleaks", "severity": "critical", "rule_id": "aws-root-credentials",
         "description": "AWS root account credentials exposed in repository", "file": "config/aws.py"},
        {"scanner": "prowler", "severity": "critical", "rule_id": "unusual-api-activity",
         "description": "Unusual API activity detected - possible data exfiltration", "file": "cloudtrail"},
        {"scanner": "trivy", "severity": "critical", "rule_id": "CVE-2021-44228",
         "description": "Log4Shell - actively exploited RCE vulnerability", "file": "pom.xml",
         "cisa_kev": True},
        {"scanner": "kubescape", "severity": "critical", "rule_id": "C-0035",
         "description": "Cluster takeover vector detected", "file": "cluster-role.yaml"},
        {"scanner": "falco", "severity": "critical", "rule_id": "shell-in-container",
         "description": "Interactive shell spawned in production container", "file": "runtime"},
    ],
}
