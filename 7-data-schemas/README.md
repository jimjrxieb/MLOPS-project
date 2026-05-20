# 7-Data Schemas

JSON Schema definitions for every structured data format in the system. These are the data contracts — if the format changes, tests should fail.

## Schemas

| Schema | What it validates | Where data lives |
|--------|------------------|-----------------|
| `training_example.json` | ChatML training examples | `1-local-pipeline/01-raw-data-lake/*.jsonl` |
| `eval_result.json` | Benchmark output (scores, categories) | `4-eval-clarify/3-results/*/full_results.json` |
| `eval_question.json` | Benchmark input (questions, expected keywords) | `4-eval-clarify/2-test-data/evaluation/*/*.jsonl` |
| `jsa_finding.json` | Scanner findings (trivy, kubescape, etc.) | `GP-PROJECTS/*/jsa/inbox/*.json` |
| `classification_result.json` | RANK-AI output (rank, confidence, action) | In-memory (returned by `rank_classifier.classify()`) |
| `generation_manifest.json` | Data generation run tracking | `0-data-lab/manifests/*.manifest.json` |

## Usage

These schemas can be used for:
1. **Validation** — `jsonschema` library to validate data at pipeline boundaries
2. **Documentation** — single source of truth for "what does this data look like"
3. **Testing** — `8-tests/test_data_quality.py` validates training data against schema
4. **Contracts** — if a generator changes output format, the schema catches it
