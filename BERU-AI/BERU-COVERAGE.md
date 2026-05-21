# BERU Control Coverage Map

**Audience:** 3PAO assessors, MLOps mentors, GRC engineers evaluating whether BERU's
output is fit-to-use for any specific control or system.
**Status:** living document. Updated when corpus, prompt, or guards change.
**Last updated:** 2026-05-20
**Operating champion:** `beru:v1.6` (exp-012/014) — knowledge_brain 20.0%, pentest_brain 68.2%.
**Active challenger:** `beru:v1.7` (exp-015) — knowledge_brain 34.1%, pentest_brain 63.0%. Not promoted (gate: 70%).
**Next:** exp-016 — dual-citation generator + ATLAS scenario generator, target 5,000+ examples.

> One-line summary: BERU reliably **screens** SSP claims against 42 bundled
> NIST 800-53 Rev 5 controls in 12 families (11 with SSP exemplars + SR added
> for supply-chain queries), with three output guards that quarantine roughly
> half of findings to a human queue. It is an assessor's assistant, not a 3PAO
> replacement, and it does not fix anything.

---

## 1. Purpose

A coverage map is the honest answer to the auditor question:

> *"What can your tool assess on its own, and what does it have to escalate?"*

If you cannot answer that with numbers, the tool is not auditable. This document
is BERU's answer — built from the bundled corpus, the eval results in
`4-eval-clarify/results/ssp_grading/`, and the architectural guards in
`BERU-AI/agent/`.

The gaps are as important as the coverage. They define where a human assessor
must take over.

---

## 2. Frameworks bundled

All of the following are vendored under `BERU-AI/knowledge/` so the agent is
self-contained — clone the repo, the knowledge ships with it.

| Framework | Path | What's in it |
|---|---|---|
| **NIST 800-53 Rev 5** | `knowledge/nist-800-53/controls/` | 42 control files (definition, assessment objectives, examiner red-flags) |
| NIST 800-53 audit playbooks | `knowledge/nist-800-53/playbooks/` | Per-family scanner-oriented playbooks (used for non-SSP triage paths) |
| NIST 800-53 templates | `knowledge/nist-800-53/templates/` | SSP, POA&M, evidence-package templates |
| NIST 800-53 SSP exemplars | `knowledge/nist-800-53/ssp-examples/` | 33 files: 11 families × bad / good / great tier |
| Control-owner matrix | `knowledge/nist-800-53/control-owner-matrix.md` | Maps each control → responsible role (CISO / SecOps / PlatformEng / etc.) |
| **NIST AI RMF (AI 100-1)** | `knowledge/frameworks/nist-ai-600-1/` | GOVERN, MAP, MANAGE subcategories |
| NIST AI 600-1 risk library | `knowledge/frameworks/nist-ai-600-1/` | Generative-AI risk taxonomy |
| **800-53 ↔ AI RMF crosswalk** | `knowledge/frameworks/crosswalk/` | Bidirectional map for dual-citation findings |
| **MITRE ATLAS** | `knowledge/frameworks/mitre-atlas/` | AI/ML adversarial TTPs |

Dual-citation policy: when an AI system is in scope, BERU cites **both** the
800-53 control **and** the AI RMF subcategory. Single-framework citation for an
AI system is treated as an incomplete finding.

---

## 3. NIST 800-53 control coverage

42 controls across 12 families. "Coverage" here means BERU has the control file
loaded; an SSP exemplar exists for 11 of the 12 families (SR is bundled for
supply-chain queries but has no SSP exemplar yet).

| Family | Controls bundled | SSP exemplars | Eval evidence |
|---|---|---|---|
| **AC** — Access Control | AC-2, AC-3, AC-5, AC-6, AC-17 | bad/good/great | **strong** — 4 runs, 50 control-grade pairs |
| **AU** — Audit & Accountability | AU-2, AU-3, AU-6, AU-7, AU-9, AU-11, AU-12 | bad/good/great | not yet eval'd under current prompt |
| **CA** — Assessment & Authorization | CA-2, CA-7 | bad/good/great | partial — 2 runs at baseline prompt only |
| **CM** — Configuration Management | CM-2, CM-3, CM-6, CM-7, CM-8 | bad/good/great | not yet eval'd under current prompt |
| **CP** — Contingency Planning | CP-9, CP-10 | bad/good/great | not yet eval'd under current prompt |
| **IA** — Identification & Authentication | IA-2, IA-3, IA-4, IA-5 | bad/good/great | not yet eval'd under current prompt |
| **IR** — Incident Response | IR-4, IR-8 | bad/good/great | partial — 2 runs at baseline prompt only |
| **PL** — Planning | PL-2 | bad/good/great | parser fix shipped exp-010; no prompt-tuned eval yet |
| **RA** — Risk Assessment | RA-3, RA-5, RA-7 | bad/good/great | not yet eval'd under current prompt |
| **SC** — System & Comms Protection | SC-7, SC-8, SC-12, SC-13, SC-28 | bad/good/great | not yet eval'd under current prompt |
| **SI** — System & Info Integrity | SI-2, SI-3, SI-4, SI-7 | bad/good/great | not yet eval'd under current prompt |
| **SR** — Supply Chain Risk Management | SR-3, SR-4 | _none yet_ | no eval — coverage is reference-only for now |

**Honest read:** training corpus covers all 11 families uniformly; prompt-tuned
eval evidence is concentrated on AC. Assessor confidence outside AC should be
calibrated to "behaves like the AC numbers in [§5](#5-measured-performance) on
average, with the caveat that we haven't proven it per-family yet." See
[§6 Per-family caveats](#6-per-family-caveats) for what to ask about each.

---

## 4. Operating model

### 4.1 The graph

A finding moves through a 12-node LangGraph DAG before it leaves the agent:

```
parse_input → extract_ssp_claims → select_next_control → assess_control
   → cite_controls → guard_citations → guard_evidence → guard_stub
   → rank_classify → hitl_gate → write_finding (loop) → emit
```

Each guard can either **pass**, **bump-to-HITL**, or **block-and-quarantine**.
The output you see is only what cleared all three guards; everything else lands
in `state["blocked_findings"]` for human review.

### 4.2 The three output guards

| Guard | Catches | What it does |
|---|---|---|
| **Citation guard** (`guard_citations`) | Invented control IDs (`AC-2(99)`, `XX-1`) | Strip + bump to HITL with `citation_invalid=True` |
| **Evidence guard** (`guard_evidence`) | Claims about files / tools / values not in the SSP or evidence input | Bump to HITL with `evidence_hallucination=True` |
| **Stub guard** (`guard_stub`) | Findings that say "needs review" without specifics, or that quote nothing | Block-and-quarantine |

The **evidence guard is the workhorse**: in the latest eval (`exp-011-promptfix`)
it intercepted 8 of 15 findings (53%) — every one of those would have been a
fabricated assessment if it had shipped.

### 4.3 The HITL gate (MANAGE-2.2)

After the guards, the rank classifier assigns E / D / C / B / S. The HITL gate
is hardcoded:

- **E, D, C with `auto_ok=True`** → emitted to the JSON output
- **B, S, or anything bumped by a guard** → routed to the HITL queue at
  `/api/beru/hitl/queue`. Cannot bypass.

This means: **BERU's max autonomous authority is C-rank.** This is architectural,
not aspirational. The check is in `agent/nodes.py::hitl_gate` and tested in
`8-tests/test_evidence_guard.py`.

### 4.4 What BERU does **not** do

- **Does not fix.** No remediation code path. Routing is "report → human / Katie / JADE."
- **Does not approve above C-rank.** Architectural ceiling, not a config knob.
- **Does not run scanners.** Only parses scanner output handed to it.
- **Does not write to git or trigger jobs.** Inference-only API.
- **Does not learn online.** Static fine-tune; retraining is a separate explicit pipeline.

---

## 5. Measured performance

Four real eval runs on the bundled SSP exemplars, scored by
`4-eval-clarify/eval_ssp_grading.py`. Headline metrics:

- `bad_caught` = fraction of BAD-tier controls that did **not** receive PASS (↑)
- `great_recognized` = fraction of GREAT-tier controls that did **not** receive FAIL (↑)
- `clean_grade_rate` = fraction of findings that cleared all guards (↑)
- `hallucination_rate` = fraction quarantined for invented evidence (↓ → 0)
- `zero_bad_pass` / `zero_great_fail` = the two hard gates that must be PASS

| Run | Model | Prompt | Controls | bad_caught | great_recognized | clean | halluc | zero_bad_pass | zero_great_fail |
|---|---|---|---|---|---|---|---|---|---|
| exp-010-baseline | v1.4 | original | 27 (AC+CA+IR) | 44% | 33% | 41% | 59% | **FAIL** | PASS |
| exp-011-vs-baseline | v1.5 | original | 27 (AC+CA+IR) | 33% | 44% | 52% | 48% | PASS | **FAIL** |
| **exp-011-promptfix** ★ | **v1.5** | **promptfix** | 15 (AC) | 40% | 40% | 47% | 53% | **PASS** | **PASS** |
| exp-012-promptfix | v1.6 | promptfix | 15 (AC) | 20% | 40% | 53% | 47% | **FAIL** | PASS |

★ = current champion. **Both hard gates PASS for the first time.**

### 5.1 Why `beru:v1.5 + promptfix` is the operating point

This is the only run that cleared **both** `zero_bad_pass` and `zero_great_fail`
with non-blocked verdicts. It is also the first run that produced any PASS
verdict on a great-tier SSP (AC-6 and AC-17 on `AC-ssp-great.md`).

Champion findings on AC (the 5/5/5 grid):

|  | AC-2 | AC-3 | AC-5 | AC-6 | AC-17 |
|---|---|---|---|---|---|
| **bad** | PARTIAL ✓ | BLOCKED | PARTIAL ✓ | BLOCKED | BLOCKED |
| **good** | PASS ✓ | PASS ✓ | PASS ✓ | BLOCKED | BLOCKED |
| **great** | BLOCKED | BLOCKED | BLOCKED | PASS ✓ | PASS ✓ |

7 of 15 controls cleanly graded. 0 wrong verdicts. 8 quarantined to HITL —
which is exactly the role of the guards.

### 5.2 Why `beru:v1.6` is **do-not-promote**

exp-012 doubled the PASS exemplars in the corpus and tightened the PASS-tier
template. The model over-generalized: it now scores any SSP narrative that
"names a mechanism + names an interval + names an artifact" as PASS, even when
the values are vague. On `AC-ssp-bad.md` it wrongly PASSed AC-3 and AC-17 —
breaking `zero_bad_pass`. **This is exactly the failure mode the eval is meant
to catch**, and the gate held: v1.6 stays in the registry but does not ship.

Path forward, **not done in this milestone**: exp-013 = roll corpus back +
add strict-discriminator examples (vague language is a disqualifier, not a
PASS hint). Tracked in `5-experiments/exp-012-beru-v1.6/notes.md`.

### 5.3 Reproducing

```bash
# from GP-MODEL-OPS/
export BERU_MODEL=beru:v1.5
python3 4-eval-clarify/eval_ssp_grading.py --families AC --tag repro
```

Outputs to `4-eval-clarify/results/ssp_grading/repro.{json,md}`.

---

## 6. Per-family caveats

For any control family **not** named here, BERU has been trained but not yet
prompt-tuned-eval'd. Assessor working position: route through HITL until a
per-family eval exists.

| Family | What you can trust today | What you must verify by hand |
|---|---|---|
| **AC** | Bad/good/great discrimination, first PASS verdicts on great-tier, 0 wrong verdicts in champion run | Findings on AC-3, AC-6 quarantined more often than the others — read the HITL queue, do not assume "blocked" = "fail" |
| **AU** | Control IDs and audit-policy concepts cited correctly | Verdicts and CISO summaries — no eval yet under current prompt |
| **CA** | Findings parsed from SSP structure; baseline prompt produces high HITL rate | CA-2, CA-7 verdicts — baseline prompt blocked 100% of great-tier on these |
| **CM** | Trained on bad/good/great; no eval evidence yet | All verdicts |
| **CP** | Trained; no eval evidence yet | All verdicts |
| **IA** | Trained; no eval evidence yet | All verdicts |
| **IR** | Findings parsed correctly; baseline prompt left great-tier at PARTIAL | Whether champion prompt improves PASS-rate on great-tier IR-8 |
| **PL** | Parser fix shipped (single-control SSP form supported as of exp-010 baseline commit) | PL-2 hasn't been re-eval'd under champion prompt |
| **RA** | Trained; no eval evidence yet | All verdicts |
| **SC** | Trained; no eval evidence yet — and SC-7 / SC-8 / SC-13 are common high-stakes findings | All verdicts; treat as HITL-only until eval'd |
| **SI** | Trained; no eval evidence yet | All verdicts |
| **SR** | Control language only (SR-3, SR-4); no SSP exemplar yet | Anything SR-related — answer is reference-grade, not grading-grade |

---

## 7. Known failure modes

These are real, observed, and documented in the eval files cited.

### 7.1 Evidence hallucination on sparse SSPs

**Symptom:** the SSP narrative says "RBAC is enforced" with no specifics; BERU
returns a finding citing `audit-policy.yaml`, `falco-rules.yaml`, and a specific
percentage that appears nowhere in the input.

**Mitigation:** `guard_evidence` flags every claim made about a file or value
that is not in the input. Findings with `evidence_hallucination=True` cannot be
emitted — they are routed to HITL.

**Current rate:** 47–53% of findings on AC bad/great tiers
(`exp-011-promptfix.json`). This is the dominant reason for HITL queue volume.

### 7.2 Pattern-matching on control ID

**Symptom:** BERU sees "AC-6" and produces a finding about Kubernetes
`cluster-admin` even when the SSP describes a non-Kubernetes IAM system. The
model is matching control-ID → memorized exemplar, not reading the narrative.

**Mitigation:** the SSP-grading prompt (`_ssp_grading_prompt` in
`agent/nodes.py`) is narrative-first and includes a one-shot "gold standard"
exemplar (the AC-6 PASS example). The family-playbook scanner-style prompt has
been removed from the SSP path because it was reinforcing the pattern-match.

**Current rate:** post-promptfix, 0 verdict-level errors in the champion run.
But this failure mode resurfaces in v1.6 (exp-012) — the gate caught it.

### 7.3 Great-tier under-recognition

**Symptom:** BERU sees a high-quality SSP narrative and still defaults to
PARTIAL because it hasn't seen enough PASS exemplars at training time.

**Mitigation:** PASS exemplars added in exp-011 corpus; champion now produces
PASS verdicts on great-tier AC-6 and AC-17. **Not yet generalized to other
families** — see [§6 Per-family caveats](#6-per-family-caveats).

### 7.4 Single-control SSPs

**Symptom:** SSPs that describe one control under an `## XX-N — Title` header
(common for PL-2, IR-8, CA-2 style narratives) used to parse as 0 claims.

**Mitigation:** `_extract_ssp_claims` in `agent/nodes.py` adds a second pass for
`## XX-N` header sections. Shipped with the exp-010 baseline commit. Tested on
all 11 family exemplars.

### 7.5 Enhancement IDs (`AC-2(1)`)

**Symptom:** SSPs cite enhancements; control-file lookup would fail because the
file is named `AC-2.md`, not `AC-2(1).md`.

**Mitigation:** `_base_control()` normalizes enhancement IDs to the parent
control for file lookup; the enhancement ref is preserved on the claim chunk
for the finding output.

---

## 8. Hard limits — what BERU cannot assess

These are areas where automation is **not** appropriate and a human assessor
must take over. Documenting them is the point.

| Out of scope | Why | Who handles it |
|---|---|---|
| **Physical access (PE family)** | No bundled corpus; physical security is interview + walkthrough work | 3PAO assessor on-site |
| **Change control board minutes (CM-3 governance)** | BERU can grade the SSP text about the CAB; it cannot read minutes or attendance | Human reviewer of meeting artifacts |
| **Cryptographic standards review (SC-12, SC-13 deep)** | BERU cites FIPS 140-2/3 control language but cannot validate that the actual algorithms in use are FIPS-validated | Cryptographic specialist + FIPS module lookup |
| **Vendor attestation chains** | BERU cannot reach out to a CSP and validate a SOC 2 / FedRAMP package on the assessor's behalf | 3PAO supply-chain review |
| **Findings rated B or S** | Architectural HITL block; B/S = "needs human + sometimes a meeting" | Human + (for B) JADE intel + (for S) CISO sign-off |
| **AI systems not in the AI inventory register** | GOVERN-1.1 says: don't assess it as infrastructure when it's an AI system | Human triage + registration |
| **Anything BERU did not directly read** | No web search, no document fetching. If it's not in `ssp_path` / `evidence_paths`, it's not in scope of that run | Re-submit with full evidence bundle |

---

## 9. Verifying this document

Any assessor reading this should be able to verify the claims directly. Here's
how, per claim:

| Claim | Where it lives | How to verify |
|---|---|---|
| 42 controls bundled in 12 families | `BERU-AI/knowledge/nist-800-53/controls/` | `ls -1 BERU-AI/knowledge/nist-800-53/controls/ \| wc -l` (42), `\| awk -F- '{print $1}' \| sort -u` (12) |
| 33 SSP exemplars (11 × 3 tiers; SR has no SSP yet) | `BERU-AI/knowledge/nist-800-53/ssp-examples/` | `ls BERU-AI/knowledge/nist-800-53/ssp-examples/` |
| Champion = `beru:v1.5` + promptfix | `5-experiments/exp-011-beru-v1.5/notes.md` | The promotion decision is in `notes.md`; the prompt is in `agent/nodes.py::_ssp_grading_prompt` |
| Eval numbers in §5 | `4-eval-clarify/results/ssp_grading/exp-*.{json,md}` | Open the .md files directly; each was written by `eval_ssp_grading.py` at run time |
| Guards do what §4.2 says | `BERU-AI/agent/nodes.py` (`guard_citations`, `guard_evidence`, `guard_stub`) + `8-tests/test_evidence_guard.py` | Read the tests; each guard has positive + negative cases |
| HITL gate is C-rank max | `BERU-AI/agent/nodes.py::hitl_gate` + `BERU-AI/tools/hitl_router.py::route` | Check the rank → auto_ok logic |
| Data-quality gate enforced in CI | `.github/workflows/ci.yml` + `8-tests/test_beru_data_quality.py` | The CI job `test` runs both; corpus must pass before any training |
| OWASP LLM Top 10 mapping | `.github/workflows/ci.yml` header comment | Each job's OWASP control is named inline |

---

## 10. Provenance

| Artifact | File | Purpose |
|---|---|---|
| Baseline eval | `4-eval-clarify/results/ssp_grading/exp-010-baseline.{json,md}` | Floor: pre-grading-corpus, pre-promptfix |
| Corpus-only eval | `4-eval-clarify/results/ssp_grading/exp-011-vs-baseline.{json,md}` | Effect of adding 196 SSP-grading examples |
| **Champion eval** | `4-eval-clarify/results/ssp_grading/exp-011-promptfix.{json,md}` | Both hard gates PASS; first PASS verdicts on great-tier |
| Regression eval | `4-eval-clarify/results/ssp_grading/exp-012-promptfix.{json,md}` | Why v1.6 is do-not-promote |
| Experiment notes | `5-experiments/exp-010-baseline/`, `exp-011-beru-v1.5/`, `exp-012-beru-v1.6/` | Params + metrics + decision per run |
| Design decisions (control-traced) | `CAPSTONE-PROJECT/beru-design-decisions.md` | 7 design decisions, each cited to a 800-53 / AI RMF control |
| Crosswalk | `BERU-AI/knowledge/frameworks/crosswalk/800-53-to-ai-rmf.md` | Bidirectional 800-53 ↔ AI RMF |
| AI inventory register (BERU itself) | `CAPSTONE-PROJECT/intake/ai-inventory-register.md` | GOVERN-1.1 compliance for this very agent |

---

## 11. Change log

| Date | Version | Change |
|---|---|---|
| 2026-05-13 | 1.0 | Initial coverage map. Champion = `beru:v1.5 + promptfix`. v1.6 documented as do-not-promote. |

---

**For the assessor:** read §5 first for the actual numbers, §6 for what to
verify on your specific family, §7 for the failure modes that determine when
to take BERU's output and when to discard it. §8 lists what BERU does not do —
treat those as your work, not BERU's.
