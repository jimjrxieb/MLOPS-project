# BERU Capstone Project

> Build a junior GRC analyst agent that a 3PAO auditor can interrogate and trust.
> Current status: working prototype with real MLOps scaffolding; the model is
> still below the autonomous promotion gate.

Start here:

- `STATUS.md` — current maturity, implemented evidence, and known gaps
- `DEMO.md` — reviewer-facing demo runbook
- `beru-design-decisions.md` — control-traceable engineering decisions

## Three Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| **Instructor / Auditor** | Claude Code | Assigns modules, asks 3PAO-style "why did you do it like this?" questions, enforces framework traceability |
| **MLOps Engineer** | You | Builds BERU — data pipelines, fine-tuning, RAG, agent loop, serving |
| **Capstone Project** | BERU | Junior GRC analyst agent — reads scanner output, maps to controls, writes findings, escalates to humans |

## Two Frameworks, Both Required

Every design decision in BERU traces to one or both:

| Framework | Scope | Why Both Matter |
|-----------|-------|-----------------|
| **NIST 800-53 Rev 5** | The IT system BERU operates in and assesses | Controls the K8s cluster, the API, the data pipeline |
| **NIST AI RMF (AI 600-1)** | BERU itself as an AI system | BERU is an AI making compliance decisions — those decisions need governance |

A 3PAO auditor will ask both sets of questions. You need answers for both.

## The "Why Did You Do It Like This?" Question

For every major design decision, you must be able to answer:

> "Which NIST control or AI RMF subcategory required this, and what evidence do you have that it's implemented?"

See `beru-design-decisions.md` for the full decision log.

## Directory Structure

```
CAPSTONE-PROJECT/
├── README.md                           → You are here
├── STATUS.md                           → Current maturity and promotion status
├── DEMO.md                             → Reproducible review/demo path
├── beru-design-decisions.md            → Why each design choice maps to a control
├── frameworks/
│   ├── nist-ai-600-1/
│   │   ├── ai-rmf-govern.md            → GOVERN function subcategories
│   │   ├── ai-rmf-map.md               → MAP function subcategories
│   │   ├── ai-rmf-measure.md           → MEASURE function subcategories
│   │   └── ai-rmf-manage.md            → MANAGE function subcategories
│   └── crosswalk/
│       └── 800-53-to-ai-rmf.md         → 800-53 control ↔ AI RMF subcategory mapping
├── intake/
│   └── ai-system-registration.md       → Form: what is this AI system and what risk tier?
└── templates/
    ├── ai-inventory-register.md         → Track all AI systems in the environment
    ├── ai-risk-assessment.md            → Risk assessment output format (AI systems)
```

## Auditor Questions You Must Be Able to Answer

These come up in every FedRAMP, NIST-based, or AI governance audit:

**On the system design:**
- "What AI system is this and who authorized its deployment?" → `intake/ai-system-registration.md`
- "What risk tier is this AI and what is your justification?" → `templates/ai-risk-assessment.md`
- "Where is your AI system inventory?" → `templates/ai-inventory-register.md`

**On the agent behavior:**
- "How does BERU handle a finding it can't classify?" → `BERU-AI/agent/graph.py`, `BERU-AI/agent/nodes.py`
- "Who reviews BERU's B/S-rank findings before action is taken?" → HITL workflow, MANAGE-2.2
- "What prevents BERU from hallucinating control IDs?" → RAG grounding, MEASURE-2.5

**On the ML pipeline:**
- "What data was used to train this model and where did it come from?" → MAP-2.3, experiment notes, model cards, data lineage manifest
- "How do you know the model is performing correctly?" → MEASURE-2.7, MLflow tracking, eval gate, `5-experiments/COMPARISON.md`
- "What happens when the model drifts or degrades?" → MANAGE-4.1, eval gate, retraining trigger

**On the output:**
- "Show me a finding BERU produced and trace it back to the scanner evidence" → evidence packager output
- "How do you ensure BERU's POA&M items are accurate?" → human review before any B/S-rank item is filed
- "Is BERU's output admissible as audit evidence?" → depends on SSP narrative quality — see `BERU-AI/knowledge/nist-800-53/playbooks/03-produce-ssp-narrative.md`
