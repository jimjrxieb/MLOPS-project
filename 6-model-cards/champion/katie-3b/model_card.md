# Model Card: Katie v1.1 (3B) — Current Champion

## Model Details

| Field | Value |
|-------|-------|
| **Name** | katie (v1.1-3b) |
| **Base model** | meta-llama/Llama-3.2-3B-Instruct |
| **Fine-tuning** | LoRA (r=64, alpha=128, 4-bit quantized) |
| **Parameters** | 3 billion |
| **Serving format** | GGUF (Q4_K_M) via Ollama |
| **Checkpoint** | `3-model-registry/v1.1-3b/chunk_0036_10k/merged` |
| **Checkpoint config SHA256** | `00a0218277c99...` |
| **Experiment** | `5-experiments/exp-001-katie-v1-bulk/` |
| **License** | Meta LLaMA Community License |

## Intended Use

Katie is a junior platform engineer brain deployed as:
- **k8sgpt backend** — explains cluster issues, suggests fixes
- **kubectl-ai backend** — converts natural language to kubectl commands
- **JSA agent LLM** — powers jsa-kubestar for E/D rank auto-fixes
- **Triage router** — classifies and routes findings by rank

Katie does NOT make C-rank decisions. She routes, diagnoses, and proposes. JADE approves.

**Out of scope:** Architecture decisions, compliance sign-off, incident response lead, anything B/S rank.

## Factors

Performance varies by domain. These factors affect quality:

| Factor | Impact | Detail |
|--------|--------|--------|
| **Domain** | High | CKS/CKA strong, Cloud/Hardening weak (0% eval) |
| **Question complexity** | High | Single-step fixes good, multi-step diagnosis weak |
| **Tool specificity** | Medium | Knows kubectl/trivy/kubescape, weak on terraform/GHA/Helm |
| **Response format** | Medium | Better at YAML generation than bash scripting |
| **Data recency** | Low | Trained on 2025-2026 data, no knowledge cutoff issues yet |

## Metrics

| Metric | How measured | Target | Current |
|--------|-------------|--------|---------|
| Weighted eval score | `eval_bridge.py` (466q, 9 categories) | ≥60% | 28.5% |
| Per-category minimum | Each category in eval suite | ≥50% | Best: 60% (K8s), Worst: 0% (Cloud) |
| Hallucination rate | Fake commands/CVEs/CIS numbers | 0% | 0% (passing) |
| Inference latency | `JADE-AI/mlops/inference_tracker.py` | <5s | ~1-2s on CPU |

## Training Data

- **Corpus:** 284,844 examples (uncurated v1 corpus)
- **Examples trained:** 294,998 (36 chunks of ~10k)
- **Format:** Mixed (ChatML + Alpaca) — this was a problem
- **Curation:** None — 85% was garbage (raw JSON, transcripts, stubs)
- **Domains:** kubernetes 38.5%, general 23.0%, devsecops 16.1%, cloud 12.1%, compliance 3.8%, secrets 3.3%, terraform 3.3%

**Known issue:** No Python, Bash, GitHub Actions, Terraform, Helm, Docker, or OPA training data. These are gaps for a platform engineer model.

## Evaluation (Best — chunk 36)

| Category | Accuracy | Questions | Status |
|----------|----------|-----------|--------|
| Kubernetes (general) | 60.0% | 10 | Above threshold |
| CNPA | 45.5% | 22 | Below threshold |
| DevSecOps | 40.0% | 10 | Below threshold |
| CKA | 31.6% | 19 | Below threshold |
| Compliance | 30.0% | 10 | Below threshold |
| **CKS** | **27.8%** | **360** | Below threshold |
| Incident Response | 20.0% | 10 | Below threshold |
| Threat Modeling | 20.0% | 10 | Below threshold |
| Cloud | 0.0% | 10 | No training data |
| Hardening | 0.0% | 5 | No training data |
| **Overall** | **28.5%** | **466** | **FAILED** (threshold: 60%) |

**Not yet evaluated on:** Python, Bash, Git, GitHub Actions, Terraform, OPA, Helm, Docker, AWS CLI (eval suites created 2026-03-25 in dirs 16-24).

**Promotion status:** Did NOT pass promotion gate. Deployed as best available while v2 trains.

## Limitations

- 28.5% overall accuracy — below 60% production threshold
- Cloud and hardening domains: 0% (no clean training data existed)
- Catastrophic forgetting after chunk 36 (stacked LoRA on noisy data → degraded to 8.3%)
- No platform engineering tool knowledge (Python, Bash, Terraform, GHA, Helm, Docker)
- Trained on uncurated data with mixed formats (Alpaca leaked in)

## Ethical Considerations

- Model generates kubectl commands that modify cluster state — wrong commands can cause outages
- E/D rank auto-fixes are applied without human review — must be scoped to safe operations only
- FedRAMP context: LLaMA is US-based, inference is local, no data leaves the network
- Model should never be given delete permissions (enforced in RBAC, not in model weights)

## Challenger

**Katie v2** (`5-experiments/exp-002-katie-v2-curated/`)
- Corpus SHA256: `0347e5e9df5aa0cf8dacfed3ba58f2e063c5c6607f2f7757b878d428b2121e30`
- 42,276 curated examples (vs 284k raw)
- Fresh LoRA from base, ChatML enforced, quality gates, domain distribution tracked
- Status: chunk 1/5 trained, eval pending

## Replacement Criteria

Katie v2 replaces v1 when:
- [ ] All 5 chunks trained with eval after each
- [ ] Weighted score ≥ 60% (CKS 40% + CKA 25% + CNPA 25% + Cloud 10%)
- [ ] Each category ≥ 50%
- [ ] Zero hallucinated commands
- [ ] Beats v1 best (28.5%) on same eval suite
- [ ] Evaluated on platform eng domains (dirs 16-24)
