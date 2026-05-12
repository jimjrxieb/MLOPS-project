# BERU Control Traceability

**System:** BERU-AI — junior GRC analyst agent, LLaMA 3.2-3B fine-tuned + LangGraph orchestrator
**Frameworks in scope:** NIST 800-53 Rev 5, NIST AI RMF 1.0, NIST AI 600-1 (Jul 2024)
**Last updated:** 2026-05-11
**Owner:** GP-Copilot platform team
**Intended reader:** 3PAO auditor, internal compliance reviewer

This document is the trace from each compliance claim BERU makes to the specific
file, function, test, or process that implements the claim. Every row is verifiable
by reading the cited path or running the cited command.

If a row claims a behavior that the cited code does not implement, this document
is wrong and must be corrected. Do not patch reality to match the document.

---

## How to read this document

1. **Component inventory** — every file in the BERU stack and what it does.
2. **AI RMF mapping** — each subcategory cited and which component satisfies it.
3. **NIST AI 600-1 risk mapping** — each risk type and the mitigation.
4. **NIST 800-53 mapping** — each control and the component or process.
5. **Gap register** — items not yet satisfied; honest list with a remediation owner.
6. **Verification commands** — copy-paste commands a 3PAO can run to confirm a claim.

---

## 1. Component Inventory

Paths are relative to `GP-MODEL-OPS/BERU-AI/` unless prefixed.

| Component | Path | Role | Traceability claim |
|---|---|---|---|
| Fine-tuned model | `../3-model-registry/beru-v1.4-3b/merged_16bit/` | The brain (LLaMA 3.2-3B fine-tune of exp-010) | Provenance: `../5-experiments/exp-010-beru-v1.4/metrics.json` |
| Quantized GGUF | `../3-model-registry/beru-v1.4-3b/gguf/beru-v1.4-q8_0.gguf` | Deployment artifact (Q8_0, 3.4 GB) | Conversion log: `../3-model-registry/beru-v1.4-3b/gguf/convert.log` |
| Deployment manifest | `Modelfile_beru_v14` | Ollama `Modelfile` — version, system prompt, params, stop tokens | Verify: `ollama show beru:v1.4 --modelfile` |
| Inference server | Ollama 0.11.7 | Local OpenAI-compatible inference endpoint | `curl http://localhost:11434/api/tags` |
| RAG corpus | `../2-rag-ingestion/05-ragged-data/chroma/` (collection `beru-nist-800-53`) | 166 docs: 42 controls + 57 AI RMF + 16 ATLAS + 33 SSP + crosswalk + audit playbooks | Ingestion: `../2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py` |
| Provider abstraction | `providers/ollama.py` | HTTP client; resolves model name via `BERU_MODEL` env or default `beru:v1.4` | grep `BERU_MODEL` |
| Scanner ingestion | `core/findings_ingestion.py`, `core/tool_output_parser.py` | Normalizes 20 scanner formats into common finding dict | `config/scanner_mappings.yaml` |
| Control tagger | `core/nist_mapper.py` | Deterministic mapping: scanner+keywords → 800-53 + AI RMF subcategories | `validate_control_id`, `validate_ai_rmf_id` |
| Triage engine | `core/triage_engine.py` | Rank classifier (E/D/C/B/S) | — |
| SSP parser | `tools/ssp_parser.py` | Markdown SSP → control-keyed chunks; `enforce_synthetic` gate for training corpus | `_validate_source` |
| HITL router | `tools/hitl_router.py` | Blocks B/S findings from auto-output; persists pending queue to disk | `route()` raises on B/S |
| Evidence packager | `tools/evidence_packager.py` | Bundles findings + POA&M + SSP narratives into sha256-manifested ZIP | `package()` |
| Agent state | `agent/state.py` | Typed BERUState; list fields use `operator.add` reducer | `BERUState` TypedDict |
| Playbook loader | `agent/playbook_loader.py` | Reads playbooks from canonical `GP-CONSULTING/NIST-800-53/` at runtime; no local copies | `load_start_here`, `load_family_playbook`, `load_control` |
| Graph nodes | `agent/nodes.py` | 12 pure-function nodes + 3 routing helpers | All node functions |
| Graph DAG | `agent/graph.py` | LangGraph workflow; conditional edges for stub-skip and HITL routing | `build_graph()` |
| **Guard 1 — stub detector** | `agent/nodes.py:narrative_check` | Synthesizes deterministic FAIL when SSP narrative < 50 chars or matches stub tokens | `_STUB_TOKENS`, `_STUB_MIN_CHARS` |
| **Guard 2 — citation validator** | `agent/nodes.py:validate_citations` | Rejects findings citing control IDs not in the allow-list or controls/ | `_NIST_RE`, `_AI_RMF_RE` |
| **Guard 3 — evidence groundedness** | `agent/nodes.py:evidence_groundedness_check` | Rejects findings citing files/commands/tools not in source input; rank bumped to B | `_tokens_in_evidence_block`, `_EVIDENCE_TOKEN_RES` |
| CLI entry | `run_beru.py` | `audit`, `grade-ssp`, `ask`, `ciso-brief` subcommands | — |
| Workflow eval | `../4-eval-clarify/beru_workflow_eval_v1.jsonl` (30 questions) + `workflow_scorer.py` | Tests analyst skill (SSP grading, evidence vs. claim, gap ID, authority, handoff) | `../5-experiments/exp-010-beru-v1.4/workflow_eval_results.json` |
| Pentest eval | `../4-eval-clarify/beru_pentest_brain_v1.jsonl` (22 questions, OWASP-LLM-tagged) | Refusal under adversarial pressure; exp-010 = 81.8% | exp-010 metrics |
| Promotion gate | `../1-local-pipeline/config_beru.yaml:promotion_gate` | Knowledge ≥ 70%, pentest ≥ 70%, must-beat-baseline, no-regression | `metrics.json:promotion_gate.decision` |
| Model card | `../6-model-cards/champion/` | Lineage, eval scores, limitations, intended use | — |
| Experiment record | `../5-experiments/exp-010-beru-v1.4/{params.yaml, metrics.json, notes.md}` | Reproducible training run record | — |

---

## 2. AI RMF 1.0 Subcategory Mapping

Lower row = strongest claim. Verification refers to commands in §6.

| Subcategory | Title | BERU implementation | Verification |
|---|---|---|---|
| **GOVERN-1.1** | AI system inventory maintained | `ai-inventory-register.md` required before assessment; missing inventory = automatic FAIL/B-rank routed through HITL | grep `GOVERN 1.1 FAIL` in `Modelfile_beru_v14` SYSTEM block |
| **GOVERN-1.3** | Roles and responsibilities documented | `Modelfile_beru_v14` SYSTEM defines role boundary; `control-owner-matrix.md` assigns owner per control | Read Modelfile + matrix |
| **GOVERN-1.4** | Accountability for outputs | Every finding includes `run_id`, `assessor=BERU-AI`, sha256-manifested archive | Inspect `manifest.json` in archive |
| **GOVERN-1.5** | Risk tolerance bounded | C-rank ceiling enforced by `HITLRouter._RANK_ROUTING`; B/S findings raise on `route()` | Test V-1 below |
| **GOVERN-1.6** | Data lineage maintained | Training data `lineage-manifest.json`; SSP corpus synthetic-only via `_validate_source` | `cat training-data/lineage-manifest.json` |
| **GOVERN-5.2** | Inventory of systems and components | This document; `ollama list`; `3-model-registry/` directory structure | V-3 |
| **GOVERN-6.1** | Third-party AI component governance | **GAP** — Ollama is a third-party dep, no formal review recorded. See §5. | — |
| **MAP-2.2** | Limitations documented | Model card; `beru-design-decisions.md`; this document's §5 gap register | — |
| **MAP-2.3** | System characteristics documented | Modelfile system prompt; design decisions; per-control evidence in `controls/<ID>.md` | — |
| **MAP-3.2** | Impact assessment | Workflow eval scores per type; `risk_summary.py` | V-2 |
| **MAP-3.5** | Adversarial input identified | `beru_pentest_brain_v1.jsonl` 22 OWASP-LLM questions; exp-010 = 81.8% pass | exp-010 metrics |
| **MAP-4.1** | Data collection lifecycle risk | `SSPParser._validate_source` enforces synthetic marker for training-corpus ingestion | V-4 |
| **MAP-4.2** | Human interface specified and tested | HITL queue files in `/tmp/beru-hitl-queue/`; routing tested in `8-tests/test_hitl_router.py` | Test V-1 |
| **MEASURE-2.1** | Test methodology documented | `4-eval-clarify/` — knowledge brain (30q), pentest brain (22q), workflow eval (30q) | — |
| **MEASURE-2.5** | Validity and reliability | **Guard 1** (stub detector) + **Guard 3** (evidence groundedness) | Test V-5, V-6 |
| **MEASURE-2.6** | RAG / retrieval grounding | **Guard 3**: cited evidence must appear in source haystack (control file + SSP/scanner input) | Test V-6 |
| **MEASURE-2.7** | Drift monitoring | MLflow logs every inference (`JADE-AI/mlruns/`); **PARTIAL** — no scheduled drift slice yet | — |
| **MEASURE-2.9** | Bias evaluated | Workflow eval per question type; per-OWASP scoring on pentest | — |
| **MEASURE-2.10** | Privacy / PII | Training corpus synthetic-only; **PARTIAL** — no PII scanner over inputs at runtime | — |
| **MEASURE-2.11** | Adversarial robustness | exp-010 pentest 81.8%; 22%+ adversarial floor in training corpus (D-012, relaxed for exp-010) | exp-010 metrics |
| **MANAGE-1.3** | Risk acceptance procedure | BERU cannot self-approve B/S; refused at `HITLRouter.route()`; documented in Modelfile hard stops | V-1 |
| **MANAGE-2.1** | Risk treatment | POA&M item generated only on FAIL/PARTIAL; never auto-accepts risk | Inspect `poam/poam.md` |
| **MANAGE-2.2** | Human oversight (HITL) | `HITLRouter` + Guard 3 rank-bump | V-1, V-6 |
| **MANAGE-2.3** | Pipeline integrity | LangGraph DAG is deterministic; tools are pinned imports; no plugin loading | Read `agent/graph.py` |
| **MANAGE-2.4** | Post-deployment evidence | `EvidencePackager` writes sha256 manifest + timestamped ZIP per run | V-7 |
| **MANAGE-4.1** | Drift response | **GAP** — process undocumented. See §5. | — |
| **MANAGE-4.2** | Model versioning | `3-model-registry/beru-v1.<N>-3b/`; Modelfile per version; Ollama tags `beru:v1.<N>` | `ollama list` |

---

## 3. NIST AI 600-1 Risk Mapping

| Risk type | Mitigation in BERU | Evidence |
|---|---|---|
| Hallucination (control IDs) | Guard 2 — citation validator against allow-list built from `controls/` | `nodes.validate_citations` |
| Hallucination (evidence) | Guard 3 — groundedness check against source input | `nodes.evidence_groundedness_check` |
| Hallucination (PASS without basis) | Guard 1 — stub-narrative detector forces FAIL | `nodes.narrative_check` |
| Prompt injection | Training-corpus adversarial floor (22%+); pentest_brain eval gates promotion | exp-010 metrics |
| Jailbreak | Same as prompt injection; refusal in fine-tune (exp-010 pentest 81.8%) | — |
| Data poisoning (training) | Synthetic-only corpus via `SSPParser._validate_source` | V-4 |
| RAG poisoning (retrieval) | ChromaDB ingestion is offline + provenance-stamped; per-doc `source_file` retained | `2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py` |
| Output bias | Per-type workflow scoring; per-OWASP pentest scoring | — |
| Model supply chain | Modelfile pins the GGUF by absolute path; sha256 logged at `ollama create` | V-3 |
| Training data integrity | `lineage-manifest.json`; experiment records | `training-data/lineage-manifest.json` |
| Lack of transparency | Modelcards (`6-model-cards/champion/`); design decisions; this document | — |
| Missing governance | `ai-inventory-register.md` gate at Modelfile system-prompt level | V-8 |
| No HITL for high-stakes | `HITLRouter._RANK_ROUTING` is hard-coded; auto-output blocked for B/S | V-1 |

---

## 4. NIST 800-53 Rev 5 Control Mapping

Only controls satisfied by the BERU agent itself are listed. Application
controls (the ones BERU *assesses*) live in `GP-CONSULTING/NIST-800-53/controls/`.

| Control | How BERU satisfies it |
|---|---|
| AC-2 | Provider abstraction in `providers/` is internal-only; no shared service account |
| AC-6 | C-rank ceiling enforced architecturally (least privilege for the agent's own authority) |
| AU-3 | Evidence package manifest records: assessor, run_id, timestamp, artifact paths, sha256 |
| AU-9 | Archives are sha256-checksummed; tampering detectable by re-hashing the contents |
| CA-2 | Workflow eval (30q) + pentest eval (22q) + knowledge eval (30q) per release |
| CA-5 | BERU produces POA&M items for every FAIL/PARTIAL; no closure without HITL approval |
| CA-7 | Continuous evaluation: each promotion runs the eval suite; results in `5-experiments/` |
| CM-3 | Modelfile is versioned; champion/challenger promotion gate in `config_beru.yaml` |
| CM-6 | Modelfile pins all generation parameters (temperature, num_ctx, stops) |
| CM-8 | This document is the component inventory; `ollama list` is the runtime inventory |
| IR-4 | If a B/S finding is auto-output (HITL bypass), it is an incident; tested in `8-tests/test_hitl_router.py` |
| PL-2 | Guard 1 enforces: SSP narrative must document implementation, not just claim it |
| RA-3 | Risk rank assigned per finding (E/D/C/B/S) via `classify_rank` |
| RA-5 | Workflow eval catches regressions; promotion gate blocks regressed model from production |
| SA-11 | Model evaluation evidence: `metrics.json`, `workflow_eval_results.json`, `notes.md` |
| SA-12 | Supply chain: dependencies pinned in `requirements.txt`; Ollama version recorded |
| SC-12 | Future: model artifact signing — currently sha256 manifest only. See §5. |
| SC-28 | No real-client data stored anywhere in `BERU-AI/` (corpus is synthetic) |
| SI-7 | sha256 in evidence manifest detects archive tampering |
| SI-10 | Guard 2 + Guard 3 validate model output against allowed citations and source input |
| SR-3 | Modelfile pins the model artifact by content path; conversion log recorded |
| SR-4 | Model provenance: `5-experiments/exp-010-beru-v1.4/` documents the full training run |

---

## 5. Gap Register

Honest list. A 3PAO will find these anyway.

| ID | Gap | Owner | Target |
|---|---|---|---|
| G-1 | **MEASURE-2.7 drift slice undefined** — MLflow logs every call but no scheduled eval against a fixed slice | GP-Copilot team | Define a 50q drift slice; schedule weekly run |
| G-2 | **MANAGE-4.1 model retirement procedure undocumented** — promotion is gated, but no documented retirement criteria | GP-Copilot team | Add retirement criteria to `config_beru.yaml` |
| G-3 | **GOVERN-6.1 third-party AI inventory incomplete** — Ollama, llama.cpp, Unsloth, HuggingFace not formally inventoried as third-party AI components | GP-Copilot team | Add `third-party-ai-inventory.md` |
| G-4 | **MEASURE-2.10 runtime PII scan absent** — training corpus is synthetic, but inputs to BERU at runtime are not scanned | GP-Copilot team | Add Presidio pre-filter to `parse_input` node |
| G-5 | **SC-12 model artifact signing not implemented** — sha256 manifest exists, but artifacts are not cryptographically signed | GP-Copilot team | Add cosign / minisign to evidence packager |
| G-6 | **Guard 3 corpus narrow** — token extraction patterns cover the common scanners but will miss arbitrary tool names | GP-Copilot team | Expand `_EVIDENCE_TOKEN_RES`; track false-negative rate |
| G-7 | **No tamper-evident HITL audit log** — `HITLRouter` queue is JSON files on disk, not append-only | GP-Copilot team | Move to an append-only log or signed JSONL |

---

## 6. Verification Commands

Copy-paste reproducibles. Each `V-N` is referenced by a row above.

**V-1 — HITL gate refuses B/S autonomously**
```bash
cd GP-MODEL-OPS/BERU-AI
python3 -c "
from tools.hitl_router import HITLRouter
r = HITLRouter()
out = r.route({'rank': 'B', 'control_id': 'AC-2', 'status': 'FAIL', 'finding_id': 'v1-test'})
print(out)
"
# Expect: status='pending_human', auto_ok=False, queue_id populated, message references MANAGE-2.2
```

**V-2 — Workflow eval reproducible**
```bash
cd GP-MODEL-OPS
cat 5-experiments/exp-010-beru-v1.4/workflow_eval_results.json | jq '.per_type'
# Expect: 5 types with pass_rate + avg_score
```

**V-3 — Model artifact + GGUF + Ollama tag are consistent**
```bash
ls -la GP-MODEL-OPS/3-model-registry/beru-v1.4-3b/gguf/beru-v1.4-q8_0.gguf
sha256sum GP-MODEL-OPS/3-model-registry/beru-v1.4-3b/gguf/beru-v1.4-q8_0.gguf
ollama show beru:v1.4 --modelfile | head -5
# Expect: GGUF present, sha256 matches what was registered, Modelfile FROM points to that GGUF
```

**V-4 — Synthetic-only gate refuses unmarked SSPs (training-corpus path)**
```bash
cd GP-MODEL-OPS/BERU-AI
python3 -c "
from tools.ssp_parser import SSPParser
try:
    SSPParser().parse_text('real client SSP without marker', 'real.md')
    print('UNEXPECTED: gate did not refuse')
except ValueError as e:
    print(f'Gate refused as expected: {e}')
"
```

**V-5 — Guard 1 catches one-word narratives**
```bash
cd GP-MODEL-OPS/BERU-AI
python3 run_beru.py grade-ssp --input ./training-data/ssps/ssp-01-bad.md \
  --system test --client test --output-dir /tmp/v5-test
# Expect: 4 findings, all FAIL, all rank=C, all deterministic=True
unzip -p /tmp/v5-test/beru-evidence-*.zip findings/beru-findings.jsonl | \
  python3 -c "
import sys, json
for line in sys.stdin:
    f = json.loads(line)
    assert f['status'] == 'FAIL' and f.get('deterministic') is True, f
print('V-5 PASS')
"
```

**V-6 — Guard 3 catches hallucinated evidence**
Construct a fixture where the brain is given a control to assess but no evidence
naming any real artifact. If the brain produces an EVIDENCE REVIEWED block citing
a tool name (e.g., `kubectl`, `trivy`) not in the source, Guard 3 must flag it
and rank-bump to B. See `8-tests/test_evidence_guard.py` (PENDING — G-6).

**V-7 — Evidence package is integrity-checkable**
```bash
ARCHIVE=$(ls /tmp/beru-smoke/guarded-run/beru-evidence-*.zip | head -1)
unzip -p "$ARCHIVE" manifest.json | jq '.artifacts[] | {path, sha256}'
# Re-hash each artifact and confirm it matches the manifest
```

**V-8 — `ai-inventory-register.md` gate is in the system prompt**
```bash
ollama show beru:v1.4 --system | grep -A1 "ai-inventory-register"
# Expect: "IF the AI system is not in ai-inventory-register.md: finding is GOVERN 1.1 FAIL"
```

---

## 7. Change Log

| Date | Author | Change |
|---|---|---|
| 2026-05-11 | platform team | Initial document; M4.1 guards added; exp-010 results referenced |

---

## 8. Related Artifacts

- **Design decisions:** `../CAPSTONE-PROJECT/beru-design-decisions.md`
- **AI inventory register:** `../CAPSTONE-PROJECT/templates/ai-inventory-register.md`
- **AI risk assessment template:** `../CAPSTONE-PROJECT/templates/ai-risk-assessment.md`
- **800-53 ↔ AI RMF crosswalk:** `../CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md`
- **NIST AI 600-1 framework files:** `../CAPSTONE-PROJECT/frameworks/nist-ai-600-1/`
- **Model card:** `../6-model-cards/champion/`
- **Experiment records:** `../5-experiments/exp-010-beru-v1.4/`
