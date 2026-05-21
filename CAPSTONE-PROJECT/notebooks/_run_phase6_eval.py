"""One-off completion script for M3 Phase 6+7.

The notebook ran Phase 1-5 successfully (trained adapter + saved merged 16-bit model).
Phase 6 hit a schema bug: eval JSONL questions use `scenario` not `input`. This script
loads the already-saved merged model from disk and runs Phase 6+7 directly.

Outputs:
  5-experiments/exp-006-beru-v1.0/metrics.json
  5-experiments/exp-006-beru-v1.0/notes.md
  5-experiments/exp-006-beru-v1.0/params.yaml
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

import yaml

GP_MODEL_OPS = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
REPO_ROOT = GP_MODEL_OPS.parent

MERGED_OUT  = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.0-3b' / 'merged_16bit'
ADAPTER_OUT = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.0-3b' / 'lora_adapter'
EXP_DIR     = GP_MODEL_OPS / '5-experiments' / 'exp-006-beru-v1.0'
BASELINE_DIR= GP_MODEL_OPS / '5-experiments' / 'exp-005-beru-3b-baseline'
EVAL_DIR    = GP_MODEL_OPS / '4-eval-clarify'
CONFIG_PATH = GP_MODEL_OPS / '1-FineTuning-Pipeline' / 'config_beru.yaml'
CORPUS_PATH = GP_MODEL_OPS / 'BERU-AI' / 'training-data' / 'chatml-examples' / 'beru-training-examples.jsonl'
VAL_PATH    = GP_MODEL_OPS / '1-FineTuning-Pipeline' / '01-raw-data-lake' / 'beru_validation_v1.jsonl'

EXP_DIR.mkdir(parents=True, exist_ok=True)

# Load config + baseline
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)
with open(BASELINE_DIR / 'metrics.json') as f:
    baseline = json.load(f)
bk = baseline['brain_baseline_with_rag']['knowledge_brain']
bp = baseline['brain_baseline_with_rag']['pentest_brain']

# Load corpus stats for the metrics file
with open(CORPUS_PATH) as f:
    corpus_size = sum(1 for l in f if l.strip())
with open(VAL_PATH) as f:
    val_size = sum(1 for l in f if l.strip())

print(f'Loading merged 16-bit model from {MERGED_OUT}...')
load_start = time.time()
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name      = str(MERGED_OUT),
    max_seq_length  = 4096,
    load_in_4bit    = False,   # already merged
    dtype           = None,
)
FastLanguageModel.for_inference(model)
print(f'Model loaded in {time.time()-load_start:.1f}s. Device: {model.device}')

# RAG setup
sys.path.insert(0, str(GP_MODEL_OPS / '2-RagIngestion-Pipeline' / '04-ingesting'))
from ingest_beru_to_chromadb import (  # noqa: E402
    COLLECTION_NAME as RAG_COLLECTION,
    CHROMA_PATH as RAG_CHROMA_PATH,
    OllamaEmbeddingFunction,
)
import chromadb  # noqa: E402
from chromadb.config import Settings as _ChromaSettings  # noqa: E402

embedder = OllamaEmbeddingFunction()
client = chromadb.PersistentClient(
    path=str(RAG_CHROMA_PATH),
    settings=_ChromaSettings(anonymized_telemetry=False),
)
collection = client.get_collection(RAG_COLLECTION, embedding_function=embedder)
print(f'RAG collection: {RAG_COLLECTION} ({collection.count()} docs)')

DEFAULT_K = 4
def retrieve_context(scenario: str, k: int = DEFAULT_K):
    q = collection.query(query_texts=[scenario], n_results=k)
    docs, ids, metas = q['documents'][0], q['ids'][0], q['metadatas'][0]
    parts = ['Reference material from your knowledge base:', '']
    for cid, doc, meta in zip(ids, docs, metas):
        tag = meta.get('control_id') or meta.get('subcategory_id') or meta.get('technique_id') or 'ref'
        parts.append(f'--- {cid}  ({tag}) ---')
        parts.append(doc.strip())
        parts.append('')
    parts.append('--- end reference material ---')
    return '\n'.join(parts), ids

# Eval scorers from runner
sys.path.insert(0, str(EVAL_DIR))
from beru_eval_runner import BERU_SYSTEM_PROMPT, score_positive, score_negative  # noqa: E402

def hf_generate(system: str, user: str, max_new: int = 1500) -> str:
    msgs = [{'role': 'system', 'content': system},
            {'role': 'user', 'content': user}]
    inputs = tokenizer.apply_chat_template(
        msgs, return_tensors='pt', add_generation_prompt=True,
    ).to(model.device)
    out = model.generate(
        input_ids        = inputs,
        max_new_tokens   = max_new,
        do_sample        = True,
        temperature      = 0.1,
        top_p            = 0.95,
        pad_token_id     = tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)


def run_suite(suite_path: Path, mode: str):
    """Fixed: uses q['scenario'] (per actual JSONL schema) not q['input']."""
    questions = []
    with open(suite_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('//'):
                questions.append(json.loads(line))

    results = []
    suite_start = time.time()
    for i, q in enumerate(questions):
        scenario = q['scenario']   # <— FIX: was q['input']
        rag_ctx, rag_ids = retrieve_context(scenario)
        full_user = f'{rag_ctx}\n\n--- Scenario ---\n{scenario}\n\nProduce the BERU response.'
        try:
            response = hf_generate(BERU_SYSTEM_PROMPT, full_user)
        except Exception as e:
            response = f'[generation error: {e}]'
        scorer = score_positive if mode == 'positive' else score_negative
        score_record = scorer(q, response)
        score_record['question_id'] = q.get('id')
        score_record['rag_ids'] = rag_ids
        results.append(score_record)
        if (i + 1) % 5 == 0 or (i + 1) == len(questions):
            partial = sum(1 for r in results if r.get('passed')) / len(results)
            elapsed = time.time() - suite_start
            print(f'  Q{i+1}/{len(questions)}: running pass-rate {partial:.1%}  ({elapsed:.0f}s elapsed)')
    return results, questions


def per_group(results, questions, weight_field):
    groups = {}
    for r, q in zip(results, questions):
        key = q.get(weight_field) or q.get('type') or 'other'
        groups.setdefault(key, []).append(r.get('passed'))
    return {k: (sum(v)/len(v), sum(v), len(v)) for k, v in groups.items()}


# ----- Run knowledge brain -----
print('\n=== knowledge_brain (30 questions) ===')
ks_results, ks_questions = run_suite(EVAL_DIR / 'beru_knowledge_brain_v2.jsonl', 'positive')
ks_passed = sum(1 for r in ks_results if r.get('passed'))
ks_overall = ks_passed / len(ks_results)
print(f'\nknowledge_brain overall: {ks_overall:.1%}  ({ks_passed}/{len(ks_results)})')

# ----- Run pentest brain -----
print('\n=== pentest_brain (22 questions) ===')
ps_results, ps_questions = run_suite(EVAL_DIR / 'beru_pentest_brain_v1.jsonl', 'negative')
ps_passed = sum(1 for r in ps_results if r.get('passed'))
ps_overall = ps_passed / len(ps_results)
print(f'\npentest_brain overall: {ps_overall:.1%}  ({ps_passed}/{len(ps_results)})')

# ----- Per-group breakdowns -----
ks_per_type = per_group(ks_results, ks_questions, 'type')
ps_per_owasp = per_group(ps_results, ps_questions, 'owasp_llm')

print('\nknowledge_brain per type:')
for k, (rate, p, n) in sorted(ks_per_type.items()):
    print(f'  {k:32} {rate:.1%}  ({p}/{n})')
print('\npentest_brain per OWASP-LLM:')
for k, (rate, p, n) in sorted(ps_per_owasp.items()):
    print(f'  {k:8} {rate:.1%}  ({p}/{n})')

# ----- Promotion gate -----
gates = config['promotion_gate']
k_gate = gates['knowledge_brain']
p_gate = gates['pentest_brain']

k_overall_pass     = ks_overall >= float(k_gate['overall_threshold'])
k_per_type_floors  = {k: rate >= float(k_gate['per_type_floor']) for k, (rate, *_) in ks_per_type.items()}
k_per_type_pass    = all(k_per_type_floors.values())
k_beats_baseline   = ks_overall > float(k_gate['baseline_score'])

p_overall_pass     = ps_overall >= float(p_gate['overall_threshold'])
p_per_cat_floors   = {k: rate >= float(p_gate['per_category_floor']) for k, (rate, *_) in ps_per_owasp.items()}
p_per_cat_pass     = all(p_per_cat_floors.values())
p_critical_floors  = {k: rate >= float(p_gate['critical_floor'])
                      for k, (rate, *_) in ps_per_owasp.items() if k in p_gate['critical_categories']}
p_critical_pass    = all(p_critical_floors.values())
p_no_regression    = ps_overall >= float(p_gate['baseline_score'])

all_pass = (k_overall_pass and k_per_type_pass and k_beats_baseline
            and p_overall_pass and p_per_cat_pass and p_critical_pass and p_no_regression)
decision = 'PROMOTE' if all_pass else 'BLOCKED'

print(f'\n=== Promotion Gate Decision: {decision} ===')

# ----- Write artifacts -----
metrics = {
    'experiment_id': 'exp-006-beru-v1.0',
    'model': 'beru-v1.0-3b',
    'base_model': config['model']['base_model'],
    'training_corpus_size': corpus_size,
    'validation_corpus_size': val_size,
    'lora_config': dict(config['lora']),
    'training_config': dict(config['training']),
    'run_date_utc': datetime.now(timezone.utc).isoformat(),
    'baseline': {
        'experiment_id': 'exp-005-beru-3b-baseline',
        'knowledge_brain_overall': bk['overall'],
        'pentest_brain_overall': bp['overall'],
    },
    'fine_tuned': {
        'knowledge_brain': {
            'overall': ks_overall,
            'questions_passed': ks_passed,
            'questions_total': len(ks_results),
            'per_type': {k: rate for k, (rate, *_) in ks_per_type.items()},
        },
        'pentest_brain': {
            'overall': ps_overall,
            'questions_passed': ps_passed,
            'questions_total': len(ps_results),
            'per_owasp_llm': {k: rate for k, (rate, *_) in ps_per_owasp.items()},
        },
    },
    'promotion_gate': {
        'decision': decision,
        'knowledge': {
            'overall_pass': k_overall_pass,
            'per_type_pass': k_per_type_pass,
            'beats_baseline': k_beats_baseline,
        },
        'pentest': {
            'overall_pass': p_overall_pass,
            'per_category_pass': p_per_cat_pass,
            'critical_pass': p_critical_pass,
            'no_regression': p_no_regression,
        },
    },
    'lift_over_baseline': {
        'knowledge_brain': ks_overall - bk['overall'],
        'pentest_brain': ps_overall - bp['overall'],
    },
    'artifacts': {
        'adapter_path': str(ADAPTER_OUT.relative_to(REPO_ROOT)),
        'merged_model_path': str(MERGED_OUT.relative_to(REPO_ROOT)),
        'notebook': 'CAPSTONE-PROJECT/notebooks/M3-fine-tuning-execution.ipynb',
    },
}
(EXP_DIR / 'metrics.json').write_text(json.dumps(metrics, indent=2, default=str))
print(f'Wrote {EXP_DIR.relative_to(REPO_ROOT)}/metrics.json')

# Notes
notes = f'''# exp-006-beru-v1.0 — Fine-Tune Run Notes

**Date:** {datetime.now(timezone.utc).date().isoformat()}
**Decision:** {decision}
**Notebook:** `CAPSTONE-PROJECT/notebooks/M3-fine-tuning-execution.ipynb`

## Results

| Metric | Baseline (exp-005) | Fine-tuned (exp-006) | Lift |
|---|---|---|---|
| Knowledge brain | {bk['overall']:.1%} | {ks_overall:.1%} | {ks_overall - bk['overall']:+.1%} |
| Pentest brain   | {bp['overall']:.1%} | {ps_overall:.1%} | {ps_overall - bp['overall']:+.1%} |

## Knowledge brain — per type

{chr(10).join(f"- **{k}**: {rate:.1%} ({p}/{n})" for k, (rate, p, n) in sorted(ks_per_type.items()))}

## Pentest brain — per OWASP-LLM category

{chr(10).join(f"- **{k}**: {rate:.1%} ({p}/{n})" for k, (rate, p, n) in sorted(ps_per_owasp.items()))}

## Promotion gate (D-010)

- Knowledge overall ≥ 70%: **{'PASS' if k_overall_pass else 'FAIL'}** ({ks_overall:.1%})
- Knowledge per-type ≥ 60%: **{'PASS' if k_per_type_pass else 'FAIL'}**
- Knowledge beats baseline: **{'PASS' if k_beats_baseline else 'FAIL'}**
- Pentest overall ≥ 70%: **{'PASS' if p_overall_pass else 'FAIL'}** ({ps_overall:.1%})
- Pentest per-OWASP-LLM ≥ 50%: **{'PASS' if p_per_cat_pass else 'FAIL'}**
- Pentest critical (LLM01/06/08) ≥ 70%: **{'PASS' if p_critical_pass else 'FAIL'}**
- Pentest no regression: **{'PASS' if p_no_regression else 'FAIL'}**

## What changed

Base model `{config['model']['base_model']}` plus LoRA r={config['lora']['r']}/alpha={config['lora']['alpha']} on {corpus_size} curated examples (D-005, D-012). Held-out validation set: {val_size} examples. Training ran on RTX 5080 Laptop GPU with QLoRA 4-bit. Adapter is 203 MB; merged 16-bit model is 6.1 GB.

## Next steps

{'1. **Promote** to champion at `6-model-cards/champion/beru-v1.md`.' if decision == 'PROMOTE' else '1. **Diagnose weak families** from the per-type / per-OWASP-LLM tables above; add targeted training data; re-run.'}
2. Convert `merged_16bit/` to GGUF Q4_K_M and register with a versioned Ollama tag for eval.
3. Cross-link this experiment in `CAPSTONE-PROJECT/templates/ai-inventory-register.md` (JSA-AI-003) under registered-versions.
4. Once M4 (LangGraph agent) is built, run the agent eval suites to complete the 4-eval architecture.

## Provenance

- Adapter:        `{ADAPTER_OUT.relative_to(REPO_ROOT)}` (203 MB)
- Merged model:   `{MERGED_OUT.relative_to(REPO_ROOT)}` (6.1 GB)
- Training data:  `BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` ({corpus_size} examples)
- Validation set: `1-FineTuning-Pipeline/01-raw-data-lake/beru_validation_v1.jsonl` ({val_size} examples)
- Eval suites:    `4-eval-clarify/beru_knowledge_brain_v2.jsonl` (30) + `beru_pentest_brain_v1.jsonl` (22)
- Baseline:       `5-experiments/exp-005-beru-3b-baseline/metrics.json`
'''
(EXP_DIR / 'notes.md').write_text(notes)
print(f'Wrote {EXP_DIR.relative_to(REPO_ROOT)}/notes.md')

# Params (snapshot of config at run time)
(EXP_DIR / 'params.yaml').write_text(yaml.dump(config, sort_keys=False))
print(f'Wrote {EXP_DIR.relative_to(REPO_ROOT)}/params.yaml')

print(f'\n=== M3 DELIVERABLE COMPLETE ===')
print(f'Decision: {decision}')
print(f'Knowledge: baseline {bk["overall"]:.1%} → fine-tune {ks_overall:.1%}  (lift {ks_overall - bk["overall"]:+.1%})')
print(f'Pentest:   baseline {bp["overall"]:.1%} → fine-tune {ps_overall:.1%}  (lift {ps_overall - bp["overall"]:+.1%})')
