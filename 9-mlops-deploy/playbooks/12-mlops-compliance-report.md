# Playbook 12 — MLOps Compliance Report

> Generate the full lifecycle report: model lineage, data provenance, eval history, serving audit.
> **When:** End of engagement or quarterly review
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] All previous playbooks executed
- [ ] KFP experiment history (or SageMaker Experiments)
- [ ] Eval results archive
- [ ] Training state records

---

## Phase 1: Model Lineage

Document the full chain from data to production:

```markdown
## Model Lineage Report

### Katie v2.0 (LLaMA 3.2-3B-Instruct)

**Base model:** meta-llama/Llama-3.2-3B-Instruct
**Fine-tuning method:** LoRA (r=64, alpha=128, 4-bit quantized)
**Training framework:** Unsloth + HuggingFace Transformers

**Data provenance:**
- Raw corpus: 300,000 examples from 23 sources
- After curation: 44,030 examples (85% rejected)
- Quality gates: ChatML format, scope check, dedup, content quality
- Domain distribution: CKS 35%, CKA 30%, CKAD 20%, CNPA 10%, OPS 5%

**Training history:**
- v1.0: 294,998 examples, 36 chunks (v1 corpus — deprecated)
- v2.0: 44,030 examples, fresh LoRA from base (clean corpus)

**Evaluation scores:**
| Category | Weight | Score | Threshold |
|----------|--------|-------|-----------|
| CKS | 40% | XX% | 50% |
| CKA | 25% | XX% | 50% |
| CNPA | 25% | XX% | 50% |
| Cloud | 10% | XX% | 50% |
| **Weighted Total** | | **XX%** | **60%** |

**Serving:**
- Format: GGUF (Q4_K_M quantization)
- Runtime: KServe + vLLM on Kubernetes
- Namespace: ml-serving
- Health checks: liveness + readiness probes
```

---

## Phase 2: Data Provenance Audit

```bash
# Generate data provenance report
python3 tools/generate-compliance-report.sh --section data-provenance

# Verify no PII in training data
python3 tools/validate-training-data.py --input 1-data-pipeline/05-data-quality/curated/ --check pii

# Verify no copyrighted material flags
python3 tools/validate-training-data.py --input 1-data-pipeline/05-data-quality/curated/ --check licensing
```

**Document:**
- [ ] All data sources with dates and licenses
- [ ] PII scan results
- [ ] Curation decisions and rejection reasons
- [ ] Domain distribution vs target

---

## Phase 3: Infrastructure Audit

```bash
# Security posture of ML infrastructure
kubectl get pods -n ml-serving -o json | python3 -c "
import json,sys
pods = json.load(sys.stdin)['items']
for pod in pods:
    for c in pod['spec']['containers']:
        sc = c.get('securityContext', {})
        print(f\"{c['name']}: nonRoot={sc.get('runAsNonRoot')}, readOnly={sc.get('readOnlyRootFilesystem')}, privEsc={sc.get('allowPrivilegeEscalation')}\")
"

# Resource limits set?
kubectl get pods -n ml-serving -o json | python3 -c "
import json,sys
pods = json.load(sys.stdin)['items']
for pod in pods:
    for c in pod['spec']['containers']:
        r = c.get('resources', {})
        print(f\"{c['name']}: requests={r.get('requests')}, limits={r.get('limits')}\")
"

# Network policies?
kubectl get networkpolicies -n ml-serving
kubectl get networkpolicies -n mlops
```

---

## Phase 4: Generate Final Report

```bash
bash tools/generate-compliance-report.sh --full

# Output: outputs/mlops-compliance-report.md
```

**Report sections:**
1. Executive Summary (maturity score before/after)
2. Model Lineage (base → fine-tune → eval → serve)
3. Data Provenance (sources, curation, quality)
4. Training History (runs, configs, metrics)
5. Evaluation Results (benchmarks, promotion decisions)
6. Serving Infrastructure (security, health, scaling)
7. Monitoring & Alerting (drift detection, retraining triggers)
8. Cost Analysis (before/after, optimization applied)
9. Recommendations (next steps, gaps remaining)

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Report delivered | Engagement complete |
| Gaps identified | Loop back to relevant playbook |
| Client wants ongoing monitoring | Set up scheduled evals (Playbook 10) |
