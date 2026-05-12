
# JADE Training & Evaluation Data

This directory contains all data for JADE fine-tuning and performance measurement.

## Directory Structure

```
2-test-data/
├── training-data/              # Data to TRAIN JADE (supervised fine-tuning)
│   ├── faulty-examples/        # Broken configs/manifests/logs (INPUT)
│   ├── fixed-examples/         # Corrected versions (OUTPUT)
│   ├── deployments/            # Test deployments (broken-app)
│   ├── jade-knowledge/         # Domain knowledge (K8s playbooks)
│   ├── scripts/                # Training data generators
│   └── training-data/          # Generated JSONL output
│
└── evaluation/                 # Data to TEST JADE (benchmarks)
    ├── 01-cloud-benchmark/     # AWS/cloud security questions
    ├── 02-cks-benchmark/       # Kubernetes security (CKS)
    ├── 03-devsecops-benchmark/ # CI/CD security
    ├── 04-compliance-benchmark/# Compliance frameworks
    ├── 05-hardening-benchmark/ # System hardening
    ├── 06-incident-response-benchmark/
    ├── 07-threat-modeling-benchmark/
    ├── task-tests/             # Specific task evaluations
    │   ├── classification/     # Rank classification tests
    │   ├── fix-generation/     # Fix generation tests
    │   ├── policy-generation/  # Policy generation tests
    │   └── code-generation/    # Code generation tests
    ├── evaluators/             # Evaluation logic
    └── run_benchmarks.py       # Benchmark runner
```

---

## The Distinction

| Folder | Purpose | When Used |
|--------|---------|-----------|
| `training-data/` | Input/output pairs for supervised fine-tuning | Updates model weights |
| `evaluation/` | Benchmarks to measure model performance | Tests model, no weight changes |

```
TRAINING DATA (Supervised Learning)
───────────────────────────────────
• Input + Expected Output pairs
• Used to UPDATE model weights
• "Here's what good looks like"
• faulty-examples/ → fixed-examples/
• playbooks → troubleshooting pairs
• Output: JSONL for LoRA fine-tuning

EVALUATION DATA (Benchmarks)
────────────────────────────
• Questions + Correct Answers
• Used to MEASURE model performance
• "Let's see if you learned it"
• Model weights DO NOT change
• Produces accuracy scores
```

---

## Training Data

**Purpose:** Input/output pairs to fine-tune JADE with supervised learning.

### Data Sources

| Folder | Description | Format |
|--------|-------------|--------|
| `faulty-examples/` | Broken configs, logs, manifests | Raw files (INPUT) |
| `fixed-examples/` | Corrected versions | Raw files (OUTPUT) |
| `jade-knowledge/k8s-playbooks/` | K8s troubleshooting playbooks | YAML |
| `deployments/training/broken-app/` | Intentionally vulnerable K8s app | YAML manifests |

### Generate Training Data

```bash
cd training-data/scripts

# Generate from scanner rules (Checkov, Semgrep, Trivy, Kube-bench)
python generate_scanner_training_data.py --source all

# Generate from K8s playbooks
python generate_k8s_training_data.py

# Combine all sources into training splits
python prepare_training_data.py --full-pipeline
```

### Output Format (Alpaca)

```json
{
  "instruction": "A Checkov scan found CKV_K8S_1 violated...",
  "input": "Deployment has privileged: true",
  "output": "This is a D-rank finding. Set privileged: false..."
}
```

### Training Data Stats

| Source | Rules/Playbooks | Training Pairs |
|--------|-----------------|----------------|
| Checkov K8s | 43 | ~215 |
| Semgrep | 15 | ~75 |
| Trivy | 28 | ~140 |
| Kube-bench | 22 | ~110 |
| K8s Playbooks | 30 | ~360 |
| **Total** | **138** | **~900** |

---

## Evaluation

**Purpose:** Measure JADE's performance through Q&A benchmarks.

### Benchmark Categories

| Benchmark | Questions | Focus |
|-----------|-----------|-------|
| 01-cloud | 50+ | AWS IAM, networking, encryption |
| 02-cks | 50+ | Pod security, RBAC, network policies |
| 03-devsecops | 50+ | CI/CD security, secrets management |
| 04-compliance | 50+ | SOC2, PCI-DSS, HIPAA, NIST |
| 05-hardening | 50+ | OS hardening, CIS benchmarks |
| 06-incident-response | 25+ | Security incident handling |
| 07-threat-modeling | 25+ | STRIDE, threat analysis |

### Question Format

```json
{
  "id": "cloud-iam-001",
  "category": "cloud",
  "subcategory": "iam",
  "rank": "D",
  "question": "An IAM policy has 'Action': '*' and 'Resource': '*'. What is the risk?",
  "expected_keywords": ["overly permissive", "least privilege"],
  "expected_fix_contains": "specific action",
  "grading": {"keywords_required": 3, "fix_required": true}
}
```

### Task Tests

Specific capability evaluations:

| Test | Purpose |
|------|---------|
| `classification/rank-classification/` | Test E-S rank assignment |
| `classification/agent-routing/` | Test JSA agent routing |
| `fix-generation/checkov-findings/` | Test Checkov fix generation |
| `fix-generation/trivy-findings/` | Test Trivy fix generation |
| `policy-generation/gatekeeper/` | Test OPA policy creation |
| `policy-generation/kyverno/` | Test Kyverno policy creation |

### Running Evaluations

```bash
cd evaluation

# Run all benchmarks
python run_benchmarks.py

# Run specific category
python run_benchmarks.py --category cloud

# Run with Claude as judge
python run_claude_judge.py --limit 10
```

---

## Output Location

All generated training data goes to:
```
/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/4-GP-CLARIFY/3-results/
```

Files:
- `jade-training-v2-train.jsonl` (80%)
- `jade-training-v2-val.jsonl` (10%)
- `jade-training-v2-test.jsonl` (10%)
- `jade-training-v2-combined.jsonl` (all)

---

## Quick Reference

| Want to... | Run this |
|------------|----------|
| Generate training data | `training-data/scripts/prepare_training_data.py --full-pipeline` |
| Run evaluations | `evaluation/run_benchmarks.py` |
| Set up test cluster | `training-data/scripts/setup_training_cluster.sh` |
| Check training stats | `training-data/scripts/generate_scanner_training_data.py --stats` |
