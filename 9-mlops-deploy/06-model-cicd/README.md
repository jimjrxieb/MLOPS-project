# 06-Model CI/CD

GitHub Actions workflows for automated model lifecycle.

## Workflows

- `github-actions/validate-training-data.yml` — Triggers on data changes, runs quality gates
- `github-actions/train-eval-promote.yml` — Full training cycle after validation passes
- `github-actions/model-rollback.yml` — Manual rollback to a previous model version
- `github-actions/weekly-eval.yml` — Scheduled weekly eval against production model

## Deployment

```bash
# Copy workflows to your repo
cp 06-model-cicd/github-actions/*.yml .github/workflows/
```

## Related

- Playbook `09-deploy-model-cicd.md`
- Tools: `tools/train-eval-promote.sh`, `tools/validate-training-data.py`
