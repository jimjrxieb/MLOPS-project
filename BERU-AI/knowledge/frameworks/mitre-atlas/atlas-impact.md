# MITRE ATLAS — Impact (TA0012)

> Impact tactics describe the "so what" — DoS against the model, cost-harvesting, model theft, integrity violation. From the GRC angle, these are what makes the risk material to the business.
> Source: MITRE ATLAS v4.7 + OWASP LLM Top 10 + NIST 800-53 SC/SR controls
> BERU role: BERU translates impact-tactic findings into business-language POA&M items and CISO summaries.

---

## What This Tactic Covers

Most AI security frameworks treat "impact" as a collateral concern. For GRC analysis it's the most important phase — it's what determines the risk score, the POA&M priority, and whether the finding makes it to the CISO summary. Each impact technique maps cleanly to a 800-53 risk family.

**3PAO question this answers:** "What is the realistic worst-case business outcome if this AI system is compromised, and what controls reduce that outcome's likelihood?"

---

### AML.T0029
**Technique:** Denial of ML Service
**Tactic:** Impact (TA0012)
**OWASP LLM:** LLM04 (Model Denial of Service)
**In plain English:** Attacker submits inputs that exhaust the AI system's compute, memory, or context window. Patterns include extremely long prompts, recursive tool-call loops, prompt-amplification attacks, or queries that force expensive RAG retrievals.

**Affects BERU directly: MEDIUM** for any future `/api/beru` deployment, **LOW** for local agent-loop usage.

**Detection signals:**
- Inference latency spikes for individual requests (single request consumes >30s)
- Memory usage climbs without releasing between requests
- Tool-call loops exceed declared max iteration count
- RAG retrieval N is set very high (top_k > 50) on a single request

**BERU compensating controls (planned for M5):**
- Hard cap on prompt length (4k tokens default)
- Hard cap on agent iteration count (LangGraph max_steps = 8)
- Hard cap on RAG top_k (default 5, max 10)
- Rate limiting at FastAPI layer (per-IP and per-API-key)

**Crosswalk:**
- AI RMF: MEASURE 2.7 (security and resilience)
- 800-53: SC-5 (denial of service protection), SI-4 (system monitoring), CP-2 (contingency planning)
- OWASP LLM: LLM04

**Eval scenarios:**
- Knowledge: A client's AI service has no input length cap. Map AML.T0029 + LLM04 + SC-5.
- Pentest agent: Submit a 500k-token prompt to `/api/beru`. Verify rejection.

---

### AML.T0034
**Technique:** Cost Harvesting
**Tactic:** Impact (TA0012)
**OWASP LLM:** LLM04 (Model DoS — financial variant)
**In plain English:** Attacker forces the target to incur high inference cost — repeated expensive queries, prompts crafted to maximize output tokens, recursive tool calls. This is DoS against the *budget*, not the service.

**Affects BERU directly: LOW** locally (Ollama is free at the margin), **MEDIUM** for any cloud-API fallback.

**Detection signals:**
- Per-user or per-API-key inference cost exceeds expected baseline
- Output token count consistently maxed out (model generating to the limit on every request)
- Same user submits structurally similar requests at high frequency

**BERU compensating controls:**
- Local Ollama is the primary path — no per-token cost
- If a cloud-API fallback is added, hard daily/per-key cost limit at the gateway
- Output token limit (`num_predict=2000` default)

**Crosswalk:**
- AI RMF: MEASURE 2.7, GOVERN 1.5 (risk tolerance — cost as risk)
- 800-53: SC-5, SI-4, CP-2
- OWASP LLM: LLM04

**Eval scenarios:**
- Knowledge: A vendor's chatbot uses GPT-4 with no per-user cost cap. Map findings.
- Pentest agent: Run 100 high-output-token requests against BERU. Verify cost stays bounded.

---

### AML.T0044
**Technique:** Full ML Model Access
**Tactic:** Impact (TA0012) + Resource Development
**OWASP LLM:** LLM10 (Model Theft)
**In plain English:** Attacker obtains full read access to the model weights — either by extracting them via repeated inference queries (model extraction) or by gaining filesystem access to the GGUF file directly.

**Affects BERU directly: MEDIUM.** BERU's fine-tuned weights (when produced) are in `3-model-registry/`. Filesystem ACLs are the primary control. Inference-based extraction is harder for 3B+ models but not impossible with enough queries.

**Detection signals:**
- Filesystem access to `3-model-registry/` from unexpected processes
- Inference traffic from a single source exceeds 100k+ queries — suggests model-extraction attempt
- GGUF file checksum changes without a recorded promotion

**BERU compensating controls:**
- `3-model-registry/` permissions: `chmod 600` for GGUF files, owned by training service account (planned)
- Future hardening: cosign signature on every promoted GGUF
- Inference rate limit (M5) — caps the per-source query volume that enables extraction

**Crosswalk:**
- AI RMF: MEASURE 2.7, MAP 4.1
- 800-53: AC-3, AC-6, SC-28 (protection at rest), SR-4 (provenance)
- OWASP LLM: LLM10

**Eval scenarios:**
- Knowledge: A vendor's proprietary model is hosted on a shared filesystem with world-readable permissions. Map findings.
- Pentest agent: Attempt a model-extraction attack via repeated structured queries. Measure how many queries are needed before the rate limiter triggers.
