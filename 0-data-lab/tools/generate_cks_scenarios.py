import json
import os
from pathlib import Path
import random

V2_PATH = "4-GP-CLARIFY/2-test-data/evaluation/02-cks-benchmark/cks_eval_suite_v2.jsonl"
V3_PATH = "4-GP-CLARIFY/2-test-data/evaluation/02-cks-benchmark/cks_eval_suite_v3.jsonl"

def get_scenarios():
    scenarios = []
    
    # CLUSTER SETUP (011 - 030)
    setup_templates = [
        "Enable audit logging for the API server. Store logs in /var/log/audit.log with max retention of {n} days.",
        "Configure etcd to use encryption at rest with the AES-GCM provider. Rotate the key to a new 32-byte value.",
        "Restrict the API server to only allow secure connections on port {port} and disable the insecure port.",
        "Use kubeadm to renew all cluster certificates and verify their expiration dates.",
        "Harden the Kubelet configuration by disabling anonymous authentication and setting the authorization mode to Webhook.",
        "Implement a custom AdmissionConfiguration file to enable the NodeRestriction and PodSecurity plugins.",
        "Configure the API server to use a specific OIDC issuer URL {url} and client ID {id} for authentication.",
        "Set up a secondary API server with identical security configuration for high availability and load balancing."
    ]
    
    for i in range(11, 31):
        template = random.choice(setup_templates)
        scenarios.append({
            "id": f"cks-cluster-setup-{i:03d}",
            "domain": "cluster_setup",
            "difficulty": random.choice(["B", "C"]),
            "scenario": template.format(n=random.randint(7, 30), port=random.randint(6443, 6450), url="https://oidc.corp.com", id="cks-client"),
            "expected_actions": ["Modify kube-apiserver.yaml", "Apply changes", "Verify component status"],
            "expected_resources": ["StaticPod", "ConfigMap"],
            "validation_keywords": ["--audit-log-path", "encryption", "kubeadm", "OIDC"],
            "cks_objective": "Harden cluster components"
        })

    # CLUSTER HARDENING (010 - 045)
    hardening_templates = [
        "A ServiceAccount '{sa}' has been found with 'cluster-admin' privileges. Revoke these and assign it a Role with only 'get' permissions in the '{ns}' namespace.",
        "Configure a ClusterRole to allow users in the group '{group}' to only view 'Secrets' across all namespaces.",
        "Disable the 'automountServiceAccountToken' for the default ServiceAccount in the '{ns}' namespace to prevent token leakage.",
        "Implement a NetworkPolicy to isolate the '{ns}' namespace, allowing only ingress traffic from the '{source_ns}' namespace.",
        "Harden the etcd cluster by requiring TLS client certificate authentication for all clients including the API server.",
        "Create a Kubeconfig for a developer that restricts access to only a single namespace '{ns}' with limited resource access.",
        "Upgrade the cluster nodes to the latest security patch version {v} using kubeadm.",
        "Restrict access to the Node's metadata API (e.g., on AWS/GCP) from pods within the cluster."
    ]
    
    for i in range(10, 46):
        template = random.choice(hardening_templates)
        scenarios.append({
            "id": f"cks-cluster-hardening-{i:03d}",
            "domain": "cluster_hardening",
            "difficulty": random.choice(["B", "C"]),
            "scenario": template.format(sa="app-sa", ns="prod", group="auditors", source_ns="frontend", v="v1.29.2"),
            "expected_actions": ["Create Role/RoleBinding", "Update ServiceAccount", "Apply NetworkPolicy"],
            "expected_resources": ["Role", "RoleBinding", "ServiceAccount", "NetworkPolicy"],
            "validation_keywords": ["RBAC", "least-privilege", "automount", "TLS"],
            "cks_objective": "Cluster hardening"
        })

    # SYSTEM HARDENING (010 - 045)
    system_templates = [
        "Apply an AppArmor profile '{profile}' to the container '{container}' to restrict unauthorized filesystem writes.",
        "Configure a Pod to use a Seccomp profile '{profile}' to limit the available system calls to a minimal set.",
        "Harden the worker node OS by disabling unused services like '{service}' and removing unnecessary packages.",
        "Set the kernel parameter 'kernel.unprivileged_userns_clone' to 0 to mitigate potential container escape vulnerabilities.",
        "Ensure that the Docker/containerd socket is only accessible by the 'root' user and the '{group}' group with minimal permissions.",
        "Configure the Kubelet to use a dedicated directory for Seccomp profiles and verify that the 'RuntimeDefault' profile is active.",
        "Identify and remove any setuid/setgid binaries on the host that are not required for operation.",
        "Harden SSH access to the nodes by disabling password authentication and only allowing specific SSH keys."
    ]
    
    for i in range(10, 46):
        template = random.choice(system_templates)
        scenarios.append({
            "id": f"cks-system-hardening-{i:03d}",
            "domain": "system_hardening",
            "difficulty": random.choice(["B", "C"]),
            "scenario": template.format(profile="strict-profile", container="api-server", service="telnetd", group="docker"),
            "expected_actions": ["Modify Pod spec", "Update host configuration", "Apply security profiles"],
            "expected_resources": ["Pod", "Node"],
            "validation_keywords": ["AppArmor", "Seccomp", "kernel", "SSH"],
            "cks_objective": "Harden host and containers"
        })

    # MINIMIZE MICROSERVICE VULNERABILITIES (013 - 060)
    micro_templates = [
        "Enable Pod Security Standard 'restricted' for the '{ns}' namespace and verify that non-compliant pods are blocked.",
        "Implement a NetworkPolicy for the '{app}' pod that allows ingress on port {port} only from pods with the label '{label}'.",
        "Configure a Pod's securityContext to run as a non-root user with UID {uid} and GID {gid}.",
        "Ensure that all containers in a Pod have 'allowPrivilegeEscalation' set to false to prevent privilege escalation attacks.",
        "Mount a Kubernetes Secret as a read-only volume in the '{container}' container instead of using environment variables.",
        "Use a service mesh to enforce mTLS for all communication between the '{svc_a}' and '{svc_b}' services.",
        "Identify and remediate a Pod that is running with a 'privileged' container by removing the privileged flag.",
        "Restrict egress traffic from the '{ns}' namespace to only allow connections to the internal database and DNS."
    ]
    
    for i in range(13, 61):
        template = random.choice(micro_templates)
        scenarios.append({
            "id": f"cks-microservice-{i:03d}",
            "domain": "minimize_microservice_vulnerabilities",
            "difficulty": random.choice(["B", "C"]),
            "scenario": template.format(ns="payments", app="web-server", port=8080, label="role=frontend", uid=10001, gid=10001, container="app", svc_a="api", svc_b="db"),
            "expected_actions": ["Label namespace", "Create NetworkPolicy", "Modify Pod spec"],
            "expected_resources": ["Namespace", "NetworkPolicy", "Pod", "Deployment"],
            "validation_keywords": ["restricted", "securityContext", "mTLS", "egress"],
            "cks_objective": "Minimize microservice vulnerabilities"
        })

    # SUPPLY CHAIN SECURITY (013 - 060)
    supply_templates = [
        "Scan the image '{image}' for CRITICAL vulnerabilities using '{scanner}' and ensure the build fails if any are found.",
        "Configure an ImagePolicyWebhook to only allow images that have been signed by the corporate private key.",
        "Harden a Dockerfile for a '{lang}' application by using a multi-stage build and a minimal base image like '{base}'.",
        "Sign the container image '{image}' using Cosign and verify the signature in the cluster using a policy engine.",
        "Ensure that all images in the '{ns}' namespace are referenced by their SHA256 digest instead of a mutable tag.",
        "Configure a private registry and ensure that the cluster uses 'imagePullSecrets' to securely authenticate.",
        "Identify and remove hardcoded secrets or sensitive information from the Dockerfile for the '{app}' application.",
        "Use 'syft' to generate an SBOM for the image '{image}' and store it for compliance auditing."
    ]
    
    for i in range(13, 61):
        template = random.choice(supply_templates)
        scenarios.append({
            "id": f"cks-supply-{i:03d}",
            "domain": "supply_chain_security",
            "difficulty": random.choice(["B", "C"]),
            "scenario": template.format(image="my-app:v1", scanner="trivy", lang="Node.js", base="alpine", ns="prod", app="gateway"),
            "expected_actions": ["Run vulnerability scan", "Update Dockerfile", "Sign image", "Verify digest"],
            "expected_resources": ["Dockerfile", "Image", "ImagePolicyWebhook"],
            "validation_keywords": ["vulnerability", "digest", "multi-stage", "Cosign"],
            "cks_objective": "Secure supply chain"
        })

    # MONITORING, LOGGING, RUNTIME SECURITY (013 - 060)
    mon_templates = [
        "Configure Falco to detect when a process attempts to modify sensitive files like '/etc/shadow' or '/etc/passwd'.",
        "Enable audit logging for specific resources like 'ConfigMaps' and 'Secrets' and verify that events are recorded.",
        "Use 'sysdig' to capture and analyze the system calls of a container '{container}' suspected of malicious activity.",
        "Implement a runtime security policy to block any container from spawning a shell process in the '{ns}' namespace.",
        "Configure a centralized log management system to aggregate logs from all nodes and provide real-time alerting for security events.",
        "Identify a Pod that is consuming excessive network bandwidth and isolate it using a NetworkPolicy.",
        "Use 'kubescape' to perform a cluster-wide security audit and remediate any high-severity findings.",
        "Detect and alert on any unauthorized access to the Kubernetes API server using audit log analysis."
    ]
    
    for i in range(13, 61):
        template = random.choice(mon_templates)
        scenarios.append({
            "id": f"cks-mon-{i:03d}",
            "domain": "monitoring_logging_runtime_security",
            "difficulty": random.choice(["B", "C"]),
            "scenario": template.format(container="web-app", ns="production"),
            "expected_actions": ["Configure Falco", "Enable audit logs", "Run security audit"],
            "expected_resources": ["FalcoRule", "AuditLog", "Pod", "NetworkPolicy"],
            "validation_keywords": ["Falco", "audit", "runtime", "Sysdig"],
            "cks_objective": "Runtime security"
        })

    return scenarios

def main():
    if not os.path.exists(V2_PATH):
        print(f"Error: {V2_PATH} not found.")
        return
        
    with open(V2_PATH, 'r') as f:
        v2_lines = [line.strip() for line in f if line.strip()]
    
    new_scenarios = get_scenarios()
    
    print(f"Current scenarios: {len(v2_lines)}")
    print(f"Adding new scenarios: {len(new_scenarios)}")
    
    with open(V3_PATH, 'w') as f:
        for line in v2_lines:
            f.write(line + "\n")
        for s in new_scenarios:
            f.write(json.dumps(s) + "\n")
            
    print(f"Total scenarios in V3: {len(v2_lines) + len(new_scenarios)}")
    print(f"V3 saved to: {V3_PATH}")

if __name__ == "__main__":
    main()
