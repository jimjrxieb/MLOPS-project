#!/usr/bin/env python3
"""
Generate synthetic BERU training data: SSPs, AI intake samples, ChatML examples.
All examples reference real NIST 800-53 controls from compliance-controls RAG.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta

# Real control IDs from compliance-controls collection
NIST_CONTROLS = [
    "AC-2", "AC-3", "AC-5", "AC-6", "AC-17",
    "AU-2", "AU-3", "AU-6", "AU-9", "AU-12",
    "CA-2", "CA-7", "CA-8",
    "CM-2", "CM-3", "CM-5", "CM-6", "CM-7", "CM-8",
    "CP-9", "CP-10",
    "IA-2", "IA-5",
    "IR-4", "IR-5", "IR-6",
    "RA-2", "RA-3", "RA-5",
    "SA-10", "SA-11", "SA-12",
    "SC-6", "SC-7", "SC-8", "SC-12", "SC-13", "SC-17", "SC-23", "SC-28",
    "SI-2", "SI-3", "SI-4", "SI-6", "SI-7", "SI-10"
]

AI_RMF_FUNCTIONS = ["GOVERN", "MAP", "MANAGE"]

OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/BERU-AI/training-data")

def generate_ssp(index: int, quality: str = "good") -> str:
    """Generate a realistic (but synthetic) System Security Plan."""
    org_name = f"SecureOrg{index}"
    system_name = f"Kubernetes-Cluster-{index}"

    if quality == "bad":
        description = "We have security measures in place."
        controls = random.sample(NIST_CONTROLS, 5)
        implementations = ["configured", "enabled", "implemented"]
    elif quality == "mediocre":
        description = f"The {system_name} is deployed on AWS EKS with network policies and RBAC controls."
        controls = random.sample(NIST_CONTROLS, 10)
        implementations = ["Kyverno policies enforce", "NetworkPolicy restricts", "RBAC limits access to"]
    else:  # good
        description = f"The {system_name} is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana."
        controls = random.sample(NIST_CONTROLS, 12)
        implementations = [
            "Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce)",
            "NetworkPolicy denies all ingress, allows only labeled services",
            "RBAC limits service accounts to pod-scoped permissions",
            "etcd encrypted with AES-256-GCM",
            "Falco monitors runtime behavior with custom rules",
            "kubeaudit logs all apiserver events",
            "ArgoCD AppProject restricts deployment sources to trusted repos"
        ]

    control_narratives = []
    for control in controls:
        impl = random.choice(implementations)
        control_narratives.append(f"**{control}**: {impl}.")

    ssp = f"""# System Security Plan
## {system_name}

**Organization**: {org_name}
**System Name**: {system_name}
**Classification**: MODERATE
**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}

### System Description
{description}

### Implemented Controls
{chr(10).join(control_narratives)}

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
{['No formal risk assessment performed.',
  'Conducted gap analysis against CIS Kubernetes Benchmark v1.6.1 (82 pass, 18 fail).',
  'Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.'][['bad', 'mediocre', 'good'].index(quality)]}
"""
    return ssp

def generate_ai_intake(index: int) -> str:
    """Generate AI System Registration form (AI RMF GOVERN-1.1)."""
    ai_systems = [
        ("BERU", "GRC Analyst Agent", "Compliance assessor reading scanner output, mapping to NIST controls"),
        ("JADE", "AppSec Executor", "Code+Cluster security engineer fixing SAST findings and misconfigurations"),
        ("Katie", "K8s Triage Router", "Kubernetes operational decision classifier for rank routing"),
        ("Raven", "Threat Predictor", "ML model predicting attack scenarios from security logs"),
        ("Atlas", "Cost Optimizer", "FinOps model recommending reserved instances and spot strategies"),
    ]

    name, role, desc = random.choice(ai_systems)

    intake = f"""# AI System Registration Form
## AI RMF GOVERN-1.1: Know Your AI System

**System Name**: {name}-v{index}
**Organization**: LinkOps Industries
**Registration Date**: {(datetime.now() - timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d')}
**AI System Owner**: Chief Security Officer

### System Identification
- **Purpose**: {role}
- **Description**: {desc}
- **Type**: {'Generative' if index % 2 else 'Discriminative'} AI
- **Model Base**: Llama {'3.1-8B' if index % 3 else '3.2-3B'}-Instruct
- **Training Data**: {['Real security findings from 5 clients', 'Synthetic scenario data from 0-data-lab', 'Open source NIST playbooks + documentation'][index % 3]}

### Impact and Risk Tier
- **Impact Level**: {'MODERATE' if index % 2 else 'HIGH'}
- **Scope**: {['Single team internal use', 'Company-wide security operations', 'Customer-facing audit reports'][index % 3]}
- **Data Classification**: {'CONTROLLED UNCLASSIFIED' if index % 2 else 'INTERNAL USE ONLY'}
- **Risk Tier**: {'MEDIUM' if index % 2 else 'HIGH'}

### Planned Controls
{chr(10).join([f'- {random.choice(["GOVERN", "MAP", "MANAGE"])}-{random.randint(1,4)}.{random.randint(1,3)}: {random.choice(["Documented decision log", "Continuous evaluation metrics", "Human-in-the-loop gate"])}'
for _ in range(3)])}

### Key Questions Answered
1. **Who authorized this AI system?** Security governance board (minutes attached)
2. **What performance targets?** ≥70% on NIST control mapping eval benchmark
3. **What's the fallback if AI fails?** Manual human review (no autonomous fixes above C-rank)
4. **What audit trail?** MLflow tracking + HITL approval logs in git
"""
    return intake

def generate_chatml_examples(count: int = 200) -> list[dict]:
    """Generate ChatML training examples: scanner output → NIST control → POA&M."""

    scanner_findings = [
        ("kubescape", "⚠️  RBAC: Service account has cluster-admin role binding", "AC-6"),
        ("kubescape", "⚠️  NETWORK: No NetworkPolicy defined for namespace", "SC-7"),
        ("kubescape", "⚠️  CONFIG: Pod runs with privileged: true", "AC-3"),
        ("kube-bench", "FAIL [1.2.1] Ensure that the --anonymous-auth argument is set to false", "IA-2"),
        ("kube-bench", "FAIL [4.2.1] Ensure that RBAC is enabled", "AC-3"),
        ("trivy", "CVE-2024-1234: libssl vulnerability in container image", "SI-2"),
        ("falco", "Alert: Suspicious privilege escalation attempt detected", "SI-4"),
        ("prowler", "AWS IAM: User has AccessKey without MFA enforcement", "IA-2"),
        ("prowler", "AWS VPC: Security group allows 0.0.0.0/0 on SSH port 22", "SC-7"),
        ("semgrep", "Python: SQL injection in query construction", "SI-3"),
    ]

    examples = []
    for _ in range(count):
        scanner, finding, control = random.choice(scanner_findings)

        # Create realistic scanner output snippet
        scanner_output = f"""[{scanner}] {finding}
Resource: {random.choice(['namespace/production', 'pod/api-server', 'deployment/auth-service', 'iam/user-admin'])}
Severity: {'CRITICAL' if random.random() > 0.7 else 'HIGH' if random.random() > 0.4 else 'MEDIUM'}"""

        # BERU's response
        chatml = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Map this finding to NIST control and propose remediation:\n\n{scanner_output}"
                },
                {
                    "role": "assistant",
                    "content": f"""FINDING: {finding}
CONTROL: {control} — {random.choice(['Account Management', 'Access Control', 'System Communications Protection', 'System and Information Integrity', 'Incident Response'])}
ENHANCEMENT: {control}({random.randint(1,5)})
STATUS: {'FAIL' if 'Error' in finding or 'FAIL' in finding else 'PARTIAL'}
EVIDENCE REVIEWED: {scanner} output + manual kubeconfig audit
EVIDENCE GAP: Proof that remediation was applied and validated
RISK: {'High × High → B-rank' if 'cluster-admin' in finding else 'Medium × Medium → C-rank'}
CONTROL OWNER: Security Architect
POA&M ITEM:
  - Weakness: {finding.lower()}
  - Remediation: {'Remove cluster-admin binding; use least-privilege roles' if 'cluster-admin' in finding else 'Apply NetworkPolicy deny-all, add service-specific allow rules'}
  - Target completion: {(datetime.now() + timedelta(days=random.randint(7, 30))).strftime('%Y-%m-%d')}
  - Responsible party: Platform Engineering

CISO SUMMARY: {random.choice(['This control gap creates elevated access risk but has clear remediation path.', 'Finding addresses critical supply chain validation requirement per RMF.', 'Mitigation aligns with FedRAMP Moderate baseline control AC-6.'])}"""
                }
            ]
        }
        examples.append(chatml)

    return examples

def main():
    print("🧠 Generating BERU synthetic training data...\n")

    # Generate SSPs
    print("📝 Generating 10 System Security Plans (varying quality)...")
    qualities = ["bad", "mediocre", "mediocre", "good", "good", "good", "good", "good", "good", "good"]
    for i, quality in enumerate(qualities, 1):
        ssp = generate_ssp(i, quality)
        (OUTPUT_DIR / "ssps" / f"ssp-{i:02d}-{quality}.md").write_text(ssp)
        print(f"  ✓ ssp-{i:02d} ({quality})")

    # Generate AI intake samples
    print("\n📋 Generating 5 AI System Registration samples...")
    for i in range(1, 6):
        intake = generate_ai_intake(i)
        (OUTPUT_DIR / "intake-samples" / f"ai-intake-{i:02d}.md").write_text(intake)
        print(f"  ✓ ai-intake-{i:02d}")

    # Generate ChatML examples
    print("\n💬 Generating 200 ChatML training examples...")
    examples = generate_chatml_examples(200)
    chatml_file = OUTPUT_DIR / "chatml-examples" / "beru-training-examples.jsonl"
    with open(chatml_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"  ✓ {len(examples)} examples written to beru-training-examples.jsonl")

    # Summary
    print(f"\n{'='*60}")
    print(f"✨ BERU TRAINING DATA GENERATED")
    print(f"{'='*60}")
    print(f"Location: {OUTPUT_DIR}/")
    print(f"  • SSPs: 10 files (~25KB)")
    print(f"  • AI Intake: 5 files (~10KB)")
    print(f"  • ChatML: 200 examples (~60KB)")
    print(f"  • Total: ~95KB synthetic data")
    print(f"\nNext steps:")
    print(f"  1. Validate with 8-tests/test_data_quality.py")
    print(f"  2. Parse SSPs with BERU-AI/tools/ssp_parser.py")
    print(f"  3. Train with 1-data-pipeline/train_beru.py")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
