# SSP-Grading Eval — `beru:v1.6` — `exp-012-promptfix`

Generated: 2026-05-13T16:45:03.199896+00:00
SSP files graded: 3  ·  controls graded: 15

## Headline

| Metric | Value | Want |
|---|---|---|
| bad_caught (BAD controls not passed) | 20% | ↑ → 100% |
| great_recognized (GREAT controls not failed) | 40% | ↑ → 100% |
| pass-rate: bad / good / great | 40% / 60% / 40% | bad < good < great |
| discrimination (pass-rate climbs) | NO | YES |
| clean_grade_rate (not HITL-blocked) | 53% | ↑ |
| hallucination_rate (blocked for invented evidence) | 47% | ↓ → 0% |
| zero_bad_pass | FAIL | PASS |
| zero_great_fail | PASS | PASS |

## Per-tier

| Tier | controls | PASS | PARTIAL | FAIL | blocked | wrong-verdicts | clean-grade |
|---|---|---|---|---|---|---|---|
| bad | 5 | 2 | 1 | 0 | 2 | 2 | 60% |
| good | 5 | 3 | 0 | 0 | 2 | 0 | 60% |
| great | 5 | 2 | 0 | 0 | 3 | 0 | 40% |

## Per-control detail

| file | control | verdict | rank | deterministic | hallucination-flagged |
|---|---|---|---|---|---|
| AC-ssp-bad.md | AC-3 | PASS | E | False | False |
| AC-ssp-bad.md | AC-5 | PARTIAL | D | False | False |
| AC-ssp-bad.md | AC-17 | PASS | E | False | False |
| AC-ssp-bad.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-bad.md | AC-6 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-3 | PASS | E | False | False |
| AC-ssp-good.md | AC-5 | PASS | E | False | False |
| AC-ssp-good.md | AC-17 | PASS | E | False | False |
| AC-ssp-good.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-6 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-2 | PASS | E | False | False |
| AC-ssp-great.md | AC-6 | PASS | E | False | False |
| AC-ssp-great.md | AC-3 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-17 | BLOCKED | B | False | True |