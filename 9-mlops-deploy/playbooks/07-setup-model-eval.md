# Playbook 07 — Setup Model Evaluation

> Deploy evaluation benchmarks with promotion gates and feedback loops.
> **When:** After training pipeline produces a model (Playbook 05)
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] Trained model checkpoint (merged LoRA)
- [ ] Eval benchmark questions (JSONL)
- [ ] Model serving running (KServe + vLLM or local checkpoint)

---

## Phase 1: Build Evaluation Suite

Create domain-specific benchmark questions:

```bash
# Eval suite structure
ls 4-eval-clarify/
# jade_8b_eval_suite_v1.jsonl    ← Benchmark questions
# v1.1_eval_suite.py             ← Eval runner
# 2-test-data/                   ← Test datasets
# 3-results/                     ← Eval outputs
```

**Eval categories with weights:**

| Category | Weight | Question Count | What It Tests |
|----------|--------|----------------|---------------|
| CKS | 40% | ~180 | Pod security, RBAC, admission, CIS |
| CKA | 25% | ~120 | Cluster ops, troubleshooting, workloads |
| CNPA | 25% | ~100 | Cloud networking, CNI, service mesh |
| Cloud | 10% | ~66 | AWS/GCP/Azure security patterns |

**Question format:**
```json
{
  "category": "CKS",
  "subcategory": "pod-security",
  "question": "A pod in namespace 'payments' is running as root with all capabilities. The namespace has PSA enforce=restricted. What happens and how do you fix it?",
  "expected_keywords": ["securityContext", "runAsNonRoot", "drop", "ALL", "readOnlyRootFilesystem"],
  "expected_commands": ["kubectl get pod", "kubectl edit"],
  "difficulty": "intermediate"
}
```

---

## Phase 2: Run Evaluation

```bash
# Run eval against trained model
python3 1-data-pipeline/eval_bridge.py \
  --model-path 3-model-registry/v2.0-3b/merged \
  --eval-suite 4-eval-clarify/jade_8b_eval_suite_v1.jsonl \
  --output 4-eval-clarify/3-results/

# Or against KServe-served model (OpenAI-compatible API)
python3 1-data-pipeline/eval_bridge.py \
  --endpoint http://katie-3b.ml-serving.svc.cluster.local/v1 \
  --eval-suite 4-eval-clarify/jade_8b_eval_suite_v1.jsonl
```

**Scoring criteria:**
- Keyword presence (does the response mention the right concepts?)
- Command correctness (are the kubectl/tool commands real and correct?)
- Completeness (does it diagnose AND fix, not just identify?)
- No hallucination (no fake CIS numbers, nonexistent CVEs, made-up flags)

---

## Phase 3: Promotion Gates

```
Eval complete → Calculate weighted score

CKS (40%) + CKA (25%) + CNPA (25%) + Cloud (10%)

Score ≥ 60%  → PROMOTE
  → merge_model.py → convert_gguf.py → upload to S3 → KServe rollout
  → Update training_state.json
  → Write promotion report

Score 40-60% → TARGETED RETRAIN
  → Identify weak categories
  → feedback_loop.py generates targeted data
  → Re-enter training pipeline at Step 1

Score < 40%  → MANUAL REVIEW
  → Check training data quality
  → Check for catastrophic forgetting
  → May need fresh LoRA from base
```

---

## Phase 4: Feedback Loop

```bash
# Identify weak categories and generate targeted data
python3 1-data-pipeline/feedback_loop.py \
  --results 4-eval-clarify/3-results/latest.json

# Output:
# Weak categories:
#   CNPA/service-mesh: 38% (target: 50%)
#   CKS/admission-controllers: 42% (target: 50%)
#
# Generated 500 targeted examples for CNPA/service-mesh
# Generated 300 targeted examples for CKS/admission-controllers
# Output: 1-data-pipeline/01-raw-data-lake/feedback_targeted_*.jsonl
```

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Model promoted (≥60%) | `08-deploy-model-serving.md` |
| Needs targeted data (40-60%) | Retrain with feedback data → re-eval |
| Failed (<40%) | Review data quality → `04-setup-data-quality-gates.md` |
