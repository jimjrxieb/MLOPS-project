import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/8b-jade")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "cloud_aws_500.jsonl"

def generate_cloud_aws_examples(count):
    services = ["IAM", "S3", "VPC", "KMS", "CloudTrail", "RDS", "Lambda"]
    scenarios = []
    
    for i in range(count):
        service = random.choice(services)
        resource_id = f"res-{random.randint(1000, 9999)}"
        
        if service == "IAM":
            finding = f"IAM User '{resource_id}' has administrative privileges assigned directly via inline policy. This violates the principle of least privilege."
            policy_json = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:ListBucket",
                            "s3:GetObject"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{resource_id}-data",
                            f"arn:aws:s3:::{resource_id}-data/*"
                        ]
                    }
                ]
            }
            code_block = f"```json\n{json.dumps(policy_json, indent=2)}\n```"
            analysis = "Directly attaching AdministratorAccess or broad inline policies to users is a high-risk configuration. Remediation involves replacing the inline policy with a managed policy that grants only the necessary permissions."
            
        elif service == "S3":
            finding = f"S3 Bucket '{resource_id}-logs' is public or lacks encryption. Compliance requirement: Enforce AES256 server-side encryption and block public access."
            hcl = f"""resource "aws_s3_bucket" "logs" {{
  bucket = "{resource_id}-logs"
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {{
  bucket = aws_s3_bucket.logs.id
  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}

resource "aws_s3_bucket_public_access_block" "logs" {{
  bucket = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}"""
            code_block = f"```hcl\n{hcl}\n```"
            analysis = "Unencrypted S3 buckets are a common cause of data exposure. This Terraform configuration enforces default encryption and blocks all public access to the bucket."

        elif service == "VPC":
            finding = f"Security Group '{resource_id}-sg' allows unrestricted SSH (port 22) from 0.0.0.0/0. This exposes the instance to brute-force attacks."
            hcl = f"""resource "aws_security_group_rule" "allow_ssh_limited" {{
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/8"] # Restricted to internal network
  security_group_id = "{resource_id}-sg"
}}"""
            code_block = f"```hcl\n{hcl}\n```"
            analysis = "Opening management ports to the internet is a severe security finding. Access should be restricted to known CIDR blocks or through a bastion host/VPN."

        else: # Default/Other
            finding = f"Service '{service}' configuration for '{resource_id}' lacks audit logging or encryption."
            code_block = """```json\n{\n  "Configuration": "Secure-Baseline",\n  "Logging": "Enabled",\n  "Encryption": "KMS"\n}\n```"""
            analysis = f"Ensuring that {service} resources are properly logged and encrypted at rest is a foundational security requirement."

        example = {
            "messages": [
                {"role": "system", "content": "You are JADE, a security analysis engine specializing in cloud infrastructure, compliance, and automated remediation. Provide expert-level analysis and precise configuration artifacts."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: {analysis}\n\nREMEDIATION:\n{code_block}\n\nVERIFICATION: Use AWS CLI or Console to verify the resource configuration matches the security baseline."}
            ],
            "metadata": {
                "domain": "cloud",
                "service": service,
                "rank": "C"
            }
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_cloud_aws_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 Cloud/AWS examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
