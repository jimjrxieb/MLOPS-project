# Model Card: BERU v1.0 (3B) — Challenger

## Status

**Challenger — pre-baseline.** This model is registered but no eval has run against it yet. Promotion to champion requires the four-eval gate per `CAPSTONE-PROJECT/beru-design-decisions.md` D-010 to pass.

| Phase | Status | Evidence path |
|---|---|---|
| Base model registered | ✅ done | `BERU-AI/Modelfile_beru3b` |
| RAG corpus ready | ✅ done | ChromaDB collection `beru-nist-800-53`, 94 docs |
| Eval suites authored | 🟡 brain done, agent pending | `4-eval-clarify/beru_{knowledge,pentest}_brain_*.jsonl` |
| **Brain baseline run** | ❌ pending | will land in `4-eval-clarify/3-results/beru/{knowledge,pentest}_brain/` |
| Training data validated | ✅ done | `8-tests/test_beru_training_data.py` 18/18 passing |
| Fine-tune run | ❌ pending | will land in `5-experiments/exp-006-beru-v1.0/` |
| Post-fine-tune eval | ❌ pending | requires fine-tune first |
| Promotion to champion | ❌ pending | requires all four eval suites + lift over baseline |

## Model Details

| Field | Value |
|---|---|
| **Name** | beru (v1.0-3b) |
| **Base model** | meta-llama/Llama-3.2-3B-Instruct (Ollama tag `llama3.2:3b`) |
| **Fine-tuning** | LoRA (r=32, alpha=64, 4-bit quantized via Unsloth) — pending |
| **Parameters** | 3 billion |
| **Serving format** | Ollama Modelfile (will become GGUF Q4_K_M after fine-tune) |
| **Modelfile** | `BERU-AI/Modelfile_beru3b` |
| **System prompt SHA-256 (first 12)** | calculated by `beru_eval_runner.py` per run |
| **Experiment dir** | `5-experiments/exp-005-beru-3b-baseline/` (baseline) → `exp-006-beru-v1.0/` (fine-tune) |
| **License** | Meta LLaMA 3.2 Community License (base) |
| **Inventory entry** | `CAPSTONE-PROJECT/templates/ai-inventory-register.md` JSA-AI-003 |

## Linked Design Decisions

| ID | Decision | Why this card cites it |
|---|---|---|
| **D-001** | Local fine-tuned base model (not external API) | Documents why we are running LLaMA at all |
| **D-002** | RAG over fine-tuning for control knowledge | Explains why this card splits "RAG corpus" from "training data" |
| **D-003** | 9-field structured output | Output format BERU is required to produce |
| **D-004** | C-rank authority ceiling (hardcoded) | Promotion gate cannot relax this |
| **D-005** | Synthetic training data only | Training data lineage + privacy rationale |
| **D-007** | Dual citation 800-53 + AI RMF | Output format requirement for AI-in-scope findings |
| **D-009** | Rebaselined from 8B to 3B | Why this card replaces the prior 8B challenger card |
| **D-010** | Four-eval architecture | Why promotion requires brain × {knowledge, pentest} + agent × {knowledge, pentest} |
| **D-011** | Ingest script in pipeline tree | Where RAG corpus refresh runs from |

## Intended Use

BERU is a **junior GRC analyst agent** that assesses *other* AI systems and IT environments for compliance. She also has to satisfy the same compliance herself — see D-010 BERU-as-subject principle.

**Inputs accepted:**
- Scanner output: Trivy, kube-bench, Prowler, Semgrep, Falco, Kubescape, GuardDuty, Bandit, Hadolint, Gitleaks
- AI-specific tooling: Garak (prompt injection), Promptfoo (jailbreak), MLflow audit, model-card review
- Per-control evidence requests, SSP excerpts

**Outputs produced:**
1. 9-field structured findings with dual citation when AI is in scope (NIST 800-53 + NIST AI RMF + MITRE ATLAS where applicable)
2. POA&M items (weakness + scheduled completion + milestones + resources)
3. SSP narratives (evidence-grounded prose at "good" or "great" quality level — see `GP-CONSULTING/NIST-800-53/ssp-examples/`)
4. CISO summaries (one paragraph, business-language, no jargon)

**Out of scope:**
- Remediation execution — that is JADE (DEVOPS) and Katie (K8s) territory
- B-rank or S-rank approvals — must escalate to a human
- Architecture decisions, audit sign-off
- AI systems not registered in `ai-inventory-register.md` (those are GOVERN 1.1 FAIL by definition)

## Knowledge Sources

### RAG corpus (`beru-nist-800-53` ChromaDB collection — 94 docs)

| Source | Count | Path |
|---|---|---|
| NIST 800-53 Rev 5 controls | 39 | `GP-CONSULTING/NIST-800-53/controls/*.md` |
| NIST AI RMF subcategories | 38 | `CAPSTONE-PROJECT/frameworks/nist-ai-600-1/*.md` |
| MITRE ATLAS techniques | 16 | `CAPSTONE-PROJECT/frameworks/mitre-atlas/*.md` |
| 800-53 ↔ AI RMF crosswalk | 1 | `CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md` |

Embedding: nomic-embed-text (768-dim) via Ollama. Stub-rejection regex enforced at ingest. Provenance metadata required on every chunk.

### Training data (synthetic, per D-005)

| Type | Count | Path |
|---|---|---|
| ChatML examples | 200 | `BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` |
| Synthetic SSPs (1 bad, 2 mediocre, 7 good) | 10 | `BERU-AI/training-data/ssps/` |
| AI intake samples | 5 | `BERU-AI/training-data/intake-samples/` |
| Lineage manifest | 1 | `BERU-AI/training-data/lineage-manifest.json` |

## Promotion Gates (per D-010)

All four required for champion:

| Suite | Threshold | Per-group floor | Critical floor (where applicable) |
|---|---|---|---|
| **Knowledge × Brain** | ≥70% overall | ≥60% per question type | — |
| **Knowledge × Agent** | ≥70% overall | ≥60% per question type | — |
| **Pentest × Brain** | ≥70% overall | ≥50% per OWASP LLM category | ≥70% on LLM01, LLM06, LLM08 |
| **Pentest × Agent** | ≥70% overall | ≥50% per OWASP LLM category | ≥70% on LLM01, LLM06, LLM08 |

Plus: zero hallucinated control IDs / AI RMF subcategory IDs / ATLAS technique IDs across all four suites. The fine-tune must beat the baseline on knowledge brain and not regress on pentest brain.

## Metrics

| Metric | How measured | Target | Baseline (exp-005) | Best fine-tune (exp-007/exp-012) |
|---|---|---|---|---|
| Knowledge × Brain overall | `beru_eval_runner.py --suite knowledge_brain` | ≥70% | 29.4% | 16.7% (exp-007) / 13.3% (exp-012) |
| Pentest × Brain overall | `beru_eval_runner.py --suite pentest_brain` | ≥70% | 40.3% | 81.8% (exp-010/011/012) |
| Critical OWASP (LLM01/06/08) | per-category score | ≥70% each | LLM01:52%, LLM06:70%, LLM08:0% | LLM01:75%, LLM06:67%, LLM08:50% |
| Hallucinated IDs | regex scan of all eval outputs | 0 | 0 | 0 |
| Inference latency (CPU) | wall clock per question | <15s | ~8s | ~8s |
| Train loss (latest) | Unsloth training loop | decreasing | — | 1.561 (exp-012) |

**Current status (exp-012, beru:v1.6):** Pentest brain passes gate at 81.8%. Knowledge brain blocked at 13.3% — 56.7 pp gap to 70% gate. Not promoted.

## Known Limitations

- **Complex multi-hop reasoning at 3B parameters:** Unmeasured pre-baseline. The brain baseline (D-009) is specifically designed to surface this. If 3B + RAG falls short, D-009 may be reversed in favor of 8B.
- **OWASP LLM coverage at brain level only:** Agent-level pentest tests (RAG poisoning, tool abuse, HITL bypass) require M4 to be complete before they can run end-to-end.
- **No evaluation against real client data:** D-005 forbids it. All evals use authored synthetic scenarios.
- **MITRE ATLAS coverage is 16 techniques, not the full ~80:** Selected for relevance to GRC analysis. Not a complete adversarial profile.

## Risk Tier

**Minimal Risk** per `CAPSTONE-PROJECT/templates/ai-inventory-register.md`. Justification:

- Authority ceiling at C-rank (D-004) — cannot make autonomous risk decisions of consequence
- Outputs are advisory artifacts (POA&M drafts, SSP narratives, CISO summaries) — never executed automatically
- HITL routing on B/S-rank findings is architecturally enforced
- Synthetic training data eliminates client-PII memorization risk

## Audit Trail

| Artifact | Location |
|---|---|
| Design decisions | `CAPSTONE-PROJECT/beru-design-decisions.md` D-001 → D-011 |
| RAG ingestion audit logs | `GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-*-beru.md` |
| Eval results (when run) | `4-eval-clarify/3-results/beru/{knowledge_brain,pentest_brain,knowledge_agent,pentest_agent}/` |
| Experiment params | `5-experiments/exp-005-beru-3b-baseline/params.yaml` |
| Test gates | `8-tests/test_beru_rag.py`, `test_beru_evals.py`, `test_beru_training_data.py`, `test_beru_core.py`, `test_beru_tools.py`, `test_beru_schemas.py` |
| AI system registration | `CAPSTONE-PROJECT/intake/ai-system-registration.md` (BERU's own registration) |
| Inventory entry | `CAPSTONE-PROJECT/templates/ai-inventory-register.md` JSA-AI-003 row |

## Card Maintenance

This card MUST be updated when:
- Brain baseline run completes (fill the Metrics table baseline column)
- Fine-tune run completes (fill post-fine-tune column, change Status from Challenger to Champion if gates pass)
- A new design decision (D-012+) materially affects BERU
- The RAG corpus expands beyond the listed sources
- A new eval suite is added
