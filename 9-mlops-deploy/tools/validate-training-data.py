#!/usr/bin/env python3
"""validate-training-data.py — Data quality gates for ML training data.

Usage:
    python3 tools/validate-training-data.py --input /path/to/data.jsonl --check all
    python3 tools/validate-training-data.py --input /path/to/data.jsonl --check format
    python3 tools/validate-training-data.py --input /path/to/data.jsonl --report
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path


# Domain keywords for scope checking
DOMAIN_KEYWORDS = {
    "CKS": [
        "pod security", "rbac", "networkpolicy", "network policy", "falco",
        "admission controller", "opa", "gatekeeper", "kyverno", "cis benchmark",
        "seccomp", "apparmor", "pss", "pod security standard", "audit log",
        "trivy", "cosign", "sbom", "supply chain", "runtime security",
        "encryption at rest", "etcd encryption", "securitycontext",
    ],
    "CKA": [
        "cluster architecture", "etcd", "kubeadm", "static pod", "deployment",
        "statefulset", "daemonset", "job", "cronjob", "service", "ingress",
        "dns", "coredns", "storage", "persistentvolume", "pvc", "storageclass",
        "troubleshoot", "crashloopbackoff", "oomkilled", "node notready",
        "kubectl", "kubelet", "kube-proxy", "scheduler", "controller manager",
    ],
    "CKAD": [
        "multi-container", "init container", "sidecar", "rolling update",
        "canary", "blue-green", "configmap", "secret", "liveness", "readiness",
        "startup probe", "resource request", "resource limit", "helm",
        "observability", "logging", "metrics",
    ],
    "CNPA": [
        "vpc", "subnet", "cidr", "security group", "nat", "cni", "calico",
        "cilium", "flannel", "service mesh", "istio", "linkerd", "route53",
        "gateway api", "load balancer", "platform engineering", "cloud native",
        "iac", "terraform", "crossplane",
    ],
    "OPS": [
        "argocd", "rank routing", "incident response", "playbook", "drift",
        "gitops", "reconciliation", "self-healing",
    ],
}

# Garbage patterns to reject
GARBAGE_PATTERNS = [
    "[CORRECTION]",
    "[NEEDS CORRECTION]",
    "Unable to provide specific correction",
    "[object Object]",
    "undefined",
]

MIN_RESPONSE_LENGTH = 50
MIN_CHUNK_SIZE = 500


def load_jsonl(path):
    """Load JSONL file(s) from a path (file or directory)."""
    examples = []
    path = Path(path)

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.glob("**/*.jsonl"))
    else:
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    for f in files:
        with open(f) as fh:
            for line_num, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"  WARN: {f}:{line_num} — invalid JSON", file=sys.stderr)

    return examples


def check_format(examples):
    """Validate ChatML format."""
    valid = 0
    invalid = 0
    errors = []

    for i, ex in enumerate(examples):
        if "messages" not in ex:
            invalid += 1
            errors.append(f"Example {i}: missing 'messages' key (Alpaca format?)")
            continue

        messages = ex["messages"]
        if not isinstance(messages, list) or len(messages) < 2:
            invalid += 1
            errors.append(f"Example {i}: messages must be a list with >=2 entries")
            continue

        roles = [m.get("role") for m in messages]
        if "assistant" not in roles:
            invalid += 1
            errors.append(f"Example {i}: no assistant response")
            continue

        valid += 1

    return {"valid": valid, "invalid": invalid, "errors": errors[:20]}


def check_scope(examples):
    """Check domain scope — every example must match at least one domain."""
    in_scope = 0
    out_of_scope = 0
    domain_counts = Counter()

    for ex in examples:
        messages = ex.get("messages", [])
        text = " ".join(m.get("content", "") for m in messages).lower()

        matched = False
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                domain_counts[domain] += 1
                matched = True

        if matched:
            in_scope += 1
        else:
            out_of_scope += 1

    return {
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
        "domain_counts": dict(domain_counts),
    }


def check_garbage(examples):
    """Check for garbage patterns."""
    clean = 0
    garbage = 0
    garbage_reasons = Counter()

    for ex in examples:
        messages = ex.get("messages", [])
        text = " ".join(m.get("content", "") for m in messages)

        is_garbage = False
        for pattern in GARBAGE_PATTERNS:
            if pattern in text:
                garbage_reasons[pattern] += 1
                is_garbage = True

        # Check for stub responses
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        for m in assistant_msgs:
            if len(m.get("content", "")) < MIN_RESPONSE_LENGTH:
                garbage_reasons["stub_response"] += 1
                is_garbage = True

        if is_garbage:
            garbage += 1
        else:
            clean += 1

    return {"clean": clean, "garbage": garbage, "reasons": dict(garbage_reasons)}


def check_dedup(examples):
    """Check for exact duplicates."""
    seen = set()
    unique = 0
    duplicates = 0

    for ex in examples:
        messages = ex.get("messages", [])
        key = json.dumps(messages, sort_keys=True)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
            unique += 1

    return {"unique": unique, "duplicates": duplicates}


def check_chunk_size(examples):
    """Verify chunk meets minimum size."""
    count = len(examples)
    passes = count >= MIN_CHUNK_SIZE
    return {
        "count": count,
        "minimum": MIN_CHUNK_SIZE,
        "passes": passes,
    }


def generate_report(examples):
    """Generate full quality report."""
    total = len(examples)
    fmt = check_format(examples)
    scope = check_scope(examples)
    garbage = check_garbage(examples)
    dedup = check_dedup(examples)
    chunk = check_chunk_size(examples)

    print(f"# Training Data Quality Report")
    print(f"")
    print(f"Total examples: {total:,}")
    print(f"")
    print(f"## Format Validation")
    print(f"  Valid (ChatML): {fmt['valid']:,} ({fmt['valid']/total*100:.1f}%)")
    print(f"  Invalid: {fmt['invalid']:,}")
    if fmt["errors"]:
        print(f"  First errors:")
        for e in fmt["errors"][:5]:
            print(f"    - {e}")
    print(f"")
    print(f"## Scope Check")
    print(f"  In-scope: {scope['in_scope']:,} ({scope['in_scope']/total*100:.1f}%)")
    print(f"  Out-of-scope: {scope['out_of_scope']:,}")
    print(f"  Domain distribution:")
    for domain in ["CKS", "CKA", "CKAD", "CNPA", "OPS"]:
        count = scope["domain_counts"].get(domain, 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"    {domain}: {count:,} ({pct:.1f}%)")
    print(f"")
    print(f"## Content Quality")
    print(f"  Clean: {garbage['clean']:,}")
    print(f"  Garbage: {garbage['garbage']:,}")
    if garbage["reasons"]:
        print(f"  Rejection reasons:")
        for reason, count in garbage["reasons"].items():
            print(f"    - {reason}: {count}")
    print(f"")
    print(f"## Deduplication")
    print(f"  Unique: {dedup['unique']:,}")
    print(f"  Duplicates: {dedup['duplicates']:,}")
    print(f"")
    print(f"## Chunk Size")
    print(f"  Examples: {chunk['count']:,}")
    print(f"  Minimum: {chunk['minimum']}")
    print(f"  Passes: {'YES' if chunk['passes'] else 'NO — TOO SMALL'}")

    # Exit code
    all_pass = (
        fmt["invalid"] == 0
        and scope["out_of_scope"] / total < 0.05 if total > 0 else True
        and garbage["garbage"] == 0
        and chunk["passes"]
    )
    return 0 if all_pass else 1


def main():
    parser = argparse.ArgumentParser(description="Training data quality gates")
    parser.add_argument("--input", required=True, help="JSONL file or directory")
    parser.add_argument("--check", choices=["all", "format", "scope", "garbage", "dedup", "chunk-size"],
                        default="all", help="Which check to run")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any quality violation")
    args = parser.parse_args()

    examples = load_jsonl(args.input)
    print(f"Loaded {len(examples):,} examples from {args.input}", file=sys.stderr)

    if args.report:
        exit_code = generate_report(examples)
        if args.strict:
            sys.exit(exit_code)
        return

    if args.check in ("all", "format"):
        result = check_format(examples)
        print(f"Format: {result['valid']} valid, {result['invalid']} invalid")
        if args.strict and result["invalid"] > 0:
            sys.exit(1)

    if args.check in ("all", "scope"):
        result = check_scope(examples)
        print(f"Scope: {result['in_scope']} in-scope, {result['out_of_scope']} out-of-scope")

    if args.check in ("all", "garbage"):
        result = check_garbage(examples)
        print(f"Garbage: {result['clean']} clean, {result['garbage']} garbage")
        if args.strict and result["garbage"] > 0:
            sys.exit(1)

    if args.check in ("all", "dedup"):
        result = check_dedup(examples)
        print(f"Dedup: {result['unique']} unique, {result['duplicates']} duplicates")

    if args.check in ("all", "chunk-size"):
        result = check_chunk_size(examples)
        print(f"Chunk size: {result['count']} examples ({'PASS' if result['passes'] else 'FAIL'})")
        if args.strict and not result["passes"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
