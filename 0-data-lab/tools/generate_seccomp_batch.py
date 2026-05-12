import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/3b-cks")
OUTPUT_FILE = OUTPUT_DIR / "seccomp_apparmor_500.jsonl"

def generate_seccomp_examples(count):
    apps = ["nginx-ingress", "redis-cache", "python-api", "go-worker", "node-frontend"]
    namespaces = ["production", "staging", "restricted-zone"]
    
    scenarios = []
    for i in range(count):
        app = random.choice(apps)
        ns = random.choice(namespaces)
        pod_name = f"{app}-{random.randint(1000, 9999)}"
        
        is_apparmor = random.random() < 0.5
        
        if is_apparmor:
            profile = f"k8s-apparmor-{app}"
            finding = f"Pod '{pod_name}' in namespace '{ns}' is running without an AppArmor profile. It should use the '{profile}' profile."
            yaml_content = f"""apiVersion: v1
kind: Pod
metadata:
  name: {pod_name}
  namespace: {ns}
  annotations:
    container.apparmor.security.beta.kubernetes.io/{app}: localhost/{profile}
spec:
  containers:
  - name: {app}
    image: {app}:latest
    securityContext:
      allowPrivilegeEscalation: false"""
        else:
            profile = "RuntimeDefault" if random.random() < 0.5 else "localhost/audit.json"
            finding = f"Pod '{pod_name}' in namespace '{ns}' needs a seccomp profile. Configure it to use '{profile}'."
            type_val = "RuntimeDefault" if "RuntimeDefault" in profile else "Localhost"
            localhost_profile = f'    localhostProfile: {profile.split("/")[-1]}' if type_val == "Localhost" else ""
            
            yaml_content = f"""apiVersion: v1
kind: Pod
metadata:
  name: {pod_name}
  namespace: {ns}
spec:
  securityContext:
    seccompProfile:
      type: {type_val}
{localhost_profile}
  containers:
  - name: {app}
    image: {app}:latest
    securityContext:
      allowPrivilegeEscalation: false"""

        example = {
            "messages": [
                {"role": "system", "content": "You are a Kubernetes security agent specializing in CKS-level cluster hardening. Analyze findings and provide precise remediation with valid YAML."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: Hardening containers with AppArmor or Seccomp is essential for minimizing the attack surface. I will update the pod specification to include the requested security profiles.\n\nREMEDIATION:\n```yaml\n{yaml_content.strip()}\n```\n\nVERIFICATION: kubectl get pod {pod_name} -n {ns} -o jsonpath='{{.spec.securityContext.seccompProfile}}'"}
            ]
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_seccomp_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 Seccomp/AppArmor examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
