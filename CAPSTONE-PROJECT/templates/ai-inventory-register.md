# AI System Inventory Register

> Tracks all AI systems in the GP-Copilot environment.
> Required by: GOVERN 5.2, CM-8 (System Component Inventory)
> Update when: any AI system is added, removed, or materially changed.
> Owner: ISSO (jimjrxieb)
> Review cadence: quarterly or after any AI system change

---

## Purpose

This register exists to answer the auditor question: "What AI systems are running in your environment, and do you know the risk posture of each one?"

A system that isn't in this register isn't authorized. Discovery of an unregistered AI system is a GOVERN 1.1 FAIL.

---

## AI System Registry

| System ID | Name | Role | Model | Version | Risk Tier | Status | Registration Date | Last Reviewed |
|---|---|---|---|---|---|---|---|---|
| JSA-AI-001 | JADE | DEVOPS-LENS execution engine | LLaMA 3.1-8B | v1.1 | Limited Risk | Active | 2026-03-25 | 2026-05-07 |
| JSA-AI-002 | Katie | K8s operations agent | LLaMA 3.2-3B | v1.1 | Limited Risk | Active | 2026-03-25 | 2026-05-07 |
| JSA-AI-003 | BERU | NIST-800-53 + AI RMF GRC analyst | LLaMA 3.2-3B | v1.0 | Minimal Risk | In Development | 2026-05-07 | 2026-05-08 |
| JSA-AI-004 | RANK-AI | E/D/C/B/S rank classifier | sklearn | v1.0 | Minimal Risk | Active | 2026-03-25 | 2026-05-07 |

---

## Per-System Risk Summary

### JSA-AI-001 — JADE

| Field | Value |
|---|---|
| **Autonomy Level** | C-rank max (proposes, human approves) |
| **Decision Authority** | Advisory for C-rank, auto for E/D |
| **Human Oversight** | Required for C-rank and above |
| **Data Processed** | Scanner output, cluster state (no PII) |
| **HITL Enforced** | Yes — B/S rank always routes to J |
| **Serving** | Ollama localhost:11434, FastAPI /api/jade |
| **Monitoring** | MLflow inference tracking in JADE-AI/mlruns/ |
| **Known Limitations** | May mis-scope findings outside 01-APP-SEC / 02-CLUSTER-HARDEN |
| **Registration Link** | [ai-system-registration-JADE.md] |

**AI RMF Coverage:** GOVERN 1.2 (accountable: J), MANAGE 2.2 (HITL enforced), MEASURE 2.7 (MLflow tracking)

---

### JSA-AI-002 — Katie (jsa-kubestar)

| Field | Value |
|---|---|
| **Autonomy Level** | C-rank max, deployed in-cluster |
| **Decision Authority** | Auto for E/D, proposes for C |
| **Human Oversight** | Required for C-rank and above |
| **Data Processed** | K8s cluster state, health metrics (no PII) |
| **HITL Enforced** | Yes — C-rank proposals await human approval |
| **Serving** | K8s Deployment in target cluster, 24/7 |
| **Monitoring** | k8sgpt health checks, Popeye audits |
| **Known Limitations** | K8s only — does not assess application or cloud controls |
| **Registration Link** | [ai-system-registration-Katie.md] |

**AI RMF Coverage:** GOVERN 1.2 (accountable: J), MAP 2.3 (limitations documented), MANAGE 2.2 (HITL enforced)

---

### JSA-AI-003 — BERU (In Development)

| Field | Value |
|---|---|
| **Autonomy Level** | Advisory only — never executes fixes |
| **Decision Authority** | None — produces findings, humans decide |
| **Human Oversight** | Always — all B/S-rank findings go to review queue |
| **Data Processed** | Scanner output (JSON), NIST control text (public), SSP narratives (internal) |
| **HITL Enforced** | Yes — HITL router required before any B/S output |
| **Serving** | Ollama (pending), FastAPI /api/beru (pending) |
| **Monitoring** | MLflow experiment 'beru-eval' (pending) |
| **Known Limitations** | See BERU-COVERAGE.md — partial coverage of 20 NIST families |
| **Registration Link** | `CAPSTONE-PROJECT/intake/ai-system-registration.md` |

**AI RMF Coverage (target):**
- GOVERN 1.1 (this document), 1.2, 1.3, 1.4, 1.5, 1.6
- MAP 1.1, 2.1, 2.3, 3.1, 3.2, 4.1, 4.2
- MEASURE 2.1, 2.5, 2.7, 2.11 (pending deployment)
- MANAGE 1.1, 2.2, 3.1, 4.1 (pending deployment)

---

### JSA-AI-004 — RANK-AI

| Field | Value |
|---|---|
| **Autonomy Level** | Fully automated (classification only) |
| **Decision Authority** | E/D/C/B/S rank assignment |
| **Human Oversight** | None for E/D, human reviews C/B/S |
| **Data Processed** | Finding text (no PII) |
| **HITL Enforced** | Downstream — rank output routes to HITL |
| **Serving** | sklearn pkl loaded at runtime |
| **Monitoring** | 8-tests/ test_rank_classifier.py |
| **Known Limitations** | Rule-based for obvious patterns; may mis-rank novel finding types |
| **Registration Link** | [ai-system-registration-RANK.md] |

---

## Audit Trail

| Date | Change | Who | AI RMF Reference |
|---|---|---|---|
| 2026-05-07 | BERU registered (in development) | jimjrxieb | GOVERN 1.1 |
| 2026-03-25 | JADE, Katie, RANK-AI registered | jimjrxieb | GOVERN 1.1 |

---

## Unregistered AI System Policy

Any AI system in the GP-Copilot environment that is not in this register is:
1. **Unauthorized** — not approved to operate
2. **GOVERN 1.1 FAIL** — BERU will generate a finding
3. **Immediate escalation** to J (human) — B-rank finding

Discovery checklist:
```bash
# Find all Ollama models running
ollama list

# Find all AI-related deployments in K8s
kubectl get deployments -A -o json | jq '.items[] | select(.metadata.name | test("ai|llm|model|ollama|jade|katie|beru"; "i")) | {ns: .metadata.namespace, name: .metadata.name}'

# Find all FastAPI routes with AI-related paths
grep -r "api/jade\|api/katie\|api/beru\|api/ai\|api/llm" GP-INFRA/GP-API/
```

Compare against this register. Any system found but not registered → BERU generates GOVERN 1.1 FAIL finding.
