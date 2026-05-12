# M7 — Commercial AI Strategy

> **Goal:** Understand how AI gets deployed commercially, how it's regulated, and how to talk about it without jargon.
> **Build:** A CISO briefing template that a non-technical executive can read in 3 minutes.
> **Gate:** Show the template to someone non-technical. If they ask "what is AC-6?" you failed.

---

## Why This Module Exists

The other six modules teach you to build. This module teaches you to sell — to a CISO, to a board, to a client, to a PwC or Deloitte hiring manager. The people who sign AI deployment decisions often have zero technical background. Your job is to give them exactly what they need to make a good decision, in plain English, without hiding behind acronyms.

**The analogy:** A doctor who can only explain a diagnosis in Latin isn't a good doctor. A senior security engineer who can only explain a finding in NIST control IDs isn't a good senior security engineer. The technical precision matters. The translation also matters.

This module is the translation layer.

---

## Concept 1 — Six Commercial AI Deployment Models

When a company uses AI, it falls into one of six models. These matter because each model has different risk, different liability, and different regulatory exposure.

| Model | What it means | Example | BERU relevance |
|-------|--------------|---------|----------------|
| **A — Consumer** | Use a commercial AI product as-is | ChatGPT for writing emails | Low risk, minimal customization |
| **B — Integrator** | Embed an existing AI API into your product | "Powered by GPT-4" chatbot | API dependency risk, data exposure |
| **C — Developer** | Fine-tune an existing model on your data | BERU (fine-tuned LLaMA 3.2-3B) | Training data risk, model governance |
| **D — Agentic** | AI takes autonomous actions with real effects | JADE approving C-rank fixes | HITL requirements, blast radius |
| **E — Decision Support** | AI recommends, human decides | BERU producing B-rank findings for human review | AI-assisted, not AI-controlled |
| **F — Embedded** | AI in a product that people rely on | AI-powered medical device | Highest risk, strongest governance |

**BERU is Model C + E**: fine-tuned model (C) used for decision support (E) with HITL for high-stakes decisions. That combination is what justifies the GOVERN/MAP/MANAGE framework — you need governance because you customized the model, and you need decision support oversight because findings affect real systems.

---

## Concept 2 — EU AI Act Risk Tiers

The EU AI Act (effective 2024-2026) creates four tiers based on risk to fundamental rights:

| Tier | What it means | Examples |
|------|--------------|---------|
| **Prohibited** | Banned entirely | Social scoring, real-time biometric surveillance |
| **High-Risk** | Strict requirements (transparency, HITL, accuracy) | AI in hiring, credit scoring, law enforcement, critical infrastructure |
| **Limited-Risk** | Transparency obligations only | Chatbots (must disclose it's AI), deepfake content |
| **Minimal-Risk** | No requirements | AI spam filters, game NPCs, most B2B analytics |

**Where BERU lands:** Limited to Minimal Risk. It's an internal audit tool, not customer-facing, doesn't affect individuals' fundamental rights. But — if BERU's findings influenced hiring or access control decisions, it could move toward High-Risk. That's why the coverage map and honest gap documentation matter.

**For the PwC/Deloitte roles:** EU AI Act compliance is a massive consulting opportunity right now. Every European company (and US companies operating in Europe) needs an AI inventory, risk assessment, and governance documentation. BERU's `CAPSTONE-PROJECT/` artifacts — intake form, inventory register, risk assessment template — are exactly the documents those engagements produce.

---

## Concept 3 — NIST AI 600-1 (Generative AI Specific)

NIST AI 600-1 (July 2024) extends the general AI RMF for generative AI. The key addition: 12 specific risk categories for GenAI systems.

The 6 you need to know cold (they come up in every AI governance conversation):

| Risk | Plain English | How BERU addresses it |
|------|--------------|----------------------|
| **Hallucination** | Model states false things confidently | RAG grounds output; `validate_control_id()` catches wrong IDs |
| **Prompt injection** | Malicious input manipulates model behavior | System prompt hard stops; garak scanner in `scanner_mappings.yaml` |
| **Data poisoning** | Corrupt training data produces wrong behavior | Synthetic-only training data policy (D-005); quality gates in `test_data_quality.py` |
| **Output bias** | Consistent unfair/incorrect treatment of some inputs | Eval suite covers multiple control families to detect bias |
| **Model supply chain** | Using base model weights from an unverified source | LLaMA 3.1 from Meta/Unsloth official channels; lineage manifest documents this |
| **Overhang/dual-use** | Capability misuse not intended by designers | HITL hardcoded; BERU cannot approve its own B/S findings |

---

## Concept 4 — Executive Communication Rules

These are the rules for CISO briefings, board reports, and client deliverables. Violate them and your work doesn't get read.

**Rule 1: No control IDs in executive output.**
Bad: "Finding F-001 maps to AC-6(5), PARTIAL. Risk: C-rank."
Good: "Three cloud administrator accounts have more access than their role requires. If compromised, an attacker could access all customer data."

**Rule 2: Risk in business terms.**
Bad: "Likelihood 4 × Impact 4 = 16, B-rank."
Good: "Medium probability of breach. Impact: potential $2.3M in regulatory fines and breach notification costs based on data volume."

**Rule 3: Three questions, one page.**
Every executive summary must answer:
1. What is the current state? (a number or percentage, not a letter grade)
2. What are the top 3 risks? (in business language)
3. What are we doing about it? (concrete actions with owners and dates)

**Rule 4: Lead with what the reader controls.**
If you're writing to a CISO: lead with the decisions they need to make.
If you're writing to a CTO: lead with the technical decisions they control.
If you're writing to a CFO: lead with budget impact.

**Rule 5: State what you're NOT saying.**
"This assessment covers the Kubernetes cluster only. It does not cover application-layer vulnerabilities, third-party integrations, or physical access controls."

A CISO who reads your briefing and then gets surprised by something out of scope will never trust your work again.

---

## Concept 5 — AI ROI Framing

When you're in a consulting or product role, you'll need to justify AI investment. The frame that works:

```
Before BERU:  GRC analyst + 1 week = one NIST 800-53 assessment cycle
After BERU:   GRC analyst + 1 day  = one NIST 800-53 assessment cycle + drafted POA&M + CISO briefing

Time saved: 4 days per assessment cycle
Assessment frequency: currently quarterly → could be weekly
Coverage increase: 60 controls manually → 80% automated, 100% audited
```

Convert to dollars: 4 days × $150/hr GRC analyst × 4 cycles/year = $9,600/year per analyst.
Scale to team: 5 analysts = $48,000/year in recovered capacity.
Reframe: that capacity goes to higher-value work (B/S-rank decisions, client communication, framework updates).

This is the conversation PwC and Deloitte clients care about. Not "BERU uses LLaMA 3.2-3B with LoRA r=32." The conversation is: "You're paying for a GRC analyst to manually run kube-bench and format the output. BERU does that. Your analyst reviews the findings and makes decisions. That's a better use of both."

---

## Troubleshooting M7

| Symptom | Cause | Fix |
|---------|-------|-----|
| Non-technical reader confused | Control IDs leaked into exec summary | Ctrl+F for "AC-", "SI-", "CM-" in the CISO briefing. Replace every one. |
| Executive asks "what should we do first?" | No prioritization in briefing | Always stack-rank your top 3. Give a recommendation, not a list. |
| "How do you know BERU is right?" | Trust challenge | Have the 30-question eval score ready. "74% accuracy on GRC-specific questions, validated against the published NIST standard." |
| EU AI Act question you can't answer | Tier classification confusion | Default to "Limited Risk" for internal tools, "High Risk" only if it affects individuals' rights or safety. Document your reasoning. |
| ROI number challenged | No baseline measurement | Always start with "how long does this take manually?" before the engagement ends. Measure it. |

---

## What You Build

A one-page CISO briefing template at `GP-CONSULTING/NIST-800-53/playbooks/04-ciso-briefing.md`.

The template has three sections:

```markdown
# [System Name] Security Posture — [Date]

## Current State
[One paragraph: overall compliance percentage, number of findings by severity,
trend vs last assessment. No NIST IDs. No jargon.]

## Top 3 Risks
1. **[Risk in business language]** — [Impact in dollars or operational terms] — [Owner]
2. ...
3. ...

## 90-Day Plan
| Action | Owner | Deadline | Resources |
|--------|-------|----------|-----------|
| [Specific action] | [Name/Team] | [Date] | [Hours/Cost] |
```

Fill it in with the NovaSec Cloud fictional system data. Then read it aloud. If you reach for a NIST reference while reading, rewrite that sentence.

**3PAO question this answers:** "Show me how BERU communicates findings to non-technical stakeholders."
Your answer: "BERU's CISO SUMMARY field strips all control IDs and produces business-language risk statements. The briefing template standardizes how those summaries are packaged for executives — three questions, one page, no jargon."

---

## Control Traceability

> When an auditor asks "why did you choose self-hosted vs. API? Was it a documented risk decision?" — point here.

**NIST 800-53:**

| Control | What it maps to in M7 | Audit answer |
|---------|----------------------|--------------|
| **SA-9** — External System Services | The make/buy decision (Anthropic API vs. Ollama local vs. air-gap Ollama) is evaluated against data sensitivity and network requirements | "We documented three deployment models in M7. The choice depends on data classification. FedRAMP/HIPAA workloads use local Ollama — no data leaves the environment." |
| **PM-9** — Risk Management Strategy | The 4 deployment tiers (cloud API, self-hosted, air-gap, fine-tuned) map to risk tolerance levels — C/B/S decisions for each tier | "The deployment model selection is a risk decision. We documented which tier is appropriate for each client classification in M7." |
| **SC-28** — Protection of Information at Rest | For clients where data cannot leave the environment, local Ollama with GGUF models keeps all inference on-prem | "Clients with data residency requirements use the air-gap deployment. No external API calls. Model weights are on-prem. Evidence: Modelfile_beru3b loads a local GGUF." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **GOVERN-1.1** — Organizational policies for AI are documented | M7 forces the deployment model decision into writing before any client engagement — it's a governance artifact | "Before deploying BERU for any client, we document the deployment model, data handling, and human oversight plan. M7 is the checklist." |
| **MAP-5.2** — Impact of the AI system is evaluated | The business case analysis in M7 — what BERU covers vs. what humans still decide — defines the scope of AI impact | "BERU's authority is bounded: assess and document up to C-rank, escalate B/S to humans. That boundary is in the deployment documentation." |
