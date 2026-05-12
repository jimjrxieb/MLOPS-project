"""
BERU Agent — Output Guards Tests (Guards 1, 2, 3) and the integration path.

Closes gap G-6 from BERU-AI/CONTROL-TRACEABILITY.md.

Tests run WITHOUT Ollama — every test isolates a single graph node and feeds it
a synthetic state. The full LangGraph DAG is exercised by run_beru.py
end-to-end runs, not here.

Control traceability:
  MEASURE-2.5  — Validity: Guards 1 + 3 enforce output validity
  MEASURE-2.6  — RAG/retrieval grounding: Guard 3 catches generation beyond source
  MANAGE-2.2   — Human oversight: rank-bump path to HITL queue
  GOVERN-1.4   — Accountability: every output traces to evidence
  GOVERN-1.5   — Risk tolerance: B/S findings never auto-output
  800-53 SI-10 — Input validation (symmetric: model output validated against input)
"""

import sys
from pathlib import Path

import pytest

BERU_PATH = Path(__file__).parent.parent / "BERU-AI"
sys.path.insert(0, str(BERU_PATH))

from agent import nodes  # noqa: E402


# ── Shared fixtures ───────────────────────────────────────────────────────────


def _base_state(control_id: str = "AC-2"):
    """Minimum state shape every node expects to find."""
    return {
        "current_control": control_id,
        "raw_finding_text": "",
        "control_definition": "",
        "evidence": [],
        "validated_control_ids": [control_id],
        "validated_ai_rmf_ids": [],
        "validation_errors": [],
        "ai_context": False,
        "deterministic_finding": False,
        "evidence_hallucination": False,
        "system_name": "TestSys",
        "client": "TestClient",
        "run_id": "test-run",
    }


GOOD_FINDING_AC2 = """FINDING: Three service accounts have cluster-admin.
CONTROL: AC-2
STATUS: PARTIAL
EVIDENCE REVIEWED: SSP narrative for AC-2; controls/AC-2.md
EVIDENCE GAP: provisioning authority for each SA
RISK: Likelihood Medium x Impact Medium -> Rank C
CONTROL OWNER: K8s lead
POA&M ITEM: Audit and scope down each SA
CISO SUMMARY: SA audit pending."""

HALLUCINATED_FINDING_AC2 = """FINDING: SA review complete.
CONTROL: AC-2
STATUS: PASS
EVIDENCE REVIEWED: /etc/kubernetes/audit.log (2026-05-08); kubectl get sa; prowler iam_no_root_access_key_present
EVIDENCE GAP: none
RISK: Likelihood Low x Impact Low -> Rank D
CONTROL OWNER: K8s lead
POA&M ITEM: n/a
CISO SUMMARY: SA management is configured."""

BAD_CITATION_FINDING = """FINDING: Test.
CONTROL: ZZ-99
STATUS: FAIL
EVIDENCE REVIEWED: nothing.
EVIDENCE GAP: everything.
RISK: Likelihood High x Impact High -> Rank C
CONTROL OWNER: nobody.
POA&M ITEM: n/a.
CISO SUMMARY: n/a."""


# ── Guard 1 — narrative_check (stub-narrative pre-detector) ───────────────────


@pytest.mark.parametrize("stub_narrative", [
    "configured.",
    "enabled.",
    "implemented.",
    "yes.",
    "in place.",
    "done",
    "ok.",
    "n/a",
])
def test_guard1_catches_known_stub_tokens(stub_narrative):
    """A one-word stub narrative must produce a deterministic FAIL finding
    (MAP-2.3 / MEASURE-2.5)."""
    state = _base_state("AC-2")
    state["evidence"] = [
        {"ssp_chunk": {"control_id": "AC-2", "text": stub_narrative}}
    ]
    out = nodes.narrative_check(state)
    assert out.get("deterministic_finding") is True, f"stub {stub_narrative!r} not flagged"
    assert "FAIL" in out["raw_finding_text"]
    assert "EVIDENCE GAP:" in out["raw_finding_text"]


def test_guard1_short_narrative_under_threshold():
    """Any narrative shorter than _STUB_MIN_CHARS counts as a stub even if it
    isn't on the known-tokens list."""
    state = _base_state("AC-2")
    state["evidence"] = [
        {"ssp_chunk": {"control_id": "AC-2", "text": "RBAC is good."}}  # 13 chars
    ]
    out = nodes.narrative_check(state)
    assert out.get("deterministic_finding") is True


def test_guard1_real_narrative_passes_through():
    """A real implementation narrative (> 50 chars, not a stub) must NOT
    trigger the deterministic path — the brain should be called normally."""
    state = _base_state("AC-2")
    state["evidence"] = [
        {"ssp_chunk": {
            "control_id": "AC-2",
            "text": (
                "Account provisioning uses ArgoCD AppProject role bindings; "
                "service account creation is gated by a two-reviewer pull request "
                "in infra-rbac repo. Quarterly reviews recorded in /audits/rbac-Q1-2026.md."
            ),
        }}
    ]
    out = nodes.narrative_check(state)
    assert out.get("deterministic_finding") in (False, None)
    assert "raw_finding_text" not in out  # node returns {} when not triggering


def test_guard1_skips_when_no_ssp_chunk_for_this_control():
    """If the SSP doesn't mention this control at all, narrative_check is a noop;
    the brain handles it (and may emit EVIDENCE GAP: 'control not addressed')."""
    state = _base_state("SI-7")
    state["evidence"] = [
        {"ssp_chunk": {"control_id": "AC-2", "text": "Some implementation for AC-2"}}
    ]
    out = nodes.narrative_check(state)
    assert out == {}


# ── Guard 2 — validate_citations ──────────────────────────────────────────────


def test_guard2_passes_when_only_allowed_controls_cited():
    state = _base_state("AC-2")
    state["raw_finding_text"] = GOOD_FINDING_AC2
    out = nodes.validate_citations(state)
    assert out.get("validation_errors", []) == [], \
        f"unexpected errors: {out.get('validation_errors')}"


def test_guard2_rejects_unknown_control_id():
    """Finding cites ZZ-99 which doesn't exist as controls/ZZ-99.md."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = BAD_CITATION_FINDING
    state["validated_control_ids"] = ["AC-2"]
    out = nodes.validate_citations(state)
    errs = out.get("validation_errors", [])
    assert errs, "validator did not reject unknown control"
    joined = " ".join(errs)
    assert "ZZ-99" in joined or "allow-list" in joined.lower()


def test_guard2_rejects_cited_control_not_in_allowlist():
    """Finding cites SC-7, which exists as a file but is not in the allow-list
    for this AC-2 assessment."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = (
        "FINDING: NetworkPolicy issue.\nCONTROL: SC-7\nSTATUS: FAIL\n"
        "EVIDENCE REVIEWED: SSP.\nEVIDENCE GAP: none.\nRISK: L x I -> C\n"
        "CONTROL OWNER: x\nPOA&M ITEM: x\nCISO SUMMARY: x"
    )
    state["validated_control_ids"] = ["AC-2"]
    out = nodes.validate_citations(state)
    assert out.get("validation_errors"), \
        "validator did not reject cross-control citation"


def test_guard2_ai_rmf_check_only_when_ai_context():
    """AI RMF allow-list is enforced only when the assessment scopes an AI system."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = (
        "FINDING: x\nCONTROL: AC-2\nAI RMF: GOVERN-1.1\nSTATUS: FAIL\n"
        "EVIDENCE REVIEWED: x\nEVIDENCE GAP: x\nRISK: L x I -> C\n"
        "CONTROL OWNER: x\nPOA&M ITEM: x\nCISO SUMMARY: x"
    )
    state["validated_ai_rmf_ids"] = []  # empty allow-list

    # ai_context=False: AI RMF citation is allowed (just informational)
    state["ai_context"] = False
    out = nodes.validate_citations(state)
    ai_errs = [e for e in out.get("validation_errors", []) if "AI RMF" in e]
    assert ai_errs == []

    # ai_context=True: AI RMF citation must be in allow-list
    state["ai_context"] = True
    out = nodes.validate_citations(state)
    ai_errs = [e for e in out.get("validation_errors", []) if "AI RMF" in e]
    assert ai_errs, "AI RMF guard did not fire under ai_context=True"


# ── Guard 3 — evidence_groundedness_check ─────────────────────────────────────


def test_guard3_passes_when_evidence_is_grounded():
    """If every artifact the brain cites appears in the source haystack, no flag."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = GOOD_FINDING_AC2
    state["control_definition"] = "AC-2 account management requires documented procedures..."
    state["evidence"] = [
        {"ssp_chunk": {
            "control_id": "AC-2",
            "text": "We reviewed the SSP narrative for AC-2 and the controls/AC-2.md file.",
            "source_file": "ssp.md",
        }}
    ]
    out = nodes.evidence_groundedness_check(state)
    assert out.get("evidence_hallucination") in (False, None), \
        f"false positive: {out}"


def test_guard3_flags_when_brain_cites_unsourced_tool():
    """Brain cites `kubectl` and a file path that aren't in the source — flag."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = HALLUCINATED_FINDING_AC2
    state["control_definition"] = "AC-2 requires account management procedures."
    state["evidence"] = []  # empty haystack — no kubectl/prowler/audit.log mentioned
    out = nodes.evidence_groundedness_check(state)
    assert out.get("evidence_hallucination") is True, "Guard 3 did not flag"
    errs = out.get("validation_errors", [])
    assert any("hallucination" in e.lower() for e in errs), \
        f"no hallucination error: {errs}"


def test_guard3_skips_deterministic_findings():
    """Regression: Guard 1 produces deterministic findings whose EVIDENCE REVIEWED
    block contains the SSP file path. Guard 3 must NOT flag those as hallucinated —
    they are constructed by the orchestrator from real input, not by the model.

    Before this fix, every deterministic finding ended up rank-bumped to B and
    HITL-blocked, which caused the entire ssp-01-bad sweep to produce 0 findings.
    """
    state = _base_state("AU-9")
    state["deterministic_finding"] = True
    state["raw_finding_text"] = (
        "FINDING: SSP narrative for AU-9 provides no implementation detail.\n"
        "CONTROL: AU-9\nSTATUS: FAIL\n"
        "EVIDENCE REVIEWED: SSP /tmp/never-mentioned-in-haystack.md — narrative for AU-9\n"
        "EVIDENCE GAP: SSP claim for AU-9 contains no implementation detail.\n"
        "RISK: Likelihood Medium x Impact Medium -> Rank C\n"
        "CONTROL OWNER: x\nPOA&M ITEM: x\nCISO SUMMARY: x"
    )
    state["control_definition"] = "AU-9 protection of audit information."
    state["evidence"] = []
    out = nodes.evidence_groundedness_check(state)
    assert out == {}, f"Guard 3 must skip deterministic findings, got: {out}"


def test_guard3_no_op_on_empty_finding():
    state = _base_state("AC-2")
    state["raw_finding_text"] = ""
    out = nodes.evidence_groundedness_check(state)
    assert out == {}


def test_guard3_accepts_tokens_that_appear_in_control_file():
    """Tools mentioned in controls/<ID>.md count as grounded — they're part of
    the documented evidence procedures for the control."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = (
        "FINDING: x.\nCONTROL: AC-2\nSTATUS: PARTIAL\n"
        "EVIDENCE REVIEWED: kubectl get sa output and the controls/AC-2.md procedures.\n"
        "EVIDENCE GAP: x.\nRISK: L x I -> C\n"
        "CONTROL OWNER: x\nPOA&M ITEM: x\nCISO SUMMARY: x"
    )
    state["control_definition"] = (
        "Run kubectl get sa to inventory service accounts. "
        "Compare against the documented owners in the SSP."
    )
    state["evidence"] = []
    out = nodes.evidence_groundedness_check(state)
    assert out.get("evidence_hallucination") in (False, None)


# ── Integration: Guard 3 → classify_rank → hitl_gate ─────────────────────────


def test_integration_hallucination_bumps_to_B_and_hitl_blocks():
    """End-to-end across three nodes: the architectural guarantee that a
    hallucinated finding cannot leave the agent as an APPROVED output.
    GOVERN-1.5 + MANAGE-2.2."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = HALLUCINATED_FINDING_AC2
    state["control_definition"] = "AC-2 requires account management procedures."
    state["evidence"] = []

    # Guard 3
    g3 = nodes.evidence_groundedness_check(state)
    state.update(g3)
    assert state.get("evidence_hallucination") is True

    # classify_rank — should bump to B because evidence_hallucination is set
    cr = nodes.classify_rank(state)
    state.update(cr)
    assert state["rank"] == "B", f"rank not bumped: {state['rank']}"
    assert state["finding"]["rank_bumped_for_hallucination"] is True

    # hitl_gate — must route to blocked_findings, not approve
    hg = nodes.hitl_gate(state)
    blocked = hg.get("blocked_findings", [])
    assert len(blocked) == 1, f"expected 1 blocked, got {len(blocked)}"
    assert blocked[0]["hitl_status"] == "BLOCKED"
    assert blocked[0]["hitl_meta"].get("auto_ok") is False
    # And the approved-output path is empty (no auto-output finding emitted)
    assert "finding" not in hg or hg.get("finding") is None


def test_integration_clean_finding_passes_to_approved():
    """Contrast: a grounded C-rank finding should reach approved output."""
    state = _base_state("AC-2")
    state["raw_finding_text"] = GOOD_FINDING_AC2
    state["control_definition"] = "AC-2 requires documented account management."
    state["evidence"] = [
        {"ssp_chunk": {
            "control_id": "AC-2",
            "text": "SSP narrative for AC-2 and controls/AC-2.md references.",
        }}
    ]
    state.update(nodes.evidence_groundedness_check(state))
    state.update(nodes.classify_rank(state))
    hg = nodes.hitl_gate(state)
    assert hg.get("blocked_findings") in (None, []), \
        f"clean finding wrongly blocked: {hg.get('blocked_findings')}"
    assert hg["finding"]["hitl_status"] == "APPROVED"


# ── State-isolation regression: select_next_control resets per-control fields ─


def test_select_next_control_resets_prior_control_state():
    """Regression: without this reset, evidence_hallucination=True from control N
    leaked into control N+1's classify_rank and incorrectly bumped its rank to B.
    The whole ssp-08 SSP produced 0 findings before this fix; every deterministic
    finding inherited the previous control's halluc flag and ended up HITL-blocked.
    """
    state = _base_state("AC-2")
    # Pollute with state from a "previous control" iteration:
    state["pending_controls"] = ["AU-9", "CM-6"]
    state["raw_finding_text"] = "STALE finding text from prior control"
    state["validation_errors"] = ["stale: evidence hallucination from prior control"]
    state["evidence_hallucination"] = True
    state["deterministic_finding"] = True
    state["finding"] = {"control_id": "PRIOR", "rank": "B"}
    state["rank"] = "B"
    state["control_definition"] = "stale definition from prior"
    state["validated_control_ids"] = ["PRIOR"]

    out = nodes.select_next_control(state)
    assert out["current_control"] == "AU-9"
    # Every per-control field must be reset:
    assert out["raw_finding_text"] == ""
    assert out["validation_errors"] == []
    assert out["evidence_hallucination"] is False
    assert out["deterministic_finding"] is False
    assert out["finding"] == {}
    assert out["rank"] == ""
    assert out["control_definition"] == ""
    assert out["validated_control_ids"] == []
    assert out["validated_ai_rmf_ids"] == []


# ── Smoke: import surface is what CONTROL-TRACEABILITY claims ────────────────


def test_nodes_exposes_documented_surface():
    """CONTROL-TRACEABILITY.md cites these function names; if they're renamed
    the doc must be updated alongside the code."""
    for name in [
        "narrative_check",
        "validate_citations",
        "evidence_groundedness_check",
        "classify_rank",
        "hitl_gate",
        "route_after_narrative_check",
        "route_after_hitl",
    ]:
        assert hasattr(nodes, name), f"missing public node fn: {name}"
