# 7-data-schemas — Data Contracts

JSON Schema definitions for every structured data format in the pipeline. These are the contracts — if an output format changes, tests should fail before anything downstream breaks.

---

## BERU Schemas

| Schema | What it validates | Where data lives |
|--------|------------------|-----------------|
| `beru_training_example.json` | ChatML training examples for BERU fine-tuning, with `_metadata` lineage block | `1-FineTuning-Pipeline/01-raw-data-lake/beru-*.jsonl` |
| `beru_risk_summary.json` | CISO-ready risk summaries from BERU — 9-field structured finding + rank | BERU-AI `/audit` and `/ciso-brief` endpoints |

## JADE / Katie Schemas

| Schema | What it validates | Where data lives |
|--------|------------------|-----------------|
| `training_example.json` | Base ChatML training examples for JADE/Katie fine-tuning | `1-FineTuning-Pipeline/01-raw-data-lake/*.jsonl` |
| `eval_question.json` | JADE/Katie benchmark questions (id, category, expected_keywords, grading) | `4-eval-clarify/2-test-data/evaluation/*-benchmark/` |
| `eval_result.json` | JADE/Katie eval benchmark results written by `eval_bridge.py` | `5-experiments/exp-NNN/metrics.json` |

## Platform Schemas

| Schema | What it validates | Where data lives |
|--------|------------------|-----------------|
| `jsa_finding.json` | Raw scanner finding (trivy, kubescape, gitleaks, bandit, etc.) — input to RANK-AI | `GP-PROJECTS/*/jsa/inbox/*.json` |
| `classification_result.json` | RANK-AI output — rank, confidence, suggested action, fix complexity | In-memory (returned by `rank_classifier.classify()`) |
| `generation_manifest.json` | Data generation run tracking — generator, domain, SHA256, example count | `0-data-lab/manifests/*.manifest.json` |

---

## Usage

```python
import jsonschema, json

schema = json.load(open("7-data-schemas/beru_training_example.json"))
example = json.loads(line)  # from a training JSONL
jsonschema.validate(example, schema)  # raises if invalid
```

The `8-tests/test_data_quality.py` suite validates training data against `training_example.json` and `beru_training_example.json` before any training run. No training on unvalidated data.

---

## Schema Gaps (tracked)

- **BERU eval question** — knowledge_brain/pentest_brain JSONL format not yet formalized as a schema. Fields: `id`, `type`/`owasp_llm`, `prompt`, `validation_keywords`/`fail_indicators`, `scoring`.
- **BERU eval result** — per-run JSON written by `beru_eval_runner.py` not yet formalized. Fields: `model`, `suite`, `timestamp`, `scores_by_type`, `overall`, `promotion_gate`.
