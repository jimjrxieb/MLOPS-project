import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/3b-cks")
OUTPUT_FILE = OUTPUT_DIR / "falco_runtime_500.jsonl"

def generate_falco_examples(count):
    scenarios = []
    
    rules = [
        {
            "name": "Unauthorized Shell in Container",
            "condition": "container.id != host and proc.name = sh",
            "output": "Shell spawned in container (user=%user.name %container.info)",
            "priority": "WARNING"
        },
        {
            "name": "Write below binary dir",
            "condition": "fd.name startswith /usr/bin and evt.type = open",
            "output": "File created below /usr/bin (user=%user.name %file.name)",
            "priority": "CRITICAL"
        },
        {
            "name": "Sensitive file modification",
            "condition": "fd.name in (/etc/shadow, /etc/passwd) and evt.type = write",
            "output": "Sensitive file modified (user=%user.name %file.name)",
            "priority": "EMERGENCY"
        },
        {
            "name": "Unexpected network connection",
            "condition": "outbound and fd.port != 80 and fd.port != 443",
            "output": "Unexpected outbound connection (user=%user.name %fd.name)",
            "priority": "NOTICE"
        }
    ]
    
    for i in range(count):
        rule = random.choice(rules)
        rule_id = f"custom-rule-{random.randint(1000, 9999)}"
        
        finding = f"Configure a Falco rule to detect: {rule['name']}. Condition: {rule['condition']}."
        
        yaml_content = f"""apiVersion: falco.org/v1
kind: FalcoRule
metadata:
  name: {rule_id}
spec:
  rule: {rule['name']}
  desc: Detect {rule['name'].lower()}
  condition: {rule['condition']}
  output: {rule['output']}
  priority: {rule['priority']}"""

        example = {
            "messages": [
                {"role": "system", "content": "You are a Kubernetes security agent specializing in CKS-level cluster hardening. Analyze findings and provide precise remediation with valid YAML."},
                {"role": "user", "content": f"FINDING: {finding}\n\nProvide remediation."},
                {"role": "assistant", "content": f"ANALYSIS: Runtime security monitoring with Falco is critical for detecting live threats. I will create a custom FalcoRule to alert on the specified activity.\n\nREMEDIATION:\n```yaml\n{yaml_content}\n```\n\nVERIFICATION: falco -c /etc/falco/falco.yaml -r /etc/falco/falco_rules.local.yaml"}
            ]
        }
        scenarios.append(example)
    return scenarios

def main():
    examples = generate_falco_examples(500)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 500 Falco/Runtime examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
