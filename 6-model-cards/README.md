# 6-Model-Cards

Champion/challenger pattern for model promotion.

## Structure

```
6-model-cards/
├── champion/              ← Currently in production
│   ├── katie-3b/          ← Katie: fast triage + routing
│   │   └── model_card.md
│   └── jade-8b/           ← JADE: C-rank reasoning + approvals
│       └── model_card.md
└── challenger/            ← Candidates being evaluated
    └── (empty until 5-experiments/exp-002 completes eval)
```

## Promotion Flow

```
5-experiments/ (train + eval)
    │
    ▼ passes promotion gate (≥60% weighted)?
    │
    ├── YES → 6-model-cards/challenger/ → canary test → 6-model-cards/champion/
    └── NO  → feedback_loop.py → more targeted data → retrain
```

## Rules

- No model enters champion/ without passing eval promotion gates
- Champion is never overwritten — old champion moves to `3-model-registry/archive/`
- model_card.md is required for every champion model
- Challenger must beat champion on weighted eval to promote
