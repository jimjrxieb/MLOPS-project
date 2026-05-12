# BERU Capstone Curriculum

> Goal: Build BERU — a production GRC analyst agent — as the capstone that lands one of the four target roles.
> Read the job requirements first: `jobdescriptions.md`

Every module has a **learn** phase and a **build** phase. The learn phase is concepts and tools. The build phase is a concrete artifact that goes in the BERU demo.

## How to Use This

**Read the lesson first, then do the build.** Each module has a lesson file with definitions, analogies, what to look for, and troubleshooting. The lesson is in `docs/lessons/`. After you read it, come back here for the build goal.

| Module | Lesson | Status |
| --- | --- | --- |
| M0 | [Python for AI Engineering](lessons/M0-python-for-ai-engineering.md) | |
| M1 | [LLM Fundamentals](lessons/M1-llm-fundamentals.md) | |
| M2 | [RAG Architecture](lessons/M2-rag-architecture.md) | |
| M3 | [Fine-Tuning](lessons/M3-fine-tuning.md) | |
| M4 | [Agentic Systems](lessons/M4-agentic-systems.md) | |
| M5 | [MLOps and Production](lessons/M5-mlops-and-production.md) | |
| M6 | [Domain: GRC and AI Security](lessons/M6-domain-grc-ai-security.md) | |
| M7 | [Commercial AI Strategy](lessons/M7-commercial-ai-strategy.md) | |
| M8 | [Capstone](lessons/M8-capstone.md) | |

Mark each module done in the Status column when you've completed the build goal and can answer the 3PAO question at the bottom of the lesson.

---

## Prerequisites — Before Module 0

You need these before starting. They are not modules — they are table stakes.

| Skill | How to confirm you have it |
| --- | --- |
| Python 3.10+ basics | Can write a function, read/write JSON, use pathlib |
| Git + GitHub | Can commit, branch, open a PR |
| Docker basics | Can write a Dockerfile, run a container |
| Linux command line | Can navigate, pipe commands, read man pages |
| VS Code or equivalent | Can run code, use a terminal, install extensions |

If anything above is missing, fix it first. Everything else builds on these.

---

## Module 0 — Python for AI Engineering

**What the roles want:** Production Python. Not notebooks. Real code that handles errors, validates input, and ships.

**What you build:** `tools/gap-to-poam.py` — already exists. Review and harden it. Add type hints, input validation, and a proper CLI with `argparse`.

**Learn:**
- Type hints and `mypy`
- `pathlib` over `os.path`
- `dataclasses` and `pydantic` for structured data
- `argparse` for CLI tools
- `pytest` — fixtures, parametrize, mocking
- `logging` module (not print)
- Context managers — always close what you open

**Build goal:** Take a working script and harden it to production standard. Running `mypy tools/gap-to-poam.py` returns zero errors. Running `pytest` against it hits ≥80% coverage.

**Evidence for interviews:** "I took an existing audit automation script and brought it to production standard — type hints, validated input, CLI interface, 80% test coverage."

---

## Module 1 — LLM Fundamentals

**What the roles want:** Working knowledge of GenAI tools. OpenAI/Anthropic API experience. Prompt engineering.

**What you build:** BERU system prompt — `GP-MODEL-OPS/BERU-AI/Modelfile_beru3b`. The persona prompt that makes LLaMA 3.2-3B behave as a NIST-800-53 + AI RMF GRC analyst.

**Learn:**
- How LLMs work at the token level — context window, temperature, top-p
- Prompt engineering patterns: role prompting, few-shot examples, chain of thought, structured output
- OpenAI and Anthropic APIs — both. They are near-identical. Learn one, know both.
- Structured output — JSON mode, function calling, response schemas
- System prompt design — how to lock a model to a specific persona and output format
- Token economics — cost vs context window vs model capability

**Build goal:** A system prompt that makes any LLM respond as BERU. Inputs: scanner output or control question. Outputs: structured finding in 9-field format (FINDING, CONTROL, STATUS, EVIDENCE REVIEWED, EVIDENCE GAP, RISK, CONTROL OWNER, POA&M ITEM, CISO SUMMARY). Test it with the Anthropic API — prove it produces consistent structured output across 10 different inputs.

**Evidence for interviews:** "I designed a system prompt that locks LLaMA 3.2-3B to a dual-framework GRC analyst persona (NIST 800-53 + AI RMF) and produces structured compliance findings in a defined 9-field format with dual citation."

---

## Module 2 — RAG Architecture

**What the roles want:** RAG implementation, embeddings, semantic search, vector databases.

**What you build:** BERU's knowledge base — ChromaDB collection `beru-nist-800-53` populated with the NIST-800-53 controls and playbooks from `GP-CONSULTING/NIST-800-53/`.

**Learn:**
- Embedding models — what they produce, why dimensions matter, nomic-embed-text vs OpenAI ada-002
- Vector similarity — cosine similarity, dot product, L2 distance
- ChromaDB — collections, persistent storage, query with embedding function
- Chunking strategy — why chunk size matters, overlap, metadata
- Retrieval pipeline — embed query → similarity search → inject into context
- Reranking — cross-encoder reranking for precision

**Build goal:** A RAG pipeline that:
1. Reads all control files from `GP-CONSULTING/NIST-800-53/controls/`
2. Chunks them with metadata (family, control ID, section)
3. Embeds with nomic-embed-text
4. Stores in ChromaDB
5. Exposes a `retrieve_control(query: str) -> list[dict]` function

Prove it works: query "least privilege access" → returns AC-6 content. Query "network boundary protection" → returns SC-7 content.

**Evidence for interviews:** "I built a RAG pipeline over 50+ NIST-800-53 controls — chunked with metadata, embedded with nomic-embed-text, stored in ChromaDB, with semantic retrieval that grounds BERU's analysis in specific control text."

---

## Module 3 — Fine-Tuning

**What the roles want:** LLM fine-tuning. LoRA/QLoRA. Data curation. Evaluation.

**What you build:** BERU training dataset — 200+ annotated GRC analyst examples in `GP-MODEL-OPS/BERU-AI/training-data/`. Format: ChatML. Input: scanner output or control question. Output: correct BERU 9-field finding.

**Learn:**
- LoRA — what r and alpha control, when to increase them
- QLoRA — 4-bit quantization, memory vs precision trade-off
- Unsloth — why it's faster than vanilla HuggingFace for LoRA on LLaMA
- Data quality gates — format, scope, dedup, min chunk size
- Evaluation design — what makes a good eval question for a compliance model
- Train/eval split — holdout strategy, no contamination

**Build goal:**
1. 200+ training examples in ChatML format, passed through `8-tests/test_data_quality.py`
2. One training run with Unsloth on LLaMA 3.2-3B-Instruct, r=32/alpha=64 (see D-009)
3. Eval suite: 30 questions across 5 GRC analyst domains (vuln triage, monitoring, NIST mapping, IR forensics, risk reporting), with MITRE ATLAS coverage for AI scenarios
4. Before/after comparison: **base LLaMA 3.2-3B + RAG (the brain baseline)** vs fine-tuned BERU score on the eval — fine-tune only ships if it beats the baseline

**Evidence for interviews:** "I curated a 200-example GRC analyst training dataset, established a brain baseline by running the eval against base LLaMA 3.2-3B + RAG, fine-tuned with LoRA r=32 using Unsloth, and measured the lift over baseline on compliance-specific eval questions."

---

## Module 4 — Agentic Systems

**What the roles want:** Agents, LangChain/LangGraph, tool use, autonomous reasoning loops.

**What you build:** BERU agentic loop — `GP-MODEL-OPS/BERU-AI/agent.py`. Takes a scanner output file as input. Autonomously:
1. Identifies which NIST control family applies
2. Retrieves relevant controls from ChromaDB (Module 2)
3. Produces BERU findings for each affected control
4. Routes findings to appropriate POA&M template

**Learn:**
- LangGraph — StateGraph, nodes, edges, conditional routing
- Tool use — how to give an LLM callable functions
- Playbook-as-brain pattern — the agent reads a playbook, follows it, doesn't improvise
- Memory — conversation memory vs. retrieved context vs. working state
- Error handling in agents — what happens when a tool call fails
- Human-in-the-loop — when to pause and ask vs. proceed autonomously

**Build goal:** `python3 BERU-AI/agent.py --input /path/to/trivy-output.json` produces:
- A structured findings list (JSON)
- A POA&M draft (Markdown)
- A CISO summary paragraph (text)

All three outputs sourced from the playbooks, not hallucinated. The agent routes through the correct family playbook from `GP-CONSULTING/NIST-800-53/playbooks/`.

**Evidence for interviews:** "I built an agentic loop that takes Trivy scan output, maps findings to NIST-800-53 controls via RAG, and produces auditor-ready POA&M and CISO summary — following playbooks rather than improvising."

---

## Module 5 — MLOps and Production

**What the roles want:** MLflow, Docker, Kubernetes, CI/CD, monitoring.

**What you build:** BERU serving stack — Ollama Modelfile deployed locally, FastAPI endpoint at `/api/beru`, MLflow experiment tracking for eval runs.

**Learn:**
- Ollama — Modelfile format, `FROM`, `SYSTEM`, `PARAMETER`, `ollama create`
- FastAPI — routing, request/response models with Pydantic, async handlers
- Docker — multi-stage builds, image layers, `.dockerignore`
- Kubernetes basics — Deployment, Service, ConfigMap, resource limits, health probes
- MLflow — experiments, runs, params, metrics, artifact logging
- GitHub Actions — workflow YAML, jobs, steps, secrets
- Monitoring basics — what to log, how to alert on quality drift

**Build goal:**
1. `BERU-AI/Modelfile_beru3b` — registered with Ollama as `beru:v1.0`
2. FastAPI route `/api/beru` added to `GP-INFRA/GP-API/routes/beru.py`
3. MLflow experiment `beru-eval` with tracked runs for each eval against the 30-question suite
4. GitHub Actions workflow `.github/workflows/beru-eval.yml` that runs the eval suite on every push to `main`

**Evidence for interviews:** "BERU runs as beru:v1.0 via Ollama, exposed through FastAPI, with MLflow tracking every eval run and GitHub Actions enforcing eval gates on every push."

---

## Module 6 — Domain: GRC and AI Security

**What the roles want:** Domain expertise in GRC, AI security governance, NIST frameworks.

**What you build:** BERU control coverage map — a document showing which NIST-800-53 controls BERU can assess, what tools it uses as evidence, and what it cannot assess (honest gap documentation).

**Learn:**
- NIST 800-53 Rev 5 — the 20 families, high-impact controls, control enhancements
- POA&M structure — weakness, scheduled completion, milestones, resources, responsible officer
- SSP narrative quality — bad vs good vs great (Module 3 in the playbooks)
- NIST AI 600-1 — the AI-specific risk framework, how it intersects with 800-53
- FedRAMP Moderate — the 325 controls and what changes at Moderate vs Low
- Risk rank system — E/D/C/B/S, what each means, what authority level each requires
- 3POA audit methodology — six phases, evidence interview, live validation

**Build goal:** `GP-CONSULTING/NIST-800-53/BERU-COVERAGE.md` — a one-page table:
- Column 1: Control ID
- Column 2: BERU can assess (yes/partial/no)
- Column 3: Primary evidence tool (kubectl, Trivy, kube-bench, Prowler, etc.)
- Column 4: Gap / what requires human judgment

This is the honest coverage document. The 20% gap list is as important as the 80% coverage.

**Evidence for interviews:** "I documented exactly which NIST-800-53 controls BERU can assess autonomously, which require human judgment, and why — the same honest gap analysis we give clients."

---

## Module 7 — Commercial AI Strategy

**What the roles want:** Commercial AI strategy literacy. Deployment models. Risk classification. Executive communication.

**What you build:** BERU CISO briefing template — `GP-CONSULTING/NIST-800-53/playbooks/04-ciso-briefing.md` already exists. Extend it with a one-page executive summary template that answers three questions with real numbers.

**Learn:**
- Six commercial AI deployment models (A-F): Consumer, Integrator, Developer, Agentic, Decision Support, Embedded
- EU AI Act risk tiers — prohibited, high-risk, limited-risk, minimal-risk
- NIST AI 600-1 — generative AI-specific risks (hallucination, data poisoning, prompt injection)
- AI governance frameworks — what boards ask, what regulators look for
- Executive communication — no NIST IDs, no jargon, risk in dollars and business impact
- AI ROI framing — how to translate "we reduced manual audit time" into business value

**Build goal:** A one-page CISO briefing that a non-technical executive can read in 3 minutes and understand:
1. What is the current compliance posture (percentage, not letter grade)
2. What are the top 3 risks (in business terms, not control IDs)
3. What is the 90-day remediation plan (concrete, with owners)

Test it: show the template to someone non-technical and ask if they understand it. If they ask "what is AC-6?" you failed.

**Evidence for interviews:** "I built executive briefing templates that translate NIST compliance findings into business risk language — the same deliverable PwC and Deloitte produce at the end of an engagement."

---

## Module 8 — Capstone: BERU End-to-End

**What the roles want:** Production AI agents end-to-end. Full SDLC. Evidence of ownership from requirements to shipping.

**What you build:** The complete BERU demo — a 5-minute walkthrough that shows all seven prior modules working together.

### Demo Flow

```
1. Input: Trivy scan output from a real cluster (GP-PROJECTS/01-instance/slot-3/)
2. BERU agent reads the scan → routes to SI-2 (Flaw Remediation) playbook
3. RAG retrieves SI-2 control text from ChromaDB
4. LLM produces structured finding in 9-field format
5. Agent writes POA&M item to disk
6. Agent produces CISO summary paragraph
7. MLflow logs the eval run
8. GitHub Actions shows the eval passed
```

The entire flow runs from one command:
```bash
python3 GP-MODEL-OPS/BERU-AI/agent.py \
  --input GP-S3/6-seclab-reports/cybersec-evidence/sample-trivy.json \
  --output /tmp/beru-demo-output/
```

### Capstone Checklist

| Component | Module | Status |
| --- | --- | --- |
| Hardened CLI script (`gap-to-poam.py`) | M0 | |
| System prompt (Modelfile_beru3b) | M1 | |
| RAG pipeline (beru-nist-800-53 collection) | M2 | |
| Training dataset (200+ examples) | M3 | |
| Fine-tuned BERU model (`beru:v1.0`) | M3 | |
| Agentic loop (`agent.py`) | M4 | |
| FastAPI endpoint (`/api/beru`) | M5 | |
| MLflow eval tracking | M5 | |
| GitHub Actions eval gate | M5 | |
| Coverage map (`BERU-COVERAGE.md`) | M6 | |
| CISO briefing template | M7 | |
| End-to-end demo (one command) | M8 | |

### Interview Story

When they ask "tell me about a project":

> "I built BERU — a dual-framework GRC analyst agent (NIST 800-53 + NIST AI RMF) running on LLaMA 3.2-3B fine-tuned with LoRA. It ingests scanner output from Trivy, kube-bench, and Prowler — and AI-specific tooling like garak and promptfoo — maps findings to controls via RAG over NIST 800-53 + AI RMF + MITRE ATLAS documents in ChromaDB, and produces structured POA&M and CISO briefings with dual citation. The whole pipeline runs in a LangGraph agentic loop, served through FastAPI, with MLflow tracking every eval run. I baseline-tested the model before fine-tuning so the post-fine-tune lift is measurable. Same methodology GuidePoint and Deloitte use on enterprise engagements — open source, end to end, runs on a laptop."

That story covers every checkmark in the cross-role skills matrix.

---

## Module Sequence and Timing

| Module | Focus | Estimated Time | Gate to Next |
| --- | --- | --- | --- |
| M0 | Python hardening | 1 week | `mypy` clean, ≥80% coverage |
| M1 | LLM fundamentals | 1 week | System prompt produces structured JSON on 10/10 inputs |
| M2 | RAG | 1 week | Semantic retrieval returns correct controls |
| M3 | Fine-tuning | 2 weeks | BERU beats base LLaMA on eval suite |
| M4 | Agents | 1 week | End-to-end demo on one scanner input |
| M5 | MLOps | 1 week | CI gate passes, endpoint live |
| M6 | Domain | 1 week | Coverage map complete with honest gaps |
| M7 | Strategy | 3 days | CISO briefing passes the non-technical reader test |
| M8 | Capstone | 1 week | One-command demo, all components wired |

**Total: ~10 weeks.** Start applying at M5. Apply hard at M8 completion.

---

## Cross-Module Evidence Map

How each module satisfies each job's requirements:

| Job Requirement | Primary Module | Secondary | Artifact |
| --- | --- | --- | --- |
| Python (production) | M0 | M4, M5 | `gap-to-poam.py`, `agent.py` |
| LLM/GenAI fundamentals | M1 | M3 | `Modelfile_beru3b`, system prompt |
| RAG + vector databases | M2 | M4 | ChromaDB collection, `retrieve_control()` |
| Fine-tuning (LoRA) | M3 | — | Training dataset, eval before/after |
| Agents / agentic arch | M4 | M5 | `agent.py`, LangGraph StateGraph |
| MLOps + CI/CD | M5 | — | MLflow runs, GitHub Actions workflow |
| Docker + Kubernetes | M5 | — | Dockerfile, K8s manifests |
| Domain expertise (GRC) | M6 | M7 | `BERU-COVERAGE.md`, control families |
| Commercial AI strategy | M7 | M6 | CISO briefing template |
| Executive communication | M7 | M8 | CISO briefing (no jargon, real numbers) |
| Testing + code quality | M0 | M5 | pytest, mypy, CI gate |
| OpenAI/Claude API | M1 | — | API calls in system prompt testing |

Every row in the `jobdescriptions.md` cross-role matrix is covered.
