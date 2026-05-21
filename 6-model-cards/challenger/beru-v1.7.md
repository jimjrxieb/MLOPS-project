# BERU v1.7 — Model Card

**Status:** CHALLENGER (not promoted — knowledge_brain 34.1%, gate requires 70%)
**Date:** 2026-05-20
**Experiment:** exp-015

---

## Model Identity

| Field | Value |
|---|---|
| Name | beru:v1.7 |
| Base model | Llama 3.2-3B-Instruct (unsloth) |
| Architecture | LoRA fine-tune, r=64, alpha=128, Q4_K_M GGUF |
| Role | GRC analyst — NIST 800-53 Rev 5 + NIST AI RMF / AI 600-1 |
| Authority ceiling | C-rank max. B/S-rank routes to HITL. Never fixes. |
| GGUF | `3-model-registry/beru/v1.7/beru-v1.7-q4_k_m.gguf` (1.88 GB) |
| Ollama tag | `beru:v1.7` |

---

## Training

| Parameter | Value |
|---|---|
| Training examples | 1,832 |
| Corpus sources | CGRC exam (5 files), CySA+ exam, AI security exam (3 files), GRC-HAT governance briefs + control maps |
| Deduplication removed | 1,971 examples |
| Epochs | 2 |
| Final loss | 1.767 |
| Training time | 33.9 min (RTX 5080 Laptop) |
| Hardware | NVIDIA RTX 5080 Laptop, 15.92 GB VRAM |

**Loss curve:** 3.18 → 1.36 (clean descent, no instability)

---

## Evaluation Results

### knowledge_brain (positive suite — GRC reasoning)

| Category | No-RAG | RAG |
|---|---|---|
| finding_accuracy | 48.8% | 51.4% |
| poam_drafting | 39.6% | 42.4% |
| tool_output_interpretation | 39.3% | **22.7%** (RAG hurt) |
| evidence_gap_detection | 29.2% | 38.3% |
| dual_citation | 24.2% | 33.9% |
| atlas_mapped_ai_risk | 23.8% | 22.1% |
| **Overall** | **34.1%** | **35.1%** |

**Promotion gate:** 70% overall, 60% per group — **NOT MET**

### pentest_brain v2 (negative suite — evidence-in/finding-out)

| Category | Score |
|---|---|
| LLM02–07, LLM08, LLM10 | 70% each (8 categories) |
| LLM01 (prompt injection resistance) | 35% |
| LLM09 (scope discipline) | 35% |
| **Overall** | **63.0%** |

*Note: pentest_brain v2 uses evidence-in/finding-out framing matching BERU's production context via CrewAI. BERU receives scanner output and evidence reports, not direct user prompts.*

---

## Known Gaps

| Gap | Score | Root Cause | Fix for exp-016 |
|---|---|---|---|
| dual_citation | 24.2% | Insufficient explicit 800-53 ↔ AI RMF pairing in corpus | Targeted dual-citation generator |
| atlas_mapped_ai_risk | 23.8% | ATLAS taxonomy not represented in training examples | ATLAS scenario generator |
| evidence_gap_detection | 29.2% | Pattern not reinforced in training | More "I see X, missing Y" examples |
| LLM01 injection resistance | 35% | BERU occasionally complies with directives embedded in scanner data | More injection-in-evidence training |
| LLM09 scope discipline | 35% | Extrapolates comprehensive assessments from single events | Scope-limiting training examples |

---

## RAG Behavior

RAG helps dual_citation and evidence_gap (+9-10%) but **hurts tool_output_interpretation (-17%)** and was previously hurting pentest_brain before suite reframe. Root cause: ChromaDB retrieval injects control text that competes with evidence parsing. Recommendation: disable RAG for tool_output_interpretation questions; enable only for dual_citation and gap_detection.

---

## Promotion Decision

**CHALLENGER — not promoted.**

Strongest performance: finding_accuracy (48.8%) and pentest_brain governance/supply chain categories. The model has learned GRC identity — it knows it's a GRC analyst, respects authority boundaries (LLM08 100%), and refuses evidence fabrication (LLM09-001). The gaps are in precision: dual-citation pattern and ATLAS mapping require more targeted training data.

**Champion remains:** beru:v1.6
**Target for promotion:** exp-016 with dual-citation and ATLAS generators + 5,000+ example corpus
