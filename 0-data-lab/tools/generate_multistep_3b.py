import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/3b-cks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "multistep_3b_300.jsonl"

def generate_crashloop_3b(count):
    scenarios = []
    apps = ["cache-server", "auth-provider", "data-ingestor", "web-api"]
    
    for i in range(count):
        app = random.choice(apps)
        ns = random.choice(["prod", "staging", "dev"])
        pod = f"{app}-{random.randint(100, 999)}"
        
        cause = random.choice(["OOMKilled", "ImagePullBackOff", "RunContainerError"])
        
        if cause == "OOMKilled":
            finding = f"FINDING: Pod '{pod}' in namespace '{ns}' is in CrashLoopBackOff. 'kubectl describe pod' shows 'Last State: Terminated', 'Reason: OOMKilled'."
            diagnosis = f"DIAGNOSIS: The container process was terminated because it exceeded its memory limit. The current limit is too low for the application workload."
            remediation = f"REMEDIATION:\nUpdate the Deployment resources to increase the memory limit.\n```yaml\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {app}\n  namespace: {ns}\nspec:\n  template:\n    spec:\n      containers:\n      - name: {app}\n        resources:\n          limits:\n            memory: \"512Mi\"\n          requests:\n            memory: \"256Mi\"\n```"
        elif cause == "ImagePullBackOff":
            finding = f"FINDING: Pod '{pod}' in namespace '{ns}' is in ImagePullBackOff status. Describe shows 'Failed to pull image \"{app}:v2.9.9\": rpc error: code = NotFound'."
            diagnosis = f"DIAGNOSIS: The kubelet cannot pull the specified image because the tag 'v2.9.9' does not exist in the registry or the image name is misspelled."
            remediation = f"REMEDIATION:\nCorrect the image tag in the Deployment specification to a valid version.\n```yaml\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {app}\n  namespace: {ns}\nspec:\n  template:\n    spec:\n      containers:\n      - name: {app}\n        image: {app}:v2.9.0 # Corrected tag\n```"
        else: # RunContainerError / Exit Code 1
            finding = f"FINDING: Pod '{pod}' in namespace '{ns}' is in CrashLoopBackOff. Exit Code: 1. Logs show: 'Error: Config file /etc/config/settings.yaml not found'."
            diagnosis = f"DIAGNOSIS: The application is failing to start because it cannot find its configuration file, which should be mounted from a ConfigMap."
            remediation = f"REMEDIATION:\nEnsure the ConfigMap is created and correctly mounted as a volume in the Pod spec.\n```yaml\napiVersion: v1\nkind: Pod\nmetadata:\n  name: {pod}\n  namespace: {ns}\nspec:\n  containers:\n  - name: {app}\n    volumeMounts:\n    - name: config-volume\n      mountPath: /etc/config\n  volumes:\n  - name: config-volume\n    configMap:\n      name: {app}-config\n```"

        example = {
            "messages": [
                {"role": "system", "content": "You are a Kubernetes diagnostic agent. Analyze pod failures and provide remediation with valid YAML."},
                {"role": "user", "content": finding + "\n\nProvide remediation."},
                {"role": "assistant", "content": f"{diagnosis}\n\n{remediation}\n\nVERIFICATION: kubectl get pods -n {ns} -w"}
            ]
        }
        scenarios.append(example)
    return scenarios

def generate_label_fix_3b(count):
    scenarios = []
    for i in range(count):
        app = random.choice(["frontend", "backend", "db"])
        ns = random.choice(["prod", "dev"])
        
        finding = f"FINDING: Service '{app}-svc' in namespace '{ns}' has no endpoints. The backend pods are running, but traffic is not reaching them."
        diagnosis = f"DIAGNOSIS: The Service selector labels do not match the labels defined on the Pods. This causes the Service to fail in routing traffic to the correct endpoints."
        remediation = f"REMEDIATION:\nAlign the Service selector with the Pod labels.\n```yaml\napiVersion: v1\nkind: Service\nmetadata:\n  name: {app}-svc\n  namespace: {ns}\nspec:\n  selector:\n    app: {app}\n    environment: {ns}\n  ports:\n  - protocol: TCP\n    port: 80\n    targetPort: 8080\n```"
        
        example = {
            "messages": [
                {"role": "system", "content": "You are a Kubernetes diagnostic agent. Analyze pod failures and provide remediation with valid YAML."},
                {"role": "user", "content": finding + "\n\nProvide remediation."},
                {"role": "assistant", "content": f"{diagnosis}\n\n{remediation}\n\nVERIFICATION: kubectl get ep {app}-svc -n {ns}"}
            ]
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = []
    examples.extend(generate_crashloop_3b(200))
    examples.extend(generate_label_fix_3b(100))
    
    random.shuffle(examples)
    
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 300 multi-step diagnostic examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
