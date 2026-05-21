# AI System Risk Assessment

> Use this template when a new AI system is registered or when an existing system changes materially.
> This is the artifact that justifies the risk tier assigned in the AI System Registration Form.
> Maps to: MAP 3.5, MAP 5.1, GOVERN 1.3, GOVERN 1.4, RA-3

---

## System Reference

| Field | Value |
|---|---|
| **System ID** | |
| **System Name** | |
| **Assessment Date** | |
| **Assessor** | |
| **Assessment Trigger** | (initial / model version change / scope change / incident) |

---

## Section 1 — Intended Use vs Actual Capability

**Intended use (from registration form):**
```
[Copy from Section 2 of registration form]
```

**Capability gap analysis:**

| Intended Capability | Tested? | Test Method | Result |
|---|---|---|---|
| Maps findings to correct 800-53 control | | eval suite | |
| Maps AI findings to correct AI RMF subcategory | | eval suite | |
| Produces PASS/PARTIAL/FAIL correctly | | eval suite | |
| Does not hallucinate control IDs | | adversarial test | |
| Escalates B/S-rank correctly | | unit test | |
| HITL router fires for B/S | | integration test | |

---

## Section 2 — AI-Specific Risk Identification (AI 600-1 Categories)

Assess each AI 600-1 risk category for this system. Mark likelihood (L) and impact (I) on 1-5 scale.

### Accuracy and Reliability
| Risk | L (1-5) | I (1-5) | Score | Mitigation |
|---|---|---|---|---|
| Misclassified control family | | | | RAG grounding, eval gate |
| Hallucinated CVE/CWE ID | | | | System prompt hard stop, validate_control_id() |
| Wrong PASS/PARTIAL/FAIL status | | | | Evidence gap field required, SSP quality standard |
| Missed critical finding | | | | Mandatory evidence review step, human confirms B/S |

### Bias and Fairness
| Risk | L (1-5) | I (1-5) | Score | Mitigation |
|---|---|---|---|---|
| Inconsistent severity rating across system types | | | | Eval suite tests same finding across different contexts |
| Over-penalizing or under-penalizing specific vendors | | | | Training data balanced across AWS/GCP/K8s/on-prem |

### Privacy
| Risk | L (1-5) | I (1-5) | Score | Mitigation |
|---|---|---|---|---|
| PII in scanner output processed by model | | | | Scanner normalization strips PII before LLM sees it |
| Training data contained sensitive org data | | | | Synthetic training data only (Gemini-generated) |

### Robustness and Adversarial Inputs
| Risk | L (1-5) | I (1-5) | Score | Mitigation |
|---|---|---|---|---|
| Prompt injection via malicious scanner output | | | | Input sanitization before LLM call, output validation |
| Adversarial input designed to suppress a finding | | | | RAG grounding — control text retrieved independently |
| System prompt extraction | | | | System prompt not exposed in API responses |

### Transparency and Explainability
| Risk | L (1-5) | I (1-5) | Score | Mitigation |
|---|---|---|---|---|
| BERU cannot explain why it assigned a control | | | | Reasoning field in finding output (mapped from RAG) |
| Auditor cannot trace finding to scanner evidence | | | | Evidence reviewed field required, timestamped artifacts |

### Security and Resilience
| Risk | L (1-5) | I (1-5) | Score | Mitigation |
|---|---|---|---|---|
| Model weights tampered with | | | | cosign verification, hash check on load |
| RAG collection poisoned | | | | Ingestion validation, collection access control |
| Unauthorized access to BERU API endpoint | | | | Auth on /api/beru, network policy, rate limiting |

---

## Section 3 — Risk Score Summary

Score = L × I. Rank using GP-Copilot rank system:

| Score | Rank | Action |
|---|---|---|
| 20-25 | S | Human only. Immediate escalation. |
| 12-19 | B | Human decides. BERU provides context. |
| 6-11 | C | BERU proposes. Human approves. |
| 2-5 | D | Auto with logging. |
| 1 | E | Auto. |

**Top risks this assessment:**

| Risk | Score | Rank | Assigned To | Due Date |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

---

## Section 4 — Risk Acceptance or Treatment

For each risk ranked C or above:

### Risk [ID]
**Risk statement:** [one sentence — what can go wrong, what is the impact]
**Treatment choice:**
- [ ] Accept: risk is within tolerance as documented in GOVERN 1.5
- [ ] Mitigate: specific control implemented (describe below)
- [ ] Transfer: responsibility assigned elsewhere (document)
- [ ] Avoid: scope limited to exclude this risk (document)

**Mitigation (if selected):**
```
[What control was implemented, where it is in code, how it is tested]
```

**Residual risk after mitigation:**
Likelihood: [1-5] × Impact: [1-5] = Score: [N] → Rank: [E/D/C/B/S]

**Accepted by:** [name + role + date]

---

## Section 5 — AI RMF Subcategory Coverage After Mitigation

| AI RMF Subcategory | Status | Evidence |
|---|---|---|
| GOVERN 1.1 (policies established) | | |
| GOVERN 1.2 (accountability) | | |
| GOVERN 1.5 (risk tolerance) | | |
| MAP 1.1 (context established) | | |
| MAP 2.3 (limitations documented) | | |
| MAP 3.1 (tested in context) | | |
| MEASURE 2.5 (output trustworthiness) | | |
| MEASURE 2.7 (monitoring) | | |
| MEASURE 2.11 (security/resilience) | | |
| MANAGE 1.1 (risks prioritized) | | |
| MANAGE 2.2 (mitigations implemented) | | |
| MANAGE 3.1 (incident response) | | |
| MANAGE 4.1 (post-deployment monitoring) | | |

---

## Completed Example — BERU Current Prototype

**Top risks:**

| Risk | L | I | Score | Rank | Mitigation |
|---|---|---|---|---|---|
| Hallucinated control ID | 3 | 4 | 12 | B | `validate_control_id()` + RAG grounding + hard stop in system prompt → residual: 2×3=6, C |
| Missed B/S-rank finding | 2 | 5 | 10 | B | HITL router required, human reviews all B/S output → residual: 1×5=5, C |
| Prompt injection via scanner output | 2 | 4 | 8 | C | Input sanitization in `scanner_normalizer.py` → residual: 1×3=3, D |
| PII in training data | 1 | 4 | 4 | D | Synthetic training data only (Gemini-generated) → residual: 1×2=2, E |

**Risk tier determination:** After mitigations, no residual S/B-rank risks. Highest residual is C. Risk tier: Minimal Risk (all decisions advisory, HITL enforced).
