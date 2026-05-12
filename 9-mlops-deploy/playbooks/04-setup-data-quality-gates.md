# Playbook 04 — Setup Data Quality Gates

> Enforce data quality before any training data enters the pipeline. No garbage in.
> **When:** Before first training run — runs on every data change
> **Time:** 2-3 hours

---

## Prerequisites

- [ ] Training data in JSONL format
- [ ] Python 3.10+ with pandas, jsonlines

---

## Phase 1: Format Validation

Every training example MUST be ChatML format:

```json
{"messages": [
  {"role": "system", "content": "You are a Kubernetes security engineer."},
  {"role": "user", "content": "A pod is running as root. How do I fix this?"},
  {"role": "assistant", "content": "Add securityContext with runAsNonRoot: true..."}
]}
```

**Rejected formats:**
- Alpaca (`instruction/input/output`) — REJECTED
- Raw JSON logs — REJECTED
- Plain text without role structure — REJECTED

```bash
# Validate format
python3 tools/validate-training-data.py --input /path/to/data.jsonl --check format
```

---

## Phase 2: Content Quality Gates

```bash
# Run full quality pipeline
python3 tools/validate-training-data.py --input /path/to/data.jsonl --check all
```

**Gate 1 — Scope check:** Every example must match at least one domain keyword.
- CKS: pod security, RBAC, NetworkPolicy, Falco, admission controllers, CIS
- CKA: cluster architecture, etcd, workloads, services, troubleshooting
- CKAD: app design, deployment strategies, probes, Helm
- CNPA: cloud networking, CNI, service mesh, DNS, IaC
- OPS: ArgoCD, rank routing, incident response

**Gate 2 — No garbage:**
- `[CORRECTION]` placeholders → REJECTED
- `[NEEDS CORRECTION]` → REJECTED
- Nested JSON inception → REJECTED
- Raw scanner output without analysis → REJECTED

**Gate 3 — No filler:**
- Stub responses (<50 chars) → REJECTED
- Generic definitions without K8s context → REJECTED
- Chitchat ("Nice work!", "I'm listening") → REJECTED

**Gate 4 — No transcripts:**
- YouTube captions → REJECTED
- Video/audio transcripts → REJECTED
- Exam cram dumps → REJECTED

**Gate 5 — Deduplication:**
- Exact duplicate (same Q+A) → keep one
- Same response, different phrasing → keep max 3 variants

**Gate 6 — Response quality:**
- Must contain real commands, real YAML, real tool names
- "Consider implementing security best practices" → REJECTED

---

## Phase 3: Chunk Size Enforcement

```bash
# Check chunk sizes before training
python3 tools/validate-training-data.py --input /path/to/data.jsonl --check chunk-size
```

**Rule:** NEVER train on chunks smaller than 500 examples. Micro-batches (16-174 examples) cause catastrophic forgetting via LoRA weight drift.

---

## Phase 4: Generate Quality Report

```bash
python3 tools/validate-training-data.py --input /path/to/data.jsonl --report

# Output:
# Total examples: 44,030
# Format valid: 44,030 (100%)
# In-scope: 43,812 (99.5%)
# Duplicates removed: 218
# Rejected (garbage): 0
# Domain distribution:
#   CKS: 35.2% (target: 35%)
#   CKA: 29.8% (target: 30%)
#   CKAD: 19.1% (target: 20%)
#   CNPA: 10.8% (target: 10%)
#   OPS:   5.1% (target: 5%)
```

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Quality gates passing | `05-setup-training-pipeline.md` |
| Need more data in weak domain | Generate with `tools/` scripts, then re-validate |
