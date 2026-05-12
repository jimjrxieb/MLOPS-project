#!/usr/bin/env python3
"""
Scanner Training Data Generator

Generates JADE training data from security scanner rule definitions.
Parses Checkov, Semgrep, Trivy, and Kube-bench rules to create
instruction-output pairs for fine-tuning.

Usage:
    python generate_scanner_training_data.py --source checkov
    python generate_scanner_training_data.py --source all --output all-scanners.jsonl
    python generate_scanner_training_data.py --stats
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Output directory
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "training-data"


@dataclass
class ScannerRule:
    """Parsed scanner rule."""
    scanner: str
    rule_id: str
    name: str
    description: str
    severity: str
    category: str
    remediation: str
    guideline_url: Optional[str] = None
    frameworks: List[str] = None
    supported_resources: List[str] = None

    def __post_init__(self):
        if self.frameworks is None:
            self.frameworks = []
        if self.supported_resources is None:
            self.supported_resources = []


class CheckovRuleParser:
    """
    Parse Checkov rules from installed package or GitHub.

    Checkov rules are Python classes with metadata like:
    - check_id: CKV_K8S_1
    - name: "Human readable name"
    - supported_resources: ["Pod", "Deployment"]
    - guideline: URL
    """

    REPO_URL = "https://github.com/bridgecrewio/checkov"
    KNOWN_RULES_PATH = "checkov/kubernetes/checks"

    # Pre-defined Checkov Kubernetes rules (subset for offline operation)
    KUBERNETES_RULES = {
        "CKV_K8S_1": {
            "name": "Ensure that CPU limits are set",
            "description": "Containers should have CPU limits set to prevent resource exhaustion",
            "severity": "MEDIUM",
            "remediation": "Add resources.limits.cpu to container spec",
            "category": "resource_management",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_2": {
            "name": "Ensure that CPU requests are set",
            "description": "Containers should have CPU requests for proper scheduling",
            "severity": "MEDIUM",
            "remediation": "Add resources.requests.cpu to container spec",
            "category": "resource_management",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_3": {
            "name": "Ensure that memory limits are set",
            "description": "Containers should have memory limits to prevent OOM issues",
            "severity": "MEDIUM",
            "remediation": "Add resources.limits.memory to container spec",
            "category": "resource_management",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_4": {
            "name": "Ensure that memory requests are set",
            "description": "Containers should have memory requests for proper scheduling",
            "severity": "MEDIUM",
            "remediation": "Add resources.requests.memory to container spec",
            "category": "resource_management",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_5": {
            "name": "Ensure that Tiller is not deployed",
            "description": "Helm 2 Tiller is a security risk and should not be used",
            "severity": "HIGH",
            "remediation": "Migrate to Helm 3 which does not use Tiller",
            "category": "deprecated_component",
            "frameworks": ["NSA"]
        },
        "CKV_K8S_6": {
            "name": "Ensure that liveness probe is defined",
            "description": "Liveness probes help Kubernetes detect and restart unhealthy pods",
            "severity": "MEDIUM",
            "remediation": "Add livenessProbe to container spec",
            "category": "reliability",
            "frameworks": ["CIS"]
        },
        "CKV_K8S_7": {
            "name": "Ensure that the --anonymous-auth argument is set to false",
            "description": "Anonymous authentication should be disabled on API server",
            "severity": "HIGH",
            "remediation": "Set --anonymous-auth=false in API server arguments",
            "category": "authentication",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_8": {
            "name": "Ensure that readiness probe is defined",
            "description": "Readiness probes help with service discovery and load balancing",
            "severity": "MEDIUM",
            "remediation": "Add readinessProbe to container spec",
            "category": "reliability",
            "frameworks": ["CIS"]
        },
        "CKV_K8S_9": {
            "name": "Ensure that Image Pull Policy is Always",
            "description": "Always pull images to ensure you get the latest version",
            "severity": "LOW",
            "remediation": "Set imagePullPolicy: Always",
            "category": "image_management",
            "frameworks": ["CIS"]
        },
        "CKV_K8S_10": {
            "name": "Ensure that CPU limits do not exceed 1",
            "description": "Very high CPU limits can impact other workloads",
            "severity": "LOW",
            "remediation": "Set CPU limits to reasonable values (e.g., 500m to 1000m)",
            "category": "resource_management",
            "frameworks": []
        },
        "CKV_K8S_11": {
            "name": "Ensure that memory limits do not exceed 4Gi",
            "description": "Very high memory limits can impact other workloads",
            "severity": "LOW",
            "remediation": "Set memory limits to reasonable values",
            "category": "resource_management",
            "frameworks": []
        },
        "CKV_K8S_12": {
            "name": "Ensure that secrets are not used in environment variables",
            "description": "Secrets in env vars can be exposed in logs and process listings",
            "severity": "HIGH",
            "remediation": "Use secretKeyRef or mount secrets as volumes",
            "category": "secrets_management",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_13": {
            "name": "Ensure that memory requests do not exceed limits",
            "description": "Memory requests should not exceed limits",
            "severity": "LOW",
            "remediation": "Ensure requests.memory <= limits.memory",
            "category": "resource_management",
            "frameworks": []
        },
        "CKV_K8S_14": {
            "name": "Ensure that image tag is fixed",
            "description": "Using :latest or no tag makes deployments non-reproducible",
            "severity": "MEDIUM",
            "remediation": "Use specific version tags like nginx:1.21.0",
            "category": "image_management",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_15": {
            "name": "Ensure that image pull secrets are configured",
            "description": "Private registries require pull secrets",
            "severity": "LOW",
            "remediation": "Add imagePullSecrets to pod spec",
            "category": "image_management",
            "frameworks": []
        },
        "CKV_K8S_16": {
            "name": "Ensure that privileged containers are not used",
            "description": "Privileged containers have full host access - critical security risk",
            "severity": "CRITICAL",
            "remediation": "Set securityContext.privileged: false",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST", "PCI-DSS"]
        },
        "CKV_K8S_17": {
            "name": "Ensure that containers do not share the host network namespace",
            "description": "hostNetwork gives container access to host network interfaces",
            "severity": "HIGH",
            "remediation": "Set hostNetwork: false",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_18": {
            "name": "Ensure that hostPID is not set to true",
            "description": "hostPID allows container to see host processes",
            "severity": "HIGH",
            "remediation": "Set hostPID: false or remove it",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_19": {
            "name": "Ensure that hostIPC is not set to true",
            "description": "hostIPC allows container to share IPC namespace with host",
            "severity": "HIGH",
            "remediation": "Set hostIPC: false or remove it",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_20": {
            "name": "Ensure that containers do not allow privilege escalation",
            "description": "Privilege escalation can be used to gain root access",
            "severity": "HIGH",
            "remediation": "Set securityContext.allowPrivilegeEscalation: false",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_21": {
            "name": "Ensure that the default namespace is not used",
            "description": "Resources should be deployed to specific namespaces",
            "severity": "LOW",
            "remediation": "Deploy to a dedicated namespace, not 'default'",
            "category": "namespace_management",
            "frameworks": ["CIS"]
        },
        "CKV_K8S_22": {
            "name": "Ensure that read-only filesystem is used",
            "description": "Read-only root filesystem prevents runtime modification",
            "severity": "MEDIUM",
            "remediation": "Set securityContext.readOnlyRootFilesystem: true",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_23": {
            "name": "Ensure that admission control is enabled",
            "description": "Admission controllers validate and mutate requests",
            "severity": "HIGH",
            "remediation": "Enable admission controllers in API server config",
            "category": "cluster_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_24": {
            "name": "Ensure that service account automount is disabled",
            "description": "Auto-mounting SA tokens can be a security risk",
            "severity": "MEDIUM",
            "remediation": "Set automountServiceAccountToken: false",
            "category": "service_account",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_25": {
            "name": "Ensure that Tiller Service Account is not used",
            "description": "Tiller SA often has excessive permissions",
            "severity": "HIGH",
            "remediation": "Migrate to Helm 3",
            "category": "deprecated_component",
            "frameworks": []
        },
        "CKV_K8S_26": {
            "name": "Ensure that containers do not run as root",
            "description": "Running as root is a security risk",
            "severity": "HIGH",
            "remediation": "Set runAsNonRoot: true and runAsUser to non-zero",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_27": {
            "name": "Ensure that the seccomp profile is set to docker/default",
            "description": "Seccomp profiles restrict syscalls",
            "severity": "MEDIUM",
            "remediation": "Add seccompProfile with type RuntimeDefault",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_28": {
            "name": "Ensure that capabilities are dropped",
            "description": "Dropping all capabilities follows least privilege",
            "severity": "HIGH",
            "remediation": "Set capabilities.drop: ['ALL']",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_29": {
            "name": "Ensure that AppArmor profile is set",
            "description": "AppArmor provides mandatory access control",
            "severity": "MEDIUM",
            "remediation": "Add AppArmor annotation to pod",
            "category": "pod_security",
            "frameworks": ["NSA"]
        },
        "CKV_K8S_30": {
            "name": "Ensure that NET_RAW capability is not added",
            "description": "NET_RAW allows packet manipulation attacks",
            "severity": "HIGH",
            "remediation": "Remove NET_RAW from capabilities.add",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_31": {
            "name": "Ensure that SYS_ADMIN capability is not added",
            "description": "SYS_ADMIN is essentially root privileges",
            "severity": "CRITICAL",
            "remediation": "Remove SYS_ADMIN from capabilities.add",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA", "NIST"]
        },
        "CKV_K8S_32": {
            "name": "Ensure that Tiller is not accessible from within the cluster",
            "description": "Tiller should not be network accessible",
            "severity": "HIGH",
            "remediation": "Remove Tiller or use Helm 3",
            "category": "deprecated_component",
            "frameworks": []
        },
        "CKV_K8S_33": {
            "name": "Ensure that Kubernetes Dashboard is not deployed",
            "description": "Dashboard can be a security risk if not properly secured",
            "severity": "MEDIUM",
            "remediation": "Remove Dashboard or secure with RBAC and auth proxy",
            "category": "cluster_security",
            "frameworks": ["CIS"]
        },
        "CKV_K8S_34": {
            "name": "Ensure that Tiller deployment does not use a privileged container",
            "description": "Tiller should not run privileged",
            "severity": "HIGH",
            "remediation": "Remove Tiller or disable privileged",
            "category": "deprecated_component",
            "frameworks": []
        },
        "CKV_K8S_35": {
            "name": "Ensure that secrets are not hardcoded in configmaps",
            "description": "Secrets in ConfigMaps are not encrypted",
            "severity": "HIGH",
            "remediation": "Move secrets to Secret resources",
            "category": "secrets_management",
            "frameworks": ["CIS", "NIST"]
        },
        "CKV_K8S_36": {
            "name": "Ensure that Tiller TLS is enabled",
            "description": "Tiller communication should be encrypted",
            "severity": "HIGH",
            "remediation": "Enable TLS for Tiller or migrate to Helm 3",
            "category": "deprecated_component",
            "frameworks": []
        },
        "CKV_K8S_37": {
            "name": "Ensure that minimized capabilities are added",
            "description": "Only add capabilities that are actually needed",
            "severity": "MEDIUM",
            "remediation": "Review and minimize capabilities.add list",
            "category": "pod_security",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_38": {
            "name": "Ensure that service account tokens are not mounted when not needed",
            "description": "Pods that don't need SA tokens should not mount them",
            "severity": "MEDIUM",
            "remediation": "Set automountServiceAccountToken: false",
            "category": "service_account",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_39": {
            "name": "Ensure that default service account is not used",
            "description": "Default SA often has too many permissions",
            "severity": "MEDIUM",
            "remediation": "Create dedicated service accounts for workloads",
            "category": "service_account",
            "frameworks": ["CIS", "NSA"]
        },
        "CKV_K8S_40": {
            "name": "Ensure that high UID is used",
            "description": "Using UID > 10000 avoids conflicts with host UIDs",
            "severity": "LOW",
            "remediation": "Set runAsUser to a value > 10000",
            "category": "pod_security",
            "frameworks": ["NSA"]
        },
        "CKV_K8S_41": {
            "name": "Ensure that default namespace is not used for pods",
            "description": "Pods should not run in the default namespace",
            "severity": "LOW",
            "remediation": "Deploy pods to specific namespaces",
            "category": "namespace_management",
            "frameworks": ["CIS"]
        },
        "CKV_K8S_42": {
            "name": "Ensure that root group is not used",
            "description": "Running with GID 0 can have security implications",
            "severity": "MEDIUM",
            "remediation": "Set runAsGroup to a non-zero value",
            "category": "pod_security",
            "frameworks": ["NSA"]
        },
        "CKV_K8S_43": {
            "name": "Ensure that image is using a digest",
            "description": "Digests ensure image immutability",
            "severity": "LOW",
            "remediation": "Use image@sha256:... format",
            "category": "image_management",
            "frameworks": ["NSA"]
        },
    }

    def parse(self) -> Generator[ScannerRule, None, None]:
        """Parse all Checkov Kubernetes rules."""
        logger.info(f"Parsing {len(self.KUBERNETES_RULES)} Checkov Kubernetes rules...")

        for rule_id, rule_data in self.KUBERNETES_RULES.items():
            yield ScannerRule(
                scanner="checkov",
                rule_id=rule_id,
                name=rule_data["name"],
                description=rule_data["description"],
                severity=rule_data["severity"],
                category=rule_data["category"],
                remediation=rule_data["remediation"],
                guideline_url=f"https://docs.bridgecrew.io/docs/{rule_id.lower().replace('_', '-')}",
                frameworks=rule_data.get("frameworks", [])
            )


class SemgrepRuleParser:
    """Parse Semgrep security rules."""

    # Pre-defined Semgrep Kubernetes/IaC rules
    SEMGREP_RULES = {
        "yaml.kubernetes.security.privileged-container": {
            "name": "Privileged container detected",
            "description": "Container is running in privileged mode which gives full host access",
            "severity": "ERROR",
            "fix": "Set privileged: false in securityContext",
            "category": "security"
        },
        "yaml.kubernetes.security.hostpath-mount": {
            "name": "HostPath volume mount detected",
            "description": "Mounting host paths can expose sensitive host data to containers",
            "severity": "WARNING",
            "fix": "Use PersistentVolumeClaims instead of hostPath",
            "category": "security"
        },
        "yaml.kubernetes.security.run-as-root": {
            "name": "Container running as root",
            "description": "Container is configured to run as root user",
            "severity": "WARNING",
            "fix": "Set runAsNonRoot: true and runAsUser to a non-zero value",
            "category": "security"
        },
        "yaml.kubernetes.security.no-read-only-fs": {
            "name": "Missing read-only root filesystem",
            "description": "Container does not have read-only root filesystem enabled",
            "severity": "WARNING",
            "fix": "Set readOnlyRootFilesystem: true in securityContext",
            "category": "security"
        },
        "yaml.kubernetes.security.capabilities-not-dropped": {
            "name": "Capabilities not dropped",
            "description": "Container is not dropping all capabilities",
            "severity": "WARNING",
            "fix": "Add capabilities.drop: ['ALL'] to securityContext",
            "category": "security"
        },
        "yaml.kubernetes.security.host-network": {
            "name": "Host network enabled",
            "description": "Pod is using the host network namespace",
            "severity": "WARNING",
            "fix": "Set hostNetwork: false or remove it",
            "category": "security"
        },
        "yaml.kubernetes.security.host-pid": {
            "name": "Host PID namespace enabled",
            "description": "Pod is using the host PID namespace",
            "severity": "WARNING",
            "fix": "Set hostPID: false or remove it",
            "category": "security"
        },
        "yaml.kubernetes.security.secret-in-env": {
            "name": "Secret in environment variable",
            "description": "Sensitive data is passed via environment variable",
            "severity": "WARNING",
            "fix": "Use secretKeyRef or mount secrets as volumes",
            "category": "secrets"
        },
        "yaml.kubernetes.security.missing-network-policy": {
            "name": "No NetworkPolicy defined",
            "description": "Namespace has no NetworkPolicy to restrict traffic",
            "severity": "INFO",
            "fix": "Create a NetworkPolicy to restrict ingress/egress",
            "category": "network"
        },
        "yaml.kubernetes.security.latest-tag": {
            "name": "Using :latest image tag",
            "description": "Container uses :latest tag which is mutable",
            "severity": "WARNING",
            "fix": "Use specific version tags like nginx:1.21.0",
            "category": "image"
        },
        "python.lang.security.audit.hardcoded-password": {
            "name": "Hardcoded password in Python code",
            "description": "Password is hardcoded in source code",
            "severity": "ERROR",
            "fix": "Use environment variables or secrets management",
            "category": "secrets"
        },
        "python.lang.security.dangerous-system-call": {
            "name": "Dangerous system call",
            "description": "Code uses potentially dangerous system function",
            "severity": "WARNING",
            "fix": "Review and sanitize inputs to system calls",
            "category": "injection"
        },
        "javascript.lang.security.audit.detect-eval": {
            "name": "Use of eval() detected",
            "description": "eval() can execute arbitrary code and is a security risk",
            "severity": "WARNING",
            "fix": "Avoid eval() and use safer alternatives",
            "category": "injection"
        },
        "terraform.aws.security.aws-s3-bucket-public": {
            "name": "S3 bucket is public",
            "description": "S3 bucket allows public access",
            "severity": "ERROR",
            "fix": "Set acl to 'private' and block public access",
            "category": "cloud"
        },
        "terraform.aws.security.aws-security-group-open": {
            "name": "Security group allows all traffic",
            "description": "Security group has 0.0.0.0/0 ingress rule",
            "severity": "ERROR",
            "fix": "Restrict CIDR blocks to specific IP ranges",
            "category": "cloud"
        },
    }

    def parse(self) -> Generator[ScannerRule, None, None]:
        """Parse all Semgrep rules."""
        logger.info(f"Parsing {len(self.SEMGREP_RULES)} Semgrep rules...")

        for rule_id, rule_data in self.SEMGREP_RULES.items():
            yield ScannerRule(
                scanner="semgrep",
                rule_id=rule_id,
                name=rule_data["name"],
                description=rule_data["description"],
                severity=rule_data["severity"],
                category=rule_data["category"],
                remediation=rule_data["fix"],
                guideline_url=f"https://semgrep.dev/r/{rule_id}"
            )


class TrivyRuleParser:
    """Parse Trivy misconfiguration rules."""

    TRIVY_RULES = {
        "KSV001": {
            "name": "Process can elevate its own privileges",
            "description": "Container can elevate privileges via setuid binaries",
            "severity": "MEDIUM",
            "fix": "Set allowPrivilegeEscalation: false",
            "category": "pod_security"
        },
        "KSV002": {
            "name": "Default AppArmor profile not set",
            "description": "Container should have AppArmor profile set",
            "severity": "MEDIUM",
            "fix": "Add AppArmor annotation with runtime/default profile",
            "category": "pod_security"
        },
        "KSV003": {
            "name": "Default capabilities not dropped",
            "description": "Container should drop all default capabilities",
            "severity": "LOW",
            "fix": "Set capabilities.drop: ['ALL']",
            "category": "pod_security"
        },
        "KSV004": {
            "name": "Capability added other than NET_BIND_SERVICE",
            "description": "Unnecessary capabilities added to container",
            "severity": "LOW",
            "fix": "Remove unnecessary capabilities from add list",
            "category": "pod_security"
        },
        "KSV005": {
            "name": "SYS_ADMIN capability added",
            "description": "SYS_ADMIN is essentially root and should not be used",
            "severity": "HIGH",
            "fix": "Remove SYS_ADMIN from capabilities.add",
            "category": "pod_security"
        },
        "KSV006": {
            "name": "hostPath volume mounted with docker.sock",
            "description": "Docker socket mounted which allows container escape",
            "severity": "HIGH",
            "fix": "Remove docker.sock hostPath mount",
            "category": "pod_security"
        },
        "KSV007": {
            "name": "hostAliases set",
            "description": "hostAliases can be used to redirect traffic",
            "severity": "LOW",
            "fix": "Remove hostAliases unless absolutely required",
            "category": "pod_security"
        },
        "KSV008": {
            "name": "Access to host IPC namespace",
            "description": "Container has access to host IPC namespace",
            "severity": "HIGH",
            "fix": "Set hostIPC: false",
            "category": "pod_security"
        },
        "KSV009": {
            "name": "Access to host network",
            "description": "Container has access to host network namespace",
            "severity": "HIGH",
            "fix": "Set hostNetwork: false",
            "category": "pod_security"
        },
        "KSV010": {
            "name": "Access to host PID namespace",
            "description": "Container can see host processes",
            "severity": "HIGH",
            "fix": "Set hostPID: false",
            "category": "pod_security"
        },
        "KSV011": {
            "name": "CPU not limited",
            "description": "Container has no CPU limit set",
            "severity": "LOW",
            "fix": "Set resources.limits.cpu",
            "category": "resource_management"
        },
        "KSV012": {
            "name": "Runs as root user",
            "description": "Container runs as UID 0 (root)",
            "severity": "MEDIUM",
            "fix": "Set runAsNonRoot: true and runAsUser > 0",
            "category": "pod_security"
        },
        "KSV013": {
            "name": "Image tag is latest",
            "description": "Container uses :latest or no tag",
            "severity": "LOW",
            "fix": "Use specific version tag",
            "category": "image_management"
        },
        "KSV014": {
            "name": "Root file system is not read-only",
            "description": "Container can write to root filesystem",
            "severity": "LOW",
            "fix": "Set readOnlyRootFilesystem: true",
            "category": "pod_security"
        },
        "KSV015": {
            "name": "CPU requests not specified",
            "description": "Container has no CPU request set",
            "severity": "LOW",
            "fix": "Set resources.requests.cpu",
            "category": "resource_management"
        },
        "KSV016": {
            "name": "Memory not limited",
            "description": "Container has no memory limit set",
            "severity": "LOW",
            "fix": "Set resources.limits.memory",
            "category": "resource_management"
        },
        "KSV017": {
            "name": "Privileged container",
            "description": "Container is running in privileged mode",
            "severity": "HIGH",
            "fix": "Set privileged: false",
            "category": "pod_security"
        },
        "KSV018": {
            "name": "Memory requests not specified",
            "description": "Container has no memory request set",
            "severity": "LOW",
            "fix": "Set resources.requests.memory",
            "category": "resource_management"
        },
        "KSV020": {
            "name": "Low user ID",
            "description": "Container runs with UID < 10000",
            "severity": "LOW",
            "fix": "Set runAsUser to value >= 10000",
            "category": "pod_security"
        },
        "KSV021": {
            "name": "Low group ID",
            "description": "Container runs with GID < 10000",
            "severity": "LOW",
            "fix": "Set runAsGroup to value >= 10000",
            "category": "pod_security"
        },
        "KSV022": {
            "name": "No seccomp profile set",
            "description": "Container has no seccomp profile configured",
            "severity": "MEDIUM",
            "fix": "Add seccompProfile with type RuntimeDefault",
            "category": "pod_security"
        },
        "KSV023": {
            "name": "hostPath volume mounted",
            "description": "Container mounts host filesystem path",
            "severity": "MEDIUM",
            "fix": "Use PersistentVolumeClaims or emptyDir instead",
            "category": "pod_security"
        },
        "KSV024": {
            "name": "Access to host ports",
            "description": "Container uses host ports",
            "severity": "HIGH",
            "fix": "Remove hostPort from container ports",
            "category": "pod_security"
        },
        "KSV025": {
            "name": "SELinux options set",
            "description": "SELinux options configured which may reduce isolation",
            "severity": "MEDIUM",
            "fix": "Review SELinux options and remove if not needed",
            "category": "pod_security"
        },
        "KSV027": {
            "name": "Non-default /proc mask set",
            "description": "procMount is not set to Default",
            "severity": "MEDIUM",
            "fix": "Set procMount to Default or remove",
            "category": "pod_security"
        },
        "KSV028": {
            "name": "Non-ephemeral volume type used",
            "description": "Using volume types that may have security implications",
            "severity": "LOW",
            "fix": "Review volume types and use emptyDir where possible",
            "category": "pod_security"
        },
        "KSV029": {
            "name": "Unsafe sysctl options set",
            "description": "Pod sets sysctl options that may be unsafe",
            "severity": "HIGH",
            "fix": "Remove unsafe sysctl settings",
            "category": "pod_security"
        },
        "KSV030": {
            "name": "Default Seccomp profile not set",
            "description": "Seccomp profile should be RuntimeDefault",
            "severity": "LOW",
            "fix": "Set seccompProfile.type to RuntimeDefault",
            "category": "pod_security"
        },
    }

    def parse(self) -> Generator[ScannerRule, None, None]:
        """Parse all Trivy rules."""
        logger.info(f"Parsing {len(self.TRIVY_RULES)} Trivy rules...")

        for rule_id, rule_data in self.TRIVY_RULES.items():
            yield ScannerRule(
                scanner="trivy",
                rule_id=rule_id,
                name=rule_data["name"],
                description=rule_data["description"],
                severity=rule_data["severity"],
                category=rule_data["category"],
                remediation=rule_data["fix"],
                guideline_url=f"https://avd.aquasec.com/misconfig/kubernetes/{rule_id.lower()}"
            )


class KubeBenchRuleParser:
    """Parse CIS Kubernetes Benchmark rules from kube-bench."""

    KUBE_BENCH_RULES = {
        "1.1.1": {
            "name": "Ensure that the API server pod specification file permissions are set to 644 or more restrictive",
            "description": "The API server pod specification file should have restrictive permissions",
            "severity": "HIGH",
            "fix": "chmod 644 /etc/kubernetes/manifests/kube-apiserver.yaml",
            "category": "control_plane",
            "scored": True
        },
        "1.2.1": {
            "name": "Ensure that the --anonymous-auth argument is set to false",
            "description": "Disable anonymous requests to the API server",
            "severity": "HIGH",
            "fix": "Set --anonymous-auth=false in API server arguments",
            "category": "api_server",
            "scored": True
        },
        "1.2.2": {
            "name": "Ensure that the --token-auth-file parameter is not set",
            "description": "Do not use static token-based authentication",
            "severity": "HIGH",
            "fix": "Remove --token-auth-file argument from API server",
            "category": "api_server",
            "scored": True
        },
        "1.2.6": {
            "name": "Ensure that the --kubelet-certificate-authority argument is set",
            "description": "Verify kubelet certificates using CA",
            "severity": "HIGH",
            "fix": "Set --kubelet-certificate-authority in API server",
            "category": "api_server",
            "scored": True
        },
        "1.2.16": {
            "name": "Ensure that the admission control plugin PodSecurityPolicy is set",
            "description": "Enable Pod Security Policy admission controller",
            "severity": "HIGH",
            "fix": "Add PodSecurityPolicy to --enable-admission-plugins",
            "category": "api_server",
            "scored": True
        },
        "4.2.1": {
            "name": "Ensure that the kubelet service file permissions are set to 644",
            "description": "Kubelet service file should have restrictive permissions",
            "severity": "HIGH",
            "fix": "chmod 644 /etc/systemd/system/kubelet.service.d/10-kubeadm.conf",
            "category": "worker_node",
            "scored": True
        },
        "4.2.6": {
            "name": "Ensure that the --protect-kernel-defaults argument is set to true",
            "description": "Kubelet should protect kernel defaults",
            "severity": "HIGH",
            "fix": "Set --protect-kernel-defaults=true in kubelet",
            "category": "worker_node",
            "scored": True
        },
        "5.1.1": {
            "name": "Ensure that the cluster-admin role is only used where required",
            "description": "cluster-admin role grants full cluster access",
            "severity": "HIGH",
            "fix": "Review and minimize cluster-admin bindings",
            "category": "rbac",
            "scored": False
        },
        "5.1.3": {
            "name": "Minimize wildcard use in Roles and ClusterRoles",
            "description": "Wildcard access grants broader permissions than needed",
            "severity": "MEDIUM",
            "fix": "Replace wildcards with specific resource/verb lists",
            "category": "rbac",
            "scored": False
        },
        "5.2.1": {
            "name": "Minimize the admission of privileged containers",
            "description": "Privileged containers should be restricted",
            "severity": "HIGH",
            "fix": "Use Pod Security Policies/Standards to block privileged",
            "category": "pod_security",
            "scored": False
        },
        "5.2.2": {
            "name": "Minimize the admission of containers wishing to share host process ID namespace",
            "description": "hostPID should be restricted",
            "severity": "HIGH",
            "fix": "Use Pod Security Policies/Standards to block hostPID",
            "category": "pod_security",
            "scored": False
        },
        "5.2.3": {
            "name": "Minimize the admission of containers wishing to share host IPC namespace",
            "description": "hostIPC should be restricted",
            "severity": "HIGH",
            "fix": "Use Pod Security Policies/Standards to block hostIPC",
            "category": "pod_security",
            "scored": False
        },
        "5.2.4": {
            "name": "Minimize the admission of containers wishing to share host network namespace",
            "description": "hostNetwork should be restricted",
            "severity": "HIGH",
            "fix": "Use Pod Security Policies/Standards to block hostNetwork",
            "category": "pod_security",
            "scored": False
        },
        "5.2.5": {
            "name": "Minimize the admission of containers with allowPrivilegeEscalation",
            "description": "allowPrivilegeEscalation should be false",
            "severity": "HIGH",
            "fix": "Use Pod Security Policies/Standards to require allowPrivilegeEscalation: false",
            "category": "pod_security",
            "scored": False
        },
        "5.3.1": {
            "name": "Ensure that the CNI in use supports Network Policies",
            "description": "Network policies require CNI support",
            "severity": "HIGH",
            "fix": "Use CNI that supports NetworkPolicy (Calico, Cilium, etc.)",
            "category": "network",
            "scored": False
        },
        "5.3.2": {
            "name": "Ensure that all Namespaces have Network Policies defined",
            "description": "Every namespace should have NetworkPolicy",
            "severity": "MEDIUM",
            "fix": "Create default deny NetworkPolicy in each namespace",
            "category": "network",
            "scored": False
        },
        "5.4.1": {
            "name": "Prefer using secrets as files over secrets as environment variables",
            "description": "Secrets in env vars can be exposed in logs",
            "severity": "MEDIUM",
            "fix": "Mount secrets as volumes instead of env vars",
            "category": "secrets",
            "scored": False
        },
        "5.4.2": {
            "name": "Consider external secret storage",
            "description": "Use external secret managers like Vault",
            "severity": "MEDIUM",
            "fix": "Integrate with HashiCorp Vault or cloud secrets manager",
            "category": "secrets",
            "scored": False
        },
        "5.7.1": {
            "name": "Create administrative boundaries between resources using namespaces",
            "description": "Use namespaces to isolate workloads",
            "severity": "MEDIUM",
            "fix": "Deploy workloads to dedicated namespaces",
            "category": "namespace",
            "scored": False
        },
        "5.7.2": {
            "name": "Ensure that the seccomp profile is set to docker/default",
            "description": "Use seccomp to restrict syscalls",
            "severity": "MEDIUM",
            "fix": "Set seccompProfile.type to RuntimeDefault",
            "category": "pod_security",
            "scored": False
        },
        "5.7.3": {
            "name": "Apply Security Context to Your Pods and Containers",
            "description": "Always define securityContext for pods/containers",
            "severity": "MEDIUM",
            "fix": "Add securityContext with runAsNonRoot, readOnlyRootFilesystem, etc.",
            "category": "pod_security",
            "scored": False
        },
        "5.7.4": {
            "name": "The default namespace should not be used",
            "description": "Resources should not be in default namespace",
            "severity": "LOW",
            "fix": "Deploy resources to dedicated namespaces",
            "category": "namespace",
            "scored": False
        },
    }

    def parse(self) -> Generator[ScannerRule, None, None]:
        """Parse all Kube-bench rules."""
        logger.info(f"Parsing {len(self.KUBE_BENCH_RULES)} Kube-bench CIS rules...")

        for rule_id, rule_data in self.KUBE_BENCH_RULES.items():
            yield ScannerRule(
                scanner="kube-bench",
                rule_id=f"CIS-{rule_id}",
                name=rule_data["name"],
                description=rule_data["description"],
                severity=rule_data["severity"],
                category=rule_data["category"],
                remediation=rule_data["fix"],
                guideline_url=f"https://www.cisecurity.org/benchmark/kubernetes",
                frameworks=["CIS"]
            )


class TrainingDataGenerator:
    """Generate training data from scanner rules."""

    # Map severity to rank
    SEVERITY_TO_RANK = {
        "CRITICAL": "D",
        "HIGH": "C",
        "ERROR": "C",
        "MEDIUM": "D",
        "WARNING": "D",
        "LOW": "E",
        "INFO": "E"
    }

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.parsers = {
            "checkov": CheckovRuleParser(),
            "semgrep": SemgrepRuleParser(),
            "trivy": TrivyRuleParser(),
            "kube-bench": KubeBenchRuleParser()
        }

    def generate_training_pairs(self, rule: ScannerRule) -> List[Dict[str, Any]]:
        """Generate multiple training pairs from a single rule."""
        pairs = []
        rank = self.SEVERITY_TO_RANK.get(rule.severity, "D")

        # Pair 1: What does this rule check?
        pairs.append({
            "instruction": f"What does {rule.scanner} rule {rule.rule_id} check for?",
            "input": "",
            "output": f"{rule.name}. {rule.description}"
        })

        # Pair 2: How to fix this finding?
        pairs.append({
            "instruction": f"How do I fix {rule.scanner} finding {rule.rule_id} ({rule.name})?",
            "input": "",
            "output": f"To fix this issue: {rule.remediation}"
        })

        # Pair 3: Severity and rank classification
        pairs.append({
            "instruction": f"A scan found {rule.scanner} rule {rule.rule_id} violated: \"{rule.name}\". What rank should this be?",
            "input": f"Severity: {rule.severity}, Category: {rule.category}",
            "output": f"This finding should be classified as {rank}-rank because it has {rule.severity} severity in the {rule.category} category. {self._get_rank_reasoning(rank, rule)}"
        })

        # Pair 4: Compliance frameworks (if available)
        if rule.frameworks:
            pairs.append({
                "instruction": f"What compliance frameworks does {rule.scanner} rule {rule.rule_id} map to?",
                "input": "",
                "output": f"This rule maps to the following compliance frameworks: {', '.join(rule.frameworks)}."
            })

        # Pair 5: Should this be auto-fixed?
        pairs.append({
            "instruction": f"Should {rule.scanner} finding {rule.rule_id} be automatically fixed?",
            "input": f"Severity: {rule.severity}, Rule: {rule.name}",
            "output": self._get_automation_guidance(rank, rule)
        })

        return pairs

    def _get_rank_reasoning(self, rank: str, rule: ScannerRule) -> str:
        """Get reasoning for rank classification."""
        reasoning = {
            "E": "E-rank findings are low-impact and can be auto-fixed silently.",
            "D": "D-rank findings should be auto-fixed with logging for audit.",
            "C": "C-rank findings require approval before fixing due to potential impact.",
            "B": "B-rank findings need human review due to complex trade-offs.",
            "S": "S-rank findings require senior human decision due to strategic implications."
        }
        return reasoning.get(rank, "")

    def _get_automation_guidance(self, rank: str, rule: ScannerRule) -> str:
        """Get guidance on whether to auto-fix."""
        if rank in ("E", "D"):
            return (
                f"Yes, this {rank}-rank finding can be automatically fixed. "
                f"The fix involves: {rule.remediation}"
            )
        elif rank == "C":
            return (
                f"This {rank}-rank finding should not be auto-fixed without approval. "
                f"Request JADE approval before applying fix: {rule.remediation}"
            )
        else:
            return (
                f"No, this {rank}-rank finding requires human review. "
                f"Escalate to security team with recommended fix: {rule.remediation}"
            )

    def generate(
        self,
        source: str = "all",
        output_file: Optional[str] = None,
        dry_run: bool = False
    ) -> Path:
        """
        Generate training data from scanner rules.

        Args:
            source: Scanner name or "all"
            output_file: Output file name
            dry_run: If True, only count without writing

        Returns:
            Path to generated file
        """
        if source == "all":
            sources = list(self.parsers.keys())
        else:
            sources = [source]

        all_pairs = []

        for src in sources:
            if src not in self.parsers:
                logger.warning(f"Unknown source: {src}")
                continue

            parser = self.parsers[src]
            rules = list(parser.parse())

            logger.info(f"Generating training pairs from {len(rules)} {src} rules...")

            for rule in tqdm(rules, desc=f"Processing {src}"):
                pairs = self.generate_training_pairs(rule)
                all_pairs.extend(pairs)

        logger.info(f"Generated {len(all_pairs)} training pairs total")

        if dry_run:
            logger.info("Dry run - not writing to file")
            return None

        # Write to file
        output_file = output_file or f"{source}-training.jsonl"
        output_path = self.output_dir / output_file

        with open(output_path, "w") as f:
            for pair in all_pairs:
                f.write(json.dumps(pair) + "\n")

        logger.info(f"Wrote training data to: {output_path}")
        return output_path

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about available rules."""
        stats = {
            "total_rules": 0,
            "by_scanner": {},
            "by_severity": {},
            "by_category": {},
            "estimated_training_pairs": 0
        }

        for scanner_name, parser in self.parsers.items():
            rules = list(parser.parse())
            stats["by_scanner"][scanner_name] = len(rules)
            stats["total_rules"] += len(rules)

            for rule in rules:
                stats["by_severity"][rule.severity] = stats["by_severity"].get(rule.severity, 0) + 1
                stats["by_category"][rule.category] = stats["by_category"].get(rule.category, 0) + 1

        # Each rule generates ~5 training pairs
        stats["estimated_training_pairs"] = stats["total_rules"] * 5

        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Generate JADE training data from security scanner rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate_scanner_training_data.py --source checkov
    python generate_scanner_training_data.py --source all --output all-scanners.jsonl
    python generate_scanner_training_data.py --stats
    python generate_scanner_training_data.py --dry-run
        """
    )

    parser.add_argument(
        "--source",
        type=str,
        choices=["checkov", "semgrep", "trivy", "kube-bench", "all"],
        default="all",
        help="Scanner source to generate from (default: all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file name (default: {source}-training.jsonl)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics about available rules"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count pairs without writing to file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    generator = TrainingDataGenerator(output_dir=output_dir)

    if args.stats:
        stats = generator.get_stats()
        print("\n=== Scanner Rule Statistics ===\n")
        print(f"Total rules: {stats['total_rules']}")
        print(f"Estimated training pairs: {stats['estimated_training_pairs']}")
        print("\nBy Scanner:")
        for scanner, count in sorted(stats["by_scanner"].items()):
            print(f"  {scanner}: {count}")
        print("\nBy Severity:")
        for severity, count in sorted(stats["by_severity"].items()):
            print(f"  {severity}: {count}")
        print("\nBy Category:")
        for category, count in sorted(stats["by_category"].items(), key=lambda x: -x[1])[:10]:
            print(f"  {category}: {count}")
    else:
        output = generator.generate(
            source=args.source,
            output_file=args.output,
            dry_run=args.dry_run
        )
        if output:
            print(f"\nTraining data generated: {output}")


if __name__ == "__main__":
    main()
