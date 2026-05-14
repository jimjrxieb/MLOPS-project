# exp-014 — Corrected Eval Suite (2026-05-14)

## What changed and why

**Removed:** `escalation_discipline` question type (5 questions)  
**Added:** `finding_accuracy` question type (5 questions)

### The mental model error

The original escalation_discipline questions tested whether BERU would:
- Refuse to mark a risk as ACCEPTED when asked by a CISO
- Refuse to falsify a FedRAMP assessment
- Block output for B/S-rank findings until a human "approved" them

This was copied from the Katie/JADE rank system, where it makes sense — Katie proposes a cluster change, a human approves it before it executes. **BERU never executes anything.** BERU's entire output is documents.

A GRC analyst does not hold their report until the CISO approves it. They write the finding, assign a risk rank, and send it. The CISO reading the CISO summary sees "B-rank finding — executive decision required" and decides what to do. That routing happens in the human's inbox, not in BERU's code.

### What finding_accuracy tests instead

Given an SSP claim and actual evidence (IAM credential report, CloudTrail events, Prowler output, etc.), BERU must:
1. Assign the correct STATUS (PASS / PARTIAL / FAIL)
2. Cite the correct NIST 800-53 control IDs
3. Assign the correct risk rank (E/D/C/B/S)
4. Identify the correct evidence gaps

This is BERU's actual job. The 5 new questions cover:
- AC-2 (account review overdue by 10 months → PARTIAL)
- IA-2 (3 of 8 admin accounts missing MFA → FAIL)
- SC-28 + SC-12 (encryption exists but CMK claim in SSP is wrong → PARTIAL)
- CM-2 + CM-3 (6 manual console changes when SSP says all changes via CI/CD → FAIL)
- AU-9 + AU-11 (audit bucket not itself audited, DeleteObject allowed → PARTIAL)

## Results

| Type | Old suite | New suite | Delta |
|------|-----------|-----------|-------|
| `escalation_discipline` | 20% (1/5) | removed | — |
| `finding_accuracy` | — | 40% (2/5) | new baseline |
| `tool_output_interpretation` | 0% (0/5) | 20% (1/5) | +20pp |
| `evidence_gap_detection` | 20% (1/5) | 40% (2/5) | +20pp |
| `dual_citation` | 0% (0/5) | 0% (0/5) | unchanged |
| `poam_drafting` | 60% (3/5) | 20% (1/5) | -40pp (temperature variance) |
| `atlas_mapped_ai_risk` | 20% (1/5) | 0% (0/5) | -20pp (temperature variance) |
| **Overall** | **20%** | **20%** | **same pass rate** |

Overall pass rate is unchanged (6/30 = 20%) but the question set now measures the right behavior.

## What exp-015 should target

`dual_citation` is 0% across every eval run. This is the hardest capability — BERU must simultaneously:
1. Recognize that an AI system is in scope
2. Cite the 800-53 control
3. Cite the AI RMF subcategory
4. Cite the MITRE ATLAS technique

The training corpus needs more dual-citation examples that use realistic scanner inputs (garak output, promptfoo results, MLflow audit reports) rather than abstract scenarios. The current training data describes the *format* but doesn't give enough exposure to the *trigger pattern* (AI system in scope → dual citation required).
