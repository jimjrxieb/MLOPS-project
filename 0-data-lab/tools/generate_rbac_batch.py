import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/3b-cks")
OUTPUT_FILE = OUTPUT_DIR / "rbac_500.jsonl"

def generate_rbac_examples(count):
    apps = ["billing-app", "auth-proxy", "log-collector", "data-cleaner", "backup-job", "monitor-agent"]
    namespaces = ["production", "dev-team", "finance", "infra", "security"]
    
    scenarios = []
    for i in range(count):
        app = random.choice(apps)
        ns = random.choice(namespaces)
        sa_name = f"{app}-sa"
        
        scenario_types = [
            f"The pod '{app}' in namespace '{ns}' is running with the default ServiceAccount. It needs permission to get and list ConfigMaps in its own namespace.",
            f"Audit report: ServiceAccount '{sa_name}' in '{ns}' has cluster-admin permissions. Remediation: restrict to only read pods and services in '{ns}'.",
            f"A new deployment '{app}' in namespace '{ns}' needs to monitor nodes in the cluster. Create the necessary RBAC resources.",
            f"Security hardening: Disable 'automountServiceAccountToken' for the '{sa_name}' and create a Role to allow reading its own secrets."
        ]
        finding = random.choice(scenario_types)
        
        # Decide if it's a Role or ClusterRole scenario
        is_cluster = "monitor nodes" in finding or random.random() < 0.2
        
        if is_cluster:
            rbac_yaml = f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: {sa_name}
  namespace: {ns}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: {sa_name}-node-viewer
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {sa_name}-node-viewer-binding
subjects:
- kind: ServiceAccount
  name: {sa_name}
  namespace: {ns}
roleRef:
  kind: ClusterRole
  name: {sa_name}-node-viewer
  apiGroup: rbac.authorization.k8s.io"""
        else:
            rbac_yaml = f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: {sa_name}
  namespace: {ns}
  automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {sa_name}-limited-role
  namespace: {ns}
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {sa_name}-limited-binding
  namespace: {ns}
subjects:
- kind: ServiceAccount
  name: {sa_name}
  namespace: {ns}
roleRef:
  kind: Role
  name: {sa_name}-limited-role
  apiGroup: rbac.authorization.k8s.io"""

        example = {
            "messages": [
                {"role": "system", "content": "You are a Kubernetes security agent specializing in CKS-level cluster hardening. Analyze findings and provide precise remediation with valid YAML."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: Over-privileged ServiceAccounts or use of default accounts violates least-privilege principles. I will create a dedicated ServiceAccount and Role with minimal required permissions.\n\nREMEDIATION:\n```yaml\n{rbac_yaml}\n```\n\nVERIFICATION: kubectl auth can-i get pods --as=system:serviceaccount:{ns}:{sa_name} -n {ns}"}
            ]
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_rbac_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 RBAC examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
