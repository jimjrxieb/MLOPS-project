#!/usr/bin/env python3
"""compare-eval.py — Compare current eval scores against baseline.

Usage:
    python3 compare-eval.py --baseline baseline.json --current current.json
"""

import argparse
import json
import sys


def compare(baseline_path, current_path):
    """Compare eval results and flag degradation."""
    with open(baseline_path) as f:
        baseline = json.load(f)
    with open(current_path) as f:
        current = json.load(f)

    bl_score = baseline.get("weighted_score", 0)
    cur_score = current.get("weighted_score", 0)
    drift = cur_score - bl_score

    print(f"Baseline weighted score: {bl_score:.1f}%")
    print(f"Current weighted score:  {cur_score:.1f}%")
    print(f"Drift:                   {drift:+.1f}%")
    print()

    # Category breakdown
    categories = ["CKS", "CKA", "CNPA", "Cloud"]
    alerts = []

    print(f"{'Category':<12} {'Baseline':>10} {'Current':>10} {'Drift':>10} {'Status':>10}")
    print("-" * 55)

    for cat in categories:
        bl_cat = baseline.get("categories", {}).get(cat, {}).get("score", 0)
        cur_cat = current.get("categories", {}).get(cat, {}).get("score", 0)
        cat_drift = cur_cat - bl_cat
        status = "OK"

        if cat_drift < -10:
            status = "CRITICAL"
            alerts.append(f"{cat} dropped {abs(cat_drift):.1f}% from baseline")
        elif cat_drift < -5:
            status = "WARNING"
            alerts.append(f"{cat} dropped {abs(cat_drift):.1f}% from baseline")
        elif cur_cat < 50:
            status = "BELOW MIN"
            alerts.append(f"{cat} below minimum threshold (50%)")

        print(f"{cat:<12} {bl_cat:>9.1f}% {cur_cat:>9.1f}% {cat_drift:>+9.1f}% {status:>10}")

    print()

    if alerts:
        print("ALERTS:")
        for alert in alerts:
            print(f"  - {alert}")
        return 1
    else:
        print("All categories within acceptable range.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Compare eval results against baseline")
    parser.add_argument("--baseline", required=True, help="Baseline eval results JSON")
    parser.add_argument("--current", required=True, help="Current eval results JSON")
    args = parser.parse_args()

    exit_code = compare(args.baseline, args.current)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
