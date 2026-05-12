import json
from pathlib import Path

OUTPUT_FILE = Path("2-GP-OPENSEARCH/01-unprocessed/compliance/ccsp_domain_summaries.jsonl")

CCSP_DOMAINS = [
    {
        "control_id": "CCSP-D1",
        "control_family": "Cloud Concepts, Architecture and Design",
        "title": "Cloud Computing Concepts",
        "summary": "Covers cloud computing definitions, service models (IaaS, PaaS, SaaS), and deployment models (Public, Private, Hybrid, Community).",
        "kubernetes_relevance": "Relates to understanding shared responsibility in managed K8s (EKS/GKE/AKS) vs self-managed clusters.",
        "common_findings": ["misunderstood-shared-responsibility", "incorrect-service-model-selection"],
        "scanner_mappings": ["general-architecture-review"],
        "remediation_approach": "Review cloud architecture against NIST SP 800-145 and verify service model security boundaries.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "CCSP-D2",
        "control_family": "Cloud Data Security",
        "title": "Cloud Data Lifecycle",
        "summary": "Focuses on data inventory, classification, and protection throughout its lifecycle (Create, Store, Use, Share, Archive, Destroy).",
        "kubernetes_relevance": "Involves encryption at rest for PVs, Secrets management, and data labeling within the cluster.",
        "common_findings": ["unencrypted-persistent-volumes", "exposed-secrets-in-logs"],
        "scanner_mappings": ["trivy-secret-scan", "checkov-aws-s3-encryption"],
        "remediation_approach": "Enforce encryption at rest and in transit. Use specialized tools like HashiCorp Vault for secret management.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "CCSP-D3",
        "control_family": "Cloud Platform and Infrastructure Security",
        "title": "Infrastructure Hardening",
        "summary": "Covers physical security, network security, and host-level hardening in a cloud environment.",
        "kubernetes_relevance": "Relates to Node hardening, VPC security groups for the control plane, and network policies.",
        "common_findings": ["open-kube-apiserver-port", "unhardened-worker-nodes"],
        "scanner_mappings": ["kube-bench", "cis-k8s-nodes"],
        "remediation_approach": "Apply CIS benchmarks to all nodes and restrict API server access via firewalls/SGs.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "CCSP-D4",
        "control_family": "Cloud Application Security",
        "title": "Secure Software Development",
        "summary": "Focuses on the SDLC, application security testing (SAST/DAST), and secure coding practices.",
        "kubernetes_relevance": "Includes container image scanning, SBOM generation, and integrating security into the CI/CD pipeline.",
        "common_findings": ["critical-vulnerabilities-in-images", "missing-sast-in-pipeline"],
        "scanner_mappings": ["trivy", "grype", "semgrep"],
        "remediation_approach": "Shift security left by integrating scanners into Git and build stages. Use multi-stage Dockerfiles.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "CCSP-D5",
        "control_family": "Cloud Security Operations",
        "title": "Operations Management",
        "summary": "Covers incident response, performance monitoring, and configuration management.",
        "kubernetes_relevance": "Relates to Falco for runtime detection, Prometheus for monitoring, and audit log analysis.",
        "common_findings": ["missing-runtime-alerts", "insufficient-audit-logging"],
        "scanner_mappings": ["falco", "sysdig"],
        "remediation_approach": "Deploy centralized logging and alerting. Automate incident response playbooks using serverless or agents.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    },
    {
        "control_id": "CCSP-D6",
        "control_family": "Legal, Risk and Compliance",
        "title": "Regulatory Requirements",
        "summary": "Focuses on international laws, privacy requirements, and audit processes.",
        "kubernetes_relevance": "Involves mapping cluster state to GDPR, HIPAA, or FedRAMP requirements for audit reporting.",
        "common_findings": ["gdpr-non-compliance", "failed-compliance-audit"],
        "scanner_mappings": ["kubescape-compliance-scan"],
        "remediation_approach": "Automate compliance reporting and maintain a continuous audit trail of all cluster changes.",
        "fedramp_baseline": "LOW, MODERATE, HIGH"
    }
]

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        for domain in CCSP_DOMAINS:
            f.write(json.dumps(domain) + "\n")
    print(f"Generated 6 CCSP domain summaries to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
