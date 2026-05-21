# SSP-Grading Eval — `beru:v1.4` — `exp-010-baseline`

Generated: 2026-05-12T12:14:41.149099+00:00
SSP files graded: 12  ·  controls graded: 27

## Headline

| Metric | Value | Want |
|---|---|---|
| bad_caught (BAD controls not passed) | 44% | ↑ → 100% |
| great_recognized (GREAT controls not failed) | 33% | ↑ → 100% |
| pass-rate: bad / good / great | 11% / 11% / 0% | bad < good < great |
| discrimination (pass-rate climbs) | NO | YES |
| clean_grade_rate (not HITL-blocked) | 41% | ↑ |
| hallucination_rate (blocked for invented evidence) | 59% | ↓ → 0% |
| zero_bad_pass | FAIL | PASS |
| zero_great_fail | PASS | PASS |

## Per-tier

| Tier | controls | PASS | PARTIAL | FAIL | blocked | wrong-verdicts | clean-grade |
|---|---|---|---|---|---|---|---|
| bad | 9 | 1 | 4 | 0 | 4 | 1 | 56% |
| good | 9 | 1 | 2 | 0 | 6 | 0 | 33% |
| great | 9 | 0 | 3 | 0 | 6 | 0 | 33% |

## Per-control detail

| file | control | verdict | rank | deterministic | hallucination-flagged |
|---|---|---|---|---|---|
| AC-ssp-bad.md | AC-3 | PARTIAL | C | False | False |
| AC-ssp-bad.md | AC-6 | PARTIAL | C | False | False |
| AC-ssp-bad.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-bad.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-bad.md | AC-17 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-3 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-6 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-17 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-6 | PARTIAL | C | False | False |
| AC-ssp-great.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-3 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-17 | BLOCKED | B | False | True |
| CA-ssp-bad.md | CA-2 | PASS | E | False | False |
| CA-ssp-bad.md | CA-7 | BLOCKED | B | False | True |
| CA-ssp-good.md | CA-2 | PASS | E | False | False |
| CA-ssp-good.md | CA-7 | BLOCKED | B | False | True |
| CA-ssp-great.md | CA-2 | BLOCKED | B | False | True |
| CA-ssp-great.md | CA-7 | BLOCKED | B | False | True |
| IR-ssp-bad.md | IR-4 | PARTIAL | D | False | False |
| IR-ssp-bad.md | IR-8 | PARTIAL | D | False | False |
| IR-ssp-good.md | IR-4 | PARTIAL | D | False | False |
| IR-ssp-good.md | IR-8 | PARTIAL | D | False | False |
| IR-ssp-great.md | IR-8 | PARTIAL | C | False | False |
| IR-ssp-great.md | IR-4 | PARTIAL | D | False | False |