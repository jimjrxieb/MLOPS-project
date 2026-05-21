# 06-Model CI/CD

GitHub Actions workflows for automated model lifecycle.

## Workflows

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `validate-training-data.yml` | Push to data branches | Runs quality gates — format, scope, dedup, content |
| `train-eval-promote.yml` | After validate passes | Full training cycle on self-hosted GPU runner; opens GitHub issue on eval failure |
| `weekly-eval.yml` | Scheduled (Sunday 02:00 UTC) | Eval against production model — drift signal |

## Deployment

```bash
# Copy workflows to your repo
cp 06-model-cicd/github-actions/*.yml .github/workflows/
```

## Requirements

- Self-hosted runner with GPU labeled `[self-hosted, gpu]` for `train-eval-promote.yml`
- `KFP_ENDPOINT` secret (or env var) if routing through KFP
- `OLLAMA_HOST` secret if running Ollama-backed eval

## Related

- `tools/train-eval-promote.sh` — same pipeline, CLI entry point
- `tools/validate-training-data.py` — what the validate workflow calls
- `4-eval-clarify/beru_eval_runner.py` — eval runner the promote step invokes
