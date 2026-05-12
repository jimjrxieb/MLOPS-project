import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/8b-jade")
OUTPUT_FILE = OUTPUT_DIR / "hardening_500.jsonl"

def generate_hardening_examples(count):
    topics = ["OS Hardening", "Container Hardening", "Zero Trust", "TLS Configuration", "Encryption"]
    scenarios = []
    
    for i in range(count):
        topic = random.choice(topics)
        target = f"target-{random.randint(100, 999)}"
        
        if topic == "OS Hardening":
            finding = f"SSH daemon on host '{target}' allows root login and password authentication. This violates OS hardening baselines."
            artifact = """# /etc/ssh/sshd_config\nPermitRootLogin no\nPasswordAuthentication no\nPubkeyAuthentication yes\nAllowUsers security-admin"""
            code_block = f"```text\n{artifact}\n```"
            analysis = "Hardening the SSH configuration by disabling root login and password-based authentication significantly reduces the risk of unauthorized access."

        elif topic == "Container Hardening":
            finding = f"Dockerfile for '{target}' uses a heavy base image and runs as root. Remediation: Use distroless and a non-root user."
            artifact = f"""FROM golang:1.21-alpine AS builder\nWORKDIR /app\nCOPY . .\nRUN go build -o main .\n\nFROM gcr.io/distroless/static-debian11\nCOPY --from=builder /app/main /\nUSER 65532:65532\nENTRYPOINT ["/main"]"""
            code_block = f"```dockerfile\n{artifact}\n```"
            analysis = "Multi-stage builds with distroless base images minimize the attack surface. Running as a non-privileged UID (65532) prevents container escape exploits."

        elif topic == "Zero Trust":
            finding = f"Application '{target}' in namespace 'prod' allows all inbound traffic. Implement zero-trust network isolation."
            artifact = f"""apiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: {target}-zero-trust\n  namespace: prod\nspec:\n  podSelector:\n    matchLabels:\n      app: {target}\n  policyTypes:\n  - Ingress\n  ingress:\n  - from:\n    - podSelector:\n        matchLabels:\n          role: authorized-client"""
            code_block = f"```yaml\n{artifact}\n```"
            analysis = "Zero-trust architecture assumes no implicit trust. Explicitly defining allowed ingress sources via NetworkPolicy ensures only authorized components can communicate."

        elif topic == "TLS Configuration":
            finding = f"Nginx ingress for '{target}' is using weak TLS ciphers or old protocols (TLS 1.0/1.1)."
            artifact = f"""apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: {target}-ingress\n  annotations:\n    nginx.ingress.kubernetes.io/ssl-ciphers: \"ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256\"\n    nginx.ingress.kubernetes.io/ssl-protocols: \"TLSv1.2 TLSv1.3\""""
            code_block = f"```yaml\n{artifact}\n```"
            analysis = "Enforcing TLS 1.2+ and strong cipher suites protects data in transit from interception and decryption by unauthorized parties."

        else: # Encryption
            finding = f"Database '{target}' does not have encryption at rest enabled. Requirement: AES-256 encryption via KMS."
            artifact = f"""resource \"aws_db_instance\" \"secure_db\" {{\n  allocated_storage    = 20\n  engine               = \"postgres\"\n  instance_class       = \"db.t3.micro\"\n  name                 = \"{target}_db\"\n  storage_encrypted    = true\n  kms_key_id           = aws_kms_key.db_key.arn\n}}"""
            code_block = f"```hcl\n{artifact}\n```"
            analysis = "Enabling storage encryption for RDS instances using customer-managed KMS keys ensures data remains protected even if physical storage media is compromised."

        example = {
            "messages": [
                {"role": "system", "content": "You are JADE, a security analysis engine specializing in cloud infrastructure, compliance, and automated remediation. Provide expert-level analysis and precise configuration artifacts."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: {analysis}\n\nREMEDIATION:\n{code_block}\n\nVERIFICATION: Apply the configuration and use automated scanning tools to verify hardening compliance."}
            ],
            "metadata": {
                "domain": "hardening",
                "topic": topic,
                "rank": "C"
            }
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_hardening_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 Hardening examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
