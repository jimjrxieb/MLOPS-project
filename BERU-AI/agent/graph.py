"""LangGraph DAG for the BERU agent.

   parse_input ──► [pending?]
                       │
                       └► select_next_control ──► load_control_context
                              ▲                          │
                              │                          ▼
                              │                    assess_control
                              │                          │
                              │                          ▼
                              │                  validate_citations
                              │                          │
                              │                          ▼
                              │                    classify_rank
                              │                          │
                              │                          ▼
                              │                       hitl_gate
                              │                       │      │
                              │            (B/S — skip)      (E/D/C)
                              │                       │      │
                              │                       ▼      ▼
                              │                  loop_check ◄┘
                              │                       │
                              │            (more pending)
                              └────────────────────┘
                                       │ (none)
                                       ▼
                                  package_evidence ──► END
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from . import nodes
from .state import BERUState, new_state


def build_graph():
    g = StateGraph(BERUState)

    g.add_node("parse_input", nodes.parse_input)
    g.add_node("select_next_control", nodes.select_next_control)
    g.add_node("load_control_context", nodes.load_control_context)
    g.add_node("narrative_check", nodes.narrative_check)               # M4.1 guard
    g.add_node("assess_control", nodes.assess_control)
    g.add_node("validate_citations", nodes.validate_citations)
    g.add_node("evidence_groundedness_check", nodes.evidence_groundedness_check)  # M4.1 guard
    g.add_node("classify_rank", nodes.classify_rank)
    g.add_node("hitl_gate", nodes.hitl_gate)
    g.add_node("produce_artifacts", nodes.produce_artifacts)
    # loop_check is a routing pseudo-node — implemented as a passthrough.
    g.add_node("loop_check", lambda s: {})
    g.add_node("package_evidence", nodes.package_evidence)

    g.set_entry_point("parse_input")

    # After parse_input, jump straight to picking a control (or out if nothing pending).
    def _after_parse(s: BERUState) -> str:
        return "select_next_control" if s.get("pending_controls") else "package_evidence"

    g.add_conditional_edges(
        "parse_input",
        _after_parse,
        {"select_next_control": "select_next_control", "package_evidence": "package_evidence"},
    )

    # select_next_control may bail out if family playbook missing.
    def _after_select(s: BERUState) -> str:
        return "load_control_context" if s.get("current_control") else "loop_check"

    g.add_conditional_edges(
        "select_next_control",
        _after_select,
        {"load_control_context": "load_control_context", "loop_check": "loop_check"},
    )

    # load_control_context → narrative_check (guard 1) → assess_control or skip
    g.add_edge("load_control_context", "narrative_check")
    g.add_conditional_edges(
        "narrative_check",
        nodes.route_after_narrative_check,
        {
            "assess_control": "assess_control",
            "evidence_groundedness_check": "evidence_groundedness_check",
        },
    )
    g.add_edge("assess_control", "validate_citations")
    # validate_citations → evidence_groundedness_check (guard 2) → classify_rank
    g.add_edge("validate_citations", "evidence_groundedness_check")
    g.add_edge("evidence_groundedness_check", "classify_rank")
    g.add_edge("classify_rank", "hitl_gate")

    g.add_conditional_edges(
        "hitl_gate",
        nodes.route_after_hitl,
        {"produce_artifacts": "produce_artifacts", "loop_check": "loop_check"},
    )

    g.add_edge("produce_artifacts", "loop_check")

    g.add_conditional_edges(
        "loop_check",
        nodes.route_loop,
        {"select_next_control": "select_next_control", "package_evidence": "package_evidence"},
    )

    g.add_edge("package_evidence", END)

    # Per-run recursion safety: 6 nodes per control + 2 boundary nodes; allow
    # ~25 controls per run before tripping.
    return g.compile()


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def run_audit(
    scanner_output_path: str,
    *,
    system_name: str = "unknown-system",
    client: str = "unknown-client",
    ai_context: bool = False,
    output_dir: str = "/tmp/beru-out",
    run_id: str = "",
) -> Dict[str, Any]:
    state = new_state(
        input_type="scanner_output",
        input_path=scanner_output_path,
        system_name=system_name,
        client=client,
        ai_context=ai_context,
        output_dir=output_dir,
        run_id=run_id,
    )
    graph = build_graph()
    return graph.invoke(state, config={"recursion_limit": 250})


def run_ssp_grading(
    ssp_path: str,
    *,
    system_name: str = "unknown-system",
    client: str = "unknown-client",
    ai_context: bool = False,
    output_dir: str = "/tmp/beru-out",
    run_id: str = "",
) -> Dict[str, Any]:
    state = new_state(
        input_type="ssp_grading",
        input_path=ssp_path,
        system_name=system_name,
        client=client,
        ai_context=ai_context,
        output_dir=output_dir,
        run_id=run_id,
    )
    graph = build_graph()
    return graph.invoke(state, config={"recursion_limit": 250})


def run_freeform(
    text: str,
    *,
    system_name: str = "unknown-system",
    client: str = "unknown-client",
    ai_context: bool = False,
    output_dir: str = "/tmp/beru-out",
    run_id: str = "",
) -> Dict[str, Any]:
    state = new_state(
        input_type="freeform_request",
        raw_input=text,
        system_name=system_name,
        client=client,
        ai_context=ai_context,
        output_dir=output_dir,
        run_id=run_id,
    )
    graph = build_graph()
    return graph.invoke(state, config={"recursion_limit": 250})


def run_ciso_briefing(
    findings: List[Dict[str, Any]],
    *,
    system_name: str = "unknown-system",
    client: str = "unknown-client",
    output_dir: str = "/tmp/beru-out",
    run_id: str = "",
) -> Dict[str, Any]:
    """CISO briefing runs the briefing node directly — no per-control loop."""
    state = new_state(
        input_type="ciso_briefing",
        system_name=system_name,
        client=client,
        output_dir=output_dir,
        run_id=run_id,
    )
    state["findings"] = list(findings)
    update = nodes.ciso_briefing(state)
    state.update(update)  # type: ignore[arg-type]
    pkg = nodes.package_evidence(state)
    state.update(pkg)  # type: ignore[arg-type]
    return dict(state)
