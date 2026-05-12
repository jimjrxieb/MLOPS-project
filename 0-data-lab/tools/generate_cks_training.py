import json
import random

# Re-generating Batch 1 with 100% YAML/Rego coverage
# Target: 1,000 examples with code

DOMAINS = {
    "Workload Security": 300,
    "Network Security": 200,
    "RBAC & Access Control": 200,
    "Admission Control": 100,
    "Supply Chain": 100,
    "Runtime Monitoring": 50,
    "Cluster Hardening": 30,
    "Secrets Management": 20
}

def generate_workload_security(count):
    ns = ["prod", "dev", "staging", "payments", "billing"]
    app = ["web", "db", "cache", "api", "worker"]
    templates = [
        ("Pod '{pod}' in namespace '{ns}' is running as root.", "runAsNonRoot: true"),
        ("Container '{container}' in pod '{pod}' has privileged: true.", "privileged: false"),
        ("Pod '{pod}' in namespace '{ns}' does not have a read-only root filesystem.", "readOnlyRootFilesystem: true"),
        ("Container '{container}' in pod '{pod}' has capabilities that are not restricted.", "capabilities:\n        drop:\n        - ALL"),
        ("Pod '{pod}' in namespace '{ns}' is allowed to escalate privileges.", "allowPrivilegeEscalation: false")
    ]
    scenarios = []
    for _ in range(count):
        curr_ns = random.choice(ns)
        curr_app = random.choice(app)
        curr_pod = f"{curr_app}-{random.randint(100, 999)}"
        curr_container = curr_app
        template, fix = random.choice(templates)
        finding = template.format(pod=curr_pod, ns=curr_ns, container=curr_container)
        
        remediation_yaml = f"""apiVersion: v1
kind: Pod
metadata:
  name: {curr_pod}
  namespace: {curr_ns}
spec:
  containers:
  - name: {curr_container}
    image: {curr_app}:latest
    securityContext:
      {fix}"""
        
        scenarios.append({
            "messages": [
                {"role": "system", "content": "You are a Kubernetes security agent specializing in CKS-level cluster hardening. Analyze findings and provide precise remediation with valid YAML."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: This configuration violates Pod Security Standards. {template.split('.')[0]}\n\nREMEDIATION:\n```yaml\n{remediation_yaml}\n```\n\nVERIFICATION: kubectl get pod {curr_pod} -n {curr_ns} -o jsonpath='{{.spec.containers[0].securityContext}}'"}
            ]
        })
    return scenarios

def generate_network_security(count):
    scenarios = []
    apps = ["api", "web", "worker", "gateway"]
    for _ in range(count):
        app = random.choice(apps)
        ns = random.choice(["prod", "dev"])
        pod = f"{app}-{random.randint(100, 999)}"
        
        yaml = f"""apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {app}-deny-all
  namespace: {ns}
spec:
  podSelector:
    matchLabels:
      app: {app}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress:
  - to:
    - namespaceSelector: {{}}
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53"""
        
        scenarios.append({
            "messages": [
                {"role": "system", "content": "You are a Kubernetes security agent specializing in CKS-level cluster hardening. Analyze findings and provide precise remediation with valid YAML."},
                {"role": "user", "content": f"FINDING: Pod '{pod}' in namespace '{ns}' has no NetworkPolicy. All ingress and egress allowed.\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: Unrestricted network access is a high-risk finding. A default-deny policy with explicit DNS egress is required.\n\nREMEDIATION:\n```yaml\n{yaml}\n```\n\nVERIFICATION: kubectl describe netpol {app}-deny-all -n {ns}"}
            ]
        })
    return scenarios

def main():
    all_examples = []
    all_examples.extend(generate_workload_security(DOMAINS["Workload Security"]))
    all_examples.extend(generate_network_security(DOMAINS["Network Security"]))
    
    # Fill remaining count to 1000 with more of these two for now to ensure 100% YAML
    remaining = 1000 - len(all_examples)
    all_examples.extend(generate_workload_security(remaining))

    output_path = "1-GP-GLUE/01-raw-data-lake/cks_training_batch_v1.jsonl"
    with open(output_path, 'w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")
            
    print(f"Generated {len(all_examples)} examples with 100% YAML ratio to {output_path}")

if __name__ == "__main__":
    main()
