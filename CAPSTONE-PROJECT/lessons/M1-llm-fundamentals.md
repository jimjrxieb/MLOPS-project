# M1 — LLM Fundamentals

> **Goal:** Understand how LLMs work well enough to use them reliably, not just hope they work.
> **Build:** BERU system prompt — already exists in `BERU-AI/modelfiles/Modelfile_beru3b`. Understand every line.
> **Gate:** System prompt produces correct 9-field output on 10 varied inputs via the Anthropic API.

---

## The Mental Model

An LLM is a function. Input: text (a "prompt"). Output: text (a "completion"). Everything else — agents, RAG, tools, fine-tuning — is just clever ways to structure that input and parse that output.

The tricky part is that the function is stochastic (random within bounds) and the "logic" is embedded in billions of weights, not readable code. You can't step through it with a debugger. You understand it by understanding its inputs.

**The analogy:** LLMs are like very well-read interns. They've read everything on the internet. They can produce plausible-sounding output on almost any topic. But they have no memory between conversations, they sometimes confabulate confidently, and they do exactly what you ask — including producing bad output if you ask badly.

---

## Concept 1 — Tokens and Context Windows

### Tokens
LLMs don't read words. They read **tokens** — roughly 3-4 characters each for English. "compliance" is one token. A 100-page SSP might be 30,000 tokens.

Why it matters:
- **Cost**: API calls are priced per token (input + output)
- **Speed**: More tokens = slower response
- **Memory**: The model can only "see" what fits in the context window at once

### Context window
This is the maximum number of tokens the model can process at once — its working memory. Older models: 4,096 tokens. Claude Sonnet 4.6: 200,000 tokens. LLaMA 3.2-3B (BERU's base): 128,000 tokens.

**The analogy:** Context window is desk space. You can only work with what's on the desk. A huge document that doesn't fit has to be summarized or chunked before it goes on the desk. This is exactly why RAG (Module 2) exists — instead of dumping all 800-53 controls into every prompt, you retrieve only the 3-4 relevant ones.

### Temperature
Controls randomness. `temperature=0` is deterministic (same input → same output every time). `temperature=1` is more creative/varied.

For BERU: use `temperature=0` or very low (0.1). Compliance findings must be consistent, not creative.

---

## Concept 2 — The System Prompt

The system prompt is what turns a generic LLM into BERU. It runs before every user message and sets the rules the model follows.

Open `BERU-AI/modelfiles/Modelfile_beru3b`. The `SYSTEM """..."""` block is the system prompt. Read these parts:

```
YOUR ROLE:
  GRC analyst. Your output is findings, POA&M items, SSP narratives, and CISO briefings.
  When the finding is about an AI system, you apply BOTH frameworks.
  You always cite the specific control and the specific evidence. Never vague. Never hallucinated.
```

This is **role prompting** — the most important prompt engineering technique. You're not asking the model to "help with compliance." You're telling it that it IS a compliance analyst. That persona change shapes every response.

Then:
```
YOUR OUTPUT FORMAT — for every finding:
  1. FINDING: one sentence describing what is wrong
  2. CONTROL: NIST 800-53 control ID + enhancement
  ...
  10. CISO SUMMARY: one paragraph, business risk language, no NIST IDs
```

This is **structured output prompting** — you're telling the model exactly what format to use. Without this, the model might answer in prose, bullet points, JSON, or whatever it feels like. With this, every response is predictable and parseable.

### The three layers of a prompt
```
System prompt   → who you are, what you do, what format to use
User message    → the specific task ("assess this Trivy output")
Context/RAG     → the relevant knowledge (control text, past findings)
```

BERU uses all three every time it runs.

---

## Concept 3 — OpenAI and Anthropic APIs

Both APIs use the same HTTP shape. If you learn one, you know both.

```python
# OpenAI
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are BERU..."},
        {"role": "user", "content": "Assess this finding: ..."},
    ],
    temperature=0.1,
)
text = response.choices[0].message.content

# Anthropic — almost identical
import anthropic
client = anthropic.Anthropic(api_key="sk-ant-...")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system="You are BERU...",
    messages=[
        {"role": "user", "content": "Assess this finding: ..."},
    ],
)
text = response.content[0].text
```

The pattern: `client → create → model + messages → parse response`. Same everywhere.

### The GP-API uses both
Older JADE API routes used hosted-model calls for high-rank review decisions; BERU's current focus is local inference plus HITL routing.
`BERU-AI/providers/ollama.py` — uses Ollama for local model serving.

Both follow the same message array format.

---

## Concept 4 — Why LLMs Hallucinate (and how to fight it)

Hallucination = the model produces text that sounds correct but is wrong. It doesn't "know" it's wrong — it's predicting plausible next tokens, not retrieving facts.

**Why BERU is especially vulnerable:** NIST control IDs are specific (`AC-6(5)`, not `AC-5`). The model can easily predict a plausible-looking but wrong control ID. That's why `validate_control_id()` and `validate_ai_rmf_id()` exist in `BERU-AI/core/nist_mapper.py`.

**How we fight it in BERU:**
1. **RAG** (Module 2) — inject the actual control text so the model has it in context, not just weights
2. **Structured output** — the format forces the model to cite evidence, not just assert
3. **Hard stops in system prompt** — "NEVER cite a control ID you cannot find in your knowledge base"
4. **Validation** — `validate_control_id()` catches bad IDs before they leave the pipeline
5. **EVIDENCE REVIEWED field** — model must cite a file path or tool output, not vague assertions

```python
# nist_mapper.py — validation runs on every BERU output
def validate_control_id(self, control_id: str) -> bool:
    match = re.match(r"^([A-Z]{2})-\d+$", control_id)
    if not match:
        return False
    family = match.group(1)
    return family in self.control_families  # AC, AU, CA, CM... etc.
```

---

## Concept 5 — Modelfile Format (Ollama)

When BERU runs locally via Ollama, the system prompt lives in the Modelfile. Key directives:

```
FROM llama3.2:3b                 ← base model (swap to ./beru-llama3b-v1.0.gguf after fine-tuning)
TEMPLATE """..."""               ← how to format the prompt for THIS model's tokenizer
SYSTEM """..."""                 ← the system prompt (runs before every user message)
PARAMETER temperature 0.1        ← sampling params
PARAMETER stop "<|eot_id|>"     ← stop tokens (model-specific — get these wrong = garbage output)
```

The `TEMPLATE` block is critical and model-specific. LLaMA 3.1 and 3.2 share the same chat template (`<|start_header_id|>` tokens). Mistral uses `[INST]`. Using the wrong template = the model never "sees" your system prompt correctly.

**Registering a new model:**
```bash
ollama create beru:local -f BERU-AI/modelfiles/Modelfile_beru3b
ollama run beru:local
# Test: "Assess this finding: Trivy found CVE-2024-1234 in base image"
```

---

## Troubleshooting M1

| Symptom | Cause | Fix |
|---------|-------|-----|
| Model ignores output format | System prompt not loaded | Check Modelfile TEMPLATE — wrong stop tokens mean system prompt never closes |
| Wrong control IDs in output | Hallucination on specific IDs | Add RAG (M2) — inject actual control text instead of relying on weights |
| Same wrong answer every time | `temperature=0` + bad prompt | Fix the prompt; low temp locks in whatever is most likely |
| `rate_limit_error` | Too many API calls | Add `time.sleep(1)` between calls; use batch endpoints where available |
| `context_length_exceeded` | Too much input | Chunk or summarize the scanner output before sending |
| Ollama returns empty string | Wrong stop tokens in Modelfile | Check the exact stop tokens for LLaMA 3.x: `<|eot_id|>`, `<|start_header_id|>` |
| `ollama: model not found` | Model not registered | Register the local Modelfile or use the Docker Compose `model-init` service |

---

## What You Build

The BERU system prompt is already written in `Modelfile_beru3b`. Your job in M1 is to understand it, not rewrite it.

**Exercise:**
1. Take the system prompt. Call the Anthropic API directly (Python, 10 lines).
2. Send 10 different scanner outputs as user messages.
3. Check: does every response have all 10 fields? Is STATUS always PASS/PARTIAL/FAIL?
4. Find one where it hallucinated a control ID. Run it through `validate_control_id()`.

This exercise is the M1 gate. You're not building new code — you're proving you understand what the system prompt does and where it fails.

**3PAO question this answers:** "How does BERU know what format to output?"
Your answer: "The system prompt defines a 10-field structured format. Every output is validated against `validate_control_id()` before it leaves the pipeline."

---

## Control Traceability

> When an auditor asks "how do you know BERU isn't hallucinating control IDs?" — point here.

**NIST 800-53:**

| Control | What it maps to in M1 | Audit answer |
|---------|----------------------|--------------|
| **SI-10** — Information Input Validation | `validate_control_id()` checks every control ID in BERU's output against the 20 real NIST families before the finding is written | "Every control ID BERU produces is validated against the NIST 800-53 family list. Hallucinated IDs are caught at output, not discovered by an auditor." |

| **SI-7** — Software, Firmware, and Information Integrity | The 10-field structure check verifies output integrity — a finding missing EVIDENCE GAP or CISO SUMMARY is flagged | "BERU's output format is verified programmatically. A structurally incomplete finding is rejected before it reaches the evidence package." |

| **SA-11** — Developer Testing and Evaluation | The 10-scanner exercise in `m1_api_exercise.py` is developer testing of the system prompt — 10 inputs, automated field check | "We tested the system prompt against 10 representative scanner inputs before treating BERU as functional. Results are logged." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **MEASURE-2.5** — AI system is demonstrated to be valid and reliable | The M1 exercise measures whether the 3B model holds the 10-field format across diverse inputs | "BERU's reliability is measured before deployment. The 10-scanner test is the baseline. Known gaps (format instability on AI-specific inputs) are documented." |

| **MAP-2.3** — AI risks and limitations are communicated | M1 surfaced three failure modes in `llama3.2:3b`: AI RMF cited for non-AI findings, tool names as control owners, past dates in POA&M items | "We documented three specific failure modes of the base 3B model in M1. These are the training gaps M3 addresses." |
