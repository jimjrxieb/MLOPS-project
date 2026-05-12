# SSP-Grading Eval — `beru:v1.5` — `exp-011-vs-baseline`

Generated: 2026-05-12T23:25:44.845123+00:00
SSP files graded: 12  ·  controls graded: 27

## Headline

| Metric | Value | Want |
|---|---|---|
| bad_caught (BAD controls not passed) | 33% | ↑ → 100% |
| great_recognized (GREAT controls not failed) | 44% | ↑ → 100% |
| pass-rate: bad / good / great | 0% / 22% / 0% | bad < good < great |
| discrimination (pass-rate climbs) | NO | YES |
| clean_grade_rate (not HITL-blocked) | 52% | ↑ |
| hallucination_rate (blocked for invented evidence) | 48% | ↓ → 0% |
| zero_bad_pass | PASS | PASS |
| zero_great_fail | FAIL | PASS |

## Per-tier

| Tier | controls | PASS | PARTIAL | FAIL | blocked | wrong-verdicts | clean-grade |
|---|---|---|---|---|---|---|---|
| bad | 9 | 0 | 3 | 0 | 6 | 0 | 33% |
| good | 9 | 2 | 2 | 2 | 3 | 0 | 67% |
| great | 9 | 0 | 4 | 1 | 4 | 1 | 56% |

## Per-control detail

| file | control | verdict | rank | deterministic | hallucination-flagged |
|---|---|---|---|---|---|
| AC-ssp-bad.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-bad.md | AC-3 | BLOCKED | B | False | True |
| AC-ssp-bad.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-bad.md | AC-6 | BLOCKED | S | False | True |
| AC-ssp-bad.md | AC-17 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-2 | PASS | C | False | False |
| AC-ssp-good.md | AC-6 | FAIL | C | False | False |
| AC-ssp-good.md | AC-17 | PARTIAL | C | False | False |
| AC-ssp-good.md | AC-3 | BLOCKED | B | False | True |
| AC-ssp-good.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-3 | PARTIAL | C | False | False |
| AC-ssp-great.md | AC-2 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-5 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-6 | BLOCKED | B | False | True |
| AC-ssp-great.md | AC-17 | BLOCKED | B | False | True |
| CA-ssp-bad.md | CA-7 | PARTIAL | D | False | False |
| CA-ssp-bad.md | CA-2 | BLOCKED | B | False | True |
| CA-ssp-good.md | CA-2 | PASS | D | False | False |
| CA-ssp-good.md | CA-7 | BLOCKED | B | False | True |
| CA-ssp-great.md | CA-2 | PARTIAL | E | False | False |
| CA-ssp-great.md | CA-7 | PARTIAL | D | False | False |
| IR-ssp-bad.md | IR-4 | PARTIAL | C | False | False |
| IR-ssp-bad.md | IR-8 | PARTIAL | D | False | False |
| IR-ssp-good.md | IR-4 | PARTIAL | D | False | False |
| IR-ssp-good.md | IR-8 | FAIL | C | False | False |
| IR-ssp-great.md | IR-8 | FAIL | C | False | False |
| IR-ssp-great.md | IR-4 | PARTIAL | D | False | False |