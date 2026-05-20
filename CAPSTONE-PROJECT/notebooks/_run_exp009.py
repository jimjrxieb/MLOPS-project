"""exp-007 — fine-tune with 4 structural fixes from the Claude+RAG control eval.

Fixes applied vs exp-007:
  1. max_seq_length: 4096 → 8192  (let the model see full RAG context)
  2. RAG top_k: 4 → 2 at eval time (keep prompts well under the 8K budget)
  3. epochs_per_chunk: 3 → 2  (pentest at 95.5% in exp-006 was refusal over-shaping)
  4. train_on_responses_only=True via Unsloth helper
     (loss now computed only on assistant tokens, not the giant user RAG block)

Fix #5 (lower adversarial floor 30→25%) is INTENTIONALLY DEFERRED.
The Claude+RAG control eval at 75% says the RAG corpus is sufficient. The exp-006
collapse is likely the structural issues above, not the corpus composition.
If exp-007 still over-refuses, exp-008 cuts the adversarial corpus.

Outputs:
  3-model-registry/beru-v1.3-3b/{lora_adapter, merged_16bit, _checkpoints}
  5-experiments/exp-009-beru-v1.3/{metrics.json, notes.md, params.yaml}
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict

import yaml

GP_MODEL_OPS  = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
REPO_ROOT     = GP_MODEL_OPS.parent
CORPUS_PATH   = GP_MODEL_OPS / '1-FineTuning-Pipeline' / '01-raw-data-lake' / 'beru_training_v1.jsonl'   # exp-009: user-authored 234-example constructive corpus
VAL_PATH      = GP_MODEL_OPS / '1-FineTuning-Pipeline' / '01-raw-data-lake' / 'beru_validation_v1.jsonl'
CONFIG_PATH   = GP_MODEL_OPS / '1-FineTuning-Pipeline' / 'config_beru.yaml'
BASELINE_DIR  = GP_MODEL_OPS / '5-experiments' / 'exp-005-beru-3b-baseline'
EXP007_DIR    = GP_MODEL_OPS / '5-experiments' / 'exp-007-beru-v1.1'
EXP_DIR       = GP_MODEL_OPS / '5-experiments' / 'exp-009-beru-v1.3'
ADAPTER_OUT   = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.3-3b' / 'lora_adapter'
MERGED_OUT    = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.3-3b' / 'merged_16bit'
CKPT_OUT      = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.3-3b' / '_checkpoints'
EVAL_DIR      = GP_MODEL_OPS / '4-eval-clarify'

EXP_DIR.mkdir(parents=True, exist_ok=True)
ADAPTER_OUT.parent.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Phase 1 — Load + verify
# ============================================================================
print('=' * 70); print('Phase 1 — Load + verify'); print('=' * 70)

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

# exp-007 overrides — applied in-memory; config file unchanged
config['model']['max_seq_length']            = 8192        # fix 1
config['training']['epochs_per_chunk']        = 2          # fix 3
config['training']['gradient_accumulation_steps'] = 8      # keep effective batch ~16 at higher seq
config['training']['batch_size']              = 2          # halve micro-batch to stay in VRAM at 8K context
config['exp_007_overrides'] = {
    'max_seq_length': 8192,
    'epochs': 2,
    'batch_size': 2,
    'grad_accum': 8,
    'rag_top_k': 2,                       # fix 2 — applied at eval
    'train_on_responses_only': True,      # fix 4
    'adversarial_floor_change': 'DEFERRED — see notes.md',
}

with open(CORPUS_PATH) as f:
    corpus = [json.loads(l) for l in f if l.strip()]
with open(VAL_PATH) as f:
    val = [json.loads(l) for l in f if l.strip()]
with open(BASELINE_DIR / 'metrics.json') as f:
    baseline = json.load(f)
bk = baseline['brain_baseline_with_rag']['knowledge_brain']
bp = baseline['brain_baseline_with_rag']['pentest_brain']
with open(EXP007_DIR / 'metrics.json') as f:
    exp007 = json.load(f)
e7k = exp007['fine_tuned']['knowledge_brain']
e7p = exp007['fine_tuned']['pentest_brain']

print(f'Training corpus: {len(corpus)} examples')
print(f'Validation set:  {len(val)} examples')
print(f'Baseline:  knowledge {bk["overall"]:.1%}, pentest {bp["overall"]:.1%}')
print(f'exp-007:   knowledge {e7k["overall"]:.1%}, pentest {e7p["overall"]:.1%}')
print(f'Target:    beat baseline on knowledge; not regress on pentest')
print()


# ============================================================================
# Phase 2 — Load Unsloth model at 8K context
# ============================================================================
print('=' * 70); print('Phase 2 — Load base model at 8K context'); print('=' * 70)

load_start = time.time()
from unsloth import FastLanguageModel, is_bfloat16_supported

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name      = config['model']['base_model'],
    max_seq_length  = config['model']['max_seq_length'],   # 8192
    load_in_4bit    = config['model']['load_in_4bit'],
    dtype           = None,
)
print(f'Base model loaded in {time.time()-load_start:.1f}s')

# Attach LoRA — same r/alpha as exp-006 (only structural fixes this round)
model = FastLanguageModel.get_peft_model(
    model,
    r                = config['lora']['r'],
    lora_alpha       = config['lora']['alpha'],
    lora_dropout     = config['lora']['dropout'],
    target_modules   = config['lora']['target_modules'],
    bias             = 'none',
    use_gradient_checkpointing = 'unsloth',
    random_state     = 3407,
    use_rslora       = False,
    loftq_config     = None,
)

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f'Trainable parameters: {trainable:,}  ({trainable/total*100:.3f}% of total)')


# ============================================================================
# Phase 3 — Format dataset + apply chat template
# ============================================================================
print('=' * 70); print('Phase 3 — Format dataset'); print('=' * 70)

from datasets import Dataset

def to_format(exs):
    return {'conversations': [ex['messages'] for ex in exs]}

train_ds = Dataset.from_dict(to_format(corpus))
val_ds   = Dataset.from_dict(to_format(val))

def format_conversations(examples):
    texts = [tokenizer.apply_chat_template(c, tokenize=False, add_generation_prompt=False)
             for c in examples['conversations']]
    return {'text': texts}

train_ds = train_ds.map(format_conversations, batched=True, remove_columns=['conversations'])
val_ds   = val_ds.map(format_conversations,   batched=True, remove_columns=['conversations'])
print(f'Train: {len(train_ds)} | Val: {len(val_ds)} | example text length: {len(train_ds[0]["text"])} chars')


# ============================================================================
# Phase 4 — Build trainer with train_on_responses_only (fix 4)
# ============================================================================
print('=' * 70); print('Phase 4 — Build trainer'); print('=' * 70)

from trl import SFTTrainer
from transformers import TrainingArguments

t_cfg = config['training']
training_args = TrainingArguments(
    output_dir                  = str(CKPT_OUT),
    per_device_train_batch_size = int(t_cfg['batch_size']),
    gradient_accumulation_steps = int(t_cfg['gradient_accumulation_steps']),
    num_train_epochs            = int(t_cfg['epochs_per_chunk']),
    learning_rate               = float(t_cfg['learning_rate']),
    warmup_ratio                = float(t_cfg['warmup_ratio']),
    lr_scheduler_type           = t_cfg['lr_scheduler'],
    weight_decay                = float(t_cfg['weight_decay']),
    logging_steps               = int(t_cfg['logging_steps']),
    eval_strategy               = 'steps',
    eval_steps                  = int(t_cfg['eval_steps']),
    save_strategy               = t_cfg['save_strategy'],
    fp16                        = not is_bfloat16_supported(),
    bf16                        = is_bfloat16_supported(),
    optim                       = 'adamw_8bit',
    seed                        = 3407,
    report_to                   = 'none',
)

trainer = SFTTrainer(
    model           = model,
    tokenizer       = tokenizer,
    train_dataset   = train_ds,
    eval_dataset    = val_ds,
    dataset_text_field = 'text',
    max_seq_length  = config['model']['max_seq_length'],
    dataset_num_proc= 2,
    packing         = False,
    args            = training_args,
)

# Fix 4: train_on_responses_only — only the assistant tokens contribute to loss
from unsloth.chat_templates import train_on_responses_only
trainer = train_on_responses_only(
    trainer,
    instruction_part = '<|start_header_id|>user<|end_header_id|>\n\n',
    response_part    = '<|start_header_id|>assistant<|end_header_id|>\n\n',
)
print('Trainer wrapped with train_on_responses_only (loss masked to assistant tokens)')

steps_per_epoch = max(1, len(train_ds) // (t_cfg['batch_size'] * t_cfg['gradient_accumulation_steps']))
total_steps     = steps_per_epoch * t_cfg['epochs_per_chunk']
print(f'Steps/epoch: ~{steps_per_epoch}  | Total: ~{total_steps}')


# ============================================================================
# Phase 5 — Train
# ============================================================================
print('=' * 70); print('Phase 5 — Train'); print('=' * 70)
print(f'Started: {datetime.now(timezone.utc).isoformat()}')
training_start = time.time()
trainer_stats  = trainer.train()
training_duration = time.time() - training_start
print(f'Training complete in {training_duration/60:.1f} min')
print(f'Final train loss: {trainer_stats.metrics.get("train_loss")}')


# ============================================================================
# Phase 6 — Save adapter + merged 16-bit
# ============================================================================
print('=' * 70); print('Phase 6 — Save'); print('=' * 70)
model.save_pretrained(str(ADAPTER_OUT))
tokenizer.save_pretrained(str(ADAPTER_OUT))
print(f'Adapter saved: {ADAPTER_OUT.relative_to(REPO_ROOT)}')

print(f'Saving merged 16-bit to {MERGED_OUT.relative_to(REPO_ROOT)}...')
model.save_pretrained_merged(str(MERGED_OUT), tokenizer, save_method='merged_16bit')
print('Merged saved.')


# ============================================================================
# Phase 7 — In-process eval with RAG top_k=2 (fix 2)
# ============================================================================
print('=' * 70); print('Phase 7 — Eval with RAG top_k=2'); print('=' * 70)

FastLanguageModel.for_inference(model)

sys.path.insert(0, str(GP_MODEL_OPS / '2-RagIngestion-Pipeline' / '04-ingesting'))
from ingest_beru_to_chromadb import (
    COLLECTION_NAME as RAG_COLLECTION,
    CHROMA_PATH as RAG_CHROMA_PATH,
    OllamaEmbeddingFunction,
)
import chromadb
from chromadb.config import Settings as _ChromaSettings

embedder = OllamaEmbeddingFunction()
client = chromadb.PersistentClient(path=str(RAG_CHROMA_PATH),
                                   settings=_ChromaSettings(anonymized_telemetry=False))
collection = client.get_collection(RAG_COLLECTION, embedding_function=embedder)

EXP007_RAG_K = 2   # fix 2

def retrieve_context(scenario, k=EXP007_RAG_K):
    q = collection.query(query_texts=[scenario], n_results=k)
    docs, ids, metas = q['documents'][0], q['ids'][0], q['metadatas'][0]
    parts = ['Reference material from your knowledge base:', '']
    for cid, doc, meta in zip(ids, docs, metas):
        tag = meta.get('control_id') or meta.get('subcategory_id') or meta.get('technique_id') or 'ref'
        parts.append(f'--- {cid}  ({tag}) ---')
        parts.append(doc.strip()); parts.append('')
    parts.append('--- end reference material ---')
    return '\n'.join(parts), ids

sys.path.insert(0, str(EVAL_DIR))
from beru_eval_runner import BERU_SYSTEM_PROMPT, score_positive, score_negative

def hf_generate(system, user, max_new=1000):
    msgs = [{'role': 'system', 'content': system},
            {'role': 'user', 'content': user}]
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

def run_suite(suite_path, mode):
    questions = []
    with open(suite_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('//'):
                questions.append(json.loads(line))
    results = []
    suite_start = time.time()
    for i, q in enumerate(questions):
        scenario = q['scenario']
        rag_ctx, rag_ids = retrieve_context(scenario)
        full_user = f'{rag_ctx}\n\n--- Scenario ---\n{scenario}\n\nProduce the BERU response.'
        try:
            response = hf_generate(BERU_SYSTEM_PROMPT, full_user)
        except Exception as e:
            response = f'[generation error: {e}]'
        scorer = score_positive if mode == 'positive' else score_negative
        sr = scorer(q, response)
        sr['question_id'] = q.get('id')
        results.append(sr)
        if (i+1) % 5 == 0 or (i+1) == len(questions):
            pr = sum(1 for r in results if r.get('passed')) / len(results)
            print(f'  Q{i+1}/{len(questions)}  pass-rate {pr:.1%}  ({time.time()-suite_start:.0f}s)')
    return results, questions

print('\n--- knowledge_brain (30 q) ---')
ks_r, ks_q = run_suite(EVAL_DIR / 'beru_knowledge_brain_v2.jsonl', 'positive')
ks_passed  = sum(1 for r in ks_r if r.get('passed'))
ks_overall = ks_passed / len(ks_r)
print(f'knowledge_brain: {ks_overall:.1%} ({ks_passed}/{len(ks_r)})')

print('\n--- pentest_brain (22 q) ---')
ps_r, ps_q = run_suite(EVAL_DIR / 'beru_pentest_brain_v1.jsonl', 'negative')
ps_passed  = sum(1 for r in ps_r if r.get('passed'))
ps_overall = ps_passed / len(ps_r)
print(f'pentest_brain: {ps_overall:.1%} ({ps_passed}/{len(ps_r)})')


# ============================================================================
# Phase 8 — Promotion gate + artifacts
# ============================================================================
print('=' * 70); print('Phase 8 — Gate + write'); print('=' * 70)

def per_group(rs, qs, field):
    g = defaultdict(list)
    for r, q in zip(rs, qs):
        key = q.get(field) or q.get('type') or 'other'
        g[key].append(r.get('passed'))
    return {k: (sum(v)/len(v), sum(v), len(v)) for k, v in g.items()}

ks_per_type  = per_group(ks_r, ks_q, 'type')
ps_per_owasp = per_group(ps_r, ps_q, 'owasp_llm')

print('\nknowledge per type:')
for t, (r, p, n) in sorted(ks_per_type.items()):
    print(f'  {t:32} {r:.1%}  ({p}/{n})')
print('\npentest per OWASP-LLM:')
for t, (r, p, n) in sorted(ps_per_owasp.items()):
    print(f'  {t:8} {r:.1%}  ({p}/{n})')

gates = config['promotion_gate']
k_g, p_g = gates['knowledge_brain'], gates['pentest_brain']
k_overall_pass    = ks_overall >= float(k_g['overall_threshold'])
k_per_type_pass   = all(rate >= float(k_g['per_type_floor']) for rate, *_ in ks_per_type.values())
k_beats_baseline  = ks_overall > float(k_g['baseline_score'])
k_beats_exp007    = ks_overall > e7k['overall']
p_overall_pass    = ps_overall >= float(p_g['overall_threshold'])
p_per_cat_pass    = all(rate >= float(p_g['per_category_floor']) for rate, *_ in ps_per_owasp.values())
p_critical_pass   = all(ps_per_owasp.get(c, (0,))[0] >= float(p_g['critical_floor'])
                        for c in p_g['critical_categories'] if c in ps_per_owasp)
p_no_regression   = ps_overall >= float(p_g['baseline_score'])

all_pass = (k_overall_pass and k_per_type_pass and k_beats_baseline
            and p_overall_pass and p_per_cat_pass and p_critical_pass and p_no_regression)
decision = 'PROMOTE' if all_pass else 'BLOCKED'
print(f'\n=== Decision: {decision} ===')

# Write metrics.json
metrics = {
    'experiment_id': 'exp-009-beru-v1.3',
    'model': 'beru-v1.3-3b',
    'base_model': config['model']['base_model'],
    'training_corpus_size': len(corpus),
    'validation_corpus_size': len(val),
    'fixes_applied_vs_exp007': {
        'max_seq_length': '4096 -> 8192',
        'rag_top_k_eval': '4 -> 2',
        'epochs_per_chunk': '3 -> 2',
        'train_on_responses_only': True,
        'adversarial_floor_change': 'DEFERRED (clean variable isolation)',
    },
    'lora_config': dict(config['lora']),
    'training_config': dict(config['training']),
    'training_duration_minutes': training_duration / 60,
    'final_train_loss': trainer_stats.metrics.get('train_loss'),
    'run_date_utc': datetime.now(timezone.utc).isoformat(),
    'baseline_exp005': {
        'knowledge_brain_overall': bk['overall'],
        'pentest_brain_overall':   bp['overall'],
    },
    'prior_exp007': {
        'knowledge_brain_overall': e7k['overall'],
        'pentest_brain_overall':   e7p['overall'],
    },
    'fine_tuned': {
        'knowledge_brain': {'overall': ks_overall, 'passed': ks_passed, 'total': len(ks_r),
                            'per_type': {k: r for k, (r, *_) in ks_per_type.items()}},
        'pentest_brain':   {'overall': ps_overall, 'passed': ps_passed, 'total': len(ps_r),
                            'per_owasp_llm': {k: r for k, (r, *_) in ps_per_owasp.items()}},
    },
    'promotion_gate': {
        'decision': decision,
        'knowledge': {'overall_pass': k_overall_pass, 'per_type_pass': k_per_type_pass,
                       'beats_baseline': k_beats_baseline, 'beats_exp007': k_beats_exp007},
        'pentest':   {'overall_pass': p_overall_pass, 'per_category_pass': p_per_cat_pass,
                       'critical_pass': p_critical_pass, 'no_regression': p_no_regression},
    },
    'lift_over_baseline': {
        'knowledge_brain': ks_overall - bk['overall'],
        'pentest_brain':   ps_overall - bp['overall'],
    },
    'lift_over_exp007': {
        'knowledge_brain': ks_overall - e7k['overall'],
        'pentest_brain':   ps_overall - e7p['overall'],
    },
    'artifacts': {
        'adapter_path':      str(ADAPTER_OUT.relative_to(REPO_ROOT)),
        'merged_model_path': str(MERGED_OUT.relative_to(REPO_ROOT)),
        'script':            'CAPSTONE-PROJECT/notebooks/_run_exp007.py',
    },
}
(EXP_DIR / 'metrics.json').write_text(json.dumps(metrics, indent=2, default=str))

notes = f'''# exp-009-beru-v1.3 — Fine-Tune Run Notes

**Date:** {datetime.now(timezone.utc).date().isoformat()}
**Decision:** {decision}
**Script:** `CAPSTONE-PROJECT/notebooks/_run_exp007.py`

## Fixes applied vs exp-006

1. **`max_seq_length` 4096 → 8192** — let the model see full RAG context (exp-006 truncated every eval prompt by 50-80%)
2. **RAG `top_k` 4 → 2 at eval** — keeps prompts under 8K budget without truncation
3. **Epochs 3 → 2** — exp-006 pentest at 95.5% indicated refusal over-shaping
4. **`train_on_responses_only`** — loss now masked to assistant tokens only

Fix #5 (adversarial floor 30→25%) was **DEFERRED** to isolate variables — if structural fixes alone recover knowledge, fix 5 was unnecessary.

## Results

| Metric | Baseline (exp-005) | exp-006 (4K, 3ep) | **exp-007 (8K, 2ep)** | Lift vs baseline | Lift vs exp-006 |
|---|---|---|---|---|---|
| Knowledge brain | {bk['overall']:.1%} | {e7k['overall']:.1%} | **{ks_overall:.1%}** | {ks_overall - bk['overall']:+.1%} | {ks_overall - e7k['overall']:+.1%} |
| Pentest brain   | {bp['overall']:.1%} | {e7p['overall']:.1%} | **{ps_overall:.1%}** | {ps_overall - bp['overall']:+.1%} | {ps_overall - e7p['overall']:+.1%} |

## Knowledge brain — per type

{chr(10).join(f"- **{k}**: {r:.1%} ({p}/{n})" for k, (r, p, n) in sorted(ks_per_type.items()))}

## Pentest brain — per OWASP-LLM

{chr(10).join(f"- **{k}**: {r:.1%} ({p}/{n})" for k, (r, p, n) in sorted(ps_per_owasp.items()))}

## Promotion gate (D-010)

- Knowledge overall ≥ 70%: **{'PASS' if k_overall_pass else 'FAIL'}** ({ks_overall:.1%})
- Knowledge per-type ≥ 60%: **{'PASS' if k_per_type_pass else 'FAIL'}**
- Knowledge beats baseline (29.4%): **{'PASS' if k_beats_baseline else 'FAIL'}**
- Knowledge beats exp-006 (3.3%): **{'PASS' if k_beats_exp007 else 'FAIL'}**
- Pentest overall ≥ 70%: **{'PASS' if p_overall_pass else 'FAIL'}** ({ps_overall:.1%})
- Pentest per-OWASP ≥ 50%: **{'PASS' if p_per_cat_pass else 'FAIL'}**
- Pentest critical (LLM01/06/08) ≥ 70%: **{'PASS' if p_critical_pass else 'FAIL'}**
- Pentest no regression vs baseline: **{'PASS' if p_no_regression else 'FAIL'}**

## Provenance

- Adapter:        `{ADAPTER_OUT.relative_to(REPO_ROOT)}`
- Merged model:   `{MERGED_OUT.relative_to(REPO_ROOT)}`
- Training data:  `BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` ({len(corpus)} examples, unchanged)
- Validation:     `1-FineTuning-Pipeline/01-raw-data-lake/beru_validation_v1.jsonl` ({len(val)} examples)
- Eval suites:    `4-eval-clarify/beru_knowledge_brain_v2.jsonl` (30) + `beru_pentest_brain_v1.jsonl` (22)
- Baseline:       `5-experiments/exp-005-beru-3b-baseline/metrics.json`
- Prior exp:      `5-experiments/exp-007-beru-v1.1/metrics.json`
- Claude+RAG control: `5-experiments/exp-007-beru-v1.1/claude_rag_control_eval.json`

## Run record

Training: {training_duration/60:.1f} min on RTX 5080 Laptop GPU with QLoRA 4-bit at 8K context (vs ~13 min at 4K in exp-006). Adapter saved at `{ADAPTER_OUT.relative_to(REPO_ROOT)}`. Merged 16-bit at `{MERGED_OUT.relative_to(REPO_ROOT)}`.
'''
(EXP_DIR / 'notes.md').write_text(notes)
(EXP_DIR / 'params.yaml').write_text(yaml.dump(config, sort_keys=False))

print(f'\nWrote {EXP_DIR.relative_to(REPO_ROOT)}/{{metrics.json, notes.md, params.yaml}}')
print(f'\n=== exp-007 COMPLETE ===')
print(f'Decision: {decision}')
print(f'Knowledge: baseline {bk["overall"]:.1%}  exp-006 {e7k["overall"]:.1%}  →  exp-007 {ks_overall:.1%}')
print(f'Pentest:   baseline {bp["overall"]:.1%}  exp-006 {e7p["overall"]:.1%}  →  exp-007 {ps_overall:.1%}')
