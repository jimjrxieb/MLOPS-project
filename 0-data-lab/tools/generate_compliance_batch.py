import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/8b-jade")
OUTPUT_FILE = OUTPUT_DIR / "compliance_500.jsonl"

def generate_compliance_examples(count):
    frameworks = ["NIST 800-53", "CIS Benchmark", "FedRAMP", "SOC2"]
    scenarios = []
    
    for i in range(count):
        framework = random.choice(frameworks)
        control_id = f"CTRL-{random.randint(100, 999)}"
        
        if framework == "NIST 800-53":
            finding = f"NIST 800-53 Control AC-6 (Least Privilege) violation: Application '{control_id}' is running with unnecessary administrative permissions."
            artifact = f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: {control_id}-sa
  namespace: restricted
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {control_id}-limited-role
  namespace: restricted
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]"""
            code_block = f"```yaml\n{artifact}\n```"
            analysis = "AC-6 requires enforcing the principle of least privilege. By creating a dedicated ServiceAccount and Role with restricted verbs, we satisfy the control requirements."

        elif framework == "CIS Benchmark":
            finding = f"CIS Kubernetes Benchmark 1.2.1: Ensure that the --anonymous-auth argument is set to false on the API server."
            artifact = """apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --anonymous-auth=false
    image: k8s.gcr.io/kube-apiserver:v1.28.0
    name: kube-apiserver"""
            code_block = f"```yaml\n{artifact}\n```"
            analysis = "Disabling anonymous authentication prevents unauthorized access to the API server, aligning with CIS security best practices."

        elif framework == "FedRAMP":
            finding = f"FedRAMP Moderate Baseline SC-8 (Transmission Confidentiality): Data in transit between services '{control_id}-a' and '{control_id}-b' is not encrypted."
            artifact = f"""apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: {control_id}-mtls
  namespace: default
spec:
  mtls:
    mode: STRICT"""
            code_block = f"```yaml\n{artifact}\n```"
            analysis = "SC-8 requires protecting the confidentiality of information during transmission. Implementing mTLS via Istio ensures all service-to-service traffic is encrypted."

        else: # SOC2
            finding = f"SOC2 Common Criteria CC6.1 (Logical Access): Lack of automated evidence for user access reviews."
            artifact = {
                "AuditLogConfig": {
                    "Service": "IAM",
                    "Status": "Enabled",
                    "Retention": "365 Days",
                    "AutoReview": "Active"
                }
            }
            code_block = f"```json\n{json.dumps(artifact, indent=2)}\n```"
            analysis = "CC6.1 requires organizations to implement logical access security. Automated audit logs provide continuous evidence for compliance monitoring and reviews."

        example = {
            "messages": [
                {"role": "system", "content": "You are JADE, a security analysis engine specializing in cloud infrastructure, compliance, and automated remediation. Provide expert-level analysis and precise configuration artifacts."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: {analysis}\n\nREMEDIATION:\n{code_block}\n\nVERIFICATION: Verify the applied configuration against the {framework} control specifications."}
            ],
            "metadata": {
                "domain": "compliance",
                "framework": framework,
                "rank": "C"
            }
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_compliance_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 Compliance examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
