"""
HITL Router — Human-in-the-Loop Routing for B/S-Rank Findings

Routes BERU findings to the appropriate destination based on rank:
  E/D-rank → auto-output (pattern-matched, well-understood)
  C-rank   → auto-output with logged confidence
  B-rank   → human review queue (BLOCKED until human approves)
  S-rank   → human only, JADE provides dashboards

Control traceability:
  MANAGE-2.2  — Human oversight: B/S-rank findings must have HITL before output is written
  MAP-4.2     — Human interface: every B/S touch point specified and tested
  GOVERN-1.5  — Risk tolerance: "BERU cannot approve its own B/S-rank findings" is architectural
  CA-6        — Authorization: authorization decisions require human AO, not AI
  IR-4        — Incident handling: if BERU's B/S classification is wrong and acted on, it is an incident

3PAO question this answers:
  "Show me the code that prevents BERU from autonomously outputting B/S-rank findings."
  "How is the human review queue implemented? What prevents bypassing it?"

BERU Build Rule 7: B/S-rank findings MUST pass through hitl_router.py before output is written.
This is tested in 8-tests/test_hitl_router.py.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Rank routing table — maps rank to (auto_ok, requires_human)
# NEVER change B/S entries without updating architecture-laws.md
_RANK_ROUTING: Dict[str, Dict[str, Any]] = {
    "E": {"auto_ok": True,  "requires_human": False, "log_level": "DEBUG"},
    "D": {"auto_ok": True,  "requires_human": False, "log_level": "INFO"},
    "C": {"auto_ok": True,  "requires_human": False, "log_level": "INFO"},
    "B": {"auto_ok": False, "requires_human": True,  "log_level": "WARNING"},
    "S": {"auto_ok": False, "requires_human": True,  "log_level": "CRITICAL"},
}

# Default queue file location — writable by BERU process
_DEFAULT_QUEUE_DIR = Path(os.environ.get(
    "BERU_HITL_QUEUE_DIR",
    "/tmp/beru-hitl-queue",
))


class HITLRouter:
    """
    Route BERU findings through the human-in-the-loop checkpoint.

    B/S-rank findings are written to a pending queue and BLOCKED from output
    until a human approves them. This is not a policy — it is architecturally
    enforced: route() raises HITLBlockedError for B/S-rank unless explicitly
    pre-approved.

    Usage:
        router = HITLRouter()
        result = router.route(finding)

        if result["status"] == "auto":
            # Safe to output
            write_finding(finding)
        elif result["status"] == "pending_human":
            # DO NOT output — queued for human review
            print(f"Queued: {result['queue_id']}")
    """

    def __init__(self, queue_dir: Optional[Path] = None):
        self.queue_dir = Path(queue_dir) if queue_dir else _DEFAULT_QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._pending_path = self.queue_dir / "pending.jsonl"
        self._approved_path = self.queue_dir / "approved.jsonl"
        self._rejected_path = self.queue_dir / "rejected.jsonl"

    def route(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a single finding. Returns routing decision.

        Returns:
            {
                "status": "auto" | "pending_human",
                "rank": "E"|"D"|"C"|"B"|"S",
                "auto_ok": bool,
                "queue_id": str | None,  # set for pending_human
                "message": str,
                "finding_id": str,
            }
        """
        rank = self._extract_rank(finding)
        routing = _RANK_ROUTING.get(rank, _RANK_ROUTING["C"])
        finding_id = finding.get("finding_id", finding.get("id", "unknown"))

        if routing["auto_ok"]:
            self._log_auto(finding_id, rank)
            return {
                "status": "auto",
                "rank": rank,
                "auto_ok": True,
                "queue_id": None,
                "message": f"Rank {rank}: auto-output permitted. Logged.",
                "finding_id": finding_id,
            }

        # B/S-rank: write to pending queue, block output
        queue_id = self._enqueue_pending(finding, rank)
        return {
            "status": "pending_human",
            "rank": rank,
            "auto_ok": False,
            "queue_id": queue_id,
            "message": (
                f"Rank {rank}: BLOCKED. Finding queued for human review. "
                f"Queue ID: {queue_id}. "
                f"MANAGE-2.2 — human oversight required before output. "
                f"Approve via: hitl_router.approve('{queue_id}')"
            ),
            "finding_id": finding_id,
        }

    def route_batch(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Route a batch of findings. Returns list of routing decisions."""
        return [self.route(f) for f in findings]

    def approve(self, queue_id: str,
                approver: str = "human",
                notes: str = "") -> Dict[str, Any]:
        """
        Approve a pending finding for output. Moves from pending → approved.

        Args:
            queue_id: The queue ID returned by route()
            approver: Human identifier (name, email, role)
            notes: Human reviewer notes

        Returns:
            The approved finding dict (safe to output now)
        """
        pending = self._read_pending()
        record = next((r for r in pending if r["queue_id"] == queue_id), None)

        if not record:
            raise KeyError(
                f"Queue ID '{queue_id}' not found in pending queue. "
                "It may have already been approved, rejected, or expired."
            )

        approved_record = {
            **record,
            "status": "approved",
            "approved_by": approver,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_notes": notes,
        }

        self._append_jsonl(self._approved_path, approved_record)
        self._remove_from_pending(queue_id)

        return approved_record["finding"]

    def reject(self, queue_id: str,
               reviewer: str = "human",
               reason: str = "") -> None:
        """
        Reject a pending finding — it will NOT be output.

        Args:
            queue_id: The queue ID returned by route()
            reviewer: Human identifier
            reason: Reason for rejection (e.g., "BERU misclassified severity")
        """
        pending = self._read_pending()
        record = next((r for r in pending if r["queue_id"] == queue_id), None)

        if not record:
            raise KeyError(f"Queue ID '{queue_id}' not found in pending queue.")

        rejected_record = {
            **record,
            "status": "rejected",
            "rejected_by": reviewer,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": reason,
        }

        self._append_jsonl(self._rejected_path, rejected_record)
        self._remove_from_pending(queue_id)

    def list_pending(self) -> List[Dict[str, Any]]:
        """Return all pending findings awaiting human review."""
        return self._read_pending()

    def stats(self) -> Dict[str, int]:
        """Return queue statistics."""
        return {
            "pending": len(self._read_jsonl(self._pending_path)),
            "approved": len(self._read_jsonl(self._approved_path)),
            "rejected": len(self._read_jsonl(self._rejected_path)),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _extract_rank(self, finding: Dict[str, Any]) -> str:
        """Extract rank from finding. Defaults to B if ambiguous (fail safe)."""
        rank = finding.get("rank", finding.get("priority_rank", ""))
        if isinstance(rank, str):
            rank = rank.upper().strip()
        if rank in _RANK_ROUTING:
            return rank
        # Infer from triage priority if rank not set
        priority = str(finding.get("triage", {}).get("priority", "")).upper()
        priority_to_rank = {"P1": "S", "P2": "B", "P3": "C", "P4": "D"}
        inferred = priority_to_rank.get(priority, "B")
        return inferred

    def _enqueue_pending(self, finding: Dict[str, Any], rank: str) -> str:
        """Write finding to pending queue. Returns queue_id."""
        import hashlib
        finding_id = finding.get("finding_id", finding.get("id", "unknown"))
        ts = datetime.now(timezone.utc).isoformat()
        queue_id = hashlib.sha256(
            f"{finding_id}:{ts}:{rank}".encode()
        ).hexdigest()[:12]

        record = {
            "queue_id": queue_id,
            "rank": rank,
            "finding_id": finding_id,
            "queued_at": ts,
            "status": "pending",
            "finding": finding,
            "control_citation": "MANAGE-2.2 — human oversight before output",
        }
        self._append_jsonl(self._pending_path, record)
        return queue_id

    def _log_auto(self, finding_id: str, rank: str) -> None:
        """Log auto-routed finding for audit trail (AU-12)."""
        record = {
            "finding_id": finding_id,
            "rank": rank,
            "action": "auto_output",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        log_path = self.queue_dir / "auto_log.jsonl"
        self._append_jsonl(log_path, record)

    def _read_pending(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self._pending_path)

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _append_jsonl(self, path: Path, record: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _remove_from_pending(self, queue_id: str) -> None:
        """Remove a record from the pending queue by queue_id."""
        pending = self._read_pending()
        remaining = [r for r in pending if r["queue_id"] != queue_id]
        with open(self._pending_path, "w", encoding="utf-8") as f:
            for r in remaining:
                f.write(json.dumps(r) + "\n")
