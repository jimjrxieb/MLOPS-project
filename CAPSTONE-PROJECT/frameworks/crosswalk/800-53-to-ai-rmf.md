# Crosswalk — NIST 800-53 Rev 5 ↔ NIST AI RMF 1.0

> When BERU assesses an AI system, it uses BOTH frameworks.
> 800-53 controls apply to the IT environment hosting the AI.
> AI RMF subcategories apply to the AI system itself.
> This crosswalk tells you which to use for which type of finding.

---

## How to Use This

**Finding from a scanner (Trivy, kube-bench, Prowler)** → Use 800-53 controls + note if AI system is in scope
**Finding about an AI system's behavior, training, or outputs** → Use AI RMF subcategories + corresponding 800-53 controls
**Finding that affects both** → Cite both (e.g., "CM-6, GOVERN 1.1" — the config that governs the AI deployment)

---

## Primary Crosswalk Table

| 800-53 Control | AI RMF Function | Subcategories | Why They Map |
|---|---|---|---|
| **PL-1** (Security Planning Policy) | GOVERN | 1.1, 5.1 | AI policy is part of the security plan |
| **PL-2** (System Security Plan) | MAP | 1.1, 2.3 | SSP documents AI system context and limitations |
| **RA-3** (Risk Assessment) | GOVERN, MAP | 1.3, 1.5, 1.1, 3.5, 5.1 | Risk assessment covers AI-specific risks |
| **RA-5** (Vulnerability Monitoring) | MEASURE | 2.1, 2.6 | AI-specific vulnerabilities (prompt injection, poisoning) |
| **CA-2** (Control Assessments) | MEASURE, MAP | 2.1, 3.1 | Assessments include AI behavior testing |
| **CA-5** (Plan of Action) | MANAGE | 1.1, 2.4 | POA&M includes AI risk mitigations |
| **CA-7** (Continuous Monitoring) | GOVERN, MANAGE | 6.1, 4.1 | AI performance monitored post-deployment |
| **CM-2** (Baseline Configuration) | GOVERN | 1.1 | AI system baseline = model version + config |
| **CM-3** (Configuration Change Control) | MANAGE | 2.4 | Model version changes are configuration changes |
| **CM-4** (Impact Analysis) | MANAGE | 2.3 | Analyze impact before retraining/updating |
| **CM-6** (Configuration Settings) | GOVERN, MAP | 1.1, 1.6, 2.3 | System prompt, LoRA config, inference params |
| **CM-8** (System Component Inventory) | GOVERN | 5.2 | AI models are components — inventory them |
| **IR-4** (Incident Handling) | MANAGE | 3.1 | AI errors are incidents |
| **IR-8** (Incident Response Plan) | MANAGE | 3.1 | Plan covers AI-specific incident types |
| **PM-9** (Risk Management Strategy) | GOVERN | 1.3, 1.5 | Strategy includes AI risk tolerance |
| **PM-10** (Authorization Process) | GOVERN | 1.2 | AI system authorization is part of ATO |
| **SA-11** (Developer Testing) | MAP, MEASURE | 3.1, 2.1 | Pre-deployment AI testing |
| **SA-22** (Unsupported System Components) | MANAGE | 4.2 | Deprecated model versions |
| **SC-28** (Protection at Rest) | MAP | 2.3 | Training data and model weights at rest |
| **SI-2** (Flaw Remediation) | MANAGE | 2.2 | AI bugs (hallucinations, misclassification) remediated |
| **SI-4** (System Monitoring) | GOVERN, MANAGE | 6.1, 4.1 | AI output monitoring |
| **SI-7** (Software Integrity) | MAP | 4.1 | Model weight integrity — cosign for GGUF files |
| **SR-3** (Supply Chain Controls) | MAP | 4.1 | Base model provenance, training data sources |
| **SR-4** (Provenance) | MAP | 2.2, 4.1 | Data and model lineage documentation |

---

## AI 600-1 Specific Controls (No Direct 800-53 Equivalent)

These AI RMF subcategories address risks unique to AI systems that 800-53 doesn't fully cover:

| AI RMF Subcategory | Gap vs 800-53 | Why It Matters for BERU |
|---|---|---|
| MEASURE 2.5 (output trustworthiness) | 800-53 doesn't assess LLM output quality | BERU's findings must be factually grounded |
| MEASURE 2.9 (fairness/bias) | 800-53 doesn't measure equitable treatment | BERU should classify risk consistently across system types |
| MEASURE 2.10 (privacy) | 800-53 PT family is partial | BERU processes scanner output — check for PII in raw fields |
| MEASURE 2.11 (security/resilience) | 800-53 misses AI-specific attacks | Prompt injection against BERU could corrupt findings |
| MAP 3.2 (stakeholder impacts) | 800-53 doesn't require AI-specific stakeholder analysis | Who is harmed if BERU produces wrong findings? |
| GOVERN 1.5 (AI risk tolerance) | 800-53 RA-3 is general | AI systems need explicit tolerance statements ("BERU can err on noisy C-rank, never on B/S") |

---

## Finding Classification Guide

When BERU produces a finding, classify it using this guide:

**IT Infrastructure Finding** (kube-bench, Trivy, Prowler result):
→ Primary: 800-53 control
→ Secondary: AI RMF only if the finding affects an AI system component (e.g., MLflow pod, Ollama deployment)

**AI System Behavior Finding** (garak, promptfoo, mlflow-audit result):
→ Primary: AI RMF subcategory
→ Secondary: Corresponding 800-53 control
→ Example: "Prompt injection detected → MEASURE 2.11, SI-3 (malicious code protection)"

**AI Governance Finding** (no intake form, no model card, no HITL workflow):
→ Primary: AI RMF GOVERN subcategory
→ Secondary: 800-53 PL/PM/CA family
→ Example: "No AI system registration found → GOVERN 1.1, PL-2 PARTIAL"

**Training/MLOps Finding** (unsigned model weights, no data lineage, untracked experiment):
→ Primary: AI RMF MAP subcategory
→ Secondary: 800-53 SA/SR/CM family
→ Example: "No data lineage manifest → MAP 2.3, SR-4 FAIL"

---

## BERU System Prompt Addition (AI RMF context)

When BERU encounters an AI-related finding, it adds this to its output:

```
AI RMF SUBCATEGORY: [e.g., MEASURE 2.11]
AI RMF FUNCTION: MEASURE
NIST AI 600-1 RISK TYPE: [e.g., Prompt injection, Data poisoning, Output bias]
800-53 CROSSWALK: [e.g., SI-3, SC-7]
```

This dual citation is what distinguishes a BERU finding from a standard scanner report.
