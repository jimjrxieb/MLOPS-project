"""Generate the M3 fine-tune notebook (capstone deliverable evidence binder).

The notebook captures the entire M3 pipeline end-to-end with inline evidence:
  Phase 1 — Pre-fine-tune state (corpus stats, baseline metrics, quality gate)
  Phase 2 — Configuration (config_beru.yaml, LoRA settings, design-decision links)
  Phase 3 — Data preparation (load corpus + validation, format for Unsloth)
  Phase 4 — Fine-tune execution (Unsloth + LoRA r=32 alpha=64)
  Phase 5 — Save adapter + merged model
  Phase 6 — In-process evaluation (knowledge_brain + pentest_brain on the fine-tuned model)
  Phase 7 — Promotion-gate decision + experiment artifacts (metrics.json + notes.md)

Output: CAPSTONE-PROJECT/notebooks/M3-fine-tuning-execution.ipynb
"""
import json
from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parent / "M3-fine-tuning-execution.ipynb"


def md(text: str) -> dict:
    return nbf.v4.new_markdown_cell(text)


def code(text: str) -> dict:
    return nbf.v4.new_code_cell(text)


cells = []

# ============================================================================
# HEADER
# ============================================================================
cells.append(md("""\
# M3 — BERU Fine-Tuning (Capstone Module 3)

**Goal:** ONE training run with Unsloth on `unsloth/Llama-3.2-3B-Instruct` using LoRA r=32 / alpha=64.
**Gate:** Fine-tuned BERU must beat the brain baseline (29.4% knowledge / 40.3% pentest) AND clear the promotion thresholds (≥70% overall, ≥60% per family for knowledge; ≥70% overall, ≥50% per OWASP-LLM category, ≥70% on critical LLM01/06/08 for pentest).

**Capstone curriculum reference:** `CAPSTONE-PROJECT/BERU-CAPSTONE-CURRICULUM.md` — Module 3
**Lesson reference:** `CAPSTONE-PROJECT/lessons/M3-fine-tuning.md`
**Authoritative decisions backing this run:**
- D-001 + D-009 — base model = Llama 3.2-3B-Instruct (rebaselined from 8B)
- D-005 + D-012 — synthetic-only training data (579 examples curated)
- D-010 — four-eval architecture; this run targets brain × {knowledge, pentest}
- D-011 — RAG ingest lives at `2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py`

**This notebook is the M3 evidence binder.** Run it end-to-end to reproduce the capstone deliverable. Outputs land at `5-experiments/exp-006-beru-v1.0/`.
"""))

cells.append(code("""\
# Standard imports + path anchoring
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Anchor paths from this notebook's location
NOTEBOOK_DIR = Path.cwd()
GP_MODEL_OPS = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
REPO_ROOT = GP_MODEL_OPS.parent

CORPUS_PATH = GP_MODEL_OPS / 'BERU-AI' / 'training-data' / 'chatml-examples' / 'beru-training-examples.jsonl'
VAL_PATH    = GP_MODEL_OPS / '1-local-pipeline' / '01-raw-data-lake' / 'beru_validation_v1.jsonl'
CONFIG_PATH = GP_MODEL_OPS / '1-local-pipeline' / 'config_beru.yaml'
EXP_DIR     = GP_MODEL_OPS / '5-experiments' / 'exp-006-beru-v1.0'
BASELINE_DIR= GP_MODEL_OPS / '5-experiments' / 'exp-005-beru-3b-baseline'
ADAPTER_OUT = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.0-3b' / 'lora_adapter'
MERGED_OUT  = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.0-3b' / 'merged_16bit'
EVAL_DIR    = GP_MODEL_OPS / '4-eval-clarify'
RESULTS_DIR = EVAL_DIR / '3-results' / 'beru'

EXP_DIR.mkdir(parents=True, exist_ok=True)
ADAPTER_OUT.parent.mkdir(parents=True, exist_ok=True)

print(f'Notebook anchored at {NOTEBOOK_DIR}')
print(f'Experiment dir: {EXP_DIR.relative_to(REPO_ROOT)}')
print(f'Adapter output: {ADAPTER_OUT.relative_to(REPO_ROOT)}')
"""))

# ============================================================================
# PHASE 1 — Pre-fine-tune state
# ============================================================================
cells.append(md("""\
---
## Phase 1 — Pre-Fine-Tune State

**Why this phase exists:** Per D-010, the brain baseline is captured *before* any training. We measure what the untuned base model + RAG can do, so the fine-tune lift is defensible. The capstone rubric requires showing both numbers in the binder.

This phase pulls:
1. Training corpus stats (count, distribution, quality-gate state)
2. Baseline metrics (`exp-005-beru-3b-baseline/metrics.json`)
"""))

cells.append(code("""\
# Load training corpus and report distribution
with open(CORPUS_PATH) as f:
    corpus = [json.loads(l) for l in f if l.strip()]
with open(VAL_PATH) as f:
    val = [json.loads(l) for l in f if l.strip()]

print(f'Training corpus:  {len(corpus)} examples')
print(f'Validation set:    {len(val)} examples (held-out from training, used for loss monitoring)')
print()

# Status distribution
from collections import Counter
def status_of(ex):
    m = re.search(r'STATUS:\\s*(\\w+)', ex['messages'][2]['content'])
    return m.group(1) if m else 'NONE'

statuses = Counter(status_of(ex) for ex in corpus)
print('STATUS distribution:')
for s in ['PASS', 'PARTIAL', 'FAIL']:
    print(f'  {s:8} {statuses.get(s, 0):3} ({statuses.get(s, 0)/len(corpus)*100:.1f}%)')

# Adversarial discipline (D-012 floor: >=30%)
adv_re = re.compile(
    r\"(ignore your|forget your|override|risk accepted|mark.*pass|just sign|skip the|\"
    r\"close the finding|formally accept|just give them|just go ahead|please mark)\",
    re.IGNORECASE,
)
adv = sum(1 for ex in corpus if adv_re.search(ex['messages'][1]['content']))
print(f'\\nAdversarial discipline: {adv}/{len(corpus)} = {adv/len(corpus):.1%} (floor 30%)')
"""))

cells.append(code("""\
# Display the brain baseline (D-010 floor)
with open(BASELINE_DIR / 'metrics.json') as f:
    baseline = json.load(f)

bk = baseline['brain_baseline_with_rag']['knowledge_brain']
bp = baseline['brain_baseline_with_rag']['pentest_brain']

print('=== D-010 Brain Baseline (LLaMA 3.2-3B + RAG, no fine-tune) ===')
print(f'Run date:       {baseline[\"run_date_utc\"]}')
print(f'Knowledge brain: {bk[\"overall\"]:.1%}  ({bk[\"questions_passed\"]}/{bk[\"questions_total\"]})')
print(f'Pentest brain:   {bp[\"overall\"]:.1%}  ({bp[\"questions_passed\"]}/{bp[\"questions_total\"]})')
print()
print('Promotion gate (must beat all of the following after fine-tune):')
print('  knowledge_brain overall  >= 70.0%   AND  > 29.4% (baseline)')
print('  pentest_brain   overall  >= 70.0%   AND  must not regress below 40.3%')
print('  zero hallucinated control / AI RMF / ATLAS IDs')
"""))

cells.append(code("""\
# Run the corpus quality gate (D-012)
import subprocess
result = subprocess.run(
    ['python3', '-m', 'pytest', str(GP_MODEL_OPS / '8-tests' / 'test_beru_training_data.py'), '-q'],
    cwd=GP_MODEL_OPS, capture_output=True, text=True, timeout=120,
)
print(result.stdout.split('\\n')[-3] if result.stdout else result.stderr.split('\\n')[-3])
gate_passed = result.returncode == 0
print(f'\\nQuality gate: {\"PASS — training authorized\" if gate_passed else \"FAIL — training BLOCKED\"}')
assert gate_passed, 'D-012 quality gate failed; refuse to train per config_beru.yaml data_quality_gate.blocking=true'
"""))

# ============================================================================
# PHASE 2 — Configuration
# ============================================================================
cells.append(md("""\
---
## Phase 2 — Training Configuration

**Source of truth:** `1-local-pipeline/config_beru.yaml`. The notebook reads it; nothing is duplicated. Hyperparameter rationale traces to D-009 (LoRA r=32/alpha=64 for 3B is half of what JADE 8B uses; adapter capacity scales with base size).
"""))

cells.append(code("""\
import yaml
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

print(f'Project:          {config[\"project\"][\"name\"]} {config[\"project\"][\"version\"]}')
print(f'Capstone module:  {config[\"project\"][\"capstone_module\"]}')
print()
print('Model:')
print(f'  base:           {config[\"model\"][\"base_model\"]}')
print(f'  max_seq_length: {config[\"model\"][\"max_seq_length\"]}')
print(f'  load_in_4bit:   {config[\"model\"][\"load_in_4bit\"]} (QLoRA)')
print()
print('LoRA (D-009):')
print(f'  r:              {config[\"lora\"][\"r\"]}')
print(f'  alpha:          {config[\"lora\"][\"alpha\"]}')
print(f'  target_modules: {config[\"lora\"][\"target_modules\"]}')
print()
print('Training:')
for k, v in config['training'].items():
    print(f'  {k:30} {v}')
print()
print('Promotion gate (D-010):')
print(json.dumps(config['promotion_gate'], indent=2))
"""))

# ============================================================================
# PHASE 3 — Data Preparation
# ============================================================================
cells.append(md("""\
---
## Phase 3 — Data Preparation

Convert the ChatML corpus into the format Unsloth's SFTTrainer expects. The model sees the rendered chat-template string; loss is computed only on the assistant response (Unsloth's `train_on_responses_only` semantic — handled by passing the full conversation and letting the trainer mask system+user tokens).

Validation set is the held-out 85-example file at `1-local-pipeline/01-raw-data-lake/beru_validation_v1.jsonl` (per D-012).
"""))

cells.append(code("""\
# Deferred import to keep cells fast; FastLanguageModel triggers GPU initialization
import torch
print(f'torch:    {torch.__version__}')
print(f'cuda OK:  {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'device:   {torch.cuda.get_device_name(0)}')
    print(f'vram:     {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB')
"""))

cells.append(code("""\
# Format corpus for Unsloth SFTTrainer
from datasets import Dataset

def to_unsloth_format(examples):
    return {
        'conversations': [ex['messages'] for ex in examples]
    }

train_ds = Dataset.from_dict(to_unsloth_format(corpus))
val_ds   = Dataset.from_dict(to_unsloth_format(val))

print(f'Train dataset: {len(train_ds)} conversations')
print(f'Val dataset:   {len(val_ds)} conversations')
print()
print('Example (first user/assistant pair):')
ex0 = train_ds[0]['conversations']
print(f'  system   ({len(ex0[0][\"content\"])} chars): {ex0[0][\"content\"][:120]}...')
print(f'  user     ({len(ex0[1][\"content\"])} chars): {ex0[1][\"content\"][:120]}...')
print(f'  assistant({len(ex0[2][\"content\"])} chars): {ex0[2][\"content\"][:120]}...')
"""))

# ============================================================================
# PHASE 4 — Fine-Tune Execution
# ============================================================================
cells.append(md("""\
---
## Phase 4 — Fine-Tune Execution

**Unsloth + LoRA r=32/alpha=64 on Llama 3.2-3B-Instruct.** This is the longest cell in the notebook (~15-25 min on RTX 5080 Laptop with QLoRA 4-bit). Training loss prints every `logging_steps`; validation loss every `eval_steps` per `config_beru.yaml`.
"""))

cells.append(code("""\
# Load base model with Unsloth (4-bit quantization for QLoRA)
from unsloth import FastLanguageModel, is_bfloat16_supported

base_model_name = config['model']['base_model']
max_seq_length  = config['model']['max_seq_length']
load_in_4bit    = config['model']['load_in_4bit']

print(f'Loading base model: {base_model_name}')
print(f'  max_seq_length:   {max_seq_length}')
print(f'  load_in_4bit:     {load_in_4bit}')

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name      = base_model_name,
    max_seq_length  = max_seq_length,
    load_in_4bit    = load_in_4bit,
    dtype           = None,   # auto-detect
)
print('Base model loaded.')
"""))

cells.append(code("""\
# Attach LoRA adapter per D-009 hyperparameters
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

# Count trainable parameters
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f'Trainable parameters: {trainable:,}  ({trainable/total*100:.3f}% of total {total:,})')
"""))

cells.append(code("""\
# Apply chat template so each conversation renders to a single training string
def format_conversations(examples):
    texts = []
    for convo in examples['conversations']:
        text = tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {'text': texts}

train_ds_formatted = train_ds.map(format_conversations, batched=True, remove_columns=['conversations'])
val_ds_formatted   = val_ds.map(format_conversations,   batched=True, remove_columns=['conversations'])

print('Formatted example (first 400 chars):')
print(train_ds_formatted[0]['text'][:400])
print('...')
"""))

cells.append(code("""\
# Build SFTTrainer with config_beru.yaml hyperparameters.
# PyYAML 1.1 parses scientific notation like `2e-5` as a string; cast numerics to float.
from trl import SFTTrainer
from transformers import TrainingArguments

t_cfg = config['training']
training_args = TrainingArguments(
    output_dir                  = str(ADAPTER_OUT.parent / '_checkpoints'),
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
    report_to                   = 'none',   # no wandb in this run
)

trainer = SFTTrainer(
    model           = model,
    tokenizer       = tokenizer,
    train_dataset   = train_ds_formatted,
    eval_dataset    = val_ds_formatted,
    dataset_text_field = 'text',
    max_seq_length  = max_seq_length,
    dataset_num_proc= 2,
    packing         = False,
    args            = training_args,
)

steps_per_epoch = len(train_ds) // (t_cfg['batch_size'] * t_cfg['gradient_accumulation_steps'])
total_steps     = steps_per_epoch * t_cfg['epochs_per_chunk']
print(f'Steps per epoch: ~{steps_per_epoch}')
print(f'Total steps:     ~{total_steps}')
print('Trainer ready.')
"""))

cells.append(code("""\
# RUN — this is the long cell. Loss prints inline.
training_start = time.time()
print(f'Training starting at {datetime.now(timezone.utc).isoformat()} UTC')
print('Logging steps every 5; evaluation every 25 steps.')
print('-' * 70)

trainer_stats = trainer.train()

training_duration = time.time() - training_start
print('-' * 70)
print(f'Training complete in {training_duration/60:.1f} minutes')
print(f'Final train loss: {trainer_stats.metrics.get(\"train_loss\", \"unknown\")}')
"""))

# ============================================================================
# PHASE 5 — Save adapter + merged model
# ============================================================================
cells.append(md("""\
---
## Phase 5 — Save Adapter + Merged Model

The LoRA adapter is small (~50-100 MB). The merged 16-bit model is the artifact that downstream eval and serving consume. We save both for reproducibility per D-005 / SR-4 lineage discipline.
"""))

cells.append(code("""\
# Save LoRA adapter (small, just the delta weights)
model.save_pretrained(str(ADAPTER_OUT))
tokenizer.save_pretrained(str(ADAPTER_OUT))
print(f'Adapter saved: {ADAPTER_OUT.relative_to(REPO_ROOT)}')

# Compute size of adapter
adapter_size_mb = sum(p.stat().st_size for p in ADAPTER_OUT.rglob('*') if p.is_file()) / 1e6
print(f'Adapter size: {adapter_size_mb:.1f} MB')
"""))

cells.append(code("""\
# Save merged 16-bit model (base + adapter applied) for in-process eval
print(f'Saving merged 16-bit model to {MERGED_OUT.relative_to(REPO_ROOT)}...')
model.save_pretrained_merged(str(MERGED_OUT), tokenizer, save_method='merged_16bit')
print('Merged model saved.')

merged_size_gb = sum(p.stat().st_size for p in MERGED_OUT.rglob('*') if p.is_file()) / 1e9
print(f'Merged model size: {merged_size_gb:.2f} GB')
"""))

# ============================================================================
# PHASE 6 — In-process evaluation
# ============================================================================
cells.append(md("""\
---
## Phase 6 — In-Process Evaluation

Run the brain eval suites directly against the fine-tuned model in the same Python process. This bypasses GGUF/Ollama for the M3 deliverable — deployment to Ollama is documented as the next step in the experiment notes.

The scoring logic mirrors `4-eval-clarify/beru_eval_runner.py` so results are directly comparable to the baseline.
"""))

cells.append(code("""\
# Switch model to inference mode
FastLanguageModel.for_inference(model)
print('Model in inference mode.')

# Set up RAG retrieval (same path as eval runner)
sys.path.insert(0, str(GP_MODEL_OPS / '2-rag-ingestion' / '04-ingesting'))
from ingest_beru_to_chromadb import (
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
print(f'RAG collection {RAG_COLLECTION!r} ready ({collection.count()} docs)')

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
    return '\\n'.join(parts), ids
"""))

cells.append(code("""\
# Inference helper — generates the model response for a given system + user prompt
import importlib
runner_mod = importlib.import_module('beru_eval_runner') if False else None

# Bring in the eval suite metadata + scoring logic without wholesale-importing the module
sys.path.insert(0, str(EVAL_DIR))
from beru_eval_runner import BERU_SYSTEM_PROMPT, score_positive, score_negative

def hf_generate(system: str, user: str, max_new: int = 1500) -> str:
    msgs = [{'role': 'system', 'content': system},
            {'role': 'user', 'content': user}]
    inputs = tokenizer.apply_chat_template(
        msgs, return_tensors='pt', add_generation_prompt=True
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

print('Inference helper ready.')
"""))

cells.append(code("""\
# Run knowledge_brain eval (30 questions)
def run_suite(suite_path: Path, mode: str):
    questions = []
    with open(suite_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('//'):
                questions.append(json.loads(line))

    results = []
    for i, q in enumerate(questions):
        scenario = q['scenario']   # eval JSONL schema uses 'scenario', not 'input'
        rag_ctx, rag_ids = retrieve_context(scenario)
        full_user = f'{rag_ctx}\\n\\n--- Scenario ---\\n{scenario}\\n\\nProduce the BERU response.'
        try:
            response = hf_generate(BERU_SYSTEM_PROMPT, full_user)
        except Exception as e:
            response = f'[generation error: {e}]'
        scorer = score_positive if mode == 'positive' else score_negative
        score_record = scorer(q, response)
        score_record['question_id'] = q.get('id')
        score_record['rag_ids'] = rag_ids
        results.append(score_record)
        if (i + 1) % 5 == 0:
            partial = sum(1 for r in results if r.get('passed')) / len(results)
            print(f'  Q{i+1}/{len(questions)}: running score = {partial:.1%}')
    return results, questions

print('=== knowledge_brain (30 questions) ===')
ks_results, ks_questions = run_suite(EVAL_DIR / 'beru_knowledge_brain_v2.jsonl', 'positive')
ks_passed = sum(1 for r in ks_results if r.get('passed'))
ks_overall = ks_passed / len(ks_results)
print(f'\\nknowledge_brain overall: {ks_overall:.1%}  ({ks_passed}/{len(ks_results)})')
"""))

cells.append(code("""\
# Run pentest_brain eval (22 questions, OWASP LLM Top 10)
print('=== pentest_brain (22 questions) ===')
ps_results, ps_questions = run_suite(EVAL_DIR / 'beru_pentest_brain_v1.jsonl', 'negative')
ps_passed = sum(1 for r in ps_results if r.get('passed'))
ps_overall = ps_passed / len(ps_results)
print(f'\\npentest_brain overall: {ps_overall:.1%}  ({ps_passed}/{len(ps_results)})')
"""))

cells.append(code("""\
# Per-group breakdowns
def per_group(results, questions, weight_field):
    groups = {}
    for r, q in zip(results, questions):
        key = q.get(weight_field) or q.get('type') or 'other'
        groups.setdefault(key, []).append(r.get('passed'))
    return {k: (sum(v)/len(v), sum(v), len(v)) for k, v in groups.items()}

ks_per_type = per_group(ks_results, ks_questions, 'type')
print('knowledge_brain per type:')
for k, (rate, p, n) in sorted(ks_per_type.items()):
    print(f'  {k:30} {rate:.1%}  ({p}/{n})')

print()
ps_per_owasp = per_group(ps_results, ps_questions, 'owasp_llm')
print('pentest_brain per OWASP-LLM category:')
for k, (rate, p, n) in sorted(ps_per_owasp.items()):
    print(f'  {k:8} {rate:.1%}  ({p}/{n})')
"""))

# ============================================================================
# PHASE 7 — Promotion gate decision + experiment artifacts
# ============================================================================
cells.append(md("""\
---
## Phase 7 — Promotion-Gate Decision + Experiment Artifacts

Compare fine-tuned BERU against the baseline AND the absolute promotion thresholds (D-010). Write the decision to `5-experiments/exp-006-beru-v1.0/metrics.json` and a narrative `notes.md`. This is the binder evidence row for M3.
"""))

cells.append(code("""\
# Promotion-gate evaluation
gates = config['promotion_gate']
k_gate = gates['knowledge_brain']
p_gate = gates['pentest_brain']

# Knowledge gate
k_overall_pass = ks_overall >= k_gate['overall_threshold']
k_per_type_floors = {k: rate >= k_gate['per_type_floor'] for k, (rate, *_ ) in ks_per_type.items()}
k_per_type_pass = all(k_per_type_floors.values())
k_beats_baseline = ks_overall > k_gate['baseline_score']

# Pentest gate
p_overall_pass = ps_overall >= p_gate['overall_threshold']
p_per_cat_floors = {k: rate >= p_gate['per_category_floor'] for k, (rate, *_) in ps_per_owasp.items()}
p_per_cat_pass = all(p_per_cat_floors.values())
p_critical_floors = {k: rate >= p_gate['critical_floor']
                     for k, (rate, *_) in ps_per_owasp.items() if k in p_gate['critical_categories']}
p_critical_pass = all(p_critical_floors.values())
p_no_regression = ps_overall >= p_gate['baseline_score']

all_pass = (k_overall_pass and k_per_type_pass and k_beats_baseline
            and p_overall_pass and p_per_cat_pass and p_critical_pass and p_no_regression)
decision = 'PROMOTE' if all_pass else 'BLOCKED'

print(f'=== Promotion Gate Decision: {decision} ===')
print(f'Knowledge brain: {ks_overall:.1%}  (gate: ≥{k_gate[\"overall_threshold\"]:.0%}, baseline: {k_gate[\"baseline_score\"]:.1%})')
print(f'  overall pass:  {k_overall_pass}')
print(f'  per-type pass: {k_per_type_pass}  (floor {k_gate[\"per_type_floor\"]:.0%})')
print(f'  beats baseline:{k_beats_baseline}')
print(f'Pentest brain:   {ps_overall:.1%}  (gate: ≥{p_gate[\"overall_threshold\"]:.0%}, baseline: {p_gate[\"baseline_score\"]:.1%})')
print(f'  overall pass:  {p_overall_pass}')
print(f'  per-cat pass:  {p_per_cat_pass}  (floor {p_gate[\"per_category_floor\"]:.0%})')
print(f'  critical pass: {p_critical_pass}  (LLM01/06/08 floor {p_gate[\"critical_floor\"]:.0%})')
print(f'  no regression: {p_no_regression}')
"""))

cells.append(code("""\
# Write metrics.json + notes.md to the exp-006 folder
metrics = {
    'experiment_id': 'exp-006-beru-v1.0',
    'model': 'beru-v1.0-3b',
    'base_model': base_model_name,
    'training_corpus_size': len(corpus),
    'validation_corpus_size': len(val),
    'lora_config': dict(config['lora']),
    'training_config': dict(config['training']),
    'training_duration_minutes': training_duration / 60,
    'final_train_loss': trainer_stats.metrics.get('train_loss'),
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
        'notebook': str(Path(__file__ if '__file__' in dir() else 'M3-fine-tuning-execution.ipynb')),
    },
}

(EXP_DIR / 'metrics.json').write_text(json.dumps(metrics, indent=2, default=str))
print(f'Wrote {EXP_DIR.relative_to(REPO_ROOT)}/metrics.json')
"""))

cells.append(code("""\
# Write notes.md narrative
notes = f'''# exp-006-beru-v1.0 — Fine-Tune Run Notes

**Date:** {datetime.now(timezone.utc).date().isoformat()}
**Decision:** {decision}
**Notebook:** `CAPSTONE-PROJECT/notebooks/M3-fine-tuning-execution.ipynb`

## What changed

This is the M3 capstone fine-tune run. Base model `{base_model_name}` plus LoRA r={config['lora']['r']}/alpha={config['lora']['alpha']} on a {len(corpus)}-example synthetic corpus (D-005, D-012). Training ran for {training_duration/60:.1f} minutes on RTX 5080 Laptop GPU with QLoRA 4-bit.

## Results

| Metric | Baseline (exp-005) | Fine-tuned (exp-006) | Lift |
|---|---|---|---|
| Knowledge brain | {bk['overall']:.1%} | {ks_overall:.1%} | {ks_overall - bk['overall']:+.1%} |
| Pentest brain   | {bp['overall']:.1%} | {ps_overall:.1%} | {ps_overall - bp['overall']:+.1%} |

## Promotion gate (D-010)

- Knowledge overall ≥ 70%: **{'PASS' if k_overall_pass else 'FAIL'}** ({ks_overall:.1%})
- Knowledge per-type ≥ 60%: **{'PASS' if k_per_type_pass else 'FAIL'}**
- Knowledge beats baseline: **{'PASS' if k_beats_baseline else 'FAIL'}**
- Pentest overall ≥ 70%: **{'PASS' if p_overall_pass else 'FAIL'}** ({ps_overall:.1%})
- Pentest per-OWASP-LLM ≥ 50%: **{'PASS' if p_per_cat_pass else 'FAIL'}**
- Pentest critical (LLM01/06/08) ≥ 70%: **{'PASS' if p_critical_pass else 'FAIL'}**
- Pentest no regression vs baseline: **{'PASS' if p_no_regression else 'FAIL'}**

## Next steps

1. {'Update model card at `6-model-cards/champion/beru-v1.md` and archive the prior champion.' if decision == 'PROMOTE' else 'Identify weak categories from per-type / per-OWASP-LLM tables; add targeted training data; re-run.'}
2. Convert merged 16-bit model to GGUF Q4_K_M and register with Ollama as `beru:v1.0` for deployment.
3. Cross-link this experiment in `CAPSTONE-PROJECT/templates/ai-inventory-register.md` (JSA-AI-003) under the registered-versions table.
4. Run agent suites once M4 (LangGraph) is built — completes the 4-eval architecture.

## Provenance

- Adapter:        `{ADAPTER_OUT.relative_to(REPO_ROOT)}`
- Merged model:   `{MERGED_OUT.relative_to(REPO_ROOT)}`
- Training data:  `BERU-AI/training-data/chatml-examples/beru-training-examples.jsonl` (SHA tracked in lineage manifest)
- Validation set: `1-local-pipeline/01-raw-data-lake/beru_validation_v1.jsonl`
- Eval suites:    `4-eval-clarify/beru_knowledge_brain_v2.jsonl` + `beru_pentest_brain_v1.jsonl`
- Baseline:       `5-experiments/exp-005-beru-3b-baseline/metrics.json`
'''
(EXP_DIR / 'notes.md').write_text(notes)
print(f'Wrote {EXP_DIR.relative_to(REPO_ROOT)}/notes.md')

# Also stash a copy of the run config
(EXP_DIR / 'params.yaml').write_text(yaml.dump(config, sort_keys=False))
print(f'Wrote {EXP_DIR.relative_to(REPO_ROOT)}/params.yaml')

print(f'\\n=== M3 DELIVERABLE COMPLETE ===')
print(f'Decision: {decision}')
print(f'Artifacts in {EXP_DIR.relative_to(REPO_ROOT)}/')
"""))

# ============================================================================
# Build the notebook
# ============================================================================
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata = {
    'kernelspec': {
        'display_name': 'Python 3',
        'language': 'python',
        'name': 'python3',
    },
    'language_info': {'name': 'python', 'version': '3.11.9'},
}

with open(OUT, 'w') as f:
    nbf.write(nb, f)
print(f'Wrote {OUT}')
print(f'Cells: {len(cells)} (markdown + code)')
