"""CrewAI state-file review template.

Copy-paste use case:
    deterministic collector writes JSON -> agents review state -> tools write overrides

This is based on the real RAG ingestion prep crew in:
    10-crewai-mlops/rag_ingestion/tools.py
    10-crewai-mlops/rag_ingestion/crews/prep_crew.py

Run:
    export CREWAI_LLM=ollama/llama3.2
    python3 crewai_statefile_review_template.py --make-sample
    python3 crewai_statefile_review_template.py --state-file /tmp/crewai-state-template/state.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai-storage")

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

_STATE_FILE: Optional[Path] = None


def make_llm() -> str:
    return os.getenv("CREWAI_LLM", "ollama/llama3.2")


def set_state_file(path: Path) -> None:
    global _STATE_FILE
    _STATE_FILE = path


def _read() -> dict:
    if _STATE_FILE is None:
        raise RuntimeError("set_state_file() must be called before tool use")
    return json.loads(_STATE_FILE.read_text())


def _write(state: dict) -> None:
    if _STATE_FILE is None:
        raise RuntimeError("set_state_file() must be called before tool use")
    _STATE_FILE.write_text(json.dumps(state, indent=2))


@tool("get_review_items")
def get_review_items() -> dict:
    """Return items that need agent review."""
    state = _read()
    return {
        "review_items": state.get("review_items", []),
        "count": len(state.get("review_items", [])),
    }


@tool("write_decision")
def write_decision(item_id: str, decision: str, rationale: str) -> dict:
    """Write PASS/FAIL/NEEDS_HUMAN decision for one item."""
    if decision not in ("PASS", "FAIL", "NEEDS_HUMAN"):
        return {"error": "decision must be PASS, FAIL, or NEEDS_HUMAN"}
    state = _read()
    state.setdefault("decisions", {})[item_id] = {
        "decision": decision,
        "rationale": rationale,
    }
    _write(state)
    return {"item_id": item_id, "decision": decision, "written": True}


@tool("get_run_stats")
def get_run_stats() -> dict:
    """Return run statistics and decisions for reporting."""
    state = _read()
    decisions = state.get("decisions", {})
    return {
        "run_id": state.get("run_id", "unknown"),
        "stats": state.get("stats", {}),
        "decisions_count": len(decisions),
        "decisions": decisions,
    }


def reviewer_agent() -> Agent:
    return Agent(
        role="Evidence Quality Reviewer",
        goal=(
            "Review every item in the state file and decide whether it is good "
            "enough to pass, should fail, or needs human review."
        ),
        backstory=(
            "You are a pragmatic GRC/data-quality reviewer. You care about "
            "evidence, traceability, and whether the item is useful downstream."
        ),
        tools=[get_review_items, write_decision],
        llm=make_llm(),
        verbose=True,
        allow_delegation=False,
    )


def reporter_agent() -> Agent:
    return Agent(
        role="Run Report Writer",
        goal=(
            "Summarize the state-file review and produce a clear go/no-go "
            "recommendation."
        ),
        backstory=(
            "You write concise engineering review reports. Your report must "
            "include numbers, notable decisions, and next action."
        ),
        tools=[get_run_stats],
        llm=make_llm(),
        verbose=True,
        allow_delegation=False,
    )


def build_state_review_crew() -> Crew:
    reviewer = reviewer_agent()
    reporter = reporter_agent()

    review_task = Task(
        description=(
            "Call get_review_items. For each item, inspect the evidence and call "
            "write_decision(item_id, decision, rationale). Use PASS only when the "
            "item has enough evidence to trust. Use NEEDS_HUMAN for high-risk or "
            "ambiguous cases."
        ),
        expected_output=(
            "A table: item_id | decision | rationale. Include total PASS, FAIL, "
            "and NEEDS_HUMAN counts."
        ),
        agent=reviewer,
    )

    report_task = Task(
        description=(
            "Call get_run_stats. Write a markdown report with Run Summary, "
            "Decision Breakdown, Notable Risks, and Go/No-Go Recommendation."
        ),
        expected_output=(
            "Markdown report with a clear APPROVED or NEEDS_REVIEW verdict."
        ),
        agent=reporter,
        context=[review_task],
    )

    return Crew(
        agents=[reviewer, reporter],
        tasks=[review_task, report_task],
        process=Process.sequential,
        verbose=True,
    )


def make_sample_state(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": "sample-001",
        "stats": {"items_total": 3, "source": "template"},
        "review_items": [
            {
                "item_id": "finding-001",
                "evidence": "Trivy reports HIGH CVE with package name and fixed version.",
                "risk": "patching gap",
            },
            {
                "item_id": "finding-002",
                "evidence": "SSP says MFA is enabled but cites no artifact.",
                "risk": "unsupported control claim",
            },
            {
                "item_id": "finding-003",
                "evidence": "Ambiguous free-text claim with no source path.",
                "risk": "low traceability",
            },
        ],
        "decisions": {},
    }
    path.write_text(json.dumps(state, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CrewAI state-file review template.")
    parser.add_argument("--state-file", type=Path, default=Path("/tmp/crewai-state-template/state.json"))
    parser.add_argument("--make-sample", action="store_true")
    args = parser.parse_args()

    if args.make_sample:
        make_sample_state(args.state_file)
        print(f"Wrote sample state: {args.state_file}")
        return

    set_state_file(args.state_file)
    crew = build_state_review_crew()
    result = crew.kickoff()
    print("\n=== CREW RESULT ===\n")
    print(result)
    print(f"\nUpdated state file: {args.state_file}")


if __name__ == "__main__":
    main()
