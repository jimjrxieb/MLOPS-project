# RAG Ingestion Prep Crew Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate all CrewAI code into `crewai-mlops/` and build a 4-agent RAG ingestion prep crew that runs deterministic stages as pure Python pre-flight and uses LLM agents only for quality review, semantic labeling, routing validation, and coverage reporting.

**Architecture:** Deterministic stages 1-4 + Tier 1/2 labeling + routing run as pure Python in `collectors.py` before CrewAI starts. Results are written to a per-run state file. Four agents read from that state file via tools and write back overrides. `main.py` assembles the final JSONL from state + overrides and writes the crew report.

**Tech Stack:** crewai==0.80.0, fastapi, uvicorn, pathlib, json, existing `stages/` modules (discover, preprocess, sanitize_npc, format_conversion_npc, labeling_npc, route)

---

## File Map

### Phase A — Reorganization (Tasks 1-3)

| Action | Path |
|--------|------|
| Create | `crewai-mlops/__init__.py` |
| Move   | `0-data-lab/synthetic-pipeline/crew/` → `crewai-mlops/synthetic_pipeline/` |
| Edit   | `crewai-mlops/synthetic_pipeline/tools.py` (fix `_PIPELINE_DIR` path) |
| Move   | `BERU-AI/crew/` → `crewai-mlops/beru/` |
| Create | `crewai-mlops/beru/__init__.py` |
| Edit   | `crewai-mlops/beru/main.py` (add sys.path + update lazy import paths) |
| Edit   | `crewai-mlops/beru/Dockerfile` (update CMD) |

### Phase B — RAG Crew (Tasks 4-8)

| Action | Path |
|--------|------|
| Create | `crewai-mlops/rag_ingestion/__init__.py` |
| Create | `crewai-mlops/rag_ingestion/collectors.py` |
| Create | `crewai-mlops/rag_ingestion/tools.py` |
| Create | `crewai-mlops/rag_ingestion/agents.py` |
| Create | `crewai-mlops/rag_ingestion/crews/__init__.py` |
| Create | `crewai-mlops/rag_ingestion/crews/prep_crew.py` |
| Create | `crewai-mlops/rag_ingestion/main.py` |

### Phase C — Tests + Docs (Tasks 9-10)

| Action | Path |
|--------|------|
| Create | `8-tests/test_rag_ingestion_crew.py` |
| Edit   | `CLAUDE.md` (update CrewAI migration table) |

---

## Task 1: Create crewai-mlops package skeleton

**Files:**
- Create: `crewai-mlops/__init__.py`

- [ ] **Step 1: Create the package init**

```python
# crewai-mlops/__init__.py
"""
crewai-mlops — all CrewAI / AI automation for GP-MODEL-OPS.

Sub-packages:
  synthetic_pipeline  — training data generation crew (port 8001)
  beru                — BERU audit + SSP-to-POA&M + AC control crew (port 8089)
  rag_ingestion       — RAG prep crew (port 8002)
"""
```

- [ ] **Step 2: Verify the directory exists and Python can see it**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
python3 -c "import importlib.util; print(importlib.util.find_spec('crewai_mlops') is not None)"
```

Expected: `False` (not yet on path — that's fine, it will work once we're in the right working directory)

- [ ] **Step 3: Commit**

```bash
git add crewai-mlops/__init__.py
git commit -m "feat(crewai): create crewai-mlops top-level package"
```

---

## Task 2: Move synthetic pipeline crew

**Files:**
- Move: `0-data-lab/synthetic-pipeline/crew/` → `crewai-mlops/synthetic_pipeline/`
- Edit: `crewai-mlops/synthetic_pipeline/tools.py` lines 14-25 (fix `_PIPELINE_DIR`)

- [ ] **Step 1: Move the directory with git mv**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
git mv 0-data-lab/synthetic-pipeline/crew crewai-mlops/synthetic_pipeline
```

- [ ] **Step 2: Fix the pipeline directory path in tools.py**

Open `crewai-mlops/synthetic_pipeline/tools.py`. Find this block (around line 16-24):

```python
_PIPELINE_DIR = Path(__file__).parent.parent  # …/synthetic-pipeline/
_PARENT_DIR = _PIPELINE_DIR.parent             # …/0-data-lab/

if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))
```

Replace with:

```python
# After move to crewai-mlops/synthetic_pipeline/, parent.parent is crewai-mlops/.
# The actual pipeline code lives at ../../0-data-lab/synthetic-pipeline/.
_PIPELINE_DIR = Path(__file__).parent.parent.parent / "0-data-lab" / "synthetic-pipeline"
_PARENT_DIR = _PIPELINE_DIR.parent             # …/0-data-lab/

if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))
```

- [ ] **Step 3: Verify the import resolves**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
python3 -c "
import sys; sys.path.insert(0, '.')
from crewai_mlops.synthetic_pipeline.tools import discover_sources
print('OK:', discover_sources)
"
```

Expected: `OK: <function discover_sources ...>` (no ImportError)

- [ ] **Step 4: Verify the crew builds**

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from crewai_mlops.synthetic_pipeline.crews.pipeline_crew import build_pipeline_crew
crew = build_pipeline_crew()
print('Agents:', len(crew.agents))
"
```

Expected: `Agents: 3`

- [ ] **Step 5: Commit**

```bash
git add crewai-mlops/synthetic_pipeline/
git commit -m "feat(crewai): move synthetic-pipeline crew to crewai-mlops/synthetic_pipeline"
```

---

## Task 3: Move BERU crew

**Files:**
- Move: `BERU-AI/crew/` → `crewai-mlops/beru/`
- Create: `crewai-mlops/beru/__init__.py`
- Edit: `crewai-mlops/beru/main.py` (sys.path + updated lazy imports)
- Edit: `crewai-mlops/beru/Dockerfile` (update CMD)

- [ ] **Step 1: Move the directory**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
git mv BERU-AI/crew crewai-mlops/beru
```

- [ ] **Step 2: Create __init__.py**

```python
# crewai-mlops/beru/__init__.py
"""BERU audit crew — NIST 800-53 assessment, SSP→SAR→POA&M, AC access control."""
```

- [ ] **Step 3: Add sys.path to main.py so bare crew imports still work**

Open `crewai-mlops/beru/main.py`. Find the imports section (around line 14). Add sys.path BEFORE any crew imports:

```python
import sys
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add this crew's directory to sys.path so bare imports (agents, crews.*) resolve
# regardless of where uvicorn or python3 is invoked from.
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
```

The lazy imports inside the route functions (`from crews.beru_audit import build_audit_crew`) remain unchanged — they work once `_HERE` is on sys.path.

- [ ] **Step 4: Update the Dockerfile CMD**

Open `crewai-mlops/beru/Dockerfile`. Find the CMD line:

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8089", "--reload"]
```

Replace with:

```dockerfile
# Run from the beru package directory so bare module imports (agents, crews.*) resolve
WORKDIR /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8089", "--reload", "--app-dir", "/app"]
```

And update the COPY so the whole beru directory is at /app:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8089

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8089", "--reload"]
```

(No change needed to Dockerfile since COPY . /app/ still works — files are in the same relative positions inside the container.)

- [ ] **Step 5: Verify the app loads**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/crewai-mlops/beru
python3 -c "from main import app; print('routes:', [r.path for r in app.routes])"
```

Expected: `routes: ['/health', '/run/beru-audit', '/run/ssp-to-poam', ...]`

- [ ] **Step 6: Commit**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
git add crewai-mlops/beru/
git commit -m "feat(crewai): move BERU crew to crewai-mlops/beru + fix sys.path"
```

---

## Task 4: collectors.py — pre-flight pipeline

**Files:**
- Create: `crewai-mlops/rag_ingestion/__init__.py`
- Create: `crewai-mlops/rag_ingestion/crews/__init__.py`
- Create: `crewai-mlops/rag_ingestion/collectors.py`
- Test: `8-tests/test_rag_ingestion_crew.py` (first section)

- [ ] **Step 1: Write the failing test**

```python
# 8-tests/test_rag_ingestion_crew.py
"""Tests for RAG ingestion prep crew — collectors, tools, agents, crew."""
import json
import sys
import tempfile
from pathlib import Path

# Add GP-MODEL-OPS root to path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

import pytest


class TestCollectors:
    """collectors.py: run_prep_collectors() pre-flight pipeline."""

    def test_run_prep_collectors_creates_state_file(self, tmp_path):
        """run_prep_collectors writes a state.json with expected top-level keys."""
        from crewai_mlops.rag_ingestion.collectors import run_prep_collectors

        state_file = tmp_path / "state.json"
        # Use a non-existent category so discover returns 0 files — fast test
        result = run_prep_collectors(
            state_file=state_file,
            category="__nonexistent_category__",
        )

        assert state_file.exists(), "state file must be written"
        state = json.loads(state_file.read_text())

        for key in ("run_id", "stats", "pass_batch", "repair_batch", "unlabeled_batch", "routing_decisions"):
            assert key in state, f"missing key: {key}"

        assert state["stats"]["discovered"] == 0
        assert isinstance(state["pass_batch"], list)
        assert isinstance(state["repair_batch"], list)
        assert isinstance(state["unlabeled_batch"], list)
        assert isinstance(state["routing_decisions"], list)

    def test_run_prep_collectors_returns_same_data_as_state_file(self, tmp_path):
        """return value matches the state file contents."""
        from crewai_mlops.rag_ingestion.collectors import run_prep_collectors

        state_file = tmp_path / "state.json"
        result = run_prep_collectors(
            state_file=state_file,
            category="__nonexistent_category__",
        )
        state = json.loads(state_file.read_text())
        assert result["run_id"] == state["run_id"]
        assert result["stats"] == state["stats"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestCollectors -v
```

Expected: `ModuleNotFoundError: No module named 'crewai_mlops'`

- [ ] **Step 3: Create package __init__ files**

```python
# crewai-mlops/rag_ingestion/__init__.py
"""RAG ingestion prep crew — pre-flight stages + 4 judgment agents (port 8002)."""
```

```python
# crewai-mlops/rag_ingestion/crews/__init__.py
```

- [ ] **Step 4: Write collectors.py**

```python
# crewai-mlops/rag_ingestion/collectors.py
"""
Pre-flight pipeline for RAG ingestion prep crew.

Runs stages 1-4 + Tier 1/2 labeling + routing as pure Python (no LLM).
Results written to a state JSON file for agents to read via tools.py.

Architecture note: deterministic work happens here, not in agents.
Same pattern as BERU-AI/crew/crews/ac-access-control/collectors.py.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add the factory stages to sys.path
_FACTORY_DIR = Path(__file__).parent.parent.parent / "2-rag-ingestion" / "02-preperation-factory"
if str(_FACTORY_DIR) not in sys.path:
    sys.path.insert(0, str(_FACTORY_DIR))

from stages.discover import SourceDiscoverer
from stages.preprocess import preprocess_file
from stages.sanitize_npc import SanitizeNPC
from stages.format_conversion_npc import FormatConversionNPC
from stages.labeling_npc import LabelingNPC
from stages.route import route_item


def run_prep_collectors(
    state_file: Path,
    category: Optional[str] = None,
    dry_run: bool = False,
    min_quality: int = 50,
) -> dict:
    """
    Run stages 1-4, Tier 1/2 labeling, and routing for all files in 01-unprocessed/.

    Produces three batches for agents:
      pass_batch      — PASS items where domain was detected (well-labeled)
      repair_batch    — REPAIR items needing quality judgment
      unlabeled_batch — PASS items where no domain was detected (need Tier 3)

    Writes state to state_file and also returns the state dict.
    """
    state_file.parent.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Stage 1: Discover
    discoverer = SourceDiscoverer()
    sources = discoverer.discover()
    if category:
        sources = {k: v for k, v in sources.items() if k == category}

    sanitizer = SanitizeNPC()
    formatter = FormatConversionNPC()
    labeler = LabelingNPC(use_claude_api=False)   # Tier 1 + 2 only

    pass_batch = []
    repair_batch = []
    unlabeled_batch = []
    routing_decisions = []

    stats = {
        "discovered": sum(len(v) for v in sources.values()),
        "preprocessed": 0,
        "pass_count": 0,
        "repair_count": 0,
        "fail_count": 0,
        "labeled_count": 0,
        "unlabeled_count": 0,
        "total_chunks": 0,
    }

    for cat, paths in sources.items():
        for path in paths:
            # Stage 2: Preprocess
            preprocessed = preprocess_file(path, cat)
            if not preprocessed.get("valid"):
                stats["fail_count"] += 1
                continue
            stats["preprocessed"] += 1

            # Stage 3: Sanitize
            sanitized = sanitizer.process(preprocessed)
            gate = sanitized.get("quality_gate", "FAIL")
            if gate == "FAIL":
                stats["fail_count"] += 1
                continue

            # Stage 4: Format convert
            formatted = formatter.process(sanitized)
            if not formatted.get("data"):
                stats["fail_count"] += 1
                continue

            stats["total_chunks"] += len(formatted["data"])

            # Stage 5 Tier 1+2: Label (no Claude API)
            labeled = labeler.process(formatted)
            chunks = labeled.get("data", [])

            # Determine if any chunk lacks domain (needs Tier 3)
            has_unlabeled = any(
                not chunk.get("metadata", {}).get("domain")
                for chunk in chunks
            )

            # Stage 6: Route
            routed = route_item({**labeled})

            item = {
                "file": str(path),
                "category": cat,
                "content_hash": sanitized.get("content_hash"),
                "quality_gate": gate,
                "chunks": chunks,
                "destination": routed.get("destination"),
                "rag_collection": routed.get("rag_collection"),
                "sql_table": routed.get("sql_table"),
                "routing_reason": routed.get("reason"),
            }

            routing_decisions.append({
                "file": str(path),
                "content_hash": sanitized.get("content_hash"),
                "category": cat,
                "destination": routed.get("destination"),
                "rag_collection": routed.get("rag_collection"),
                "sql_table": routed.get("sql_table"),
                "reason": routed.get("reason"),
            })

            if gate == "REPAIR":
                stats["repair_count"] += 1
                repair_batch.append(item)
            else:
                stats["pass_count"] += 1
                if has_unlabeled:
                    stats["unlabeled_count"] += 1
                    unlabeled_batch.append(item)
                else:
                    stats["labeled_count"] += 1
                    pass_batch.append(item)

    state = {
        "run_id": run_id,
        "category": category,
        "dry_run": dry_run,
        "min_quality": min_quality,
        "stats": stats,
        "pass_batch": pass_batch,
        "repair_batch": repair_batch,
        "unlabeled_batch": unlabeled_batch,
        "routing_decisions": routing_decisions,
        "quality_overrides": {},   # {content_hash: {decision, rationale}}
        "label_overrides": {},     # {content_hash: {domain, type, difficulty, tags}}
        "routing_overrides": {},   # {content_hash: {destination, rag_collection, reason}}
    }

    state_file.write_text(json.dumps(state, indent=2, default=str))
    return state
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestCollectors -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add crewai-mlops/rag_ingestion/ 8-tests/test_rag_ingestion_crew.py
git commit -m "feat(rag-crew): collectors.py — pre-flight stages 1-4 + Tier1/2 labeling"
```

---

## Task 5: tools.py — state file + tool functions

**Files:**
- Create: `crewai-mlops/rag_ingestion/tools.py`
- Edit: `8-tests/test_rag_ingestion_crew.py` (add TestTools class)

- [ ] **Step 1: Write the failing tests**

Add this class to `8-tests/test_rag_ingestion_crew.py`:

```python
class TestTools:
    """tools.py: each tool reads/writes state correctly."""

    def _make_state(self, tmp_path: Path) -> Path:
        """Write a minimal state fixture to tmp_path/state.json."""
        state = {
            "run_id": "20260520T120000Z",
            "stats": {"discovered": 5, "pass_count": 3, "repair_count": 1, "fail_count": 1,
                      "labeled_count": 2, "unlabeled_count": 1, "total_chunks": 12, "preprocessed": 4},
            "pass_batch": [],
            "repair_batch": [
                {"file": "a.md", "content_hash": "abc123", "category": "compliance",
                 "quality_gate": "REPAIR", "chunks": [{"content": "x", "metadata": {"domain": []}}],
                 "destination": "RAG", "rag_collection": "jade-general", "sql_table": None, "routing_reason": "default"}
            ],
            "unlabeled_batch": [
                {"file": "b.md", "content_hash": "def456", "category": "domain-sme",
                 "quality_gate": "PASS", "chunks": [{"content": "y", "metadata": {"domain": []}}],
                 "destination": "RAG", "rag_collection": "jade-domain-sme", "sql_table": None, "routing_reason": "domain-sme"}
            ],
            "routing_decisions": [
                {"file": "c.md", "content_hash": "ghi789", "category": "opa-policies",
                 "destination": "RAG", "rag_collection": "jade-general", "sql_table": None, "reason": "default fallback"}
            ],
            "quality_overrides": {},
            "label_overrides": {},
            "routing_overrides": {},
        }
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        return sf

    def test_get_repair_items_returns_repair_batch(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_repair_items.func()
        assert "repair_batch" in result
        assert result["repair_batch"][0]["content_hash"] == "abc123"

    def test_override_quality_gate_writes_to_overrides(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        tools.override_quality_gate.func("abc123", "FAIL", "content too short")
        state = json.loads(sf.read_text())
        assert "abc123" in state["quality_overrides"]
        assert state["quality_overrides"]["abc123"]["decision"] == "FAIL"

    def test_get_unlabeled_items_returns_unlabeled_batch(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_unlabeled_items.func()
        assert result["unlabeled_batch"][0]["content_hash"] == "def456"

    def test_apply_labels_writes_to_label_overrides(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        tools.apply_labels.func("def456", ["kubernetes"], ["documentation"], "intermediate", ["pod", "rbac"])
        state = json.loads(sf.read_text())
        assert "def456" in state["label_overrides"]
        assert state["label_overrides"]["def456"]["domain"] == ["kubernetes"]

    def test_get_routing_decisions_returns_decisions(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_routing_decisions.func()
        assert any(d["destination"] == "RAG" for d in result["routing_decisions"])

    def test_override_routing_writes_to_routing_overrides(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        tools.override_routing.func("ghi789", "RAG", "jade-policy-as-code", "rego file — belongs in policy collection")
        state = json.loads(sf.read_text())
        assert "ghi789" in state["routing_overrides"]
        assert state["routing_overrides"]["ghi789"]["rag_collection"] == "jade-policy-as-code"

    def test_get_pipeline_stats_returns_stats_dict(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_pipeline_stats.func()
        assert result["stats"]["discovered"] == 5
        assert "quality_overrides_count" in result
        assert "label_overrides_count" in result
        assert "routing_overrides_count" in result
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestTools -v
```

Expected: `ModuleNotFoundError: No module named 'crewai_mlops.rag_ingestion.tools'`

- [ ] **Step 3: Write tools.py**

```python
# crewai-mlops/rag_ingestion/tools.py
"""
CrewAI tools for the RAG ingestion prep crew.

All tools read from / write to a per-run state JSON file.
main.py calls set_state_file() before crew kickoff.

Tool contract: always return a dict (CrewAI serializes tool output as str).
Writes are atomic: read → mutate → write.
"""
import json
from pathlib import Path
from typing import List, Optional

from crewai.tools import tool

_STATE_FILE: Optional[Path] = None


def set_state_file(path: Path) -> None:
    """Called by main.py before crew kickoff to wire tools to this run's state."""
    global _STATE_FILE
    _STATE_FILE = path


def _read() -> dict:
    if _STATE_FILE is None:
        raise RuntimeError("tools.set_state_file() must be called before any tool")
    return json.loads(_STATE_FILE.read_text())


def _write(state: dict) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


@tool("get_repair_items")
def get_repair_items() -> dict:
    """Return items flagged REPAIR by the sanitize stage. Review each and decide PASS or FAIL."""
    state = _read()
    return {
        "repair_batch": state["repair_batch"],
        "count": len(state["repair_batch"]),
    }


@tool("override_quality_gate")
def override_quality_gate(content_hash: str, decision: str, rationale: str) -> dict:
    """
    Override the quality gate decision for one item.

    Args:
        content_hash: The item's SHA256 hash (from the repair_batch entry).
        decision: 'PASS' to promote the item, 'FAIL' to discard it.
        rationale: One sentence explaining the decision.
    """
    if decision not in ("PASS", "FAIL"):
        return {"error": f"decision must be PASS or FAIL, got: {decision}"}
    state = _read()
    state["quality_overrides"][content_hash] = {
        "decision": decision,
        "rationale": rationale,
    }
    _write(state)
    return {"content_hash": content_hash, "decision": decision, "written": True}


@tool("get_unlabeled_items")
def get_unlabeled_items() -> dict:
    """Return items where Tier 1 + Tier 2 labeling found no domain. Classify each."""
    state = _read()
    return {
        "unlabeled_batch": state["unlabeled_batch"],
        "count": len(state["unlabeled_batch"]),
    }


@tool("apply_labels")
def apply_labels(
    content_hash: str,
    domain: List[str],
    type_: List[str],
    difficulty: str,
    tags: List[str],
) -> dict:
    """
    Apply semantic labels to one unlabeled item.

    Args:
        content_hash: The item's SHA256 hash.
        domain: List of domain strings e.g. ['kubernetes', 'security'].
        type_: List of content types e.g. ['documentation', 'troubleshooting'].
        difficulty: One of 'beginner', 'intermediate', 'advanced'.
        tags: List of specific tags e.g. ['pod', 'rbac', 'networkpolicy'].
    """
    state = _read()
    state["label_overrides"][content_hash] = {
        "domain": domain,
        "type": type_,
        "difficulty": difficulty,
        "tags": tags,
    }
    _write(state)
    return {"content_hash": content_hash, "domain": domain, "written": True}


@tool("get_routing_decisions")
def get_routing_decisions() -> dict:
    """
    Return all routing decisions. Focus on items going to jade-general (catch-all)
    or marked SKIP — these are most likely to be misrouted.
    """
    state = _read()
    decisions = state["routing_decisions"]
    needs_review = [
        d for d in decisions
        if d.get("rag_collection") == "jade-general" or d.get("destination") == "SKIP"
    ]
    return {
        "routing_decisions": decisions,
        "total": len(decisions),
        "needs_review": needs_review,
        "needs_review_count": len(needs_review),
    }


@tool("override_routing")
def override_routing(
    content_hash: str,
    destination: str,
    rag_collection: str,
    reason: str,
) -> dict:
    """
    Override the routing decision for one item.

    Args:
        content_hash: The item's SHA256 hash.
        destination: 'RAG', 'SQL', 'BOTH', or 'SKIP'.
        rag_collection: Target ChromaDB collection name e.g. 'jade-policy-as-code'.
        reason: One sentence explaining why you changed the routing.
    """
    if destination not in ("RAG", "SQL", "BOTH", "SKIP"):
        return {"error": f"destination must be RAG/SQL/BOTH/SKIP, got: {destination}"}
    state = _read()
    state["routing_overrides"][content_hash] = {
        "destination": destination,
        "rag_collection": rag_collection,
        "reason": reason,
    }
    _write(state)
    return {"content_hash": content_hash, "destination": destination, "rag_collection": rag_collection, "written": True}


@tool("get_pipeline_stats")
def get_pipeline_stats() -> dict:
    """
    Return full pipeline run statistics including agent override counts.
    Use this to synthesize the coverage report and issue a go/no-go recommendation.
    """
    state = _read()
    return {
        "run_id": state["run_id"],
        "stats": state["stats"],
        "quality_overrides_count": len(state["quality_overrides"]),
        "label_overrides_count": len(state["label_overrides"]),
        "routing_overrides_count": len(state["routing_overrides"]),
        "quality_overrides": state["quality_overrides"],
        "label_overrides": state["label_overrides"],
        "routing_overrides": state["routing_overrides"],
        "routing_decisions": state["routing_decisions"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestTools -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add crewai-mlops/rag_ingestion/tools.py 8-tests/test_rag_ingestion_crew.py
git commit -m "feat(rag-crew): tools.py — 7 state-file tools for 4 agents"
```

---

## Task 6: agents.py — 4 agent definitions

**Files:**
- Create: `crewai-mlops/rag_ingestion/agents.py`
- Edit: `8-tests/test_rag_ingestion_crew.py` (add TestAgents class)

- [ ] **Step 1: Write the failing test**

Add to `8-tests/test_rag_ingestion_crew.py`:

```python
class TestAgents:
    """agents.py: each agent has correct role, max 2 tools, distinct goals."""

    def test_four_agents_defined(self):
        from crewai_mlops.rag_ingestion.agents import (
            quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter
        )
        agents = [quality_reviewer(), semantic_labeler(), routing_validator(), pipeline_reporter()]
        assert len(agents) == 4

    def test_each_agent_has_at_most_two_tools(self):
        from crewai_mlops.rag_ingestion.agents import (
            quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter
        )
        for agent_factory in [quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter]:
            agent = agent_factory()
            assert len(agent.tools) <= 2, f"{agent.role} has {len(agent.tools)} tools — max is 2"

    def test_agent_roles_are_unique(self):
        from crewai_mlops.rag_ingestion.agents import (
            quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter
        )
        roles = [a().role for a in [quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter]]
        assert len(roles) == len(set(roles)), "duplicate agent role detected"
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestAgents -v
```

Expected: `ModuleNotFoundError: No module named 'crewai_mlops.rag_ingestion.agents'`

- [ ] **Step 3: Write agents.py**

```python
# crewai-mlops/rag_ingestion/agents.py
"""
Four agents for the RAG ingestion prep crew.

Design rule: each agent has one job and at most 2 tools.
Deterministic work (stages 1-4, routing rules) lives in collectors.py, not here.
"""
import os
from crewai import Agent
from .tools import (
    get_repair_items,
    override_quality_gate,
    get_unlabeled_items,
    apply_labels,
    get_routing_decisions,
    override_routing,
    get_pipeline_stats,
)

LLM_MODEL = os.getenv("CREWAI_LLM", "ollama/llama3.1")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def quality_reviewer() -> Agent:
    return Agent(
        role="RAG Quality Gatekeeper",
        goal=(
            "Review every item in the REPAIR batch and decide whether to promote it "
            "to PASS (worth ingesting despite partial issues) or demote it to FAIL "
            "(too corrupted or low-value to ingest). Call override_quality_gate for "
            "each item with a one-sentence rationale."
        ),
        backstory=(
            "You are a senior data quality engineer. The sanitize pipeline flagged "
            "these chunks as partially corrupted or borderline — they passed JSON repair "
            "but had issues. You know that a chunk with a minor encoding problem can still "
            "be a high-value NIST finding, while a chunk that's just a log dump with "
            "a fixed trailing comma is garbage. Context is everything. Review the content, "
            "not just the flag."
        ),
        tools=[get_repair_items, override_quality_gate],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )


def semantic_labeler() -> Agent:
    return Agent(
        role="Semantic Domain Classifier",
        goal=(
            "Classify every item in the unlabeled batch with the correct domain, "
            "content type, difficulty, and tags. Call apply_labels for each item. "
            "Domain must be one or more of: kubernetes, terraform, opa, docker, "
            "cloud, security, compliance, general. "
            "Type must be one or more of: documentation, troubleshooting, policy, "
            "example, fix, configuration, best-practice, vulnerability, tutorial."
        ),
        backstory=(
            "You are an expert in cloud-native security and infrastructure. The "
            "automated labeling pipeline (ontology lookup + regex patterns) couldn't "
            "classify these chunks — they don't match known keywords but they clearly "
            "belong somewhere. Read the content carefully and assign the most precise "
            "labels you can. Good labels make RAG retrieval accurate; vague labels "
            "send everything to jade-general and hurt JADE's answers."
        ),
        tools=[get_unlabeled_items, apply_labels],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )


def routing_validator() -> Agent:
    return Agent(
        role="Collection Routing Auditor",
        goal=(
            "Review all routing decisions and fix misroutes. Focus especially on: "
            "(1) items going to jade-general — the catch-all that should rarely be used; "
            "(2) items marked SKIP — are they genuinely low-value or was the rule wrong? "
            "Call override_routing for every item you reroute with a clear reason."
        ),
        backstory=(
            "You know every ChromaDB collection: jade-projects (scan results), "
            "jade-sessions (Claude sessions), jade-troubleshooting (debug guides), "
            "jade-consulting (playbooks/cheatsheets), jade-policy-as-code (rego), "
            "jade-operational (JSA operational training), jade-domain-sme (SME content), "
            "jade-nist-800-53 (controls + compliance), jade-general (everything else). "
            "A rego policy in jade-general is a routing bug. A NIST control narrative "
            "in jade-projects is a routing bug. Fix them."
        ),
        tools=[get_routing_decisions, override_routing],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )


def pipeline_reporter() -> Agent:
    return Agent(
        role="RAG Coverage Analyst",
        goal=(
            "Synthesize the full run statistics into a markdown coverage report. "
            "Include: files discovered/processed/failed, quality gate distribution, "
            "agent override counts and rationale summary, collection routing table "
            "(how many chunks go to each collection), and a go/no-go recommendation "
            "for ChromaDB ingestion."
        ),
        backstory=(
            "You produce the final artifact a data engineer uses to decide whether to "
            "run ingest_to_chromadb.py. Your report must answer: Was the data clean? "
            "Are the labels reasonable? Are the routing decisions defensible? "
            "Would a RAG query return useful results from this batch? "
            "If quality_overrides_count is high, flag it. If routing_overrides_count "
            "is high, note which collections had the most fixes. Be specific — "
            "vague go/no-go with no numbers is useless."
        ),
        tools=[get_pipeline_stats],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestAgents -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add crewai-mlops/rag_ingestion/agents.py 8-tests/test_rag_ingestion_crew.py
git commit -m "feat(rag-crew): agents.py — 4 focused agents, max 2 tools each"
```

---

## Task 7: crews/prep_crew.py — crew definition

**Files:**
- Create: `crewai-mlops/rag_ingestion/crews/prep_crew.py`
- Edit: `8-tests/test_rag_ingestion_crew.py` (add TestCrew class)

- [ ] **Step 1: Write the failing test**

Add to `8-tests/test_rag_ingestion_crew.py`:

```python
class TestCrew:
    """prep_crew.py: crew has 4 tasks in correct dependency order."""

    def test_build_prep_crew_returns_crew_with_four_tasks(self):
        from crewai_mlops.rag_ingestion.crews.prep_crew import build_prep_crew
        crew = build_prep_crew()
        assert len(crew.tasks) == 4

    def test_tasks_have_correct_agent_assignments(self):
        from crewai_mlops.rag_ingestion.crews.prep_crew import build_prep_crew
        crew = build_prep_crew()
        roles = [task.agent.role for task in crew.tasks]
        assert roles[0] == "RAG Quality Gatekeeper"
        assert roles[1] == "Semantic Domain Classifier"
        assert roles[2] == "Collection Routing Auditor"
        assert roles[3] == "RAG Coverage Analyst"

    def test_report_task_has_context_from_all_prior_tasks(self):
        from crewai_mlops.rag_ingestion.crews.prep_crew import build_prep_crew
        crew = build_prep_crew()
        report_task = crew.tasks[3]
        assert report_task.context is not None
        assert len(report_task.context) == 3
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestCrew -v
```

Expected: `ModuleNotFoundError: No module named 'crewai_mlops.rag_ingestion.crews.prep_crew'`

- [ ] **Step 3: Write prep_crew.py**

```python
# crewai-mlops/rag_ingestion/crews/prep_crew.py
"""
RAG ingestion prep crew — sequential, 4 tasks.

Task chain:
  quality_task  → semantic_labeler_task → routing_task → report_task

Inputs come from the state file written by collectors.py.
main.py calls collectors.run_prep_collectors() then this crew's kickoff().
"""
from crewai import Crew, Task, Process
from ..agents import quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter


def build_prep_crew() -> Crew:
    """Build the RAG ingestion prep crew. Call after collectors.py writes the state file."""
    reviewer = quality_reviewer()
    labeler = semantic_labeler()
    validator = routing_validator()
    reporter = pipeline_reporter()

    quality_task = Task(
        description=(
            "Call get_repair_items to retrieve all REPAIR-flagged items from this run. "
            "For each item, read its content and chunks. Decide: is this worth ingesting "
            "despite the quality issue, or should it be discarded? "
            "Call override_quality_gate(content_hash, decision, rationale) for each item "
            "where decision is 'PASS' (promote) or 'FAIL' (discard). "
            "If the repair_batch is empty, report '0 REPAIR items — no overrides needed'."
        ),
        expected_output=(
            "A summary table: content_hash | file | decision | rationale. "
            "Total PASS overrides: N. Total FAIL overrides: N."
        ),
        agent=reviewer,
    )

    labeling_task = Task(
        description=(
            "Call get_unlabeled_items to retrieve items that Tier 1 + Tier 2 labeling "
            "could not classify. For each item, read its content and infer: "
            "domain (e.g. ['kubernetes', 'security']), type (e.g. ['documentation']), "
            "difficulty ('beginner'/'intermediate'/'advanced'), tags (specific keywords). "
            "Call apply_labels(content_hash, domain, type_, difficulty, tags) for each. "
            "If unlabeled_batch is empty, report '0 unlabeled items — no labels applied'."
        ),
        expected_output=(
            "A summary table: content_hash | file | domain | type | difficulty | tags. "
            "Total items labeled: N."
        ),
        agent=labeler,
        context=[quality_task],
    )

    routing_task = Task(
        description=(
            "Call get_routing_decisions. Review the 'needs_review' list — items going to "
            "jade-general or marked SKIP. For each, determine the correct collection: "
            "jade-projects (scan results/project docs), jade-sessions (Claude sessions), "
            "jade-troubleshooting (debug/fix guides), jade-consulting (playbooks/cheatsheets), "
            "jade-policy-as-code (rego/OPA), jade-operational (JSA operational training), "
            "jade-domain-sme (SME content), jade-nist-800-53 (NIST/compliance controls), "
            "jade-general (truly general content with no better home). "
            "Call override_routing(content_hash, destination, rag_collection, reason) for "
            "each rerouted item. Leave correctly-routed items alone."
        ),
        expected_output=(
            "A summary: total routing decisions reviewed, items rerouted (N), items confirmed correct (N). "
            "For rerouted items: content_hash | old collection | new collection | reason."
        ),
        agent=validator,
        context=[labeling_task],
    )

    report_task = Task(
        description=(
            "Call get_pipeline_stats to retrieve the full run statistics and override counts. "
            "Write a markdown coverage report with these sections:\n"
            "1. Run Summary — discovered, preprocessed, pass/repair/fail counts, total chunks\n"
            "2. Quality Gate Results — PASS/REPAIR/FAIL distribution, override breakdown\n"
            "3. Labeling Coverage — labeled vs unlabeled, domains detected\n"
            "4. Collection Routing — table of rag_collection → chunk count, override count\n"
            "5. Agent Overrides — quality N, label N, routing N, notable decisions\n"
            "6. Go/No-Go — APPROVED or NEEDS_REVIEW with one-paragraph justification\n\n"
            "APPROVED means: fail rate < 20%, labeled rate > 70%, routing overrides < 15% of total. "
            "NEEDS_REVIEW means any of those thresholds failed."
        ),
        expected_output=(
            "A complete markdown report with all 6 sections and a clear APPROVED or NEEDS_REVIEW "
            "verdict in section 6."
        ),
        agent=reporter,
        context=[quality_task, labeling_task, routing_task],
    )

    return Crew(
        agents=[reviewer, labeler, validator, reporter],
        tasks=[quality_task, labeling_task, routing_task, report_task],
        process=Process.sequential,
        verbose=False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestCrew -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add crewai-mlops/rag_ingestion/crews/prep_crew.py 8-tests/test_rag_ingestion_crew.py
git commit -m "feat(rag-crew): prep_crew.py — 4 sequential tasks with context chain"
```

---

## Task 8: main.py — FastAPI + CLI

**Files:**
- Create: `crewai-mlops/rag_ingestion/main.py`
- Edit: `8-tests/test_rag_ingestion_crew.py` (add TestMain class)

- [ ] **Step 1: Write the failing test**

Add to `8-tests/test_rag_ingestion_crew.py`:

```python
class TestMain:
    """main.py: FastAPI app has correct routes and health check works."""

    def test_app_has_required_routes(self):
        from crewai_mlops.rag_ingestion.main import app
        paths = [r.path for r in app.routes]
        assert "/health" in paths
        assert "/run/rag-prep" in paths

    def test_health_returns_ok(self):
        from fastapi.testclient import TestClient
        from crewai_mlops.rag_ingestion.main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["crew"] == "rag-ingestion"
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestMain -v
```

Expected: `ModuleNotFoundError: No module named 'crewai_mlops.rag_ingestion.main'`

- [ ] **Step 3: Write main.py**

```python
# crewai-mlops/rag_ingestion/main.py
"""
RAG Ingestion Prep Crew — FastAPI entry point + CLI.

Endpoints:
  POST /run/rag-prep   — run pre-flight + crew, write processed JSONL + report
  GET  /health

CLI:
  python3 -m crewai_mlops.rag_ingestion.main run
  python3 -m crewai_mlops.rag_ingestion.main run --category compliance
  python3 -m crewai_mlops.rag_ingestion.main run --dry-run
  python3 -m crewai_mlops.rag_ingestion.main run --min-quality 70
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import tools as _tools
from .collectors import run_prep_collectors
from .crews.prep_crew import build_prep_crew

# Output goes here (same as existing preprocess_pipeline.py)
_PREPROCESSED_DIR = (
    Path(__file__).parent.parent.parent
    / "2-rag-ingestion"
    / "03-preprocessed"
)

app = FastAPI(
    title="RAG Ingestion Prep Crew",
    version="1.0.0",
    description="CrewAI-orchestrated RAG prep: quality review, semantic labeling, routing validation.",
)


class PrepRequest(BaseModel):
    category: Optional[str] = None
    dry_run: bool = False
    min_quality: int = 50


@app.get("/health")
def health():
    return {"status": "ok", "crew": "rag-ingestion", "port": 8002}


@app.post("/run/rag-prep")
async def run_rag_prep(req: PrepRequest):
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, _run_pipeline, req.category, req.dry_run, req.min_quality
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_pipeline(
    category: Optional[str] = None,
    dry_run: bool = False,
    min_quality: int = 50,
) -> dict:
    """Orchestrate pre-flight + crew. Returns summary dict."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state_file = Path(f"/tmp/rag-prep-{run_id}/state.json")

    print(f"[rag-prep] run_id={run_id} category={category} dry_run={dry_run}")

    # Step 1: Pre-flight — pure Python, no LLM
    print("[rag-prep] running pre-flight collectors (stages 1-4 + Tier1/2 labeling)...")
    state = run_prep_collectors(
        state_file=state_file,
        category=category,
        dry_run=dry_run,
        min_quality=min_quality,
    )
    stats = state["stats"]
    print(
        f"[rag-prep] pre-flight done: "
        f"{stats['pass_count']} PASS, {stats['repair_count']} REPAIR, "
        f"{stats['fail_count']} FAIL, {stats['total_chunks']} chunks"
    )

    # Step 2: Wire tools to this run's state file
    _tools.set_state_file(state_file)

    # Step 3: Crew kickoff — agents handle judgment
    print("[rag-prep] starting crew (quality review → labeling → routing → report)...")
    crew = build_prep_crew()
    crew_result = crew.kickoff()
    crew_report = str(crew_result)

    # Step 4: Apply overrides + assemble final JSONL
    if not dry_run:
        processed_file, report_file = _write_outputs(run_id, state_file, crew_report)
        print(f"[rag-prep] wrote {processed_file}")
        print(f"[rag-prep] wrote {report_file}")
    else:
        processed_file = report_file = None
        print("[rag-prep] dry-run: no files written")

    return {
        "run_id": run_id,
        "stats": stats,
        "processed_file": str(processed_file) if processed_file else None,
        "report_file": str(report_file) if report_file else None,
        "crew_report": crew_report,
    }


def _write_outputs(run_id: str, state_file: Path, crew_report: str):
    """Apply agent overrides and write processed JSONL + markdown report."""
    state = json.loads(state_file.read_text())
    quality_overrides = state["quality_overrides"]
    label_overrides = state["label_overrides"]
    routing_overrides = state["routing_overrides"]

    _PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    processed_file = _PREPROCESSED_DIR / f"processed_{run_id}.jsonl"
    report_file = _PREPROCESSED_DIR / f"crew-report_{run_id}.md"

    # Collect all items: pass_batch + repair_batch promoted items
    all_items = list(state["pass_batch"]) + list(state["unlabeled_batch"])
    for item in state["repair_batch"]:
        override = quality_overrides.get(item.get("content_hash", ""))
        if override and override["decision"] == "PASS":
            all_items.append(item)

    # Apply label + routing overrides, write JSONL
    with processed_file.open("w") as f:
        for item in all_items:
            h = item.get("content_hash", "")
            chunks = item.get("chunks", [])
            dest = routing_overrides.get(h, {}).get("destination") or item.get("destination")
            collection = routing_overrides.get(h, {}).get("rag_collection") or item.get("rag_collection")
            lab = label_overrides.get(h, {})
            for chunk in chunks:
                if lab:
                    chunk.setdefault("metadata", {}).update({
                        "domain": lab.get("domain", []),
                        "type": lab.get("type", []),
                        "difficulty": lab.get("difficulty", "intermediate"),
                        "tags": lab.get("tags", []),
                    })
                chunk.setdefault("metadata", {}).update({
                    "rag_collection": collection,
                    "destination": dest,
                    "run_id": run_id,
                })
                f.write(json.dumps(chunk) + "\n")

    report_file.write_text(crew_report)
    return processed_file, report_file


def _cli():
    parser = argparse.ArgumentParser(description="RAG Ingestion Prep Crew CLI")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="Run the prep crew")
    run_p.add_argument("--category", default=None, help="Process one category only")
    run_p.add_argument("--dry-run", action="store_true", help="Skip writing output files")
    run_p.add_argument("--min-quality", type=int, default=50, help="Min quality score (0-100)")
    args = parser.parse_args()

    if args.command == "run":
        result = _run_pipeline(
            category=args.category,
            dry_run=args.dry_run,
            min_quality=args.min_quality,
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "serve":
        _cli()
    else:
        uvicorn.run("crewai_mlops.rag_ingestion.main:app", host="0.0.0.0", port=8002, reload=True)
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest 8-tests/test_rag_ingestion_crew.py::TestMain -v
```

Expected: `2 passed`

- [ ] **Step 5: Verify CLI help works**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
python3 -m crewai_mlops.rag_ingestion.main --help
```

Expected: usage text with `run` subcommand

- [ ] **Step 6: Commit**

```bash
git add crewai-mlops/rag_ingestion/main.py 8-tests/test_rag_ingestion_crew.py
git commit -m "feat(rag-crew): main.py — FastAPI + CLI, pre-flight → crew → JSONL output"
```

---

## Task 9: Run all tests + smoke check

- [ ] **Step 1: Run the full test file**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
python3 -m pytest 8-tests/test_rag_ingestion_crew.py -v
```

Expected: all `TestCollectors`, `TestTools`, `TestAgents`, `TestCrew`, `TestMain` tests pass. Count: 17 tests (2+7+3+3+2).

- [ ] **Step 2: Verify synthetic crew still works after move**

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from crewai_mlops.synthetic_pipeline.crews.pipeline_crew import build_pipeline_crew
crew = build_pipeline_crew()
assert len(crew.agents) == 3
print('synthetic_pipeline crew: OK')
"
```

Expected: `synthetic_pipeline crew: OK`

- [ ] **Step 3: Verify BERU crew still loads after move**

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/crewai-mlops/beru
python3 -c "from main import app; routes = [r.path for r in app.routes]; assert '/health' in routes; print('beru crew: OK')"
```

Expected: `beru crew: OK`

- [ ] **Step 4: Commit if any fixups were needed**

```bash
# Only if step 1-3 required any fixes
git add -p
git commit -m "fix(crewai): smoke test fixes post-reorganization"
```

---

## Task 10: Update CLAUDE.md migration table

**Files:**
- Edit: `CLAUDE.md` (CrewAI Migration Status section)

- [ ] **Step 1: Update the migration table**

Find the `## CrewAI Migration Status` section in `GP-MODEL-OPS/CLAUDE.md`. Replace the table and note with:

```markdown
## CrewAI Migration Status

All CrewAI code lives in `crewai-mlops/`. Entry point pattern: `POST /run/<crew-name>` + `python3 -m crewai_mlops.<crew>.main run`.

| Pipeline | Crew | Status | Location |
|----------|------|--------|----------|
| `0-data-lab/synthetic-pipeline/` | 3-agent crew: Orchestrator → Quality Auditor → Report Generator | **DONE** | `crewai-mlops/synthetic_pipeline/` |
| `BERU-AI/` | 6-agent pool across 3 sub-crews: beru_audit / ssp_to_poam / ac-access-control | **DONE** | `crewai-mlops/beru/` |
| `2-RagIngestion-Pipeline/02-preperation-factory/` | 4-agent crew: Quality Reviewer → Semantic Labeler → Routing Validator → Pipeline Reporter | **DONE** | `crewai-mlops/rag_ingestion/` |
| `4-eval-clarify/` | 4-agent parallel crew: one per eval suite | PLANNED | `crewai-mlops/eval/` |
| `1-FineTuning-Pipeline/` ETL + Chunk only | Wrap as tools, not agents | PLANNED | `crewai-mlops/training_pipeline/` |
| `1-FineTuning-Pipeline/` Training/Merge/Convert | **DO NOT MIGRATE** — GPU subprocess, no benefit | N/A | — |

**Port assignment:** synthetic_pipeline=8001, rag_ingestion=8002, beru=8089 (Docker), eval=TBD
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): update crewai migration table — rag_ingestion DONE, crewai-mlops reorganized"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `python3 -m pytest 8-tests/test_rag_ingestion_crew.py -v` → 15 passed
- [ ] `from crewai_mlops.synthetic_pipeline.crews.pipeline_crew import build_pipeline_crew` → no error
- [ ] `cd crewai-mlops/beru && python3 -c "from main import app"` → no error  
- [ ] `python3 -m crewai_mlops.rag_ingestion.main run --dry-run` → prints pre-flight stats + crew starts
- [ ] `crewai-mlops/` contains `__init__.py`, `synthetic_pipeline/`, `beru/`, `rag_ingestion/`
- [ ] `0-data-lab/synthetic-pipeline/crew/` → deleted (moved)
- [ ] `BERU-AI/crew/` → deleted (moved)
