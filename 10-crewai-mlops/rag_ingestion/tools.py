"""
CrewAI tools for the RAG ingestion prep crew.

All tools read from / write to a per-run state JSON file.
main.py calls set_state_file() before crew kickoff.

Tool contract: always return a dict (CrewAI serializes tool output as str).
Writes are atomic: read -> mutate -> write.
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
    or marked SKIP -- these are most likely to be misrouted.
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
