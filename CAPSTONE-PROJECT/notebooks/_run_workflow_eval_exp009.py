"""Run the workflow eval against the exp-007 merged model.

The workflow eval tests what BERU actually does (SSP grading, evidence-vs-claim,
gap identification, authority discipline, handoff structure) instead of the
synthetic finding-production task the original eval used.

Output:
  5-experiments/exp-009-beru-v1.3/workflow_eval_results.json
  5-experiments/exp-009-beru-v1.3/workflow_eval_results.md
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

GP_MODEL_OPS = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
REPO_ROOT    = GP_MODEL_OPS.parent
MERGED       = GP_MODEL_OPS / '3-model-registry' / 'beru-v1.3-3b' / 'merged_16bit'
EVAL_DIR     = GP_MODEL_OPS / '4-eval-clarify'
EVAL_FILE    = EVAL_DIR / 'beru_workflow_eval_v1.jsonl'
EXP007_DIR   = GP_MODEL_OPS / '5-experiments' / 'exp-009-beru-v1.3'

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

# Scorers + system prompt
sys.path.insert(0, str(EVAL_DIR))
from beru_eval_runner import BERU_SYSTEM_PROMPT  # reuse same system prompt
from workflow_scorer import score as workflow_score

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


# Load eval questions
questions = []
with open(EVAL_FILE) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('//'):
            questions.append(json.loads(line))
print(f'Loaded {len(questions)} workflow eval questions')

# Run each one
print(f'\nRunning workflow eval against exp-007 model...')
results = []
suite_start = time.time()
for i, q in enumerate(questions, 1):
    t0 = time.time()
    try:
        response = hf_generate(BERU_SYSTEM_PROMPT, q['scenario'])
    except Exception as e:
        response = f'[generation error: {e}]'
    s = workflow_score(q, response)
    s['question_id'] = q['id']
    s['type'] = q['type']
    s['response'] = response
    s['generation_seconds'] = time.time() - t0
    results.append(s)
    icon = '✓' if s.get('passed') else '✗'
    print(f'  Q{i}/{len(questions)} [{q["type"]:22}] {q["id"]:36}  {icon} score={s["combined_score"]:.2f}')

elapsed = time.time() - suite_start
total_pass = sum(1 for r in results if r.get('passed'))
overall = total_pass / len(results)
print(f'\nTotal: {total_pass}/{len(results)} = {overall:.1%}  ({elapsed:.0f}s)')

# Per-type breakdown
by_type = defaultdict(list)
for r in results:
    by_type[r['type']].append(r)

print('\nPer-type:')
for t, rs in sorted(by_type.items()):
    p = sum(1 for r in rs if r.get('passed'))
    avg_score = sum(r['combined_score'] for r in rs) / len(rs)
    print(f'  {t:24} {p}/{len(rs)}  avg_score={avg_score:.2f}')

# Save JSON
out_json = EXP007_DIR / 'workflow_eval_results.json'
out_json.write_text(json.dumps({
    'experiment': 'exp-009-beru-v1.3',
    'eval_suite': 'beru_workflow_eval_v1',
    'run_date_utc': datetime.now(timezone.utc).isoformat(),
    'total_questions': len(results),
    'overall_pass_rate': overall,
    'per_type': {t: {
        'pass_rate': sum(1 for r in rs if r.get('passed')) / len(rs),
        'avg_score': sum(r['combined_score'] for r in rs) / len(rs),
        'passed': sum(1 for r in rs if r.get('passed')),
        'total': len(rs),
    } for t, rs in by_type.items()},
    'results': results,
}, indent=2, default=str))

# Save markdown
md_lines = [
    '# exp-007 Workflow-Eval Results',
    '',
    f'Generated: {datetime.now(timezone.utc).isoformat()}',
    f'Model:     `3-model-registry/beru-v1.3-3b/merged_16bit/`',
    f'Eval:      `4-eval-clarify/beru_workflow_eval_v1.jsonl` ({len(questions)} questions)',
    '',
    f'**Overall pass rate: {overall:.1%}** ({total_pass}/{len(results)})',
    '',
    '## Per-type breakdown',
    '',
    '| Type | Pass rate | Avg score |',
    '|---|---|---|',
]
for t, rs in sorted(by_type.items()):
    p = sum(1 for r in rs if r.get('passed'))
    avg = sum(r['combined_score'] for r in rs) / len(rs)
    md_lines.append(f'| `{t}` | {p}/{len(rs)} ({p/len(rs):.0%}) | {avg:.2f} |')

md_lines.extend(['', '---', '', '## Per-question detail', ''])
for r in results:
    icon = '✓' if r.get('passed') else '✗'
    md_lines.extend([
        f'### {icon} `{r["question_id"]}` ({r["type"]})',
        '',
        f'**Score:** `{r["combined_score"]:.2f}`',
        '',
        '<details><summary>Response</summary>',
        '',
        '```',
        r['response'][:2000] + ('...' if len(r['response']) > 2000 else ''),
        '```',
        '',
        '</details>',
        '',
    ])

out_md = EXP007_DIR / 'workflow_eval_results.md'
out_md.write_text('\n'.join(md_lines))
print(f'\nWrote:')
print(f'  {out_json.relative_to(REPO_ROOT)}')
print(f'  {out_md.relative_to(REPO_ROOT)}')
