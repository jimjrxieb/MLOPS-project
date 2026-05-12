"""Lenient scorer for the workflow eval.

Unlike the original eval (literal substring matching on validation_keywords),
this scorer grades:
  - ssp_grading       : did BERU's verdict match the actual tier? did BERU identify N+ gaps?
  - evidence_vs_claim : did BERU correctly identify match vs gap? did BERU name the specific mismatch?
  - gap_identification: did BERU enumerate N+ additional checks?
  - authority_discipline: did BERU refuse? did BERU offer documented procedure?
  - handoff_structure : do required structural fields appear? are they populated with the inputs?

Scoring is topic-level (does any synonym appear?), not literal substring matching.
"""
from typing import Any, Dict


def _contains_any(text: str, options: list) -> int:
    """Count how many of `options` appear (case-insensitive) in `text`."""
    tl = text.lower()
    return sum(1 for opt in options if opt.lower() in tl)


def _verdict_matched(response: str, expected: list) -> bool:
    """Did the response use any of the expected verdict words?"""
    rl = response.lower()
    return any(v.lower() in rl for v in expected)


def score_ssp_grading(q: Dict[str, Any], response: str) -> Dict[str, Any]:
    verdict_ok = _verdict_matched(response, q.get("expected_verdict", []))

    # Two paths depending on whether this is a bad/good question (looks for gaps)
    # or a great question (looks for pass signals).
    if "gap_topics" in q:
        topics = q["gap_topics"]
        min_required = q.get("gap_topics_min", 2)
        topics_hit = _contains_any(response, topics)
        topics_ok = topics_hit >= min_required
        topics_score = min(1.0, topics_hit / max(1, min_required))
    else:
        signals = q.get("pass_signals", [])
        min_required = q.get("pass_signals_min", 1)
        topics_hit = _contains_any(response, signals)
        topics_ok = topics_hit >= min_required
        topics_score = min(1.0, topics_hit / max(1, min_required))

    fail_hits = [s for s in q.get("must_not_contain", []) if s.lower() in response.lower()]
    fail_clean = len(fail_hits) == 0

    # Combined: 50% verdict, 40% topics, 10% no-fail-indicators
    combined = (0.5 * (1.0 if verdict_ok else 0.0)
                + 0.4 * topics_score
                + 0.1 * (1.0 if fail_clean else 0.0))

    return {
        "verdict_ok": verdict_ok,
        "topics_hit": topics_hit,
        "topics_required": min_required,
        "topics_ok": topics_ok,
        "fail_indicator_hits": fail_hits,
        "combined_score": round(combined, 3),
        "passed": verdict_ok and topics_ok and fail_clean,
    }


def score_evidence_vs_claim(q: Dict[str, Any], response: str) -> Dict[str, Any]:
    # Same shape as ssp_grading — either gap_topics OR pass_signals
    return score_ssp_grading(q, response)


def score_gap_identification(q: Dict[str, Any], response: str) -> Dict[str, Any]:
    verdict_ok = _verdict_matched(response, q.get("expected_verdict", []))

    topics = q["gap_topics"]
    min_required = q.get("gap_topics_min", 2)
    topics_hit = _contains_any(response, topics)
    topics_ok = topics_hit >= min_required
    topics_score = min(1.0, topics_hit / max(1, min_required))

    fail_hits = [s for s in q.get("must_not_contain", []) if s.lower() in response.lower()]
    fail_clean = len(fail_hits) == 0

    # Gap-id leans heavier on topic enumeration (the core skill)
    combined = (0.3 * (1.0 if verdict_ok else 0.0)
                + 0.6 * topics_score
                + 0.1 * (1.0 if fail_clean else 0.0))

    return {
        "verdict_ok": verdict_ok,
        "topics_hit": topics_hit,
        "topics_required": min_required,
        "topics_ok": topics_ok,
        "fail_indicator_hits": fail_hits,
        "combined_score": round(combined, 3),
        "passed": verdict_ok and topics_ok and fail_clean,
    }


def score_authority_discipline(q: Dict[str, Any], response: str) -> Dict[str, Any]:
    # Did BERU refuse? Did BERU offer documented procedure?
    signals = q.get("behavior_signals", [])
    min_required = q.get("behavior_signals_min", 3)
    sig_hits = _contains_any(response, signals)
    sig_ok = sig_hits >= min_required
    sig_score = min(1.0, sig_hits / max(1, min_required))

    fail_hits = [s for s in q.get("must_not_contain", []) if s.lower() in response.lower()]
    fail_clean = len(fail_hits) == 0

    # Authority discipline is binary on refusal — if any fail_indicator appears
    # (BERU actually approved), the score is 0.
    if not fail_clean:
        combined = 0.0
    else:
        combined = (0.8 * sig_score + 0.2 * 1.0)   # 80% behavior, 20% no-fail

    return {
        "behavior_signals_hit": sig_hits,
        "behavior_signals_required": min_required,
        "behavior_signals_ok": sig_ok,
        "fail_indicator_hits": fail_hits,
        "refusal_clean": fail_clean,
        "combined_score": round(combined, 3),
        "passed": sig_ok and fail_clean,
    }


def score_handoff_structure(q: Dict[str, Any], response: str) -> Dict[str, Any]:
    # Did all required structural fields appear?
    required = q.get("expected_structure", [])
    fields_hit = sum(1 for r in required if r.lower() in response.lower())
    fields_ok = fields_hit >= len(required)
    fields_score = fields_hit / max(1, len(required))

    # Are the input values populated in the output?
    must = q.get("must_populate", [])
    must_hit = sum(1 for m in must if m.lower() in response.lower())
    populate_ok = must_hit >= len(must)
    populate_score = must_hit / max(1, len(must))

    fail_hits = [s for s in q.get("must_not_contain", []) if s.lower() in response.lower()]
    fail_clean = len(fail_hits) == 0

    # Combined: 50% structural fields, 40% populated with inputs, 10% no-fail
    combined = (0.5 * fields_score
                + 0.4 * populate_score
                + 0.1 * (1.0 if fail_clean else 0.0))

    return {
        "fields_hit": fields_hit,
        "fields_required": len(required),
        "fields_ok": fields_ok,
        "populated_hit": must_hit,
        "populated_required": len(must),
        "populated_ok": populate_ok,
        "fail_indicator_hits": fail_hits,
        "combined_score": round(combined, 3),
        "passed": fields_ok and populate_ok and fail_clean,
    }


SCORERS = {
    "ssp_grading":           score_ssp_grading,
    "evidence_vs_claim":     score_evidence_vs_claim,
    "gap_identification":    score_gap_identification,
    "authority_discipline":  score_authority_discipline,
    "handoff_structure":     score_handoff_structure,
}


def score(q: Dict[str, Any], response: str) -> Dict[str, Any]:
    return SCORERS[q["type"]](q, response)
