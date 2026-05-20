# 0-data-lab — Data Science Workspace

Raw data goes in. Training-ready JSONL comes out.

This is where the corpus gets built — one gap at a time. Every time an eval run shows a weak category, the fix starts here: write a generator, produce examples, validate them, drop them into `1-FineTuning-Pipeline/01-raw-data-lake/`.

---

## What's Here

```
tools/                ← 45 targeted generators, one per domain/skill gap
synthetic-pipeline/   ← automated pipeline: JSA findings → ChatML training examples
mlops-loop-training/  ← feedback loop data: gap audits + new targeted examples
ci-evidence/          ← CI debugging sessions that became training signal
claudecode-fixes/     ← real Claude Code engagement sessions (AppSec, Falco, FedRAMP)
gp-consulting-findings/ ← real consulting data (gitignored — NIST control matrix)
seclab-findings/      ← SecLab scan evidence for BERU training scenarios
```

---

## tools/ — 45 Targeted Generators

Each script builds a specific batch of ChatML training examples for one domain or skill:

| Category | Scripts |
|----------|---------|
| CKS | `generate_cks_scenarios.py`, `generate_cks_training.py`, `generate_cks_terminology_*.py` |
| CKA / CNPA | `generate_cka_admin_ops.py`, `generate_cnpa_training.py`, `generate_cnpa_platform_gaps.py` |
| BERU / GRC | `generate_beru_*.py`, `generate_compliance_batch.py` |
| Cloud | `generate_cloud_aws_batch.py`, `generate_aws_cli_ops.py`, `generate_aws_saa_study.py` |
| Security tooling | `generate_falco_batch.py`, `generate_checkov_batch.py`, `generate_admission_deny_fixes.py` |
| Hardening | `generate_hardening_batch.py`, `generate_netpol_batch.py` |
| Eval repair | `generate_eval_corrections.py` — fixes wrong answers caught in live eval |

All generators write to `1-FineTuning-Pipeline/01-raw-data-lake/` (gitignored).

```bash
python3 tools/generate_cks_scenarios.py
python3 tools/generate_falco_batch.py --count 200
```

---

## synthetic-pipeline/ — Automated Training Factory

Converts real JSA security findings and scan outputs into ChatML examples automatically.

```
pipeline.py (5 phases: discover → generate → merge → validate → save)
    ↓
crew/ → 10-crewai-mlops/synthetic_pipeline/ (CrewAI: orchestrator + auditor + reporter)
```

Use this when you have real JSA operational data (scan logs, escalations, fix notes) and want to convert it to training examples at scale. The direct pipeline runs without LLM overhead; the crew adds quality analysis and coverage reporting.

```bash
cd 0-data-lab/synthetic-pipeline
python3 -m pipeline                         # run from real JSA findings
python3 -m crewai_mlops.synthetic_pipeline.main run  # via crew (port 8001)
```

See [`synthetic-pipeline/README.md`](synthetic-pipeline/README.md) for full docs.

---

## mlops-loop-training/ — Feedback Loop

When `4-eval-clarify/` identifies a gap, new examples go here first:

```
mlops-loop-training/
  audit/       ← corpus audit notes (what the eval found, what to generate next)
  new-data/    ← targeted JSONL batches from gap analysis
    dual-citation-50.jsonl     ← 50 dual-citation examples (800-53 + AI RMF)
    finding-accuracy-30.jsonl  ← 30 SSP-claim-vs-evidence grading examples
```

Once validated with `8-tests/test_beru_data_quality.py`, move to `1-FineTuning-Pipeline/01-raw-data-lake/`.

---

## ci-evidence/ and claudecode-fixes/

Real operational experience turned into training signal:

- `ci-evidence/` — notes from CI debugging sessions (pipeline failures, fix sequences)
- `claudecode-fixes/` — Claude Code engagement sessions: AppSec FedRAMP work, Falco+JSON+Splunk tooling

These are the raw material. Extract patterns with `tools/extract_playbooks_for_training.py`.

---

## Data Flow

```
Real findings (seclab-findings/, claudecode-fixes/, ci-evidence/)
    + targeted generation (tools/)
    + automated conversion (synthetic-pipeline/)
          ↓
    Validate: python3 -m pytest 8-tests/test_beru_data_quality.py -v
          ↓
    1-FineTuning-Pipeline/01-raw-data-lake/   ← training corpus (gitignored)
          ↓
    1-FineTuning-Pipeline/etl_pipeline.py     ← ETL → chunk → train
```
