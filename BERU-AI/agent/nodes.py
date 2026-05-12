"""LangGraph nodes for the BERU agent.

Each node is a pure function: takes the current BERUState and returns a partial
update dict. The graph engine merges updates back into state.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .playbook_loader import (
    PLAYBOOK_DIR,
    ai_rmf_subcategories_for,
    available_control_ids,
    control_exists,
    family_playbook_path,
    load_control,
    load_family_playbook,
    load_ssp_example,
    load_start_here,
    load_template,
)
from .state import BERUState

# Reusable regexes
_NIST_RE = re.compile(r"\b[A-Z]{2}-\d+(?:\(\d+\))?\b")
_AI_RMF_RE = re.compile(r"\b(?:GOVERN|MAP|MEASURE|MANAGE)-\d+\.\d+\b")
_STATUS_RE = re.compile(r"\bSTATUS\s*:?\s*\**\s*(PASS|PARTIAL|FAIL)", re.IGNORECASE)
_RANK_RE = re.compile(r"\bRANK\s*:?\s*\**\s*([EDCBS])\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Provider / tool wiring — imported lazily so test runs don't require Ollama
# ---------------------------------------------------------------------------
def _make_provider(stub: bool):
    if stub:
        return _StubProvider()
    from providers.ollama import OllamaProvider
    return OllamaProvider()


class _StubProvider:
    """Deterministic stand-in for the brain. Lets the graph run end-to-end without Ollama."""

    def chat(self, messages, temperature=0.1, max_tokens=1200) -> str:
        # Pull the control ID out of the prompt for the stub finding.
        joined = "\n".join(m.get("content", "") for m in messages)
        m = _NIST_RE.search(joined)
        cid = m.group(0) if m else "CM-6"
        return (
            f"FINDING: Stubbed assessment for {cid}.\n"
            f"CONTROL: {cid}\n"
            "AI RMF: n/a\n"
            "STATUS: PARTIAL\n"
            "EVIDENCE REVIEWED: stub-evidence.txt (dry-run)\n"
            "EVIDENCE GAP: dry-run; no real evidence reviewed\n"
            "RISK: Likelihood Medium x Impact Medium -> Rank C\n"
            "CONTROL OWNER: Platform Team\n"
            "POA&M ITEM: Stubbed remediation; replace with real assessment.\n"
            "CISO SUMMARY: Dry-run smoke test of the BERU graph wiring."
        )


def _get_mapper():
    from core.nist_mapper import NISTMapper
    return NISTMapper()


def _get_triage():
    from core.triage_engine import TriageEngine
    return TriageEngine()


def _get_hitl():
    from tools.hitl_router import HITLRouter
    return HITLRouter()


def _get_packager(output_dir: str):
    from tools.evidence_packager import EvidencePackager
    return EvidencePackager(output_dir=output_dir)


def _get_findings_ingestion():
    from core.findings_ingestion import FindingsIngestion
    return FindingsIngestion()


def _get_ssp_parser():
    # enforce_synthetic gate is for training-corpus ingestion (D-005, MAP-4.1).
    # The agent reads SSPs to grade them, not to add them to the corpus, so the
    # gate is disabled here. Corpus ingestion still uses the default (strict).
    from tools.ssp_parser import SSPParser
    return SSPParser(enforce_synthetic=False)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
# Matches "**AC-2**: narrative", "AC-2: narrative", "AC-6(5) — narrative" — one per line.
_SSP_CLAIM_RE = re.compile(
    r"^\s*\**\s*([A-Z]{2}-\d+(?:\(\d+\))?)\s*\**\s*[:\-—]\s*(.+?)\s*$",
    re.MULTILINE,
)


def _extract_ssp_claims(text: str) -> List[Dict[str, Any]]:
    """Pull `<CONTROL>: <narrative>` lines straight out of pasted SSP text.

    Backstop for the structured SSP parser, which only recognizes control
    sections when they have a list-like shape (≥2 entries / a known header).
    A user pasting one control line gets handled too.
    """
    out: List[Dict[str, Any]] = []
    seen = set()
    for m in _SSP_CLAIM_RE.finditer(text or ""):
        cid = m.group(1).split("(")[0]
        narrative = m.group(2).strip()
        if cid in seen:
            continue
        seen.add(cid)
        out.append({"chunk_type": "control_implementation", "control_id": cid,
                    "text": narrative, "source_file": "pasted"})
    return out


def _merge_ssp_chunks(parser_chunks: List[Dict[str, Any]], raw_text: str,
                      candidate: List[str], evidence: List[Dict[str, Any]]) -> None:
    """Take whatever the parser found, then backfill from a regex pass over the
    raw text so single-line pastes and odd formatting still produce controls."""
    have_cid = set()
    for c in parser_chunks:
        cid = c.get("control_id")
        if cid and control_exists(cid) and cid not in candidate:
            candidate.append(cid)
        if cid:
            have_cid.add(cid)
        evidence.append({"ssp_chunk": c})
    for c in _extract_ssp_claims(raw_text):
        cid = c["control_id"]
        if cid in have_cid:
            continue  # parser already covered it
        if control_exists(cid) and cid not in candidate:
            candidate.append(cid)
        evidence.append({"ssp_chunk": c})


def parse_input(state: BERUState) -> Dict[str, Any]:
    """Classify input + extract initial evidence items and candidate control IDs."""
    itype = state["input_type"]
    raw = state.get("raw_input", "")
    path = state.get("input_path")
    ai_context = state.get("ai_context", False)

    evidence: List[Dict[str, Any]] = []
    candidate_controls: List[str] = []
    errors: List[str] = []

    if itype == "scanner_output":
        if not path:
            errors.append("scanner_output input requires input_path")
        else:
            try:
                findings_raw = _get_findings_ingestion().ingest_file(Path(path))
                mapper = _get_mapper()
                for f in findings_raw:
                    f.setdefault("ai_context", ai_context)
                    mapped = mapper.map_finding(f)
                    f["mapped_controls"] = mapped.get("controls", [])
                    f["mapped_ai_rmf"] = mapped.get("ai_rmf_subcategories", [])
                    evidence.append(f)
                    for cid in mapped.get("controls", []):
                        if cid not in candidate_controls and control_exists(cid):
                            candidate_controls.append(cid)
            except Exception as e:
                errors.append(f"scanner ingestion failed: {e}")

    elif itype == "ssp_grading":
        if not path and not raw:
            errors.append("ssp_grading input requires input_path or raw_input")
        else:
            try:
                parser = _get_ssp_parser()
                raw_text = Path(path).read_text(errors="replace") if path else raw
                chunks = parser.parse_file(path) if path else parser.parse_text(raw, "inline")
                _merge_ssp_chunks(chunks, raw_text, candidate_controls, evidence)
            except Exception as e:
                errors.append(f"ssp parse failed: {e}")

    elif itype == "assessment":
        # SSP (the system owner's CLAIMS) + evidence artifacts (scanner output,
        # policy docs, command outputs). We assess the controls the SSP claims,
        # using the evidence to confirm or contradict each claim.
        if not path and not raw:
            errors.append("assessment requires an SSP (input_path or ssp_text)")
        else:
            try:
                parser = _get_ssp_parser()
                raw_text = Path(path).read_text(errors="replace") if path else raw
                chunks = parser.parse_file(path) if path else parser.parse_text(raw, "inline")
                _merge_ssp_chunks(chunks, raw_text, candidate_controls, evidence)
            except Exception as e:
                errors.append(f"ssp parse failed: {e}")

        # Evidence files: try to parse as scanner output (so findings map to
        # controls); if that yields nothing, treat the file as a policy/text
        # artifact and include it as general context for every control.
        mapper = _get_mapper()
        for ep in state.get("evidence_paths", []) or []:
            p = Path(ep)
            if not p.exists():
                errors.append(f"evidence path not found: {ep}")
                continue
            attached = False
            try:
                findings_raw = _get_findings_ingestion().ingest_file(p)
                for f in findings_raw:
                    f.setdefault("ai_context", ai_context)
                    mapped = mapper.map_finding(f)
                    f["mapped_controls"] = mapped.get("controls", [])
                    f["mapped_ai_rmf"] = mapped.get("ai_rmf_subcategories", [])
                    f["evidence_label"] = p.name
                    evidence.append(f)
                    attached = True
            except Exception:
                pass
            if not attached:
                try:
                    evidence.append({"freeform": p.read_text(errors="replace")[:8000],
                                     "label": f"evidence:{p.name}"})
                except Exception as e2:
                    errors.append(f"could not read evidence {ep}: {e2}")

        # Inline evidence blobs (pasted text — policy excerpts, command outputs).
        for i, blob in enumerate(state.get("evidence_text", []) or []):
            if blob and blob.strip():
                evidence.append({"freeform": blob[:8000], "label": f"evidence:inline-{i+1}"})

    elif itype == "freeform_request":
        # Pull any explicit control IDs out of the user's text.
        for m in _NIST_RE.finditer(raw):
            cid = m.group(0).split("(")[0]
            if cid not in candidate_controls and control_exists(cid):
                candidate_controls.append(cid)
        # If the text names no control IDs (e.g. a pasted scanner finding), infer
        # candidate controls from its content via the deterministic mapper.
        if not candidate_controls:
            try:
                mapped = _get_mapper().map_finding({
                    "title": raw[:200], "description": raw[:4000],
                    "ai_context": ai_context,
                })
                for cid in mapped.get("controls", []):
                    if control_exists(cid) and cid not in candidate_controls:
                        candidate_controls.append(cid)
            except Exception as e:
                errors.append(f"control inference failed: {e}")
        evidence.append({"freeform": raw})

    elif itype == "ciso_briefing":
        # No discovery — caller already populated state.findings.
        pass

    return {
        "pending_controls": candidate_controls,
        "evidence": evidence,
        "errors": errors,
    }


def select_next_control(state: BERUState) -> Dict[str, Any]:
    """Pop the next pending control and resolve its family playbook.

    Per-control working-memory fields are reset here so state from the previous
    iteration doesn't leak into this one. Accumulators (findings, poam_items,
    ssp_narratives, blocked_findings) are NOT reset — they use operator.add
    reducers and grow across iterations.
    """
    pending = list(state.get("pending_controls", []))
    if not pending:
        return {"current_control": None}
    cid = pending.pop(0)
    # Reset all per-control state every iteration. If we don't, prior values
    # (raw_finding_text, evidence_hallucination, validation_errors, etc.)
    # carry over and contaminate this control's assessment.
    reset = {
        "current_control": cid,
        "pending_controls": pending,
        "control_definition": "",
        "validated_control_ids": [],
        "validated_ai_rmf_ids": [],
        "raw_finding_text": "",
        "validation_errors": [],
        "finding": {},
        "rank": "",
        "deterministic_finding": False,
        "evidence_hallucination": False,
    }
    try:
        reset["family_playbook_path"] = str(family_playbook_path(cid))
    except FileNotFoundError as e:
        reset["current_control"] = None
        return {**reset, "errors": [f"family playbook lookup failed for {cid}: {e}"]}
    return reset


def load_control_context(state: BERUState) -> Dict[str, Any]:
    """Load controls/<ID>.md and pre-compute the validated-citation allow-list."""
    cid = state.get("current_control")
    if not cid:
        return {"errors": ["load_control_context called without a current_control"]}

    control_text = load_control(cid)

    # Allow-list for output guard: the active control + anything referenced in
    # the control file itself (so cross-references like AC-6 inside AC-2.md don't
    # trip the validator).
    allowed_controls = {cid}
    for m in _NIST_RE.finditer(control_text):
        allowed_controls.add(m.group(0).split("(")[0])
    allowed_controls = {c for c in allowed_controls if control_exists(c)}

    allowed_ai_rmf: List[str] = []
    if state.get("ai_context"):
        allowed_ai_rmf = ai_rmf_subcategories_for(cid)

    return {
        "control_definition": control_text,
        "validated_control_ids": sorted(allowed_controls),
        "validated_ai_rmf_ids": allowed_ai_rmf,
    }


_STUB_TOKENS = {
    "configured", "configured.", "enabled", "enabled.", "implemented",
    "implemented.", "yes", "yes.", "in place", "in place.", "done", "done.",
    "ok", "ok.", "compliant", "compliant.", "n/a", "tbd",
}
_STUB_MIN_CHARS = 50


def narrative_check(state: BERUState) -> Dict[str, Any]:
    """Stub-narrative pre-detector — runs BEFORE assess_control.

    If the SSP claim for the current control is shorter than _STUB_MIN_CHARS
    (after stripping whitespace) or consists of one of the known stub tokens,
    we synthesize a deterministic FAIL finding without invoking the brain.
    The brain hallucinated implementation details on one-word SSPs in the
    M4 smoke test — this guard kills that failure mode at the source.

    AI RMF / 800-53 traceability:
      MAP-2.3       — AI system documentation must be complete; stub claims aren't
      MEASURE-2.5   — Validity: a claim with no implementation detail is unverifiable
      MANAGE-2.1    — Risk treatment: refuse to validate what hasn't been documented
      800-53 PL-2   — SSP must document each control's implementation
    """
    cid = state.get("current_control")
    if not cid:
        return {}

    # Find the SSP chunk that covers this control, if any.
    narrative = ""
    for ev in state.get("evidence", []):
        chunk = ev.get("ssp_chunk") if isinstance(ev, dict) else None
        if isinstance(chunk, dict) and chunk.get("control_id") == cid:
            narrative = (chunk.get("text") or chunk.get("narrative") or "").strip()
            break

    if not narrative:
        return {}  # no SSP claim for this control — assess normally

    stripped = narrative.strip()
    is_stub = (
        len(stripped) < _STUB_MIN_CHARS
        or stripped.lower() in _STUB_TOKENS
        or stripped.lower().rstrip(".").rstrip() in _STUB_TOKENS
    )

    if not is_stub:
        return {}

    deterministic = (
        f"FINDING: SSP narrative for {cid} provides no implementation detail "
        f"(claim: {stripped!r}).\n"
        f"CONTROL: {cid}\n"
        f"AI RMF: n/a\n"
        f"STATUS: FAIL\n"
        f"EVIDENCE REVIEWED: SSP {state.get('input_path', 'inline')} — narrative for {cid}\n"
        f"EVIDENCE GAP: SSP claim for {cid} contains no implementation detail. "
        f"Required: documented implementation, responsible party, evidence pointer, "
        f"and validation method.\n"
        f"RISK: Likelihood Medium x Impact Medium -> Rank C — control claim is "
        f"unverifiable; treat as not-implemented until SSP is rewritten.\n"
        f"CONTROL OWNER: (look up via control-owner-matrix.md)\n"
        f"POA&M ITEM: Rewrite the SSP narrative for {cid} to the great-tier rubric "
        f"in ssp-examples/. Include implementation, responsible party, evidence "
        f"pointer with timestamp, and validation command. Scheduled completion: TBD.\n"
        f"CISO SUMMARY: The plan-of-record for {cid} is a single phrase, not a "
        f"described implementation. Auditors will reject this on first read. "
        f"Remediation is documentation, not infrastructure work."
    )
    return {
        "raw_finding_text": deterministic,
        "deterministic_finding": True,
    }


def assess_control(state: BERUState) -> Dict[str, Any]:
    """Call the brain to produce a 9-field finding for the current control."""
    cid = state.get("current_control")
    if not cid:
        return {"errors": ["assess_control called without a current_control"]}

    control_text = state.get("control_definition", "")
    family_playbook = load_family_playbook(cid.split("-")[0])
    template = load_template("beru-finding")

    # Filter evidence relevant to this control.
    relevant_evidence: List[Dict[str, Any]] = []
    for ev in state.get("evidence", []):
        if cid in (ev.get("mapped_controls") or []):
            relevant_evidence.append(ev)
        elif "ssp_chunk" in ev and ev["ssp_chunk"].get("control_id") == cid:
            relevant_evidence.append(ev)
        elif "freeform" in ev:
            relevant_evidence.append(ev)

    evidence_block = (
        "\n\n".join(json.dumps(e, indent=2)[:1500] for e in relevant_evidence)
        if relevant_evidence
        else "(no evidence collected — note this as an EVIDENCE GAP)"
    )
    ai_rmf_hint = (
        f"\nWhen citing AI RMF, you may only use: {state.get('validated_ai_rmf_ids', [])}."
        if state.get("ai_context") and state.get("validated_ai_rmf_ids")
        else ""
    )
    assessment_hint = ""
    if state.get("input_type") == "assessment":
        assessment_hint = (
            "\n\nThis is an evidence-vs-claim assessment. The SSP narrative above is the "
            "system owner's CLAIM about how this control is implemented. The other evidence "
            "is what you actually have to verify it. Rules: STATUS=PASS only if the claim is "
            "BOTH documented in the SSP AND supported by the evidence; STATUS=PARTIAL if the "
            "claim is documented but the evidence is incomplete — name the specific missing "
            "artifact in EVIDENCE GAP; STATUS=FAIL if the SSP claim is missing or a stub, OR "
            "the evidence contradicts the claim. Do not pass a control on the strength of the "
            "narrative alone — a claim without supporting evidence is at best PARTIAL."
        )

    user_msg = (
        f"You are assessing control {cid}.\n\n"
        f"--- Control definition (read first) ---\n{control_text}\n\n"
        f"--- Family playbook (assessment rubric) ---\n{family_playbook[:3000]}\n\n"
        f"--- Evidence reviewed ---\n{evidence_block}\n\n"
        f"--- Output template ---\n{template}\n\n"
        f"Produce the BERU finding for {cid}. Cite only validated controls "
        f"({state.get('validated_control_ids', [cid])}).{ai_rmf_hint}{assessment_hint}"
    )

    provider = _make_provider((state.get("run_id") or "").endswith("-dry"))
    try:
        text = provider.chat(
            [{"role": "user", "content": user_msg}],
            temperature=0.1,
            max_tokens=1200,
        )
    except Exception as e:
        return {"errors": [f"brain call failed for {cid}: {e}"], "raw_finding_text": ""}
    return {"raw_finding_text": text}


def validate_citations(state: BERUState) -> Dict[str, Any]:
    """Reject the finding if it cites unknown control or AI RMF IDs.

    The brain is fine-tuned to avoid hallucination but the guard is the
    architectural protection: no finding ships with a citation we cannot
    point at a file in controls/.
    """
    text = state.get("raw_finding_text", "")
    if not text.strip():
        return {"validation_errors": ["empty finding text"]}

    cited_controls = {m.group(0).split("(")[0] for m in _NIST_RE.finditer(text)}
    cited_ai_rmf = {m.group(0) for m in _AI_RMF_RE.finditer(text)}

    allowed_controls = set(state.get("validated_control_ids", []))
    allowed_ai_rmf = set(state.get("validated_ai_rmf_ids", []))

    errs: List[str] = []
    bad_controls = cited_controls - allowed_controls
    if bad_controls:
        errs.append(f"finding cites controls not in allow-list: {sorted(bad_controls)}")
    if state.get("ai_context"):
        bad_ai_rmf = cited_ai_rmf - allowed_ai_rmf
        if bad_ai_rmf:
            errs.append(f"finding cites AI RMF IDs not in allow-list: {sorted(bad_ai_rmf)}")

    # Also reject if any cited control doesn't exist as a file
    nonexistent = [c for c in cited_controls if not control_exists(c)]
    if nonexistent:
        errs.append(f"finding cites controls with no controls/<ID>.md: {sorted(nonexistent)}")

    return {"validation_errors": errs}


_EVIDENCE_BLOCK_RE = re.compile(
    r"EVIDENCE\s+REVIEWED\s*:?\s*\**\s*\n?(.*?)(?=\n\s*(?:EVIDENCE\s+GAP|RISK|CONTROL\s+OWNER|POA&M|CISO\s+SUMMARY)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
# Tokens we extract from the model's EVIDENCE REVIEWED block for grounding.
# Each pattern captures something concrete the brain claimed to have looked at.
_EVIDENCE_TOKEN_RES = [
    re.compile(r"(?<![\w./])(/[a-zA-Z0-9_\-./]+\.(?:yaml|yml|json|log|conf|md|txt|tf|sh|py))\b"),
    re.compile(r"\b([a-zA-Z][a-zA-Z0-9_\-]{2,}\.(?:json|yaml|yml|log|conf|md|txt|sarif))\b"),
    re.compile(r"\b((?:https?|s3|arn):/?/?[A-Za-z0-9_\-./:%@?=&+]+)\b"),
    re.compile(r"\b(kubectl|kube-bench|kubescape|trivy|prowler|falco|gitleaks|semgrep|polaris|cosign|kyverno|cloudtrail|guardduty|rbac-lookup|garak|promptfoo)\b", re.IGNORECASE),
]
_EVIDENCE_MIN_TOKEN_LEN = 4


def _tokens_in_evidence_block(text: str) -> List[str]:
    """Return concrete artifact tokens the brain claimed to have reviewed."""
    m = _EVIDENCE_BLOCK_RE.search(text)
    if not m:
        return []
    block = m.group(1)
    found: List[str] = []
    for pat in _EVIDENCE_TOKEN_RES:
        for tok_m in pat.finditer(block):
            tok = tok_m.group(1)
            if len(tok) >= _EVIDENCE_MIN_TOKEN_LEN and tok not in found:
                found.append(tok)
    return found


def evidence_groundedness_check(state: BERUState) -> Dict[str, Any]:
    """Post-validator — every concrete artifact the brain cites in EVIDENCE
    REVIEWED must appear in the source input (SSP body, scanner output, or
    the control file). Anything else is hallucinated evidence.

    Hallucinated evidence does NOT silently get dropped — it gets flagged
    and the finding's rank is bumped to B in classify_rank so the HITL
    queue catches it. The model can speculate; the agent will not ship
    speculation as evidence.

    AI RMF / 800-53 traceability:
      MEASURE-2.5  — Validity: outputs must be supported by reviewed evidence
      MEASURE-2.6  — RAG/retrieval grounding: catches generation beyond context
      MANAGE-2.1   — Risk treatment: hallucinated PASS is the target failure mode
      GOVERN-1.4   — Accountability: every output must trace to evidence
      800-53 SI-10 — Information Input Validation (symmetric: applies to output)
      800-53 AU-3  — Audit Record Content: evidence references must be auditable
    """
    text = state.get("raw_finding_text", "")
    if not text.strip():
        return {}

    # Deterministic findings are constructed by Guard 1, not by the model.
    # Their citations are by construction grounded in the input — running Guard 3
    # on them would false-flag tokens we put there ourselves (e.g., the SSP path).
    if state.get("deterministic_finding"):
        return {}

    # Build the haystack: everything the model was actually allowed to look at.
    haystack_parts: List[str] = []
    cid = state.get("current_control") or ""
    if cid:
        # The control file itself is implicitly grounded: BERU was given it to read.
        # Adding the filename forms lets the brain cite `controls/AC-2.md` or `AC-2.md`
        # without tripping a false positive.
        haystack_parts.extend([cid, f"{cid}.md", f"controls/{cid}.md"])
    if state.get("control_definition"):
        haystack_parts.append(state["control_definition"])
    for ev in state.get("evidence", []):
        if not isinstance(ev, dict):
            continue
        if "ssp_chunk" in ev:
            chunk = ev["ssp_chunk"] or {}
            haystack_parts.append(chunk.get("text", ""))
            haystack_parts.append(chunk.get("narrative", ""))
            haystack_parts.append(chunk.get("source_file", ""))
        elif "freeform" in ev:
            haystack_parts.append(ev["freeform"])
        else:
            # raw scanner finding — dump its visible fields
            for k in ("title", "description", "source_file"):
                if ev.get(k):
                    haystack_parts.append(str(ev[k]))
            raw_fields = ev.get("raw_fields") or {}
            if isinstance(raw_fields, dict):
                haystack_parts.append(" ".join(str(v) for v in raw_fields.values()))
    haystack = "\n".join(haystack_parts).lower()

    cited_tokens = _tokens_in_evidence_block(text)
    hallucinated = [t for t in cited_tokens if t.lower() not in haystack]
    errs: List[str] = list(state.get("validation_errors", []))
    is_hallucinating = False
    if hallucinated:
        is_hallucinating = True
        errs.append(
            f"evidence hallucination: cited tokens not found in source input: "
            f"{hallucinated[:6]}"
        )
    return {
        "validation_errors": errs,
        "evidence_hallucination": is_hallucinating,
    }


def classify_rank(state: BERUState) -> Dict[str, Any]:
    """Extract STATUS + RANK from the finding text; fall back to triage engine on rank."""
    text = state.get("raw_finding_text", "")
    cid = state.get("current_control", "")

    status_m = _STATUS_RE.search(text)
    status = status_m.group(1).upper() if status_m else "PARTIAL"

    rank_m = _RANK_RE.search(text)
    rank = rank_m.group(1).upper() if rank_m else ""

    if not rank:
        try:
            triage = _get_triage()
            # TriageEngine expects a finding-like dict; pass what we have.
            t = triage.classify({"control": cid, "status": status, "title": cid, "description": text[:500]})
            rank = (t.get("rank") if isinstance(t, dict) else "") or "C"
        except Exception:
            rank = "C"

    # Evidence-hallucination override: any finding whose EVIDENCE REVIEWED block
    # cites artifacts not present in the source input gets escalated to B-rank.
    # The HITL gate downstream catches B-rank and routes to a human reviewer.
    # AI RMF: MANAGE-2.2 (human oversight) + MEASURE-2.5 (validity).
    bumped = False
    if state.get("evidence_hallucination") and rank in ("E", "D", "C"):
        rank = "B"
        bumped = True

    finding = {
        "control_id": cid,
        "status": status,
        "rank": rank,
        "raw": text,
        "ai_context": state.get("ai_context", False),
        "system_name": state.get("system_name", ""),
        "client": state.get("client", ""),
        "run_id": state.get("run_id", ""),
        "deterministic": state.get("deterministic_finding", False),
        "evidence_hallucination": state.get("evidence_hallucination", False),
        "rank_bumped_for_hallucination": bumped,
        "validation_errors": list(state.get("validation_errors", [])),
    }
    return {"finding": finding, "rank": rank}


def hitl_gate(state: BERUState) -> Dict[str, Any]:
    """Route B/S findings to the human queue; pass E/D/C through."""
    finding = dict(state.get("finding", {}))
    if not finding:
        return {"errors": ["hitl_gate called without a finding"]}

    try:
        result = _get_hitl().route(finding)
    except Exception as e:
        # HITLBlockedError is the expected B/S signal — anything else is real.
        msg = f"{type(e).__name__}: {e}"
        if "Blocked" in type(e).__name__ or "blocked" in msg.lower():
            blocked = dict(finding)
            blocked["hitl_status"] = "BLOCKED"
            blocked["hitl_reason"] = msg
            return {"blocked_findings": [blocked]}
        return {"errors": [f"hitl_router failed: {msg}"]}

    # HITLRouter returns auto_ok=False for B/S; status is 'pending_human' (not 'BLOCKED').
    # Treat any non-auto-ok result as a hold.
    is_held = (
        result.get("auto_ok") is False
        or result.get("status") in ("pending_human", "BLOCKED")
    )
    if is_held:
        blocked = dict(finding)
        blocked["hitl_status"] = "BLOCKED"
        blocked["hitl_meta"] = result
        return {"blocked_findings": [blocked]}

    return {"finding": {**finding, "hitl_status": "APPROVED", "hitl_meta": result}}


def produce_artifacts(state: BERUState) -> Dict[str, Any]:
    """For FAIL/PARTIAL → produce POA&M item. For PASS → draft SSP narrative."""
    finding = state.get("finding", {})
    cid = finding.get("control_id") or state.get("current_control", "")
    status = finding.get("status", "")

    new_poam: List[str] = []
    new_ssp: List[str] = []

    if status in ("FAIL", "PARTIAL"):
        poam_template = load_template("poam-item")
        family_pb = load_family_playbook(cid.split("-")[0]) if cid else ""
        prompt = (
            f"Convert this BERU finding into a POA&M item.\n\n"
            f"--- Finding ---\n{finding.get('raw', '')}\n\n"
            f"--- POA&M template ---\n{poam_template}\n\n"
            f"--- Family playbook (owner routing) ---\n{family_pb[:2000]}\n\n"
            f"Produce the POA&M item only. Do not invent dates — use the placeholder TBD."
        )
        provider = _make_provider(state.get("run_id", "").endswith("-dry"))
        try:
            poam_text = provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=900,
            )
            new_poam.append(poam_text)
        except Exception as e:
            return {"errors": [f"poam draft failed for {cid}: {e}"]}

    elif status == "PASS":
        family = cid.split("-")[0] if cid else ""
        great = load_ssp_example(family, "great") if family else None
        prompt = (
            f"Draft a great-tier SSP control implementation narrative for {cid}.\n\n"
            f"--- BERU finding (basis) ---\n{finding.get('raw', '')}\n\n"
            f"--- Quality reference (great-tier example for this family) ---\n"
            f"{great[:2500] if great else '(no example available; produce in the same style)'}\n\n"
            f"Write the narrative only — no headings, no extra commentary."
        )
        provider = _make_provider(state.get("run_id", "").endswith("-dry"))
        try:
            ssp_text = provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=900,
            )
            new_ssp.append(ssp_text)
        except Exception as e:
            return {"errors": [f"ssp narrative draft failed for {cid}: {e}"]}

    return {
        "findings": [finding],
        "poam_items": new_poam,
        "ssp_narratives": new_ssp,
    }


def package_evidence(state: BERUState) -> Dict[str, Any]:
    """Bundle every artifact produced this run into a timestamped ZIP."""
    output_dir = state.get("output_dir", "/tmp/beru-out")
    findings = state.get("findings", [])
    poam_text = "\n\n---\n\n".join(state.get("poam_items", []))
    ssp_text = "\n\n---\n\n".join(state.get("ssp_narratives", []))
    ciso_text = state.get("ciso_summary", "")

    try:
        pkg = _get_packager(output_dir).package(
            findings=findings,
            poam_text=poam_text,
            ssp_narrative=ssp_text,
            ciso_briefing=ciso_text,
            system_name=state.get("system_name", "unknown"),
            run_id=state.get("run_id", "beru-run"),
        )
        return {"artifact_archive_path": pkg.get("archive_path")}
    except Exception as e:
        return {"errors": [f"evidence packaging failed: {e}"]}


def ciso_briefing(state: BERUState) -> Dict[str, Any]:
    """Aggregate findings into an executive summary (only runs when called explicitly)."""
    findings = state.get("findings", [])
    if not findings:
        return {"ciso_summary": "(no findings produced)"}

    # Read the CISO briefing playbook for the rubric, then call the brain
    pb_text = (PLAYBOOK_DIR / "04-ciso-briefing.md").read_text()
    bullets = []
    for f in findings:
        bullets.append(
            f"- {f.get('control_id', '?')} | {f.get('status', '?')} | "
            f"rank {f.get('rank', '?')} | {f.get('hitl_status', '?')}"
        )
    prompt = (
        f"Produce a CISO briefing for {state.get('system_name', 'the system')}.\n\n"
        f"--- Playbook rubric ---\n{pb_text[:3500]}\n\n"
        f"--- Findings inventory ---\n{chr(10).join(bullets)}\n\n"
        f"Use business language. No NIST IDs without explanation. "
        f"Lead with material risk, then trajectory, then asks of the CISO."
    )
    provider = _make_provider(state.get("run_id", "").endswith("-dry"))
    try:
        text = provider.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )
    except Exception as e:
        return {"errors": [f"ciso briefing failed: {e}"], "ciso_summary": ""}
    return {"ciso_summary": text}


# ---------------------------------------------------------------------------
# Conditional edge helpers (the graph imports these)
# ---------------------------------------------------------------------------
def route_after_validate(state: BERUState) -> str:
    """If validation_errors exist, re-assess the control (one retry max); else continue."""
    errs = state.get("validation_errors", [])
    # We never want infinite loops — record the error and continue, downstream
    # nodes will see the issue and skip output. A real retry policy belongs
    # in a future re-author node; for now, fail open with the recorded error.
    if errs:
        return "classify_rank"  # proceed but the errors are now in state
    return "classify_rank"


def route_after_narrative_check(state: BERUState) -> str:
    """If narrative_check synthesized a deterministic finding, skip the brain."""
    if state.get("deterministic_finding"):
        return "evidence_groundedness_check"
    return "assess_control"


def route_after_hitl(state: BERUState) -> str:
    """B/S → loop back without producing artifacts. E/D/C → produce_artifacts."""
    rank = state.get("rank", "")
    if rank in ("B", "S"):
        return "loop_check"
    return "produce_artifacts"


def route_loop(state: BERUState) -> str:
    """If pending_controls non-empty → keep iterating; else → package_evidence."""
    if state.get("pending_controls"):
        return "select_next_control"
    return "package_evidence"
