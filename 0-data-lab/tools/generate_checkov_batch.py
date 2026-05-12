import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/8b-jade")
OUTPUT_FILE = OUTPUT_DIR / "checkov_terraform_400.jsonl"

def generate_checkov_examples(count):
    scenarios = []
    
    findings = [
        {
            "check_id": "CKV_AWS_18",
            "description": "Ensure S3 bucket has logging enabled",
            "resource": "aws_s3_bucket",
            "fix": 'logging {\n    target_bucket = "log-bucket"\n    target_prefix = "log/"\n  }'
        },
        {
            "check_id": "CKV_AWS_19",
            "description": "Ensure all data stored in the S3 bucket is securely encrypted at rest",
            "resource": "aws_s3_bucket",
            "fix": 'server_side_encryption_configuration {\n    rule {\n      apply_server_side_encryption_by_default {\n        sse_algorithm = "AES256"\n      }\n    }\n  }'
        },
        {
            "check_id": "CKV_AWS_21",
            "description": "Ensure all data stored in the S3 bucket has versioning enabled",
            "resource": "aws_s3_bucket",
            "fix": 'versioning {\n    enabled = true\n  }'
        },
        {
            "check_id": "CKV_AWS_158",
            "description": "Ensure that CloudWatch Log Group is encrypted by KMS",
            "resource": "aws_cloudwatch_log_group",
            "fix": 'kms_key_id = aws_kms_key.example.arn'
        }
    ]
    
    for i in range(count):
        item = random.choice(findings)
        name = f"example_{random.randint(100, 999)}"
        
        finding_text = f"FINDING: Checkov {item['check_id']} failed for resource {item['resource']}.{name}. Description: {item['description']}."
        
        hcl = f"""resource "{item['resource']}" "{name}" {{
  # ... existing configuration ...
  {item['fix']}
}}"""

        example = {
            "messages": [
                {"role": "system", "content": "You are JADE, an AI assistant specializing in IaC security and automated remediation using Checkov and Terraform. Provide precise HCL fixes for detected vulnerabilities."},
                {"role": "user", "content": f"{finding_text}\n\nProvide the Terraform remediation."},
                {"role": "assistant", "content": f"ANALYSIS: The {item['check_id']} check identifies a lack of security best practices in the {item['resource']} resource. I will provide the necessary HCL configuration to remediate this finding.\n\nREMEDIATION:\n```hcl\n{hcl}\n```\n\nVERIFICATION: Run 'checkov -f main.tf' to confirm the finding is resolved."}
            ],
            "metadata": {"domain": "terraform", "tool": "checkov", "check_id": item['check_id']}
        }
        scenarios.append(example)
        
    return scenarios

def main():
    examples = generate_checkov_examples(400)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 400 Checkov/Terraform examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
