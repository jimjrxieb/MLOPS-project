# RANK-AI

E/D/C/B/S rank classification for security findings and K8s operational events.

## What It Does

Classifies any security finding or K8s event by **fix complexity**, not just severity:

| Rank | Meaning | Who Handles | Example |
|------|---------|-------------|---------|
| **E** | One command, zero diagnosis | Pattern NPC (auto) | ImagePullBackOff, missing label |
| **D** | Known fix, <3 steps | Pattern NPC (auto) | OPA deny, add resource limits, pin image tag |
| **C** | Multi-step diagnosis | Katie diagnoses, JADE approves | CrashLoopBackOff, OOMKilled, ArgoCD OutOfSync |
| **B** | Cross-cluster impact | Human decides, JADE provides intel | NodeNotReady, RBAC wildcard, webhook timeout |
| **S** | Architectural / active incident | Human only | etcd corruption, control plane down, data loss |

## Two Classifiers

### 1. Rule-Based (`rank_classifier.py`)
- Pattern matching: rule ID → scanner → operational event → text patterns
- Handles scanner findings (trivy, kubescape, gitleaks, etc.)
- Handles K8s runtime events (CrashLoopBackOff, OPA denies, ArgoCD sync)
- Sub-millisecond latency, no dependencies
- Covers 90%+ of findings

### 2. ML-Based (`ml/rank_classifier_ml.py`)
- sklearn RandomForest trained on 239 labeled examples
- Called by JADE for ambiguous cases (confidence < 0.6)
- Model: `training-data/rank_classifier.joblib`
- Perfect accuracy on training set (100% F1 across all ranks)

## Files

```
RANK-AI/
├── rank_classifier.py              ← Rule-based classifier (source of truth)
├── ml/
│   ├── rank_classifier_ml.py       ← sklearn ML classifier
│   ├── rank_decision.py            ← Decision logic helpers
│   └── rank_definitions.py         ← Rank enum and constants
└── training-data/
    ├── rank_classifier.joblib      ← Trained sklearn model
    └── rank_classifier.metrics.json ← Training metrics (100% accuracy)
```

## Usage

```python
from rank_classifier import RankClassifier

classifier = RankClassifier()

# Scanner finding
result = classifier.classify({
    "scanner": "trivy",
    "rule_id": "CVE-2024-1234",
    "severity": "CRITICAL",
    "title": "Vulnerable package",
    "fixed_version": "2.0.1"
})
# → D-rank, auto_fix

# K8s operational event
result = classifier.classify({
    "source": "kubectl-events",
    "reason": "CrashLoopBackOff",
    "title": "Pod payments/api-7f8b9d restarting",
    "kind": "Pod",
    "namespace": "payments"
})
# → C-rank, request_approval

# ArgoCD sync issue
result = classifier.classify({
    "source": "argocd",
    "sync_status": "OutOfSync",
    "health_status": "Degraded",
    "title": "Application portfolio-api is OutOfSync"
})
# → C-rank, request_approval

# OPA/Gatekeeper deny
result = classifier.classify({
    "source": "opa-gatekeeper",
    "reason": "denied",
    "title": "Container must not run as root",
    "description": "denied by run-as-root policy"
})
# → D-rank, auto_fix
```

## Consumers

- **GP-BEDROCK-AGENTS** — JSA agents import from `shared/ranking/` (re-exports from here)
- **GP-INFRA/GP-API** — `/api/findings/rank` endpoint uses the ranking service
- **JADE-AI** — C-rank approval decisions verify rank with ML classifier
- **KATIE-AI** — Triage router uses rank to decide routing

## Test

```bash
python3 rank_classifier.py
```
