#!/usr/bin/env python3
"""
JADE Config Fix Benchmark

Tests JADE's ability to fix faulty Kubernetes manifests, Terraform, Dockerfiles,
GitHub Actions, and Rego policies. Simulates incident response scenarios.

Usage:
    python3 run_config_benchmark.py                    # Run full benchmark
    python3 run_config_benchmark.py --limit 5         # Test first 5 scenarios
    python3 run_config_benchmark.py --category k8s    # Only K8s scenarios
    python3 run_config_benchmark.py --verbose         # Show JADE responses
"""

import json
import os
import sys
import argparse
import requests
import re
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
BENCHMARK_FILE = SCRIPT_DIR / "faulty_config_scenarios.jsonl"
RESULTS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-GP-CLARIFY/3-results")


def ask_jade(prompt: str, model: str = "jade:v1.0", timeout: int = 120) -> str:
    """Query JADE via Ollama API."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=timeout
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        return "[ERROR: Timeout]"
    except Exception as e:
        return f"[ERROR: {e}]"


def extract_code_block(response: str, file_type: str) -> str:
    """Extract code block from JADE response based on file type."""
    # Map file types to likely code fence labels
    type_hints = {
        "yaml": ["yaml", "yml"],
        "hcl": ["hcl", "terraform", "tf"],
        "dockerfile": ["dockerfile", "docker"],
        "rego": ["rego"],
    }

    hints = type_hints.get(file_type, [file_type])

    # Try specific code fences first
    for hint in hints:
        pattern = rf'```{hint}\n(.*?)```'
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Try generic code fence
    pattern = r'```\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try any code fence
    pattern = r'```[\w]*\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    return ""


def check_fix_quality(fixed_code: str, file_type: str, issues: list) -> dict:
    """Check if the fix addresses the known issues."""
    result = {
        "has_code": bool(fixed_code),
        "issues_addressed": 0,
        "issues_found": [],
        "issues_missing": [],
        "quality_score": 0.0
    }

    if not fixed_code:
        return result

    lower_code = fixed_code.lower()

    # Issue detection patterns
    fix_patterns = {
        # K8s/YAML issues
        "privileged": [
            ("privileged: false", "privileged"),
            ("privileged: true", None),  # Still has issue if present
        ],
        "hostnetwork": [
            ("hostnetwork: false", "hostNetwork"),
            ("hostnetwork: true", None),
        ],
        "hostpid": [
            ("hostpid: false", "hostPID"),
            ("hostpid: true", None),
        ],
        "hostipc": [
            ("hostipc: false", "hostIPC"),
            ("hostipc: true", None),
        ],
        "latest-tag": [
            (":latest", None),  # Bad if present
            ("@sha256:", "digest"),
            (r":\d+\.\d+", "version-tag"),
        ],
        "run-as-root": [
            ("runasnonroot: true", "runAsNonRoot"),
            ("runasuser: 0", None),  # Bad
        ],
        "hardcoded-secrets": [
            ("secretkeyref", "secret-ref"),
            ("valuefrom", "valuefrom"),
            ("externalsecrets", "external-secrets"),
            ("password=", None),
            ("secret=", None),
        ],
        "docker-sock-mount": [
            ("/var/run/docker.sock", None),
        ],
        "no-limits": [
            ("limits:", "limits"),
            ("resources:", "resources"),
        ],
        "no-probes": [
            ("livenessprobe:", "livenessProbe"),
            ("readinessprobe:", "readinessProbe"),
        ],
        "automount-sa-token": [
            ("automountserviceaccounttoken: false", "automount-disabled"),
        ],
        "wildcard-actions": [
            ('action.*"\\*"', None),
            ("action.*\\*", None),
        ],
        "wildcard-resources": [
            ('resource.*"\\*"', None),
            ("resources.*\\*", None),
        ],
        # Terraform issues
        "no-encryption": [
            ("server_side_encryption", "sse"),
            ("kms_key", "kms"),
            ("storage_encrypted", "encrypted"),
        ],
        "no-versioning": [
            ("versioning", "versioning"),
        ],
        "no-logging": [
            ("logging", "logging"),
            ("access_log", "access-log"),
        ],
        "no-public-access-block": [
            ("public_access_block", "public-block"),
            ("block_public", "block-public"),
        ],
        "world-open-ingress": [
            ("0.0.0.0/0", None),  # Bad
            ("cidr_blocks", "specific-cidr"),
        ],
        "publicly-accessible": [
            ("publicly_accessible.*=.*false", "private"),
            ("publicly_accessible.*=.*true", None),
        ],
        # Docker issues
        "running-as-root": [
            ("user ", "user-directive"),
            ("user:", "user-directive"),
        ],
        "no-healthcheck": [
            ("healthcheck", "healthcheck"),
        ],
        "copy-all": [
            ("copy . .", None),  # Bad
            (".dockerignore", "dockerignore"),
        ],
        # GitHub Actions issues
        "pull-request-target": [
            ("pull_request_target", None),  # Bad
            ("pull_request:", "pull-request-safe"),
        ],
        "secrets-in-logs": [
            ("echo.*secrets\\.", None),  # Bad
            ("mask", "masking"),
        ],
        "write-all-permissions": [
            ("permissions: write-all", None),
            ("permissions:", "scoped-permissions"),
        ],
        "unpinned-actions": [
            ("@latest", None),
            ("@v\\d+$", None),  # Just major version
            ("@[a-f0-9]{40}", "sha-pinned"),
        ],
        # Rego issues
        "missing-msg-assignment": [
            ("msg :=", "msg-assigned"),
            ("msg =", "msg-assigned"),
        ],
        "inverted-logic": [
            ("not.*limits", "negation-check"),
        ],
        "missing-package": [
            ("package ", "package-decl"),
        ],
        "invalid-string-concat": [
            ("sprintf", "sprintf"),
        ],
        "nil-pointer": [
            ("object.get", "safe-access"),
            ("default ", "default-value"),
        ],
    }

    for issue in issues:
        issue_lower = issue.lower().replace("-", "").replace("_", "")
        addressed = False

        # Check each pattern
        for pattern_key, patterns in fix_patterns.items():
            key_normalized = pattern_key.replace("-", "").replace("_", "")
            if issue_lower in key_normalized or key_normalized in issue_lower:
                for pattern, fix_name in patterns:
                    if fix_name is None:
                        # This is a bad pattern - should NOT be present
                        if re.search(pattern, lower_code, re.IGNORECASE):
                            # Issue still present
                            pass
                        else:
                            addressed = True
                    else:
                        # This is a good pattern - should be present
                        if re.search(pattern, lower_code, re.IGNORECASE):
                            addressed = True
                            break
                break

        if addressed:
            result["issues_addressed"] += 1
            result["issues_found"].append(issue)
        else:
            result["issues_missing"].append(issue)

    # Calculate quality score
    if issues:
        result["quality_score"] = result["issues_addressed"] / len(issues)

    return result


def load_scenarios(filepath: Path, limit: int = None, category: str = None) -> list:
    """Load benchmark scenarios from JSONL."""
    scenarios = []
    with open(filepath) as f:
        for line in f:
            if line.strip():
                scenario = json.loads(line)
                if category:
                    if category.lower() not in scenario.get("category", "").lower():
                        continue
                scenarios.append(scenario)
                if limit and len(scenarios) >= limit:
                    break
    return scenarios


def run_benchmark(model: str = "jade:v1.0", limit: int = None,
                  category: str = None, verbose: bool = False) -> dict:
    """Run the config fix benchmark."""
    scenarios = load_scenarios(BENCHMARK_FILE, limit, category)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe = model.replace(":", "_").replace("/", "_")
    output_dir = RESULTS_DIR / f"config_benchmark_{model_safe}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"JADE Config Fix Benchmark")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Scenarios: {len(scenarios)}")
    if category:
        print(f"Category filter: {category}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    results = []
    passed = 0

    for i, scenario in enumerate(scenarios, 1):
        sid = scenario["id"]
        cat = scenario["category"]
        file_type = scenario["file_type"]
        prompt = scenario["scenario"]
        issues = scenario.get("issues", [])

        print(f"[{i}/{len(scenarios)}] {sid} ({cat})...", end=" ", flush=True)

        # Ask JADE
        jade_response = ask_jade(prompt, model)

        if jade_response.startswith("[ERROR"):
            print(f"ERROR")
            result = {
                "id": sid,
                "category": cat,
                "file_type": file_type,
                "passed": False,
                "error": jade_response,
                "jade_response": "",
                "fixed_code": "",
                "quality": {}
            }
        else:
            # Extract fixed code
            fixed_code = extract_code_block(jade_response, file_type)

            # Check fix quality
            quality = check_fix_quality(fixed_code, file_type, issues)

            # Pass if addressed at least 50% of issues and has code
            is_pass = quality["has_code"] and quality["quality_score"] >= 0.5

            if is_pass:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            score_pct = quality["quality_score"] * 100
            print(f"{status} ({quality['issues_addressed']}/{len(issues)} issues, {score_pct:.0f}%)")

            result = {
                "id": sid,
                "category": cat,
                "file_type": file_type,
                "rank": scenario.get("rank", "D"),
                "issues": issues,
                "passed": is_pass,
                "jade_response": jade_response,
                "fixed_code": fixed_code,
                "quality": quality
            }

            if verbose:
                print(f"    Code extracted: {len(fixed_code)} chars")
                print(f"    Issues fixed: {quality['issues_found']}")
                print(f"    Issues missing: {quality['issues_missing']}")

        results.append(result)

    # Save results
    results_file = output_dir / "jade_config_results.jsonl"
    with open(results_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Calculate stats
    total = len(results)
    accuracy = (passed / total * 100) if total > 0 else 0

    # By category
    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0}
        by_category[cat]["total"] += 1
        if r.get("passed"):
            by_category[cat]["passed"] += 1

    # By file type
    by_type = {}
    for r in results:
        ftype = r.get("file_type", "unknown")
        if ftype not in by_type:
            by_type[ftype] = {"total": 0, "passed": 0}
        by_type[ftype]["total"] += 1
        if r.get("passed"):
            by_type[ftype]["passed"] += 1

    summary = {
        "model": model,
        "timestamp": timestamp,
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy_percent": round(accuracy, 2),
        "by_category": by_category,
        "by_file_type": by_type
    }

    summary_file = output_dir / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total} ({accuracy:.1f}%)")
    print(f"\nBy File Type:")
    for ftype, stats in sorted(by_type.items()):
        pct = (stats['passed']/stats['total']*100) if stats['total'] > 0 else 0
        print(f"  {ftype}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")
    print(f"\nBy Category:")
    for cat, stats in sorted(by_category.items()):
        pct = (stats['passed']/stats['total']*100) if stats['total'] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")
    print(f"\nFailed Scenarios:")
    for r in results:
        if not r.get("passed"):
            missing = r.get("quality", {}).get("issues_missing", [])
            print(f"  - {r['id']}: {r['category']} (missing: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''})")
    print(f"{'='*60}")
    print(f"Results: {output_dir}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="JADE Config Fix Benchmark")
    parser.add_argument("--model", default="jade:v1.0", help="Ollama model to test")
    parser.add_argument("--limit", type=int, help="Limit number of scenarios")
    parser.add_argument("--category", help="Filter by category (k8s, terraform, docker, gha, rego)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    run_benchmark(
        model=args.model,
        limit=args.limit,
        category=args.category,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
