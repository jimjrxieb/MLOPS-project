# RAG Ingestion Prep Crew — Design Spec
**Date:** 2026-05-20  
**Status:** Approved  
**Author:** Jimmie / Claude Code

---

## Summary

Build the RAG ingestion prep crew for `2-rag-ingestion/02-preperation-factory/` and consolidate **all CrewAI/AI automation code** into a new top-level directory `GP-MODEL-OPS/crewai-mlops/`.

Two things happen in parallel:
1. **Reorganization:** Move existing crews (`synthetic-pipeline/crew/` and `BERU-AI/crew/`) into `crewai-mlops/` — one home for all CrewAI work.
2. **New crew:** Build the RAG ingestion prep crew inside `crewai-mlops/rag-ingestion/`.

---

## Reorganization: crewai-mlops/

### Before
```
GP-MODEL-OPS/
  0-data-lab/synthetic-pipeline/crew/    ← synthetic pipeline crew
  BERU-AI/crew/                          ← BERU audit + SSP-to-POA&M + AC crews
```

### After
```
GP-MODEL-OPS/crewai-mlops/         ← directory name (dashes OK)
  synthetic_pipeline/    ← moved from 0-data-lab/synthetic-pipeline/crew/
  beru/                  ← moved from BERU-AI/crew/
  rag_ingestion/         ← NEW (this spec)
  eval/                  ← PLANNED (4-eval-clarify crew)
  __init__.py            ← makes crewai_mlops a Python package
```

### Move Rules
- Source code in `0-data-lab/synthetic-pipeline/` and `BERU-AI/` stays where it is — crews reference it, they don't own it.
- Move only the `crew/` directories. All stage modules, tools, models stay in place.
- Update relative imports in moved crews to use absolute paths from `GP-MODEL-OPS/` root.
- Each crew's FastAPI port and CLI entry point remain unchanged (synthetic=8001, BERU=dynamic, RAG=8002).

---

## New Crew: rag-ingestion

### Architecture

```
crewai-mlops/rag-ingestion/
  main.py kickoff():
    1. run_prep_collectors()   ← pure Python, no LLM
       calls stages 1-4 from 02-preperation-factory/stages/
       produces: pass_batch, repair_batch, unlabeled_batch, routing_decisions
    2. CrewAI crew.kickoff(inputs={batches})
       4 agents work sequentially on the results
    3. Write processed_{timestamp}.jsonl + crew-report_{timestamp}.md
       to 03-preprocessed/
```

### Pre-flight (collectors.py — pure Python, no LLM)

Runs stages 1-4 against `01-unprocessed/`. Returns structured batches:

| Batch | Contents |
|-------|----------|
| `pass_batch` | Items that cleared sanitize with PASS — formatted, ready for labeling stage |
| `repair_batch` | Items flagged REPAIR by sanitize — formatted chunks, needs quality judgment |
| `unlabeled_batch` | Items where Tier 1 + Tier 2 labeling found no domain/tags — needs semantic classification |
| `routing_decisions` | All routed items with their destination/collection/reason — needs routing audit |

Stage 5 (labeling) Tier 1 + Tier 2 runs in the pre-flight for all items. Only items where both tiers find nothing land in `unlabeled_batch` for the semantic_labeler agent.

### Agents (4 total)

**quality_reviewer**
- Role: RAG Quality Gatekeeper
- Goal: Review borderline REPAIR items and decide promote-to-PASS or demote-to-FAIL with rationale
- Tools: `get_repair_items` (reads repair_batch), `override_quality_gate` (writes decision)
- Max tools: 2
- Why LLM: Regex-based quality gates produce false positives. A partially-corrupted chunk may still be high-value. Context judgment required.

**semantic_labeler**
- Role: Semantic Domain Classifier
- Goal: Classify domain/type/difficulty/tags for items that Tier 1 (ontology) and Tier 2 (regex) could not label
- Tools: `get_unlabeled_items` (reads unlabeled_batch), `apply_labels` (writes labels to items)
- Max tools: 2
- Why LLM: Tier 3 fallback logic already exists in `labeling_npc.py`. This agent formalizes it — tracked, retried, logged by CrewAI rather than a raw API call.
- Context: depends on quality_reviewer output (promoted items may need labeling too)

**routing_validator**
- Role: Collection Routing Auditor
- Goal: Review all routing decisions. Challenge SKIP decisions. Reroute items incorrectly defaulting to `jade-general` catch-all. Flag novel categories.
- Tools: `get_routing_decisions` (reads routing_decisions), `override_routing` (writes routing update)
- Max tools: 2
- Why LLM: Rule-based routing in `route.py` has gaps — new categories, novel file types, ambiguous content. Agent reviews and catches misroutes before they pollute a collection.
- Context: depends on semantic_labeler output (labeled items may route differently)

**pipeline_reporter**
- Role: RAG Coverage Analyst
- Goal: Synthesize full run stats. Report quality gate distribution, labeling coverage by domain, collection distribution. Issue go/no-go recommendation for ingestion.
- Tools: `get_pipeline_stats` (reads all batch stats + agent overrides)
- Max tools: 1
- Why LLM: Same as synthetic-pipeline's report_generator — pattern recognition across stats, gap analysis, human-readable recommendation.
- Context: depends on all 3 prior agents

### Tasks

| Task | Agent | Context deps | Output |
|------|-------|-------------|--------|
| `quality_task` | quality_reviewer | none (first in chain) | List of PASS/FAIL overrides with rationale |
| `labeling_task` | semantic_labeler | quality_task | List of label assignments for unlabeled items |
| `routing_task` | routing_validator | labeling_task | List of routing overrides with rationale |
| `report_task` | pipeline_reporter | quality_task + labeling_task + routing_task | Markdown report with stats, gaps, go/no-go |

Process: `Process.sequential`

### File Structure

```
GP-MODEL-OPS/crewai-mlops/rag_ingestion/
  __init__.py
  main.py          ← FastAPI (POST /run/rag-prep) + CLI entry point — port 8002
  agents.py        ← 4 agent definitions
  tools.py         ← tool functions that read/write batch state
  collectors.py    ← stages 1-4 pre-flight + Tier 1/2 labeling (wraps stages/ modules)
  crews/
    __init__.py
    prep_crew.py   ← crew definition, 4 tasks, Process.sequential
```

### Entry Points

```bash
# FastAPI
POST /run/rag-prep
  body: {"category": "compliance", "dry_run": false, "min_quality": 50}

# CLI (module path uses underscores; directory name uses dashes)
python3 -m crewai_mlops.rag_ingestion.main run
python3 -m crewai_mlops.rag_ingestion.main run --category compliance
python3 -m crewai_mlops.rag_ingestion.main run --dry-run
python3 -m crewai_mlops.rag_ingestion.main run --min-quality 70
```

### Output Files

Written to `2-rag-ingestion/03-preprocessed/`:
- `processed_{timestamp}.jsonl` — clean JSONL ready for `04-ingesting/ingest_to_chromadb.py`
- `crew-report_{timestamp}.md` — human-readable: quality gate distribution, labeling coverage, collection routing table, agent overrides, go/no-go

### What This Crew Does NOT Do

- Does not call `04-ingesting/ingest_to_chromadb.py` — ingestion stays a separate step
- Does not run Stage 7 cleanup — cleanup runs after ingestion, not before
- Does not modify any file in `02-preperation-factory/stages/` — stages are treated as library code

---

## Data Flow

```
01-unprocessed/{28 categories}/
          ↓
[collectors.py — pure Python, no LLM]
  Stage 1: discover all files by category
  Stage 2: preprocess each file (parse format)
  Stage 3: sanitize (dedup, PII, JSON repair) → classify PASS/REPAIR/FAIL
  Stage 4: format_convert PASS+REPAIR items → JSONL chunks with metadata
  Stage 5 Tier 1+2: ontology + regex labeling → classify labeled/unlabeled
  Stage 6: route → routing_decisions
  Outputs: pass_batch, repair_batch, unlabeled_batch, routing_decisions
          ↓
[CrewAI crew — judgment layer]
  quality_reviewer  → REPAIR items → promote PASS or demote FAIL
  semantic_labeler  → unlabeled items → domain/type/tags
  routing_validator → routing_decisions → override misroutes/SKIPs
  pipeline_reporter → all stats + overrides → markdown report + go/no-go
          ↓
03-preprocessed/processed_{timestamp}.jsonl   ← feed to 04-ingesting/
03-preprocessed/crew-report_{timestamp}.md    ← human review
```

---

## Constraints

- **No stage modules modified.** `stages/` is library code. `collectors.py` imports it.
- **Tool count per agent:** max 2. No agent gets 3+ tools.
- **Agents don't handle file I/O.** Tools handle reads/writes. Agents handle reasoning.
- **Tier 3 labeling goes through semantic_labeler only.** No direct `anthropic` calls in tools.py.
- **State between agents via file.** Batch state written to a temp JSON file per run. Tools read from it. Avoids passing large data through CrewAI context strings.

---

## Testing

- `collectors.py` runs standalone: `python3 collectors.py --dry-run` shows what would be processed
- Each tool is testable independently (reads from a fixture batch JSON)
- `crew/prep_crew.py` can run against a small fixture batch (10 items) for LLM agent testing
- Port 8002 health check: `GET /health` returns `{"status": "ok", "crew": "rag-ingestion"}`
