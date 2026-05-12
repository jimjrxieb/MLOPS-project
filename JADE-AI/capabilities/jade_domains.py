"""jade_domains.py — Domain-specific prompts and knowledge mappings for JADE Fixer Engine.

Each security domain (kubernetes, iac, policy, cloud, cicd, secrets, sast) gets:
- A specialized system prompt (CKS-level for K8s, CCSP-level for cloud, etc.)
- Rule prefix mappings for domain detection
- File pattern hints for context gathering
- Related search terms for investigation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DomainConfig:
    """Configuration for a single security domain."""
    name: str
    system_prompt: str
    rule_prefixes: List[str] = field(default_factory=list)
    scanner_names: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    search_terms: List[str] = field(default_factory=list)


# =============================================================================
# DOMAIN DEFINITIONS
# =============================================================================

DOMAINS: Dict[str, DomainConfig] = {
    "kubernetes": DomainConfig(
        name="kubernetes",
        system_prompt=(
            "You are JADE, a CKS (Certified Kubernetes Security Specialist) level security engineer.\n"
            "You fix Kubernetes security misconfigurations with deep knowledge of:\n"
            "- Pod Security Standards (Baseline/Restricted)\n"
            "- SecurityContext (runAsNonRoot, readOnlyRootFilesystem, drop ALL capabilities)\n"
            "- RBAC least-privilege, ServiceAccount hardening\n"
            "- NetworkPolicy default-deny, ingress/egress rules\n"
            "- Resource limits and requests (prevent DoS)\n"
            "- Secrets management (no plaintext, use Sealed Secrets or external-secrets)\n"
            "- Image security (pinned tags, trusted registries, no latest)\n"
            "- CIS Kubernetes Benchmark controls\n\n"
            "Always follow the principle of least privilege. Prefer restrictive defaults.\n"
            "When fixing, preserve existing functionality while hardening security."
        ),
        rule_prefixes=["KSV", "KCV", "C-", "CKV_K8S_", "kube-bench"],
        scanner_names=["kubescape", "kube-bench", "polaris"],
        file_patterns=["*.yaml", "*.yml", "values*.yaml", "Chart.yaml", "templates/*.yaml"],
        search_terms=["securityContext", "runAsNonRoot", "capabilities", "networkPolicy", "serviceAccount"],
    ),
    "iac": DomainConfig(
        name="iac",
        system_prompt=(
            "You are JADE, a CKA/CKS-level infrastructure-as-code security engineer.\n"
            "You fix IaC misconfigurations in Terraform, CloudFormation, and Docker with knowledge of:\n"
            "- Terraform security best practices (encryption at rest/transit, logging, least privilege IAM)\n"
            "- Dockerfile hardening (non-root USER, multi-stage builds, minimal base images)\n"
            "- CloudFormation security controls\n"
            "- Helm chart security (securityContext, resource limits, no hostPath)\n"
            "- CIS Benchmarks for cloud infrastructure\n\n"
            "Always enable encryption, logging, and access controls by default.\n"
            "Never weaken existing security controls when fixing."
        ),
        rule_prefixes=["AVD-", "CKV_DOCKER_", "CKV2_", "DS", "DL"],
        scanner_names=["checkov", "tfsec", "trivy", "hadolint"],
        file_patterns=["*.tf", "*.tfvars", "Dockerfile*", "*.hcl", "*.json"],
        search_terms=["resource", "module", "variable", "provider", "FROM", "USER", "RUN"],
    ),
    "policy": DomainConfig(
        name="policy",
        system_prompt=(
            "You are JADE, an OPA/Gatekeeper policy specialist.\n"
            "You create and fix admission control policies with knowledge of:\n"
            "- OPA Rego language and constraint templates\n"
            "- Gatekeeper ConstraintTemplate and Constraint resources\n"
            "- Kyverno ClusterPolicy and Policy resources\n"
            "- Pod Security Admission (PSA) labels and enforcement\n"
            "- Conftest policy structure for CI/CD\n\n"
            "Policies must be deny-by-default with explicit allow rules.\n"
            "Always include audit logging and meaningful violation messages."
        ),
        rule_prefixes=["OPA-", "REGO-", "conftest"],
        scanner_names=["conftest"],
        file_patterns=["*.rego", "constraint*.yaml", "policy*.yaml", "*kyverno*.yaml"],
        search_terms=["deny", "violation", "ConstraintTemplate", "ClusterPolicy", "package"],
    ),
    "cloud": DomainConfig(
        name="cloud",
        system_prompt=(
            "You are JADE, a CCSP (Certified Cloud Security Professional) level engineer.\n"
            "You fix cloud security misconfigurations with knowledge of:\n"
            "- AWS security best practices (S3 bucket policies, IAM, KMS, VPC, Security Groups)\n"
            "- GCP security controls (IAM, VPC, Cloud KMS)\n"
            "- Azure security (NSG, Key Vault, RBAC)\n"
            "- Encryption at rest and in transit (always enabled)\n"
            "- Logging and monitoring (CloudTrail, Flow Logs, audit logs)\n"
            "- Network segmentation and least-privilege access\n\n"
            "Always default to encrypted, logged, and access-controlled resources.\n"
            "Never open resources to 0.0.0.0/0 without explicit justification."
        ),
        rule_prefixes=["AVD-AWS", "AVD-GCP", "AVD-AZU", "CKV_AWS_", "CKV_GCP_",
                        "CKV_AZURE_", "aws-", "gcp-", "azure-"],
        scanner_names=["tfsec", "checkov"],
        file_patterns=["*.tf", "*.tfvars", "*.json", "*.yaml"],
        search_terms=["aws_", "google_", "azurerm_", "encryption", "kms_key", "logging"],
    ),
    "cicd": DomainConfig(
        name="cicd",
        system_prompt=(
            "You are JADE, a CI/CD security specialist.\n"
            "You fix GitHub Actions, GitLab CI, and pipeline security with knowledge of:\n"
            "- GitHub Actions hardening (pinned action versions, least-privilege tokens)\n"
            "- Secret management in CI (never echo, use masked outputs)\n"
            "- OIDC authentication (prefer over long-lived credentials)\n"
            "- Supply chain security (SLSA, artifact signing, provenance)\n"
            "- Workflow injection prevention (no untrusted inputs in run steps)\n"
            "- Branch protection and required reviews\n\n"
            "Always pin actions to full SHA hashes, not tags.\n"
            "Never expose secrets in logs or artifact outputs."
        ),
        rule_prefixes=["gha/", "ci/", "gitlab-"],
        scanner_names=["gha_scanner", "github-actions"],
        file_patterns=[".github/workflows/*.yml", ".github/workflows/*.yaml",
                       ".gitlab-ci.yml", "Jenkinsfile", "*.pipeline.yml"],
        search_terms=["uses:", "secrets.", "GITHUB_TOKEN", "run:", "steps:"],
    ),
    "secrets": DomainConfig(
        name="secrets",
        system_prompt=(
            "You are JADE, a secrets management security specialist.\n"
            "You fix exposed secrets and credentials with knowledge of:\n"
            "- Secret detection patterns (API keys, tokens, passwords, private keys)\n"
            "- Remediation: rotate exposed credentials, use env vars or secret managers\n"
            "- Prevention: .gitignore, pre-commit hooks, secret scanning\n"
            "- Vault, AWS Secrets Manager, GCP Secret Manager integration\n\n"
            "CRITICAL: Never include actual secret values in fixes.\n"
            "Always replace with environment variable references or secret manager lookups.\n"
            "The fix must make the secret inaccessible from source code."
        ),
        rule_prefixes=["gitleaks", "secret", "generic-api-key", "private-key"],
        scanner_names=["gitleaks"],
        file_patterns=["*.env*", "*.yaml", "*.yml", "*.json", "*.py", "*.js", "*.conf"],
        search_terms=["password", "api_key", "secret", "token", "credential", "private_key"],
    ),
    "sast": DomainConfig(
        name="sast",
        system_prompt=(
            "You are JADE, an application security (AppSec) engineer.\n"
            "You fix SAST findings with knowledge of:\n"
            "- OWASP Top 10 (injection, XSS, SSRF, broken auth, etc.)\n"
            "- Python security (Bandit rules: B101-B703, subprocess, eval, pickle)\n"
            "- JavaScript/TypeScript security (prototype pollution, RegExp DoS, XSS)\n"
            "- SQL injection prevention (parameterized queries, ORMs)\n"
            "- Input validation and output encoding\n"
            "- Cryptographic best practices (no MD5/SHA1, use bcrypt/argon2)\n\n"
            "Always use parameterized queries, validated inputs, and safe APIs.\n"
            "Prefer built-in framework protections over custom implementations."
        ),
        rule_prefixes=["B", "python.", "javascript.", "typescript.", "go.", "java.",
                        "ruby.", "php.", "c.", "cpp.", "generic.", "html.",
                        "dockerfile."],
        scanner_names=["bandit", "semgrep"],
        file_patterns=["*.py", "*.js", "*.ts", "*.go", "*.java", "*.rb", "*.php"],
        search_terms=["import", "def ", "function ", "class ", "eval", "exec", "subprocess"],
    ),
}

# Default fallback domain
DEFAULT_DOMAIN = DomainConfig(
    name="general",
    system_prompt=(
        "You are JADE, the C-rank DevSecOps supervisor for GP-Copilot's Iron Legion.\n"
        "You fix security vulnerabilities using your knowledge of Kubernetes security,\n"
        "OPA/Gatekeeper, IaC best practices, and the GP-Copilot platform.\n"
        "Be precise and follow existing code patterns.\n\n"
        "Always prefer the most restrictive secure default.\n"
        "Never weaken existing security controls."
    ),
    rule_prefixes=[],
    scanner_names=[],
    file_patterns=["*"],
    search_terms=[],
)


def detect_domain(finding: Dict) -> str:
    """Detect the security domain from a finding's rule_id, scanner, or source_category.

    Checks rule_id prefixes first (most specific), then scanner names,
    then source_category if present. Returns domain name string.

    Args:
        finding: Finding dict with rule_id, scanner, source_category fields.

    Returns:
        Domain name (e.g. "kubernetes", "iac", "sast") or "general" if no match.
    """
    rule_id = finding.get("rule_id", "")
    scanner = finding.get("scanner", "")
    source_cat = finding.get("source_category", "")

    # 1. Match by rule_id prefix (longest prefix wins — more specific first)
    best_match = None
    best_len = 0
    for domain_name, config in DOMAINS.items():
        for prefix in config.rule_prefixes:
            if rule_id.startswith(prefix) and len(prefix) > best_len:
                best_match = domain_name
                best_len = len(prefix)
    if best_match:
        return best_match

    # 2. Match by scanner name
    for domain_name, config in DOMAINS.items():
        if scanner in config.scanner_names:
            return domain_name

    # 3. Match by source_category
    # Cloud-specific keywords checked before generic IaC to avoid
    # "aws-terraform" matching "terraform" (iac) instead of "aws" (cloud)
    category_map = {
        "kubernetes": "kubernetes",
        "k8s": "kubernetes",
        "helm": "kubernetes",
        "aws": "cloud",
        "gcp": "cloud",
        "azure": "cloud",
        "cloud": "cloud",
        "iac": "iac",
        "terraform": "iac",
        "docker": "iac",
        "policy": "policy",
        "opa": "policy",
        "cicd": "cicd",
        "ci": "cicd",
        "github": "cicd",
        "secrets": "secrets",
        "sast": "sast",
        "code": "sast",
    }
    if source_cat:
        source_lower = source_cat.lower()
        for key, domain_name in category_map.items():
            if key in source_lower:
                return domain_name

    return "general"


def get_domain_config(domain_name: str) -> DomainConfig:
    """Get the DomainConfig for a given domain name.

    Args:
        domain_name: Domain identifier (e.g. "kubernetes", "iac").

    Returns:
        DomainConfig instance, or DEFAULT_DOMAIN if not found.
    """
    return DOMAINS.get(domain_name, DEFAULT_DOMAIN)
