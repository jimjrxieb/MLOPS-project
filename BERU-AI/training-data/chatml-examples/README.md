# BERU ChatML Training Examples

## Current state

The active training corpus is being authored fresh per `CAPSTONE-PROJECT/beru-design-decisions.md` D-012. Target is **500 training + 75 validation examples**, hand-authored.

| Phase | File | Status |
|---|---|---|
| Phase 1 | `beru-training-v1-llm08.jsonl` | pending — 150 LLM08 authority-bypass examples |
| Phase 2 | `beru-training-v1-{llm01,llm03,llm06,schema,normal}.jsonl` | pending — 350 examples |
| Phase 3 | `beru-validation-v1.jsonl` | pending — 75 held-out validation examples |
| Final merged | `beru-training-examples.jsonl` | pending — Phase 1 + Phase 2, post-quality-gate |

When Phase 1 + Phase 2 are complete, the per-category files are concatenated in deterministic order into `beru-training-examples.jsonl` and that becomes the input to `1-local-pipeline/01-raw-data-lake/`.

## Archived corpus — `_archived-200-rejected.jsonl`

200 Gemini-generated ChatML examples authored before D-012. **Discarded, not used for training.** Kept for audit traceability and as a teaching artifact for "what bad synthetic data looks like."

### Why they were rejected

Audit run on 2026-05-08:

| Quality dimension | Result | Should have been |
|---|---|---|
| Control name matches the canonical NIST 800-53 name for that ID | **0 / 200 correct** | 200 / 200 correct |
| Distinct remediation strings | **2 total** | ≥40 distinct (1 per ~5 examples) |
| Distinct risk strings | **2 total** | ≥20 distinct |
| Distinct evidence-gap strings | **1 ("Proof that remediation was applied and validated")** | ≥40 distinct |
| Adversarial / authority-refusal examples | **0** | ≥50% of corpus per D-012 |
| Contrast pairs (legitimate vs unsafe with similar framing) | **none** | required by D-012 |

### Examples of the wrong control-name pairings

```text
CONTROL: SC-7 — System Communications Protection   (real: Boundary Protection)            x12
CONTROL: SC-7 — Access Control                     (real: Boundary Protection)            x11
CONTROL: SI-3 — Access Control                     (real: Malicious Code Protection)
CONTROL: AC-3 — System and Information Integrity   (real: Access Enforcement)             x8
CONTROL: IA-2 — System and Information Integrity   (real: Identification & Authentication)x10
```

Training a 3B model on these would have baked the wrong control mappings into weights — a class of hallucination that is harder to fix than starting fresh.

### Examples of cookie-cutter content

```text
Remediation:  "Apply NetworkPolicy deny-all, add service-specific allow rules"   x181 / 200
              even on findings about SQL injection, S3 buckets, AWS IAM, hardcoded secrets

RISK:         "Medium × Medium → C-rank"                                          x181 / 200
              same risk for every finding regardless of CVSS or impact

EVIDENCE GAP: "Proof that remediation was applied and validated"                  x200 / 200
              identical generic gap on every example
```

### What this teaches us

The original quality gate at `8-tests/test_beru_training_data.py` validated:
- ChatML format compliance ✅
- Control IDs match a regex pattern ✅
- Control IDs exist in the `compliance-controls` ChromaDB collection ✅

But did NOT validate:
- That the control NAME paired with the ID is correct
- That remediation / risk / evidence-gap strings are diverse
- That the corpus contains both adversarial and normal-compliant examples

Those gaps were the blind spots Gemini drove a truck through. The new test class `TestCorpusQuality` in `test_beru_training_data.py` plugs all four. Per D-012 the new corpus cannot land without passing them.

## Authoring rules for the new corpus (D-012)

1. **Quality > raw count** — author 575 right rather than 1500 sloppy
2. **Coverage** — same attack worded many different ways; same finding type with varied scanner outputs and varied control names from the canonical set
3. **Contrast** — every adversarial example has a near-twin legitimate example so BERU learns to discriminate
4. **Exact output format** — every assistant response uses the 9-field schema; dual citation when AI is in scope; ATLAS technique IDs where applicable
5. **Eval separation** — no overlap with `4-eval-clarify/beru_knowledge_brain_v2.jsonl` or `beru_pentest_brain_v1.jsonl`. Validation set is also disjoint from both.

Per D-012 + D-005 lineage manifest, every new file's SHA-256 will be recorded in `BERU-AI/training-data/lineage-manifest.json`.
