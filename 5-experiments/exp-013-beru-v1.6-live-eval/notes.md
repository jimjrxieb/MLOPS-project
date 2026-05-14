# exp-013 — beru:v1.6 Live Serving Eval (2026-05-14)

## What this is

First **serving-time** eval run against the Ollama-deployed beru:v1.6. Previous evals (exp-006 through exp-012) were done at **training time** against the merged HuggingFace weights (merged_16bit, full precision). This run evaluates what users actually hit — the GGUF Q4_K_M quantized model served via Ollama.

## Results

| Suite | Training-time (exp-012) | Serving-time (exp-013) | Delta |
|-------|------------------------|----------------------|-------|
| Knowledge Brain | 13.3% (4/30) | 20.0% (6/30) | **+6.7pp** |
| Pentest Brain | 81.8% (18/22) | 68.2% (15/22) | **-13.6pp** |

## Why the gap exists

1. **Quantization (Q4_K_M vs merged_16bit)** — GGUF reduces weights from float16 to 4-bit. This hurts precise recall tasks (dual-citation, escalation rules) and can flip borderline pentest answers.

2. **System prompt tokenization** — Ollama's Modelfile injects the system prompt with its own template. The training-time eval uses the BERU_SYSTEM_PROMPT constant from beru_eval_runner.py directly. Small formatting differences can shift responses.

3. **Temperature** — Ollama default is 0.8. Training-time eval used 0.0 (greedy). Stochastic generation helps some knowledge questions (POA&M gets more creative completions) but hurts pentest (model more likely to add preamble that triggers fail_indicator keywords).

## What this means for the next experiment

- **KB improvement (+6.7pp)** is likely temperature-driven, not real — greedy eval is more conservative.
- **PB regression (-13.6pp)** is partially temperature-driven but may also reflect that beru:v1.6's adversarial training overfit to a specific greedy decoding pattern that fails under sampling.
- **Next step**: eval with explicit `temperature=0.0` in Ollama to isolate quantization from temperature effects.

## Action items

- [ ] Re-run with `--temperature 0.0` via Ollama API override and log as exp-013b
- [ ] Add serving-eval as a required gate step before promotion (not just training-time eval)
- [ ] Track serving gap per experiment going forward
