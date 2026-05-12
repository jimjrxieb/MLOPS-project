"""Sweep — run BERU agent against every SSP in BERU-AI/training-data/ssps/.

Captures per-run statistics and writes a comparison report to:
    /tmp/beru-rubric-sweep/COMPARISON.md
    /tmp/beru-rubric-sweep/<ssp-name>/  (one dir per run with the evidence ZIP)
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

GP_MODEL_OPS = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
BERU_AI = GP_MODEL_OPS / 'BERU-AI'
SSP_DIR = BERU_AI / 'training-data' / 'ssps'
OUT_ROOT = Path('/tmp/beru-rubric-sweep')

sys.path.insert(0, str(BERU_AI))
from agent.graph import run_ssp_grading  # noqa: E402

OUT_ROOT.mkdir(parents=True, exist_ok=True)

ssps = sorted(SSP_DIR.glob('ssp-*.md'))
print(f'Grading {len(ssps)} SSPs against the rubric...\n')

rows = []
for i, ssp in enumerate(ssps, 1):
    name = ssp.stem
    tier = name.split('-')[-1]
    out_dir = OUT_ROOT / name
    out_dir.mkdir(exist_ok=True)
    print(f'[{i}/{len(ssps)}] {name} ...', flush=True)
    t0 = time.time()
    try:
        result = run_ssp_grading(
            ssp_path=str(ssp),
            system_name=f'sweep-{name}',
            client='rubric-sweep',
            output_dir=str(out_dir),
            run_id=f'sweep-{name}-{int(t0)}',
        )
    except Exception as e:
        print(f'    FAILED: {e}')
        rows.append({'ssp': name, 'tier': tier, 'error': str(e)})
        continue

    findings = result.get('findings', []) or []
    blocked = result.get('blocked_findings', []) or []
    errors = result.get('errors', []) or []
    elapsed = time.time() - t0
    if errors:
        for e in errors:
            print(f'    err: {e}')
    status_dist = Counter(f.get('status', '?') for f in findings)
    rank_dist = Counter(f.get('rank', '?') for f in findings)
    det = sum(1 for f in findings if f.get('deterministic'))
    halluc = sum(1 for f in findings if f.get('evidence_hallucination'))
    bumped = sum(1 for f in findings if f.get('rank_bumped_for_hallucination'))

    rows.append({
        'ssp': name,
        'tier': tier,
        'findings_total': len(findings),
        'blocked_total': len(blocked),
        'deterministic': det,
        'brain_runs': len(findings) - det,
        'evidence_hallucinations': halluc,
        'rank_bumped': bumped,
        'status_dist': dict(status_dist),
        'rank_dist': dict(rank_dist),
        'elapsed_s': round(elapsed, 1),
        'archive': result.get('artifact_archive_path'),
        'agent_errors': errors,
        '_findings': findings,
        '_blocked': blocked,
    })
    print(
        f'    {len(findings)} findings ({det} det, {len(findings)-det} brain) | '
        f'{dict(status_dist)} | ranks {dict(rank_dist)} | '
        f'halluc={halluc} bumped={bumped} | {elapsed:.1f}s'
    )


# ── Comparison report ─────────────────────────────────────────────────────────
report = ['# BERU Rubric Sweep — All SSPs', '']
report.append(f'Generated: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}')
report.append(f'Model: beru:v1.4 (exp-010)')
report.append(f'Guards: 1 (stub), 2 (citation), 3 (evidence-groundedness)')
report.append('')

report.append('## Summary table')
report.append('')
report.append('| SSP | Tier | # findings | det/brain | PASS | PARTIAL | FAIL | ranks | halluc | bumped | time |')
report.append('|---|---|---|---|---|---|---|---|---|---|---|')
for r in rows:
    if 'error' in r:
        report.append(f'| {r["ssp"]} | {r["tier"]} | — | — | — | — | — | — | — | — | (error: {r["error"][:40]}) |')
        continue
    sd = r['status_dist']
    rd = ', '.join(f'{k}={v}' for k, v in sorted(r['rank_dist'].items()))
    report.append(
        f'| {r["ssp"]} | {r["tier"]} | {r["findings_total"]} | '
        f'{r["deterministic"]}/{r["brain_runs"]} | '
        f'{sd.get("PASS", 0)} | {sd.get("PARTIAL", 0)} | {sd.get("FAIL", 0)} | '
        f'{rd} | {r["evidence_hallucinations"]} | {r["rank_bumped"]} | {r["elapsed_s"]}s |'
    )

# Pick one example finding per tier
report.append('')
report.append('## Sample findings per tier')
report.append('')
seen_tiers = set()
for r in rows:
    if 'error' in r or r['tier'] in seen_tiers:
        continue
    if not r.get('_findings'):
        continue
    # Prefer a brain-run finding if available; else fall back to deterministic
    brain_findings = [f for f in r['_findings'] if not f.get('deterministic')]
    pick = brain_findings[0] if brain_findings else r['_findings'][0]
    seen_tiers.add(r['tier'])
    report.append(f'### Tier: `{r["tier"]}` — sample from `{r["ssp"]}` ({pick["control_id"]})')
    report.append('')
    report.append(f'- status: **{pick.get("status")}**, rank: **{pick.get("rank")}**, '
                  f'deterministic: {pick.get("deterministic", False)}, '
                  f'hallucination flagged: {pick.get("evidence_hallucination", False)}')
    if pick.get('validation_errors'):
        for e in pick['validation_errors']:
            report.append(f'- guard note: {e}')
    report.append('')
    report.append('```')
    report.append(pick.get('raw', '')[:1500])
    report.append('```')
    report.append('')

report_path = OUT_ROOT / 'COMPARISON.md'
report_path.write_text('\n'.join(report))
print()
print('=' * 60)
print(f'Comparison report: {report_path}')
print('=' * 60)
