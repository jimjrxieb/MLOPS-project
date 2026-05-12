"""SSP-grading eval — run the real ssp-examples through BERU and score the verdicts.

This is the exp-011 acceptance test. exp-010's failure mode: BERU can flag a bad
SSP (returns 0 PASS) but can't recognize a good one (also returns 0 PASS), and it
confabulates evidence on most controls (→ HITL-blocked). The fix needs to move
three numbers:

  bad_caught          fraction of BAD-tier controls assessed FAIL or PARTIAL
                      (NOT PASS, NOT blocked) — BERU must never pass a bad control.   ↑
  great_recognized    fraction of GREAT-tier controls assessed PASS or PARTIAL
                      (NOT FAIL, NOT blocked) — BERU must never fail a great control. ↑
  discrimination      does the PASS-rate climb bad < good < great?                    True
  clean_grade_rate    fraction of all controls that got a clean verdict (not blocked) ↑
  hallucination_rate  fraction HITL-blocked for invented evidence (the exp-010 bug)   ↓ → 0

Hard checks (must be zero for promotion):
  zero_bad_pass       BAD-tier controls wrongly assessed PASS
  zero_great_fail     GREAT-tier controls wrongly assessed FAIL

Usage:
  python3 4-eval-clarify/eval_ssp_grading.py                 # all 11 families (~30-60 min)
  python3 4-eval-clarify/eval_ssp_grading.py --families AC    # one family (~5-8 min)
  python3 4-eval-clarify/eval_ssp_grading.py --families AC,CA,IR --tag exp-010-baseline

Output:
  4-eval-clarify/results/ssp_grading/<tag>.json   (full per-control detail)
  4-eval-clarify/results/ssp_grading/<tag>.md     (the summary table)
  + a console summary
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

GP_MODEL_OPS = Path(__file__).resolve().parent.parent
BERU_AI = GP_MODEL_OPS / "BERU-AI"
# Use the bundled snapshot so the eval is self-contained within GP-MODEL-OPS.
SSP_DIR = BERU_AI / "knowledge" / "nist-800-53" / "ssp-examples"
RESULTS_DIR = GP_MODEL_OPS / "4-eval-clarify" / "results" / "ssp_grading"

import sys
sys.path.insert(0, str(BERU_AI))
from agent.graph import run_ssp_grading  # noqa: E402
from providers.ollama import OllamaProvider  # noqa: E402


# expected verdict per tier (what a competent assessor would do)
ACCEPTABLE = {
    "bad":   {"FAIL", "PARTIAL"},   # never PASS
    "good":  {"PARTIAL", "PASS", "FAIL"},  # a mix is fine; we only score "not all blocked"
    "great": {"PASS", "PARTIAL"},   # never FAIL
}
WRONG = {
    "bad":   {"PASS"},     # passing a bad control is a hard error
    "good":  set(),
    "great": {"FAIL"},     # failing a great control is a hard error
}


def grade_one(path: Path, tier: str):
    """Returns list of per-control records for one SSP file."""
    t0 = time.time()
    try:
        result = run_ssp_grading(
            ssp_path=str(path),
            system_name=f"eval-{path.stem}",
            client="ssp-grading-eval",
            output_dir=f"/tmp/beru-ssp-eval/{path.stem}",
            run_id=f"sspeval-{path.stem}-{int(t0)}",
        )
    except Exception as e:
        return [{"file": path.name, "tier": tier, "control_id": "(run-error)",
                 "verdict": "ERROR", "rank": "", "deterministic": False,
                 "hallucination": False, "blocked": True, "error": str(e)}]
    recs = []
    for f in result.get("findings", []) or []:
        recs.append({
            "file": path.name, "tier": tier,
            "control_id": f.get("control_id", "?"),
            "verdict": (f.get("status") or "?").upper(),
            "rank": f.get("rank", ""),
            "deterministic": bool(f.get("deterministic", False)),
            "hallucination": bool(f.get("evidence_hallucination", False)),
            "blocked": False,
        })
    for b in result.get("blocked_findings", []) or []:
        recs.append({
            "file": path.name, "tier": tier,
            "control_id": b.get("control_id", "?"),
            "verdict": "BLOCKED",
            "rank": b.get("rank", ""),
            "deterministic": False,
            "hallucination": True,  # blocked findings here were bumped for hallucinated evidence
            "blocked": True,
        })
    elapsed = time.time() - t0
    for r in recs:
        r["file_elapsed_s"] = round(elapsed, 1)
    return recs


def score(records):
    by_tier = defaultdict(list)
    for r in records:
        by_tier[r["tier"]].append(r)

    def tier_stats(tier):
        rs = by_tier.get(tier, [])
        total = len(rs)
        if not total:
            return {}
        blocked = sum(1 for r in rs if r["blocked"])
        clean = total - blocked
        verdicts = Counter(r["verdict"] for r in rs)
        passes = verdicts.get("PASS", 0)
        partials = verdicts.get("PARTIAL", 0)
        fails = verdicts.get("FAIL", 0)
        wrong = sum(1 for r in rs if r["verdict"] in WRONG.get(tier, set()))
        # "caught"/"recognized": clean verdict in the acceptable set
        good_calls = sum(1 for r in rs if (not r["blocked"]) and r["verdict"] in ACCEPTABLE.get(tier, set()))
        return {
            "controls": total,
            "blocked": blocked,
            "clean_grade_rate": round(clean / total, 3),
            "pass": passes, "partial": partials, "fail": fails,
            "pass_rate": round(passes / total, 3),
            "wrong_verdicts": wrong,
            "acceptable_clean_rate": round(good_calls / total, 3),
        }

    bad = tier_stats("bad")
    good = tier_stats("good")
    great = tier_stats("great")
    all_recs = records
    n = len(all_recs)
    halluc = sum(1 for r in all_recs if r["hallucination"]) / n if n else 0.0
    clean = sum(1 for r in all_recs if not r["blocked"]) / n if n else 0.0
    pr_b = bad.get("pass_rate", 0.0); pr_g = good.get("pass_rate", 0.0); pr_gt = great.get("pass_rate", 0.0)
    return {
        "totals": {"controls_graded": n,
                   "clean_grade_rate": round(clean, 3),
                   "hallucination_rate": round(halluc, 3)},
        "bad_tier": bad, "good_tier": good, "great_tier": great,
        "headline": {
            "bad_caught": bad.get("acceptable_clean_rate", 0.0),       # ↑ — bad controls NOT passed
            "great_recognized": great.get("acceptable_clean_rate", 0.0),  # ↑ — great controls NOT failed
            "discrimination": (pr_b <= pr_g <= pr_gt) and (pr_gt > pr_b),
            "pass_rates": {"bad": pr_b, "good": pr_g, "great": pr_gt},
            "zero_bad_pass": bad.get("pass", 0) == 0,
            "zero_great_fail": great.get("fail", 0) == 0,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", default="ALL", help="comma-sep family codes (AC,AU,...) or ALL")
    ap.add_argument("--tag", default="", help="label for the result files (default: model + timestamp)")
    args = ap.parse_args()

    fams = None if args.families.upper() == "ALL" else {f.strip().upper() for f in args.families.split(",")}
    model = OllamaProvider().model_name
    tag = args.tag or f"{model.replace(':', '_')}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    files = []
    for path in sorted(SSP_DIR.glob("*-ssp-*.md")):
        m = re.match(r"([A-Z]{2})-ssp-(bad|good|great)\.md", path.name)
        if not m:
            continue
        fam, tier = m.group(1), m.group(2)
        if fams and fam not in fams:
            continue
        files.append((path, tier))

    print(f"SSP-grading eval — model={model}  tag={tag}")
    print(f"grading {len(files)} SSP files ({sorted({f.name.split('-')[0] for f,_ in files})} families)\n")

    all_records = []
    for i, (path, tier) in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name} ...", flush=True)
        recs = grade_one(path, tier)
        all_records.extend(recs)
        vd = Counter(r["verdict"] for r in recs)
        el = recs[0].get("file_elapsed_s", 0) if recs else 0
        print(f"    {len(recs)} controls | {dict(vd)} | {el}s")

    summary = score(all_records)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / f"{tag}.json"
    out_json.write_text(json.dumps({
        "model": model, "tag": tag,
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "ssp_dir": str(SSP_DIR),
        "summary": summary,
        "records": all_records,
    }, indent=2))

    # markdown
    h = summary["headline"]; t = summary["totals"]
    md = [f"# SSP-Grading Eval — `{model}` — `{tag}`", "",
          f"Generated: {datetime.now(timezone.utc).isoformat()}",
          f"SSP files graded: {len([f for f in files])}  ·  controls graded: {t['controls_graded']}",
          "", "## Headline", "",
          "| Metric | Value | Want |", "|---|---|---|",
          f"| bad_caught (BAD controls not passed) | {h['bad_caught']:.0%} | ↑ → 100% |",
          f"| great_recognized (GREAT controls not failed) | {h['great_recognized']:.0%} | ↑ → 100% |",
          f"| pass-rate: bad / good / great | {h['pass_rates']['bad']:.0%} / {h['pass_rates']['good']:.0%} / {h['pass_rates']['great']:.0%} | bad < good < great |",
          f"| discrimination (pass-rate climbs) | {'YES' if h['discrimination'] else 'NO'} | YES |",
          f"| clean_grade_rate (not HITL-blocked) | {t['clean_grade_rate']:.0%} | ↑ |",
          f"| hallucination_rate (blocked for invented evidence) | {t['hallucination_rate']:.0%} | ↓ → 0% |",
          f"| zero_bad_pass | {'PASS' if h['zero_bad_pass'] else 'FAIL'} | PASS |",
          f"| zero_great_fail | {'PASS' if h['zero_great_fail'] else 'FAIL'} | PASS |",
          "", "## Per-tier", "",
          "| Tier | controls | PASS | PARTIAL | FAIL | blocked | wrong-verdicts | clean-grade |", "|---|---|---|---|---|---|---|---|"]
    for tier in ("bad", "good", "great"):
        s = summary[f"{tier}_tier"]
        if not s: continue
        md.append(f"| {tier} | {s['controls']} | {s['pass']} | {s['partial']} | {s['fail']} | {s['blocked']} | {s['wrong_verdicts']} | {s['clean_grade_rate']:.0%} |")
    md += ["", "## Per-control detail", "", "| file | control | verdict | rank | deterministic | hallucination-flagged |", "|---|---|---|---|---|---|"]
    for r in all_records:
        md.append(f"| {r['file']} | {r['control_id']} | {r['verdict']} | {r['rank']} | {r['deterministic']} | {r['hallucination']} |")
    out_md = RESULTS_DIR / f"{tag}.md"
    out_md.write_text("\n".join(md))

    # console
    print("\n" + "=" * 64)
    print(f"SSP-GRADING EVAL — {model} — {tag}")
    print("=" * 64)
    print(f"controls graded: {t['controls_graded']}")
    print(f"bad_caught (BAD not passed):        {h['bad_caught']:.0%}")
    print(f"great_recognized (GREAT not failed): {h['great_recognized']:.0%}")
    print(f"pass-rate  bad/good/great:          {h['pass_rates']['bad']:.0%} / {h['pass_rates']['good']:.0%} / {h['pass_rates']['great']:.0%}")
    print(f"discrimination (climbs bad<good<great): {'YES' if h['discrimination'] else 'NO'}")
    print(f"clean_grade_rate (not blocked):    {t['clean_grade_rate']:.0%}")
    print(f"hallucination_rate (blocked):      {t['hallucination_rate']:.0%}")
    print(f"zero_bad_pass:   {'PASS' if h['zero_bad_pass'] else 'FAIL — '+str(summary['bad_tier'].get('pass',0))+' bad controls wrongly PASSed'}")
    print(f"zero_great_fail: {'PASS' if h['zero_great_fail'] else 'FAIL — '+str(summary['great_tier'].get('fail',0))+' great controls wrongly FAILed'}")
    print(f"\nwrote {out_json.relative_to(GP_MODEL_OPS)} and {out_md.relative_to(GP_MODEL_OPS)}")


if __name__ == "__main__":
    main()
