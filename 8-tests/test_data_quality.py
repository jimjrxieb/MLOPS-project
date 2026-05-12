"""
test_data_quality.py — Validates training data meets quality gates.

Run: python3 -m pytest tests/test_data_quality.py -v
"""

import json
import os
from pathlib import Path

import pytest

# Paths
CURATED_CORPUS = Path("1-data-pipeline/05-data-quality/curated/katie_v2_clean.jsonl")
RAW_DATA_LAKE = Path("1-data-pipeline/01-raw-data-lake")
ETL_OUTPUT = Path("1-data-pipeline/02-ETL-data")

# Domain keywords (same as curate_corpus.py)
DOMAIN_KEYWORDS = {
    "CKS": ["pod security", "rbac", "networkpolicy", "falco", "admission controller",
             "gatekeeper", "kyverno", "cis benchmark", "seccomp", "apparmor"],
    "CKA": ["cluster architecture", "etcd", "kubeadm", "deployment", "statefulset",
             "daemonset", "service", "ingress", "dns", "coredns", "troubleshoot"],
    "CKAD": ["multi-container", "init container", "sidecar", "rolling update",
             "configmap", "secret", "liveness", "readiness", "helm"],
    "CNPA": ["vpc", "subnet", "cidr", "cni", "calico", "cilium", "service mesh",
             "istio", "gateway api", "terraform"],
    "OPS": ["argocd", "rank routing", "incident response", "playbook", "gitops"],
}

GARBAGE_PATTERNS = [
    "[CORRECTION]", "[NEEDS CORRECTION]",
    "Unable to provide specific correction", "[object Object]",
]

MIN_RESPONSE_LENGTH = 50
MIN_CHUNK_SIZE = 500


def load_corpus(path):
    """Load JSONL file as list of dicts."""
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


@pytest.fixture(scope="module")
def corpus():
    """Load curated corpus once for all tests."""
    if not CURATED_CORPUS.exists():
        pytest.skip(f"Curated corpus not found: {CURATED_CORPUS}")
    return load_corpus(CURATED_CORPUS)


class TestChatMLFormat:
    """Every training example must be valid ChatML."""

    def test_all_examples_have_messages_key(self, corpus):
        invalid = [i for i, ex in enumerate(corpus) if "messages" not in ex]
        assert len(invalid) == 0, f"{len(invalid)} examples missing 'messages' key"

    def test_all_examples_have_assistant_response(self, corpus):
        missing = []
        for i, ex in enumerate(corpus):
            roles = [m.get("role") for m in ex.get("messages", [])]
            if "assistant" not in roles:
                missing.append(i)
        assert len(missing) == 0, f"{len(missing)} examples missing assistant response"

    def test_all_messages_have_role_and_content(self, corpus):
        bad = []
        for i, ex in enumerate(corpus):
            for m in ex.get("messages", []):
                if "role" not in m or "content" not in m:
                    bad.append(i)
                    break
        assert len(bad) == 0, f"{len(bad)} examples have messages without role/content"

    def test_no_alpaca_format(self, corpus):
        """Alpaca format (instruction/input/output) is rejected."""
        alpaca = [i for i, ex in enumerate(corpus)
                  if "instruction" in ex or "input" in ex or "output" in ex]
        assert len(alpaca) == 0, f"{len(alpaca)} examples in Alpaca format (should be ChatML)"


class TestContentQuality:
    """Training content must meet quality gates."""

    def test_no_garbage_patterns(self, corpus):
        garbage = []
        for i, ex in enumerate(corpus):
            text = " ".join(m.get("content", "") for m in ex.get("messages", []))
            for pattern in GARBAGE_PATTERNS:
                if pattern in text:
                    garbage.append((i, pattern))
                    break
        assert len(garbage) == 0, f"{len(garbage)} examples contain garbage patterns"

    def test_no_stub_responses(self, corpus):
        stubs = []
        for i, ex in enumerate(corpus):
            for m in ex.get("messages", []):
                if m.get("role") == "assistant" and len(m.get("content", "")) < MIN_RESPONSE_LENGTH:
                    stubs.append(i)
                    break
        assert len(stubs) == 0, f"{len(stubs)} examples have stub responses (<{MIN_RESPONSE_LENGTH} chars)"

    def test_all_in_scope(self, corpus):
        """Every example must match at least one domain keyword."""
        out_of_scope = 0
        for ex in corpus:
            text = " ".join(m.get("content", "") for m in ex.get("messages", [])).lower()
            matched = any(
                any(kw in text for kw in keywords)
                for keywords in DOMAIN_KEYWORDS.values()
            )
            if not matched:
                out_of_scope += 1
        # Allow up to 5% out-of-scope (some examples are cross-domain)
        threshold = len(corpus) * 0.05
        assert out_of_scope <= threshold, (
            f"{out_of_scope} examples out of scope (>{threshold:.0f} = 5% of {len(corpus)})"
        )


class TestCorpusSize:
    """Corpus must meet minimum size requirements."""

    def test_corpus_not_empty(self, corpus):
        assert len(corpus) > 0

    def test_corpus_above_minimum_chunk_size(self, corpus):
        assert len(corpus) >= MIN_CHUNK_SIZE, (
            f"Corpus has {len(corpus)} examples, minimum is {MIN_CHUNK_SIZE}"
        )

    def test_no_exact_duplicates(self, corpus):
        seen = set()
        dupes = 0
        for ex in corpus:
            key = json.dumps(ex.get("messages", []), sort_keys=True)
            if key in seen:
                dupes += 1
            seen.add(key)
        # Allow up to 1% duplicates
        threshold = len(corpus) * 0.01
        assert dupes <= threshold, f"{dupes} exact duplicates (>{threshold:.0f} = 1%)"


class TestDomainDistribution:
    """Training data should cover all target domains."""

    def test_cks_coverage(self, corpus):
        """CKS should be the largest domain (~35% target)."""
        count = self._count_domain(corpus, "CKS")
        pct = count / len(corpus) * 100
        assert pct >= 20, f"CKS coverage is {pct:.1f}%, should be ≥20%"

    def test_cka_coverage(self, corpus):
        count = self._count_domain(corpus, "CKA")
        pct = count / len(corpus) * 100
        assert pct >= 15, f"CKA coverage is {pct:.1f}%, should be ≥15%"

    def test_cnpa_coverage(self, corpus):
        """CNPA is the known weak domain — flag if too low."""
        count = self._count_domain(corpus, "CNPA")
        pct = count / len(corpus) * 100
        assert pct >= 5, f"CNPA coverage is {pct:.1f}%, should be ≥5%"

    @staticmethod
    def _count_domain(corpus, domain):
        count = 0
        keywords = DOMAIN_KEYWORDS.get(domain, [])
        for ex in corpus:
            text = " ".join(m.get("content", "") for m in ex.get("messages", [])).lower()
            if any(kw in text for kw in keywords):
                count += 1
        return count
