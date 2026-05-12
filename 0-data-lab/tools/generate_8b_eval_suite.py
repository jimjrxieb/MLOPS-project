import json
import random
from pathlib import Path

OUTPUT_FILE = Path("4-GP-CLARIFY/jade_8b_eval_suite_v1.jsonl")

def generate_8b_scenarios():
    scenarios = []
    
    # 1. Cloud Security (50)
    cloud_services = ["IAM", "S3", "VPC", "KMS", "Lambda", "GuardDuty"]
    for i in range(1, 51):
        service = random.choice(cloud_services)
        scenarios.append({
            "id": f"jade-8b-cloud-{i:03d}",
            "domain": "cloud_security",
            "difficulty": random.choice(["B", "C"]),
            "scenario": f"Analyze and remediate a security finding in AWS {service}: Policy allows broad access or lacks encryption.",
            "expected_actions": ["Analyze policy document", "Identify over-privileged statements", "Generate least-privilege JSON policy"],
            "expected_resources": [service, "IAM Policy"],
            "validation_keywords": ["Effect: Allow", "Resource: *", "json"],
            "objective": f"Secure {service} infrastructure"
        })

    # 2. Compliance & Governance (50)
    frameworks = ["NIST 800-53", "FedRAMP", "SOC2", "HIPAA", "PCI-DSS"]
    for i in range(1, 51):
        framework = random.choice(frameworks)
        scenarios.append({
            "id": f"jade-8b-compliance-{i:03d}",
            "domain": "compliance",
            "difficulty": "B",
            "scenario": f"Map a detected Kubernetes misconfiguration to a specific {framework} control and provide implementation guidance.",
            "expected_actions": ["Identify control mapping", "Generate technical remediation", "Document evidence requirements"],
            "expected_resources": ["Compliance Report", "Config artifact"],
            "validation_keywords": ["Control", "Implementation", "Evidence"],
            "objective": f"Ensure {framework} alignment"
        })

    # 3. System & Network Hardening (50)
    hardening_topics = ["OS Hardening", "Container Hardening", "Zero Trust", "TLS 1.3", "Encryption at rest"]
    for i in range(1, 51):
        topic = random.choice(hardening_topics)
        scenarios.append({
            "id": f"jade-8b-hardening-{i:03d}",
            "domain": "hardening",
            "difficulty": "C",
            "scenario": f"Implement a comprehensive hardening strategy for {topic} across a multi-node cluster.",
            "expected_actions": ["Apply CIS benchmarks", "Configure kernel parameters", "Enforce secure protocols"],
            "expected_resources": ["ConfigMap", "DaemonSet", "PodSecurityPolicy"],
            "validation_keywords": ["sysctl", "cipher", "benchmark"],
            "objective": f"Reduce attack surface via {topic}"
        })

    # 4. Complex Diagnostic Reasoning (50)
    diag_types = ["Intermittent Timeout", "Race Condition", "Storage Performance", "Memory Leak", "Secret Rotation Failure"]
    for i in range(1, 51):
        diag = random.choice(diag_types)
        scenarios.append({
            "id": f"jade-8b-diagnostic-{i:03d}",
            "domain": "diagnostic",
            "difficulty": "S",
            "scenario": f"A complex {diag} is causing production instability. Analyze logs, describe investigative steps, and fix.",
            "expected_actions": ["Examine application logs", "Check node level events", "Identify root cause across multiple layers"],
            "expected_resources": ["Pod", "Service", "PersistentVolume"],
            "validation_keywords": ["Root Cause", "Investigation", "Log analysis"],
            "objective": f"Resolve complex {diag} issues"
        })

    return scenarios

def main():
    examples = generate_8b_scenarios()
    random.shuffle(examples)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 200 8B evaluation scenarios to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
