# M3 — Fine-Tuning

> **Goal:** Understand why you fine-tune, what LoRA does, and what makes training data good or garbage.
> **Build:** 200+ BERU training examples in ChatML format that pass `8-tests/test_data_quality.py`.
> **Gate:** Fine-tuned BERU beats the **brain baseline** (base LLaMA 3.2-3B + RAG, no fine-tune) on the 30-question dual-framework GRC eval suite. See D-009 for the rebaseline rationale.

---

## Why Fine-Tune at All?

You already have RAG (M2) injecting control text. Why fine-tune on top of that?

Because RAG handles *knowledge* — it gives the model the right facts. Fine-tuning handles *behavior* — it shapes how the model uses those facts. A base LLaMA 3.2-3B can read NIST control text and produce something compliance-adjacent. A fine-tuned BERU will produce the exact 10-field structured format with dual citation (800-53 + AI RMF), use the right tone, and know when to escalate to B-rank — consistently, without needing it spelled out in every prompt.

**But you don't get to assume that.** Before you fine-tune, you measure what RAG alone gets you — the **brain baseline**. If base 3B + RAG already hits the 70% promotion gate, fine-tuning is a discretionary improvement. If it falls short, the eval tells you exactly which control families to target with training data. Skip the baseline and you're guessing.

**The analogy:** RAG is handing a consultant the client's documents. Fine-tuning is the three years they spent at a GRC firm before you hired them. The documents tell them what. The training tells them how.

---

## Concept 1 — LoRA (Low-Rank Adaptation)

### What full fine-tuning would be
Training all 3 billion parameters from scratch — expensive (tens to hundreds of GPU-hours), slow, and risks destroying what the base model already knows. Not practical for a single project.

### What LoRA does instead
LoRA freezes the original model weights and adds a small set of adapter layers alongside them. Instead of updating 3B parameters, you update ~5-15M. The adapters learn the domain-specific patterns. The base model handles everything else.

```
Base LLaMA weights (frozen, 3B params)
     +
LoRA adapters (trainable, ~10M params at r=32)
     =
BERU — speaks dual-framework GRC analyst
```

### The two hyperparameters you care about
- **r (rank)** — size of the adapter matrices. Higher r = more parameters = more capacity to learn domain patterns = higher VRAM cost. BERU uses `r=32` for 3B (the JADE 8B model uses `r=64` — adapters scale with base size).
- **alpha** — scaling factor. Usually set to 2× r. BERU uses `alpha=64`. This controls how much the adapters influence the output vs. the frozen base model.

**Practical rule:** Start with `r=32, alpha=64` for 3B models, `r=64, alpha=128` for 8B. If the model isn't learning your format, increase r. If it's losing general capability (catastrophic forgetting), decrease r.

### QLoRA (Quantized LoRA)
Same as LoRA but the frozen base model is loaded in 4-bit precision instead of 16-bit. For 3B this cuts VRAM from ~6GB to ~3GB, making fine-tuning viable on a laptop-class GPU or a small spot instance. The adapters themselves train in 16-bit for precision.

**The tradeoff:** 4-bit quantization introduces slight numerical imprecision in the base model. For compliance text, this is acceptable. For math-heavy tasks, it might not be.

---

## Concept 2 — Unsloth

Unsloth is the training library BERU uses. It wraps HuggingFace PEFT (the standard LoRA library) with optimized kernels that are 2-5× faster on consumer GPUs.

```python
# Standard HuggingFace PEFT would be:
from peft import get_peft_model, LoraConfig
# ~10 lines of setup, standard speed

# Unsloth replaces this with:
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-3B-Instruct",
    max_seq_length=2048,
    dtype=None,   # auto-detect
    load_in_4bit=True,  # QLoRA
)
model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    lora_alpha=64,
    target_modules=["q_proj", "v_proj"],  # which layers get adapters
)
```

**Why it matters for BERU:** BERU is 3B (per D-009). With vanilla PEFT on a laptop-class GPU, a training run could take 3-4 hours. With Unsloth, it's 1-2 hours. That difference matters when you're iterating on data quality. The 3B size also means inference runs adequately on CPU — the agent loop in M4 doesn't need a GPU to demo.

The training script for this repo: `1-data-pipeline/train_v11.py`

---

## Concept 3 — ChatML Format (Training Data)

LLMs are trained with a specific message format that separates system/user/assistant turns. LLaMA 3.x (including the 3.2-3B base BERU uses) uses ChatML. Your training examples must match exactly.

```jsonl
{
  "messages": [
    {
      "role": "system",
      "content": "You are BERU, the GRC analyst..."
    },
    {
      "role": "user",
      "content": "Trivy scan found: CVE-2024-1234 in python:3.9-slim. CVSS 9.8. Image used by 3 production deployments."
    },
    {
      "role": "assistant",
      "content": "FINDING: Critical CVE-2024-1234 in base image python:3.9-slim affects 3 production deployments.\nCONTROL: SI-2 Flaw Remediation\nSTATUS: FAIL\nEVIDENCE REVIEWED: Trivy image scan output, 2026-05-07\nEVIDENCE GAP: Patch deployment timeline not documented\nRISK: Likelihood 4 × Impact 5 = 20 → B-rank. Remote code execution possible on internet-facing services.\nCONTROL OWNER: DevSecOps Lead\nPOA&M ITEM: Weakness — base image unpinned, CVE unpatched. Scheduled completion: 2026-05-21. Milestone: Pin python:3.11-slim, redeploy all 3 services.\nCISO SUMMARY: Three production services are running a Python base image with a critical remote code execution vulnerability. An attacker who can reach these services could take full control of the containers. Emergency patching is required within 48 hours."
    }
  ]
}
```

One JSON object per line. One training example = one system + user + assistant exchange.

### What makes a good training example
- **User message**: real-looking scanner output (not just "check AC-6")
- **Assistant response**: perfect 10-field BERU format with real control IDs
- **Variety**: different scanners, different control families, different pass/partial/fail
- **Edge cases**: what should BERU do when evidence is missing? When the scanner found nothing?

### What Gemini generates for you
Gemini Flash can produce 200+ varied examples in this format from a single prompt. Your job: review 20% of them manually to check quality, then run them through `test_data_quality.py`.

---

## Concept 4 — Data Quality Gates

These exist in `8-tests/test_data_quality.py`. Nothing trains until it passes. The rules (from `CLAUDE.md`):

| Gate | What it checks | Why |
|------|---------------|-----|
| Format | ChatML `messages` array with system/user/assistant roles | Wrong format = training loop crashes or produces garbage |
| Scope | Response contains NIST control IDs or GRC keywords | Prevents off-topic examples from diluting the domain signal |
| No placeholders | `[FINDING HERE]`, `TODO`, etc. rejected | Placeholder text teaches the model to produce placeholder text |
| Min length | Assistant response ≥ 50 chars | Stubs teach the model to truncate |
| No duplicates | Exact matches removed | Duplicate examples overfit, causing the model to repeat verbatim |
| Min chunk size | At least 500 examples per training run | Tiny runs cause catastrophic forgetting of prior learning |

### Catastrophic forgetting
When you fine-tune on new data, the model can partially forget what it knew before. Mitigation: train on a diverse corpus that includes both BERU-specific examples and general instruction-following examples. The quality gates enforce minimum corpus size to prevent this.

---

## Concept 5 — Eval Design

The eval suite is 30 questions covering 5 control families: AC, AU, CM, SC, SI. Each question tests whether BERU:
1. Identifies the right control
2. Produces the right STATUS for the given evidence
3. Doesn't hallucinate control IDs

```python
# Example eval question (lives in 4-eval-clarify/)
{
  "question_id": "eval-si-001",
  "input": "kube-bench check 4.2.1 FAIL: privileged containers running in default namespace",
  "expected_control": "CM-7",
  "expected_status": "FAIL",
  "expected_rank_min": "C",
  "expected_rank_max": "B",
  "family": "CM"
}
```

**Before/after comparison (the brain baseline pattern):** Run the 30-question suite on base LLaMA 3.2-3B + RAG (no fine-tune). Record the score in `5-experiments/exp-005-beru-3b-baseline/metrics.json` — this is your floor. Fine-tune BERU. Run the same suite again. BERU must beat the baseline by a measurable margin AND hit the absolute promotion gate. If BERU underperforms the baseline, the training data hurt the model — review and re-curate before retraining.

**The promotion gate:** ≥70% overall, ≥60% per family, zero hallucinated control IDs. Below 70% → add more training data to the weak families and retrain.

---

## Troubleshooting M3

| Symptom | Cause | Fix |
|---------|-------|-----|
| Training loss not decreasing | Learning rate too high or data quality issues | Check `train_v11.py` config — `lr=2e-4` for LoRA is standard |
| Model produces correct format but wrong controls | Good format learning, weak domain knowledge | Add more examples with explicit control-to-finding mappings |
| Catastrophic forgetting (general capability gone) | Too little data, too many epochs | Add diversity to corpus; reduce epochs from 3 to 1-2 |
| CUDA out of memory | Batch size too large for VRAM | Reduce `per_device_train_batch_size` to 1, increase `gradient_accumulation_steps` |
| eval score lower than baseline | Data quality issues in training set | Audit 50 random training examples manually — common cause: Gemini-generated examples with wrong control IDs |
| `test_data_quality.py` fails on scope check | Gemini examples lack NIST control IDs | Add "include a NIST 800-53 control ID" to your Gemini prompt |
| Training hangs at "Loading tokenizer" | Unsloth environment issue | `pip install unsloth --upgrade`; check CUDA version matches |

---

## What You Build

0. **Brain baseline run** — `python3 4-eval-clarify/beru_eval_runner.py --model llama3.2:3b` against the 30-question dual-framework eval suite. Record in `5-experiments/exp-005-beru-3b-baseline/`. **This is the floor every fine-tune must beat.**
1. Write a Gemini prompt that generates BERU-format training examples (you do this in the Gemini CLI)
2. Drop the output into `BERU-AI/training-data/`
3. Run `python3 -m pytest 8-tests/test_data_quality.py -v` — fix failures
4. Run one training chunk through `train_v11.py` (Unsloth, r=32/alpha=64, target_modules=q_proj,v_proj)
5. Run the same 30-question eval against fine-tuned model
6. Record the comparison in `5-experiments/exp-006-beru-v1.0/metrics.json` — must show lift over baseline AND meet absolute promotion gate

**The Gemini prompt skeleton:**
```
Generate 50 BERU GRC analyst training examples in ChatML JSON format.
Each example:
- user: realistic scanner output (Trivy, kube-bench, Prowler, or GuardDuty)
- assistant: BERU 10-field response with a real NIST 800-53 control ID (AC-x, AU-x, CM-x, SC-x, or SI-x)
Cover: 10 FAIL findings, 5 PARTIAL, 5 PASS. Mix control families.
Output: one JSON object per line. No markdown, no explanation.
```

**3PAO question this answers:** "You fine-tuned the model — what data did you train it on? Was any real client data used?"
Your answer: "200+ Gemini-generated synthetic examples. No real client data. Synthetic-only policy is documented in `beru-design-decisions.md D-005`, traced to `MAP-4.1` and `SC-28`."

---

## Control Traceability

> When an auditor asks "what data did you train BERU on? How do you know it's not worse than before?" — point here.

**NIST 800-53:**

| Control | What it maps to in M3 | Audit answer |
|---------|----------------------|--------------|
| **SA-11** — Developer Testing and Evaluation | 30-question GRC eval suite with ≥70% gate — BERU cannot be promoted without passing | "Every BERU version runs the same 30-question eval before promotion. Below 70%, it doesn't ship. Scores are in `5-experiments/`." |
| **CM-3** — Configuration Change Control | `params.yaml` is versioned per experiment in `5-experiments/exp-NNN/` — every training run is a documented configuration change | "Every training run has its own config file. We can reproduce any experiment by running the same params against the same data." |
| **CM-6** — Configuration Settings | LoRA hyperparameters (r=64, alpha=128, 4-bit quantization, 2 epochs) are documented and locked per training run | "LoRA config is in `params.yaml` and `6-model-cards/`. Any change to hyperparameters creates a new experiment entry." |
| **SC-28** — Protection of Information at Rest | Training corpus is synthetic-only (Gemini-generated). No real scanner findings, no real client SSPs | "The training data is synthetic. Real client data never touches the training pipeline. Enforced by the data quality gate." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **MEASURE-2.5** — AI system is demonstrated to be valid and reliable | The eval gate (≥70% overall, ≥60% per control family, zero hallucinated IDs) is the validity gate before any version is promoted | "BERU v1.0 passed the eval gate: score is in `5-experiments/exp-004-beru-v1.0/metrics.json`. The gate criteria are in `CLAUDE.md`." |
| **MANAGE-2.4** — Mechanisms to sustain deployed AI systems | MLflow tracks training loss, eval scores, and data version per run — performance regressions are detectable | "MLflow experiment tracking lets us compare any two BERU versions on the same eval suite. A regression shows up before deployment." |
