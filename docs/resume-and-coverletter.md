# JIMMIE COLEMAN

AI Analyst | AI Governance & MLOps
Jacksonville, FL · 904-305-4220 · jimmie012506@gmail.com
linksmlm.com · github.com/jimjrxieb

---

## PROFESSIONAL SUMMARY

AI practitioner working at the intersection of model deployment and governance. Built and operate an internal AI lab covering air-gapped LLM deployment (Llama 3.2-3B), retrieval-augmented generation over ChromaDB, FastAPI integration layers, and Prometheus/Grafana monitoring of deployed AI services. Currently building **BERU** — a NIST 800-53 + NIST AI RMF GRC analyst agent — with full lineage manifest discipline, OWASP LLM Top 10 / MITRE ATLAS adversarial coverage, and a four-eval promotion-gate architecture (knowledge × brain/agent, pentest × brain/agent). Bias and explainability pipelines mapped to NIST AI RMF MEASURE and MANAGE functions — the same fairness, validity, and human-oversight discipline regulated industries require for production AI. Seven years of federal regulatory compliance translates directly into the documentation, evidence, and risk-mapping discipline financial-services AI deployment demands. Self-funded Security+, CKA, and AWS SAA. Studying for CySA+. Active DoD Public Trust Clearance.

---

## AI PROJECTS & TECHNICAL WORK

### BERU — NIST 800-53 + AI RMF GRC Analyst Agent (2026 – Present)

LLaMA 3.2-3B fine-tuned to act as a junior GRC analyst that ingests scanner output and produces structured 9-field findings with dual-framework citation (NIST 800-53 + AI RMF) and MITRE ATLAS technique mapping for AI-system findings. End-to-end build with documented design decisions, lineage discipline, and adversarial-resilience training.

**Implementation & MLOps:**
- Authored 400+ ChatML training examples (target 575) covering behavior-shaping under adversarial pressure — OWASP LLM08 (authority bypass), LLM01 (prompt injection), LLM03 (training-data poisoning), LLM06 (sensitive disclosure). Synthetic-only corpus per documented data-protection policy.
- Built 97-document RAG corpus: 39 NIST 800-53 controls + 38 AI RMF subcategories + 16 MITRE ATLAS techniques + crosswalk. Embedded with nomic-embed-text (768-dim) into ChromaDB with stable IDs and per-chunk provenance metadata.
- Established pre-fine-tune brain baseline: knowledge eval 29.4%, pentest eval 40.3% — measurable floor that the fine-tuned model must beat. Configured Unsloth/LoRA pipeline (r=32, alpha=64) for behavior-shaping SFT.
- Built four-eval-suite promotion-gate architecture: knowledge × {brain, agent}, pentest × {brain, agent}. Each suite covers OWASP LLM Top 10, AI RMF MEASURE 2, NIST 800-53, and MITRE ATLAS techniques in cross-cited test cases.

**Governance & Documentation:**
- Authored 12 design decisions (D-001 through D-012) traced to specific NIST 800-53 controls and AI RMF subcategories — every architectural choice answers a 3PAO "why did you build it that way?" question.
- Built lineage manifest with SHA-256 hash per artifact, generation-source attribution, control-evidence cross-reference. Captures the reproducibility chain from training corpus to deployed weights.
- Built corpus quality test harness — control-name pairing validation against canonical NIST sources, homogeneity check (no single phrase >5% of corpus), adversarial-floor assertion. Caught and documented a 200-example synthetic corpus that would have baked hallucinated control names into model weights.
- Documented BERU as JSA-AI-003 in AI inventory register with risk classification, risk assessment, design decisions, model card, and known-limitation disclosure.

### Anthra-SecLab — AI Deployment, Monitoring & Governance Lab (2026 – Present)

Live K3s environment running BERU and other internal AI use cases plus a production web target system. Lab produces evidence across AI implementation, MLOps monitoring, and AI governance under NIST AI RMF / AI 600-1.

**AI Implementation & MLOps:**
- Deployed air-gapped Llama 3B inference service for use cases where hosted-model APIs are prohibited (cleared / regulated environments) — the deployment pattern banks need for sensitive-data AI use cases.
- Built RAG pipeline over ChromaDB; ingestion, embedding, and query-side context injection structured for reproducibility and source-traceable model outputs.
- Exposed model and RAG endpoints through FastAPI service layer — Python-based microservice integration pattern aligned with how AI capabilities integrate into existing application workflows.
- Operate model monitoring infrastructure with Prometheus + Grafana + Alertmanager — runtime visibility, drift indicators, and alert routing for deployed AI services. Iterative tuning informed by observed performance data.

**AI Governance — NIST AI RMF & NIST AI 600-1:**
- Built bias and explainability pipeline mapped to AI RMF MEASURE 2 (fairness, validity, reliability) — the practical control evidence that demonstrates ethical AI practices to a regulator or risk function.
- Implemented Slack-based human-in-the-loop approval gate for sensitive AI actions, mapped to AI RMF MANAGE 2.3 (human oversight). Gate, decision log, and downstream action are auditable end-to-end.
- Risk-assessed each internal AI use case for data usage, model risk, and transparency posture; maintain AI inventory and risk register tracking purpose, risk classification, control mappings, mitigation status, and oversight checkpoints.

**Supporting Infrastructure & Compliance:**
- Production target system runs on K3s with Trivy vulnerability scanning, Kyverno policy enforcement, and Falco eBPF runtime detection — the operating environment within which AI services are deployed and monitored.
- Mapped infrastructure findings across ten NIST 800-53 Rev 5 control families with finding → remediation → rescan → SHA-256-signed evidence artifact, providing the regulatory baseline AI governance work sits on top of.

---

## WORK EXPERIENCE

### Preventative Maintenance Technician — JLL @ NAS Jacksonville (DoD) (2017 – Present)

Seven years of federal regulatory compliance on an active DoD installation. The same documentation discipline, gap identification, and corrective-action tracking that AI governance and regulated-industry deployment require.

- Operated under OSHA 29 CFR 1910 and HAZWOPER 29 CFR 1910.120; maintained documentation for chemical handling, EPA 608 refrigerant management, and site safety checklists in a federally regulated environment — direct analog to the regulatory recordkeeping required for financial-services compliance.
- Daily work structured against written regulatory requirements — site conditions verified, deltas documented, corrective actions logged. Functionally identical to verifying AI control implementations against documented requirements and recording gaps in a register.
- Independent operation in access-controlled facilities with continuous favorable background investigation status throughout tenure. Preventative maintenance across 600+ HVAC units on three-month cycles.

---

## EDUCATION

Undergraduate Coursework, Computer Science — Sophia Learning (transferring to WGU BS Computer Science, AI/ML focus) · January 2026 – Present

---

## CERTIFICATIONS

All certifications self-funded and self-studied.

- CompTIA CySA+ (CS0-003) — In progress
- AWS Solutions Architect Associate (SAA-C03) — February 2026
- Certified Kubernetes Administrator (CKA) — Linux Foundation, June 2025
- CompTIA Security+ (SY0-701) — February 2024

---

## TECHNICAL SKILLS

**AI / ML:** LLM deployment (air-gapped Llama 3.2-3B) · LoRA fine-tuning via Unsloth · RAG pipelines (ChromaDB, nomic-embed-text 768-dim) · FastAPI service integration · prompt engineering · adversarial robustness evaluation (Garak, promptfoo) · model monitoring (Prometheus / Grafana) · human-in-the-loop approval workflows · model lineage manifests (SHA-256 per artifact)

**AI Governance:** NIST AI Risk Management Framework · NIST AI 600-1 · MITRE ATLAS · OWASP LLM Top 10 · AI risk assessment · AI inventory & risk register · MEASURE / MANAGE function mapping · model card discipline · design-decision traceability to specific controls

**Languages & Automation:** Python · Bash · FastAPI · GitHub Actions · ArgoCD · Helm

**Cloud & Infrastructure:** AWS (EKS, IRSA, KMS, Secrets Manager) · Terraform · Ansible · Kubernetes · K3s · Docker · cosign / SBOM supply-chain controls

**GRC & Compliance:** NIST 800-53 Rev 5 (dual-citation with AI RMF for AI-in-scope findings) · NIST CSF 2.0 · FedRAMP Moderate · CIS Benchmarks · POA&M · SSP review · evidence packaging · control testing · gap analysis

**Monitoring, Logging, Detection:** Prometheus · Grafana · Alertmanager · Loki · Falco (eBPF) · Splunk (HEC) · AWS CloudTrail · GuardDuty

---
---

# COVER LETTER

**JIMMIE COLEMAN**
Jacksonville, FL · 904-305-4220 · jimmie012506@gmail.com
linksmlm.com · github.com/jimjrxieb

May 9, 2026

Hiring Team
Pathward
Re: Artificial Intelligence Analyst, I

Dear Hiring Team,

Pathward's stated purpose — financial inclusion built on responsible, secure, high-quality products — is the kind of mission where AI deployment cannot be separated from AI governance. Bias in a credit-decisioning model isn't a technical edge case in your environment; it's a regulatory and customer-trust event. That's why I'm applying for the Artificial Intelligence Analyst, I role: I work specifically at the intersection of building AI systems and governing how they make decisions, and that intersection is exactly where regulated financial-services AI lives.

On the implementation side, I run an internal AI lab where I've deployed an air-gapped Llama 3B inference service for use cases that prohibit hosted-model APIs, built a retrieval-augmented generation pipeline over ChromaDB, and exposed model and RAG endpoints through a FastAPI service layer — the same Python-based microservice integration pattern your job description calls out. Deployed services are monitored end-to-end with Prometheus, Grafana, and Alertmanager, and tuning decisions are made from observed performance data, not assumptions. My current focus project, **BERU**, is a NIST 800-53 + AI RMF GRC analyst agent: 400+ hand-authored synthetic training examples covering OWASP LLM Top 10 adversarial scenarios, an LLM + RAG brain baseline measured before any fine-tune to give a defensible score floor, and a four-eval promotion-gate architecture (knowledge × brain/agent, pentest × brain/agent) that determines whether a fine-tuned model is allowed near production.

On the governance side, I've mapped my AI work to the NIST AI Risk Management Framework — bias and explainability evaluation tied to MEASURE 2 (fairness, validity, reliability), and a Slack-based human-in-the-loop approval gate for sensitive AI actions tied to MANAGE 2.3 (human oversight). For BERU specifically, I authored 12 design decisions traced to specific NIST 800-53 controls and AI RMF subcategories — the answer to "why did you build it like this?" lives in the project, not just in my head. Each AI use case lives in a documented inventory and risk register tracking purpose, risk classification, control mappings, and oversight checkpoints. This is the same structure 3PAOs and bank examiners look for when reviewing AI deployments. Seven years operating under federal regulatory frameworks (OSHA, HAZWOPER, EPA 608) on a DoD installation is what trained me in checklist-against-reality discipline before I ever touched an AI model — and that discipline transfers cleanly to financial-services regulatory environments.

I hold an active Public Trust authorization, am self-funded through Security+, CKA, and AWS Solutions Architect Associate, and start a WGU BS in Computer Science with an AI/ML focus this fall. I'd welcome the chance to talk through how my deployment and governance work could support Pathward's AI roadmap — and to learn more about the specific use cases your team is bringing forward.

Thank you for your consideration.

Sincerely,

Jimmie Coleman
