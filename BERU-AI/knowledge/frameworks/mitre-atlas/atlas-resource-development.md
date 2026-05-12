# MITRE ATLAS — Resource Development (TA0003)

> Resource development is the supply-chain reconnaissance phase: attacker acquires public AI artifacts, builds tooling, identifies which targets use which models. From a defender perspective, this is where you ask "what AI artifacts have I downloaded and do I trust them?"
> Source: MITRE ATLAS v4.7 + NIST 800-53 SR controls
> BERU role: BERU verifies that AI systems she assesses have provenance evidence for every external artifact.

---

## What This Tactic Covers

Most enterprise AI systems are built on third-party components: base models from HuggingFace, embedding models from cloud providers, datasets from public hubs, fine-tuning libraries from open source. Each of those is an attack surface. Resource development covers the techniques attackers use to *prepare* attacks against this supply chain.

**3PAO question this answers:** "Which third-party AI components does this system depend on, and how do you verify their integrity at intake?"

---

### AML.T0011
**Technique:** Acquire Public ML Artifacts
**Tactic:** Resource Development (TA0003)
**OWASP LLM:** LLM05 (Supply Chain Vulnerabilities)
**In plain English:** Attacker downloads the same public ML artifacts (base models, embedding models, libraries) that defenders use, in order to study them and craft targeted attacks. From the *defender's* angle — this technique tells you to assume any public artifact you use has also been studied by attackers.

**Affects BERU directly: MEDIUM.** BERU uses three public artifacts: `llama3.2:3b` (base model), `nomic-embed-text:latest` (embedding model), and `unsloth` (fine-tuning library). Each is a supply-chain dependency.

**Detection signals (during intake):**
- Model pulled from a non-official registry or unsigned source
- Embedding model dimension or behavior inconsistent with documentation (could indicate substitution)
- Library version in `requirements.txt` doesn't match a verified release tag

**BERU compensating controls:**
- Modelfile pins `FROM llama3.2:3b` (Ollama official tag)
- `requirements.txt` pins exact versions for `chromadb`, `requests`, `pyyaml`
- Embedding dim assertion at ingest (768 or fail) — catches embedding model substitution
- Future hardening: SBOM (Software Bill of Materials) for the BERU stack

**Crosswalk:**
- AI RMF: MAP 4.1 (third-party component risks documented), MAP 2.2 (provenance)
- 800-53: SR-3 (supply chain controls), SR-4 (provenance), CM-8 (component inventory)
- OWASP LLM: LLM05

**Eval scenarios:**
- Knowledge: A vendor's AI system uses a base model from HuggingFace with no signed release. Map findings.
- Pentest agent: Swap the embedding model behind Ollama (e.g., to a 384-dim model) — does ingest abort with the dim assertion?

---

### AML.T0049
**Technique:** Exploit Public-Facing Application
**Tactic:** Initial Access (TA0005) — included here because the attack chain begins with public-facing AI APIs
**OWASP LLM:** LLM01 (Prompt Injection via API), LLM07 (Insecure Plugin Design)
**In plain English:** Attacker exploits a public-facing AI inference API to gain initial access to the AI system or the infrastructure behind it.

**Affects BERU directly: LOW** in current architecture (BERU doesn't expose a public API) — **HIGH** in the planned `/api/beru` FastAPI surface (M5 work). This is exactly why M5 deserves separate threat modeling.

**Detection signals:**
- Inference API receives requests with structural anomalies (prompts >> normal length, uncommon Unicode, repeated control characters)
- API logs show enumeration patterns (sequential model name probes, error-message harvesting)
- Inference latency or token usage spikes for individual requests

**BERU compensating controls (planned for M5):**
- Rate limiting at the FastAPI layer
- Input length cap (reject prompts > 4k tokens)
- Auth required (API key or mTLS)
- Output goes to filesystem, not back to the requester (limits info disclosure)

**Crosswalk:**
- AI RMF: MEASURE 2.7, MEASURE 2.10, GOVERN 1.2
- 800-53: AC-3 (access enforcement), SC-7 (boundary protection), SI-4 (system monitoring)
- OWASP LLM: LLM01, LLM07

**Eval scenarios:**
- Knowledge: An organization exposes their LLM API at `https://ai.example.com/v1/generate` with no auth. Map controls.
- Pentest agent: Once `/api/beru` exists, fuzz it with malformed JSON, oversized prompts, repeated requests.
