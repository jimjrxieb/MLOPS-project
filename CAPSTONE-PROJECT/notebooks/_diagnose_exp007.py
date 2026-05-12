"""Diagnostic on exp-007 — read raw BERU outputs on representative questions
to determine why per-type scores were 0% on 4 categories.

For each of 6 strategic questions (one per type), this script:
  1. Loads the exp-007 merged model
  2. Retrieves RAG (top_k=2, same as eval)
  3. Generates the BERU response
  4. Scores it against validation_keywords + fail_indicators
  5. Saves the raw output to disk for review

Output: 5-experiments/exp-007-beru-v1.1/diagnostic_outputs.md
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

GP_MODEL_OPS = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
REPO_ROOT    = GP_MODEL_OPS.parent
MERGED       = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.1-3b' / 'merged_16bit'
EVAL_DIR     = GP_MODEL_OPS / '4-eval-clarify'
EXP007_DIR   = GP_MODEL_OPS / '5-experiments' / 'exp-007-beru-v1.1'

print('Loading exp-007 merged model...')
load_start = time.time()
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name      = str(MERGED),
    max_seq_length  = 8192,
    load_in_4bit    = False,
    dtype           = None,
)
FastLanguageModel.for_inference(model)
print(f'Model loaded in {time.time()-load_start:.1f}s')


# RAG setup
sys.path.insert(0, str(GP_MODEL_OPS / '2-rag-ingestion' / '04-ingesting'))
from ingest_beru_to_chromadb import (  # noqa: E402
    COLLECTION_NAME as RAG_COLLECTION,
    CHROMA_PATH as RAG_CHROMA_PATH,
    OllamaEmbeddingFunction,
)
import chromadb
from chromadb.config import Settings as _ChromaSettings

embedder = OllamaEmbeddingFunction()
client = chromadb.PersistentClient(
    path=str(RAG_CHROMA_PATH),
    settings=_ChromaSettings(anonymized_telemetry=False),
)
collection = client.get_collection(RAG_COLLECTION, embedding_function=embedder)

def retrieve_context(scenario, k=2):
    q = collection.query(query_texts=[scenario], n_results=k)
    docs, ids, metas = q['documents'][0], q['ids'][0], q['metadatas'][0]
    parts = ['Reference material from your knowledge base:', '']
    for cid, doc, meta in zip(ids, docs, metas):
        tag = meta.get('control_id') or meta.get('subcategory_id') or meta.get('technique_id') or 'ref'
        parts.append(f'--- {cid} ({tag}) ---')
        parts.append(doc.strip()); parts.append('')
    parts.append('--- end reference material ---')
    return '\n'.join(parts), ids


# Eval scorers
sys.path.insert(0, str(EVAL_DIR))
from beru_eval_runner import BERU_SYSTEM_PROMPT, score_positive  # noqa: E402

def hf_generate(system, user, max_new=1000):
    msgs = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    inputs = tokenizer.apply_chat_template(
        msgs, return_tensors='pt', add_generation_prompt=True,
    ).to(model.device)
    out = model.generate(
        input_ids       = inputs,
        max_new_tokens  = max_new,
        do_sample       = True,
        temperature     = 0.1,
        top_p           = 0.95,
        pad_token_id    = tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)


# Load eval set, group by type, pick 1 per type
qs = []
with open(EVAL_DIR / 'beru_knowledge_brain_v2.jsonl') as f:
    for l in f:
        l = l.strip()
        if l and not l.startswith('//'):
            qs.append(json.loads(l))

by_type = defaultdict(list)
for q in qs:
    by_type[q['type']].append(q)

# 6 strategic picks: 4 from failing types + 2 from working types (control)
sample = []
for t in ['atlas_mapped_ai_risk', 'dual_citation', 'escalation_discipline',
          'evidence_gap_detection', 'poam_drafting', 'tool_output_interpretation']:
    sample.append(by_type[t][0])


# Run + collect raw outputs
print(f'\nRunning {len(sample)} diagnostic questions...')
diagnostics = []
for i, q in enumerate(sample, 1):
    print(f'  Q{i}/{len(sample)}: {q["id"]} ({q["type"]})')
    rag_ctx, rag_ids = retrieve_context(q['scenario'])
    full_user = f'{rag_ctx}\n\n--- Scenario ---\n{q["scenario"]}\n\nProduce the BERU response.'
    t0 = time.time()
    try:
        response = hf_generate(BERU_SYSTEM_PROMPT, full_user)
    except Exception as e:
        response = f'[generation error: {e}]'
    elapsed = time.time() - t0
    score = score_positive(q, response)
    diagnostics.append({
        'question_id': q['id'],
        'type': q['type'],
        'scenario': q['scenario'],
        'validation_keywords': q.get('validation_keywords', []),
        'expected_actions': q.get('expected_actions', []),
        'fail_indicators': q.get('fail_indicators', []),
        'expected_control_ids': q.get('expected_control_ids', []),
        'expected_status': q.get('expected_status'),
        'expected_rank': q.get('expected_rank'),
        'response': response,
        'score': score,
        'generation_seconds': elapsed,
        'rag_ids': rag_ids,
    })
    icon = '✓' if score['passed'] else '✗'
    print(f'    {icon} score={score["combined_score"]:.2f} elapsed={elapsed:.1f}s')


# Save raw JSON for further inspection
out_json = EXP007_DIR / 'diagnostic_outputs.json'
out_json.write_text(json.dumps(diagnostics, indent=2, default=str))

# Save human-readable markdown
md_lines = ['# exp-007 Diagnostic — Raw BERU Outputs',
            '',
            f'Generated: {datetime.now(timezone.utc).isoformat()}',
            'Model:     `3-model-registry/beru-v1.1-3b/merged_16bit/`',
            'RAG:       `beru-nist-800-53` (top_k=2)',
            '',
            'Purpose: see what BERU is actually outputting on the 4 failing types vs 2 working types,',
            'so we can tell whether the model is producing nonsense (training problem), reasonable',
            'answers that miss keywords (scorer problem), or wrong-citation findings (data shape problem).',
            '',
            '---',
            '']

for d in diagnostics:
    md_lines.extend([
        f'## {d["type"]} — `{d["question_id"]}`',
        '',
        f'**Score:** `{d["score"]["combined_score"]:.2f}` ({"PASS" if d["score"]["passed"] else "FAIL"})',
        f'  kw {d["score"]["keyword_score"]:.2f}  ·  actions {d["score"]["action_score"]:.2f}  ·  gen {d["generation_seconds"]:.1f}s',
        '',
        f'**Expected:** status `{d["expected_status"]}`, rank `{d["expected_rank"]}`, controls `{d["expected_control_ids"]}`',
        f'**Validation keywords:** `{d["validation_keywords"]}`',
        f'**Fail indicators:** `{d["fail_indicators"]}`',
        f'**RAG retrieved:** `{d["rag_ids"]}`',
        '',
        '### Scenario',
        '',
        d['scenario'],
        '',
        '### BERU response (raw)',
        '',
        '```',
        d['response'],
        '```',
        '',
        '### Scorer breakdown',
        '',
        f'- matched keywords: `{d["score"]["matched_keywords"]}`',
        f'- missed keywords:  `{d["score"]["missed_keywords"]}`',
        f'- matched actions:  `{d["score"]["matched_actions"]}`',
        f'- fail-indicator hits: `{d["score"]["fail_indicator_hits"]}`',
        '',
        '---',
        '',
    ])

out_md = EXP007_DIR / 'diagnostic_outputs.md'
out_md.write_text('\n'.join(md_lines))

print(f'\nDiagnostic written to:')
print(f'  {out_md.relative_to(REPO_ROOT)}')
print(f'  {out_json.relative_to(REPO_ROOT)}')
print(f'\nScores: ' + ', '.join(f'{d["type"][:14]}={d["score"]["combined_score"]:.2f}' for d in diagnostics))
