# What I Built Here — CrewAI for AI Governance Workflows

## The Core Idea

Most AI governance work is already a workflow:

- gather evidence
- compare it against a control
- identify the gap
- write the finding
- route the risk to the right owner
- document the decision

I built those playbooks as CrewAI agentic workflows.

The key design decision: **deterministic Python does the collection, LLM agents do the judgment.**

Collectors read files, call APIs, run pipeline stages, and normalize the output to structured JSON. Agents get that pre-digested evidence and do the reasoning — quality review, risk classification, control mapping, gap analysis, report drafting. Token cost stays low. Failures are diagnosable. Outputs are inspectable.

---

## What's Running

| Crew | What it automates |
|------|------------------|
| `beru/crews/beru_audit` | NIST 800-53 finding → 9-field structured audit output |
| `beru/crews/ssp_to_poam` | SSP narrative → SAR gap analysis → POA&M draft |
| `beru/crews/ac-access-control` | Access control evidence → AC family findings |
| `beru/crews/au-logging-maturity` | Log config review → AU family maturity assessment |
| `beru/crews/icam-m24-04` | ICAM posture → identity control gap findings |
| `beru/crews/ai-safety-m23-07` | AI system inputs → NIST AI RMF + 800-53 dual-citation findings |
| `beru/crews/zt-zero-trust` | ZT architecture evidence → SC/AC gap findings |
| `rag_ingestion` | RAG prep batch → quality review → labeling → routing → report |
| `synthetic_pipeline` | JSA security findings → ChatML training examples for BERU |

All BERU crews call BERU-AI (FastAPI :8088 → Ollama :11434). CrewAI on :8089 is the orchestration layer.

---

## The Architecture

```
deterministic collectors (pure Python, no LLM)
    read files / call APIs / run pipeline stages
    normalize to structured JSON state
          ↓
CrewAI agents (LLM judgment)
    quality review / semantic labeling
    risk classification / control mapping
    gap analysis / report drafting
          ↓
structured output (JSON + markdown)
    inspectable, challengeable, auditable
```

This keeps the LLM focused on what it's actually good at. It also means when something fails, you know immediately whether the problem is in the collector (deterministic, easy to debug) or the agent (reasoning, harder to debug).

---

## Honest Maturity

**What's solid:**
- Architecture pattern is real and consistent across all crews
- Collectors are deterministic and tested (`8-tests/test_rag_ingestion_crew.py`)
- Output contracts enforced by Pydantic schemas (`beru/schemas.py`)
- CLI works: `gp-crewai-beru audit "..."`, `gp-crewai-rag-prep`, `gp-crewai-synthetic`
- CrewAI telemetry disabled for clean test runs

**What's still being built:**
- BERU model behind the crews hasn't cleared the 70% eval gate yet (at 34.1% KB, 63% PB after 15 experiments)
- More automated tests for BERU crew outputs
- Run versioning and corpus versioning
- Stronger evaluation of agent output quality

---

## Demo Flow

If you want to walk someone through the code:

1. Start with this README — architecture pattern
2. `rag_ingestion/collectors.py` — the deterministic side
3. `rag_ingestion/agents.py` — the judgment-agent side
4. `beru/crews/ssp_to_poam.py` — a governance workflow end to end
5. `beru/crews/ai-safety-m23-07/manifest.yaml` — how a playbook becomes a crew config
6. `beru/schemas.py` — output contracts that enforce what BERU can produce

---

## One-Sentence Version

Built a CrewAI orchestration layer that turns AI governance and security playbooks into deterministic evidence collectors plus LLM judgment agents — covering RAG prep, BERU compliance review, SSP-to-POA&M generation, and training data quality workflows.
