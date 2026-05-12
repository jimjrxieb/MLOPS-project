import json
from pathlib import Path

OUTPUT_FILE = Path("1-GP-GLUE/01-raw-data-lake/8b-jade/nist_800_53_controls.jsonl")

CONTROLS = [
    {
        "control_id": "AC-6",
        "control_family": "Access Control",
        "title": "Least Privilege",
        "summary": "The system enforces least privilege, allowing only authorized access needed for users and processes to accomplish assigned organizational tasks.",
        "kubernetes_relevance": "Maps to RBAC configuration, ServiceAccount permissions, pod security contexts, and namespace isolation. Findings related to cluster-admin bindings, wildcard permissions, or default ServiceAccount usage violate this control.",
        "common_findings": ["cluster-admin-binding", "wildcard-iam", "default-sa-token-mount", "privileged-container"],
        "scanner_mappings": ["ckv-k8s-43", "ckv-k8s-49", "kubescape-C-0035"],
        "remediation_approach": "Implement dedicated ServiceAccounts with minimum required permissions. Use Role/RoleBinding instead of ClusterRole/ClusterRoleBinding where possible. Set automountServiceAccountToken: false by default.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "AU-2",
        "control_family": "Audit and Accountability",
        "title": "Event Logging",
        "summary": "The organization determines that the information system is capable of auditing the following events: [Assignment: organization-defined auditable events].",
        "kubernetes_relevance": "Maps to Kubernetes API server audit logging, Falco runtime events, and CloudTrail logs. Missing audit policies or insufficient log retention violate this control.",
        "common_findings": ["audit-logging-disabled", "insufficient-log-retention"],
        "scanner_mappings": ["kube-bench-1.2.22", "falco-rule-shell-in-container"],
        "remediation_approach": "Enable the Kubernetes audit log with an appropriate policy file. Configure central log aggregation (e.g., Fluentd, CloudWatch) with long-term retention.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "SC-8",
        "control_family": "System and Communications Protection",
        "title": "Transmission Confidentiality and Integrity",
        "summary": "The system protects the confidentiality and integrity of transmitted information.",
        "kubernetes_relevance": "Maps to TLS configuration for Ingress, mTLS for service-to-service communication (Service Mesh), and encrypted connections to external databases.",
        "common_findings": ["weak-tls-ciphers", "unencrypted-traffic", "missing-mtls"],
        "scanner_mappings": ["sslyze-vulnerability", "istio-analyzer-mtls"],
        "remediation_approach": "Enforce TLS 1.2+ with strong cipher suites. Implement a Service Mesh (Istio/Linkerd) for STRICT mTLS between workloads.",
        "fedramp_baseline": "MODERATE, HIGH"
    },
    {
        "control_id": "SI-2",
        "control_family": "System and Information Integrity",
        "title": "Flaw Remediation",
        "summary": "The organization identifies, reports, and corrects system flaws; tests software and firmware updates related to flaw remediation.",
        "kubernetes_relevance": "Maps to container image vulnerability scanning (Trivy/Grype) and automated patching/updates of base images and Kubernetes components.",
        "common_findings": ["critical-cve-detected", "outdated-base-image"],
        "scanner_mappings": ["trivy-scan-high", "grype-sbom-vulnerability"],
        "remediation_approach": "Integrate image scanning into CI/CD pipelines. Use multi-stage builds and minimal base images. Automate image rebuilds when new patches are available.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    }
]

def main():
    with open(OUTPUT_FILE, 'w') as f:
        for control in CONTROLS:
            f.write(json.dumps(control) + "\n")
    print(f"Generated {len(CONTROLS)} NIST 800-53 control summaries to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
