"""Pull 10 representative knowledge_brain questions + their RAG context for a
Claude-as-control evaluation of the BERU RAG corpus.

This decides: is the RAG corpus the bottleneck, or is the fine-tune?

For each question, prints:
  - question id + type
  - RAG context retrieved from beru-nist-800-53 (same path as runner)
  - the scenario
  - the validation_keywords + expected_actions Claude will be scored against

After Claude answers each one inline, _claude_rag_score.py reads the
JSONL of (question_id, claude_response) pairs and scores per the same logic
as beru_eval_runner.py.
"""
import json
import sys
from pathlib import Path

GP_MODEL_OPS = Path('/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS')
EVAL_DIR = GP_MODEL_OPS / '4-eval-clarify'
KNOWLEDGE_FILE = EVAL_DIR / 'beru_knowledge_brain_v2.jsonl'

# Same RAG setup as the eval runner
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

DEFAULT_K = 4

def retrieve_context(scenario: str, k: int = DEFAULT_K):
    q = collection.query(query_texts=[scenario], n_results=k)
    docs, ids, metas = q['documents'][0], q['ids'][0], q['metadatas'][0]
    parts = []
    for cid, doc, meta in zip(ids, docs, metas):
        tag = meta.get('control_id') or meta.get('subcategory_id') or meta.get('technique_id') or 'ref'
        parts.append(f'--- {cid} ({tag}) ---')
        parts.append(doc.strip())
        parts.append('')
    return '\n'.join(parts), ids


# Load all 30 questions and select a stratified sample — 1-2 per type
questions = []
with open(KNOWLEDGE_FILE) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('//'):
            questions.append(json.loads(line))

# Group by type, pick 2 from each of the 6 types → 12 questions
from collections import defaultdict
by_type = defaultdict(list)
for q in questions:
    by_type[q['type']].append(q)

# Stable 2-per-type pick (first 2)
sample = []
for t in sorted(by_type):
    sample.extend(by_type[t][:2])

print(f'# Claude+RAG smoke test — {len(sample)} questions across {len(by_type)} types')
print()
print(f'Compare against:')
print(f'  - Baseline (Llama 3.2-3B + RAG):    29.4%')
print(f'  - Fine-tuned BERU (exp-006):         3.3%')
print()

for i, q in enumerate(sample, 1):
    rag_ctx, rag_ids = retrieve_context(q['scenario'])
    print('=' * 80)
    print(f'## Q{i}/{len(sample)} — id: {q["id"]}  type: {q["type"]}')
    print('=' * 80)
    print()
    print('### RAG retrieved (top_k=4):')
    print()
    print(rag_ctx)
    print()
    print('### Scenario:')
    print(q['scenario'])
    print()
    print('### Will be scored against:')
    print(f'  validation_keywords: {q.get("validation_keywords", [])}')
    print(f'  expected_actions:    {q.get("expected_actions", [])}')
    print(f'  fail_indicators:     {q.get("fail_indicators", [])}')
    print()
