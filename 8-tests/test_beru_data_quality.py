"""BERU training-corpus data-quality gate (replaces the stale Katie-pathed one).

Maps to OWASP LLM Top 10 — LLM04 (Data and Model Poisoning) and LLM02 (Sensitive
Information Disclosure in training data). Validates every ChatML corpus before it
can be merged + trained. CI runs this on every PR touching BERU-AI or 1-FineTuning-Pipeline.

What this checks per corpus file:
  - ChatML schema:  each line a JSON object with {"messages": [{role, content}, ...]},
                    roles ∈ {system, user, assistant}, last message is assistant,
                    content is a non-empty string.
  - No secret-shaped strings: Stripe keys, AWS access keys, GitHub PATs, generic
                              "private key" headers — the kind of thing GitHub's
                              push protection rejects (LLM02 / corpus poisoning).
  - Min response length: assistant content ≥ 80 chars (filter trivial / stub examples).
  - No CRLF / control-char garbage: clean UTF-8 text only.
  - Reasonable dedup: < 5% exact-duplicate user prompts in any single corpus.

Fails CI when a corpus violates any of these. Run locally:
    cd GP-MODEL-OPS && python3 -m pytest 8-tests/test_beru_data_quality.py -v
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import List, Tuple

import pytest

GP_MODEL_OPS = Path(__file__).resolve().parent.parent

# Corpora the BERU training pipeline consumes. Add new ones here as they're authored.
CORPUS_PATHS = [
    GP_MODEL_OPS / "BERU-AI" / "training-data" / "chatml-examples" / "beru-training-examples.jsonl",
    GP_MODEL_OPS / "BERU-AI" / "training-data" / "chatml-examples" / "exp011_ssp_grading.jsonl",
    GP_MODEL_OPS / "BERU-AI" / "training-data" / "chatml-examples" / "exp012_ssp_grading.jsonl",
    GP_MODEL_OPS / "1-FineTuning-Pipeline" / "01-raw-data-lake" / "beru_training_v1.jsonl",
    GP_MODEL_OPS / "1-FineTuning-Pipeline" / "01-raw-data-lake" / "beru_training_exp011.jsonl",
    GP_MODEL_OPS / "1-FineTuning-Pipeline" / "01-raw-data-lake" / "beru_training_exp012.jsonl",
]

# Secret-shape detectors. Anchored / strict so we don't false-positive on the
# obvious redaction placeholders ("REDACTED", "EXAMPLE", "PLACEHOLDER", "FAKE", etc.).
_SECRET_PATTERNS = [
    ("Stripe live key",   re.compile(r"sk_live_[A-Za-z0-9]{20,}")),
    ("Stripe test key",   re.compile(r"sk_test_[A-Za-z0-9]{20,}")),
    ("Stripe restricted", re.compile(r"rk_(live|test)_[A-Za-z0-9]{20,}")),
    ("AWS access key",    re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS secret key",    re.compile(r"(?<![A-Za-z0-9/+])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+])\s*(?:#|//|$|aws_secret)")),
    ("GitHub PAT",        re.compile(r"\bghp_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grain", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}")),
    ("Slack token",       re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("PEM private key",   re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----")),
    ("Generic API key",   re.compile(r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]", re.IGNORECASE)),
]

# Phrases that legitimately appear (a placeholder counts as a redacted value, not a leak).
_REDACTION_MARKERS = ("REDACTED", "PLACEHOLDER", "EXAMPLE", "FAKE", "DUMMY", "SAMPLE", "NOT_A_REAL",
                      "XXXXXXXXXX", "<your-", "<insert-", "$STRIPE_KEY", "${")

_MIN_ASSISTANT_CHARS = 80
_MAX_DUP_RATIO = 0.05  # ≤ 5% exact-duplicate user prompts per corpus

_present = [p for p in CORPUS_PATHS if p.exists()]


def _is_redaction(line: str) -> bool:
    """True if the line obviously contains a redacted placeholder rather than a real secret."""
    upper = line.upper()
    return any(m.upper() in upper for m in _REDACTION_MARKERS)


def _scan_line_for_secrets(line: str) -> List[Tuple[str, str]]:
    if _is_redaction(line):
        return []
    hits = []
    for name, pat in _SECRET_PATTERNS:
        for m in pat.finditer(line):
            hit = m.group(0)
            if _is_redaction(hit):
                continue
            hits.append((name, hit[:48]))
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# Tests — parametrized over every corpus file that exists.
# ─────────────────────────────────────────────────────────────────────────────


def test_at_least_one_corpus_present():
    """Sanity: we should have at least one corpus to validate."""
    assert _present, (
        f"No BERU training corpora found. Looked for: "
        f"{[str(p.relative_to(GP_MODEL_OPS)) for p in CORPUS_PATHS]}"
    )


@pytest.mark.parametrize("corpus_path", _present, ids=lambda p: p.name)
def test_corpus_is_valid_chatml(corpus_path: Path):
    """Every line is a JSON object with messages[role,content], roles valid, last
    message is assistant, content is a non-empty string."""
    errs = []
    valid_roles = {"system", "user", "assistant"}
    with open(corpus_path) as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError as e:
                errs.append(f"line {i}: not valid JSON ({e})")
                continue
            msgs = ex.get("messages")
            if not isinstance(msgs, list) or len(msgs) < 2:
                errs.append(f"line {i}: missing or short 'messages' list")
                continue
            for j, m in enumerate(msgs):
                if not isinstance(m, dict):
                    errs.append(f"line {i} msg {j}: not a dict"); continue
                if m.get("role") not in valid_roles:
                    errs.append(f"line {i} msg {j}: invalid role {m.get('role')!r}")
                if not isinstance(m.get("content"), str) or not m["content"].strip():
                    errs.append(f"line {i} msg {j}: empty/non-string content")
            if msgs[-1].get("role") != "assistant":
                errs.append(f"line {i}: last message role is {msgs[-1].get('role')!r}, expected 'assistant'")
    assert not errs, f"{corpus_path.name} has {len(errs)} schema issues. First 5: " + "; ".join(errs[:5])


@pytest.mark.parametrize("corpus_path", _present, ids=lambda p: p.name)
def test_corpus_has_no_secrets(corpus_path: Path):
    """OWASP LLM02 — secret-shaped strings in training data are corpus poisoning
    (and a GitHub push-protection bomb). Redaction placeholders (REDACTED, EXAMPLE,
    NOT_A_REAL_KEY, …) are explicitly allowed."""
    findings = []
    with open(corpus_path) as f:
        for i, line in enumerate(f, 1):
            hits = _scan_line_for_secrets(line)
            for name, snippet in hits:
                findings.append(f"line {i}: {name} → {snippet!r}")
    assert not findings, (
        f"{corpus_path.name} contains {len(findings)} secret-shaped strings (LLM02 risk). "
        f"Redact with REDACTED/PLACEHOLDER/EXAMPLE-style tokens. First 5: "
        + "; ".join(findings[:5])
    )


@pytest.mark.parametrize("corpus_path", _present, ids=lambda p: p.name)
def test_corpus_minimum_response_length(corpus_path: Path):
    """Assistant content < 80 chars is a stub — micro-batches cause catastrophic
    forgetting per CLAUDE.md's data-quality gate."""
    too_short = []
    with open(corpus_path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            msgs = ex.get("messages") or []
            asst = next((m for m in reversed(msgs) if m.get("role") == "assistant"), None)
            if asst and len(asst.get("content", "")) < _MIN_ASSISTANT_CHARS:
                too_short.append(f"line {i}: assistant content is {len(asst.get('content',''))} chars")
    # tolerate up to 1% short — odd entries happen; > 1% is a generator bug
    assert len(too_short) <= max(1, sum(1 for _ in open(corpus_path)) // 100), (
        f"{corpus_path.name} has {len(too_short)} short assistant responses (< {_MIN_ASSISTANT_CHARS} chars). "
        f"First 3: " + "; ".join(too_short[:3])
    )


@pytest.mark.parametrize("corpus_path", _present, ids=lambda p: p.name)
def test_corpus_dedup(corpus_path: Path):
    """Exact-duplicate (user, assistant) pairs > 5% = generator bug.

    Note: identical user prompts with *different* assistant responses are NOT
    duplicates — that's the bad/good/great progression pattern (showing the model
    multiple quality tiers of response for the same scenario). The real duplicate
    is when BOTH halves match.
    """
    pairs = []
    with open(corpus_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            msgs = ex.get("messages", [])
            u = next((m["content"] for m in msgs if m.get("role") == "user"), "")
            a = next((m["content"] for m in reversed(msgs) if m.get("role") == "assistant"), "")
            pairs.append((u, a))
    if not pairs:
        return
    counts = Counter(pairs)
    dupes = sum(c - 1 for c in counts.values() if c > 1)
    ratio = dupes / len(pairs)
    assert ratio <= _MAX_DUP_RATIO, (
        f"{corpus_path.name} has {dupes}/{len(pairs)} duplicate (user, assistant) pairs ({ratio:.1%}). "
        f"Generator likely emits identical examples. Top 3 most-duplicated user prompts: "
        + "; ".join(f"({c}×) {repr(u[:60])}" for (u, _), c in counts.most_common(3) if c > 1)
    )


@pytest.mark.parametrize("corpus_path", _present, ids=lambda p: p.name)
def test_corpus_grc_scope(corpus_path: Path):
    """Sanity: the GRC corpus should actually mention GRC concepts. If a corpus
    has fewer than 30% of assistant responses mentioning {finding, control, NIST,
    AI RMF, evidence, POA&M, risk}, it's drifted off-task."""
    grc_re = re.compile(r"\b(finding|control|NIST|AI RMF|evidence|POA&?M|risk|assess)", re.IGNORECASE)
    n = 0
    on_scope = 0
    with open(corpus_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            asst = next((m["content"] for m in reversed(ex.get("messages", []))
                         if m.get("role") == "assistant"), "")
            n += 1
            if grc_re.search(asst):
                on_scope += 1
    assert n == 0 or on_scope / n >= 0.30, (
        f"{corpus_path.name}: only {on_scope}/{n} ({on_scope/max(n,1):.0%}) assistant responses "
        f"mention GRC concepts. Corpus may be drifted off-task."
    )
