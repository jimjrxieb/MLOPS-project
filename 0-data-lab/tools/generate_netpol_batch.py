import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/3b-cks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "netpol_500.jsonl"

def generate_netpol_examples(count):
    apps = ["api-gateway", "auth-service", "payment-api", "inventory-db", "frontend-v2", "worker-queue", "logging-aggregator", "metrics-collector"]
    namespaces = ["production", "staging", "secure-vault", "customer-data", "external-api"]
    
    scenarios = []
    for i in range(count):
        app = random.choice(apps)
        ns = random.choice(namespaces)
        pod_name = f"{app}-{random.randint(1000, 9999)}"
        
        # Variation in scenario description
        scenario_types = [
            f"Pod '{pod_name}' in namespace '{ns}' has no NetworkPolicy. All ingress and egress traffic is currently allowed.",
            f"Security audit found that pod '{pod_name}' in '{ns}' lacks network isolation. It needs to communicate with DNS and specific internal services.",
            f"Namespace '{ns}' is missing default-deny policies. Configure isolation for pod '{pod_name}'.",
            f"Compliance requirement: Restrict all traffic for '{pod_name}' in namespace '{ns}' except for essential DNS and service-to-service communication."
        ]
        finding = random.choice(scenario_types)
        
        # Build YAML with mandatory DNS egress (UDP 53)
        yaml_content = f"""apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {app}-isolation
  namespace: {ns}
spec:
  podSelector:
    matchLabels:
      app: {app}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {{}}
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432"""
        
        example = {
            "messages": [
                {"role": "system", "content": "You are a Kubernetes security agent specializing in CKS-level cluster hardening. Analyze findings and provide precise remediation with valid YAML."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: Unrestricted network access is a critical security risk. I will implement a least-privilege NetworkPolicy that allows necessary ingress from frontend and egress to DNS and the database.\n\nREMEDIATION:\n```yaml\n{yaml_content}\n```\n\nVERIFICATION: kubectl describe networkpolicy {app}-isolation -n {ns}"}
            ]
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_netpol_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 NetworkPolicy examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
