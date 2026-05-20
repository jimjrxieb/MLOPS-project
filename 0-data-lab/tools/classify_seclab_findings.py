#!/usr/bin/env python3
"""
Classify SecLab Findings — Tag by Target Model and Pipeline

Reads raw scanner output from 0-data-lab/seclab-findings/ and classifies
each file by:
1. Target model (beru, jade, katie) — based on content domain
2. Pipeline (training, rag) — based on content type

Not hardcoded to any model — tagging rules are keyword-based and extensible.

Usage:
    python3 classify_seclab_findings.py [--dry-run]

Output:
    Prints classification for each file. With --dry-run, no files are moved.
    Without --dry-run, copies files to appropriate pipeline directories.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Paths
SECLAB_DIR = Path(__file__).parent.parent / "seclab-findings"
TRAINING_DIR = Path(__file__).parent.parent.parent / "1-FineTuning-Pipeline" / "01-raw-data-lake"
RAG_DIR = Path(__file__).parent.parent.parent / "2-RagIngestion-Pipeline" / "01-unprocessed"

# Model tagging rules — keyword-based, not hardcoded
# Add new models by extending this dict
MODEL_TAGS = {
    "beru": {
        "description": "Security analyst — CySA+, NIST, vulnerability management, risk reporting",
        "keywords": [
            "nist", "800-53", "800-61", "cve", "cvss", "vulnerability",
            "nessus", "openvas", "guardduty", "securityhub", "prowler",
            "wazuh", "suricata", "zeek", "crowdstrike", "siem",
            "incident response", "forensic", "triage", "risk score",
            "compliance", "fedramp", "hipaa", "pci", "ciso",
            "ids", "ips", "firewall", "network security",
            "openscap", "lynis", "scap", "cis benchmark",
        ],
    },
    "jade": {
        "description": "Platform security — DevSecOps, K8s, containers, CI/CD",
        "keywords": [
            "kubernetes", "k8s", "pod", "deployment", "namespace",
            "helm", "argocd", "kyverno", "gatekeeper", "falco",
            "trivy", "kubescape", "semgrep", "bandit", "gitleaks",
            "dockerfile", "container", "rbac", "serviceaccount",
            "admission control", "securitycontext", "networkpolicy",
            "ci/cd", "github actions", "pipeline",
        ],
    },
    "katie": {
        "description": "Platform operations — K8s ops, health, diagnostics",
        "keywords": [
            "kubectl", "k8sgpt", "popeye", "node", "drain",
            "cordon", "etcd", "kubelet", "scheduler",
            "resource quota", "limitrange", "hpa", "pdb",
            "crashloopbackoff", "oomkilled", "pending pod",
        ],
    },
}

# Pipeline classification rules
PIPELINE_RULES = {
    "training": {
        "description": "Structured Q&A, triage decisions, tool walkthroughs",
        "extensions": [".jsonl", ".json"],
        "content_hints": ["messages", "question", "answer", "scenario"],
    },
    "rag": {
        "description": "Reference docs, scan reports, compliance docs, templates",
        "extensions": [".md", ".txt", ".pdf", ".csv", ".xml", ".html", ".log"],
        "content_hints": ["report", "template", "procedure", "policy", "standard"],
    },
}


def classify_file(file_path: Path) -> dict:
    """Classify a single file by target model and pipeline."""
    try:
        content = file_path.read_text(errors="replace").lower()
    except Exception:
        content = ""

    filename = file_path.name.lower()

    # Score each model
    model_scores = {}
    for model, config in MODEL_TAGS.items():
        score = sum(1 for kw in config["keywords"] if kw in content or kw in filename)
        model_scores[model] = score

    # Pick highest scoring model (ties go to first match)
    best_model = max(model_scores, key=model_scores.get)
    best_score = model_scores[best_model]

    # If no keywords matched, mark as unclassified
    if best_score == 0:
        best_model = "unclassified"

    # Determine pipeline
    ext = file_path.suffix.lower()
    pipeline = "rag"  # Default to RAG
    for pipe, rules in PIPELINE_RULES.items():
        if ext in rules["extensions"]:
            if any(hint in content for hint in rules["content_hints"]):
                pipeline = pipe
                break

    return {
        "file": str(file_path),
        "target_model": best_model,
        "pipeline": pipeline,
        "model_scores": model_scores,
        "classified_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    dry_run = "--dry-run" in sys.argv

    if not SECLAB_DIR.exists():
        print(f"seclab-findings directory not found: {SECLAB_DIR}")
        sys.exit(1)

    files = [f for f in SECLAB_DIR.iterdir() if f.is_file()]
    if not files:
        print("No files found in seclab-findings/")
        sys.exit(0)

    print(f"Classifying {len(files)} files from {SECLAB_DIR}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    results = []
    for f in sorted(files):
        result = classify_file(f)
        results.append(result)
        print(f"  {f.name}")
        print(f"    Model: {result['target_model']} (scores: {result['model_scores']})")
        print(f"    Pipeline: {result['pipeline']}")

        if not dry_run and result["target_model"] != "unclassified":
            dest_dir = TRAINING_DIR if result["pipeline"] == "training" else RAG_DIR
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f.name
            shutil.copy2(f, dest)
            print(f"    -> Copied to {dest}")

        print()

    # Summary
    print("--- Summary ---")
    for model in list(MODEL_TAGS.keys()) + ["unclassified"]:
        count = sum(1 for r in results if r["target_model"] == model)
        if count:
            print(f"  {model}: {count} files")

    # Write manifest
    manifest_path = SECLAB_DIR / ".classification_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nManifest written to {manifest_path}")


if __name__ == "__main__":
    main()
