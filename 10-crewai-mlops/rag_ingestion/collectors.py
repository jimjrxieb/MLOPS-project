"""
Pre-flight pipeline for RAG ingestion prep crew.

Runs stages 1-4 + Tier 1/2 labeling + routing as pure Python (no LLM).
Results written to a state JSON file for agents to read via tools.py.

Architecture note: deterministic work happens here, not in agents.
Same pattern as BERU-AI/crew/crews/ac-access-control/collectors.py.

Stage API notes (actual signatures in 02-preperation-factory/stages/):
  discover.py         → discover_files(base_path) → Dict[str, List[Path]]
  preprocess.py       → preprocess_file(path, category) → dict with valid: bool
  sanitize_npc.py     → SanitizeNPC().process(item) → dict with quality_gate, content_hash
  format_conversion_npc.py → FormatConversionNPC().process(item) → dict with data: List[dict]
  labeling_npc.py     → LabelingNPC(use_claude_api=False).process(item) → dict with data: List[dict]
  route.py            → route_item(item) → dict with destination, rag_collection, sql_table, reason
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add the factory stages to sys.path
_FACTORY_DIR = Path(__file__).parent.parent.parent / "2-RagIngestion-Pipeline" / "02-preperation-factory"
if str(_FACTORY_DIR) not in sys.path:
    sys.path.insert(0, str(_FACTORY_DIR))

from stages.discover import discover_files
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

    Args:
        state_file: Path to write the JSON state file.
        category: If set, restrict discovery to this one category.
                  Pass a nonexistent category name for a fast zero-file test run.
        dry_run: If True, skip writing to disk (state_file is still written).
        min_quality: Minimum quality threshold (passed through to state; not yet enforced here).

    Returns:
        The state dict (same contents as state_file).
    """
    state_file = Path(state_file)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Stage 1: Discover
    sources = discover_files()
    if category:
        # Filter to requested category only; handle nonexistent category gracefully
        sources = {k: v for k, v in sources.items() if k == category}

    sanitizer = SanitizeNPC()
    formatter = FormatConversionNPC()
    labeler = LabelingNPC(use_claude_api=False)   # Tier 1 + 2 only (no Claude API)

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
            if not preprocessed or not preprocessed.get("valid"):
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

            # Determine if any chunk lacks domain (needs Tier 3 labeling by agents)
            has_unlabeled = any(
                not chunk.get("metadata", {}).get("domain")
                for chunk in chunks
            )

            # Stage 6: Route — route_item expects valid + sanitized fields (inherited via spread)
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
        "quality_overrides": {},
        "label_overrides": {},
        "routing_overrides": {},
    }

    state_file.write_text(json.dumps(state, indent=2, default=str))
    return state
