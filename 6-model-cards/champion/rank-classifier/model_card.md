# Model Card: Rank Classifier (sklearn + Rule-Based)

## Model Details

| Field | Value |
|-------|-------|
| **Name** | rank_classifier |
| **Type** | Two-tier: rule-based (primary) + sklearn RandomForest (fallback) |
| **Rule-based** | `RANK-AI/rank_classifier.py` — pattern matching, 0 dependencies |
| **ML model** | `RANK-AI/training-data/rank_classifier.joblib` — sklearn RandomForest |
| **ML parameters** | ~10K (lightweight ensemble) |
| **Training data** | 239 labeled security findings (ML model only) |
| **Location** | `GP-MODEL-OPS/RANK-AI/` |

## Intended Use

Classifies security findings AND K8s operational events into E/D/C/B/S ranks by **fix complexity**, not just severity:

| Rank | Meaning | Who handles | Example |
|------|---------|-------------|---------|
| E | One command | Auto-fix | ImagePullBackOff, missing label |
| D | Known fix, <3 steps | Auto-fix | OPA deny, add resource limits |
| C | Multi-step diagnosis | Katie → JADE approves | CrashLoopBackOff, OOMKilled, ArgoCD OutOfSync |
| B | Cross-cluster impact | Human decides | NodeNotReady, RBAC wildcard |
| S | Architectural/incident | Human only | etcd corruption, control plane down |

**Two classifiers, one interface:**
- Rule-based handles 90%+ of findings (sub-ms, no GPU)
- ML model called only when confidence < 0.6 (rare)

## Factors

| Factor | Impact | Detail |
|--------|--------|--------|
| **Source type** | High | Scanner findings (trivy, kubescape) rank differently than operational events (CrashLoopBackOff) |
| **Rule ID specificity** | High | Exact rule ID match (CVE-2021-44228 → S) is more confident than text pattern match |
| **Event reason** | High | K8s event reason maps directly to rank (60+ patterns defined) |
| **ArgoCD vs kubectl** | Medium | ArgoCD-managed resources route differently (fix in git, not kubectl) |

## Metrics

| Metric | How measured | Current |
|--------|-------------|---------|
| Rule-based coverage | % of findings classified without ML fallback | ~90%+ (estimated) |
| ML accuracy | 5-fold cross-validation on 239 examples | 100% (likely overfit) |
| ML F1 (per rank) | Classification report | 1.00 all ranks |
| Latency | Time per classification | <1ms (rule-based), <5ms (ML) |

## Training Data (ML model)

- **Size:** 239 labeled security findings
- **Source:** JSA scan findings labeled by human (J)
- **Distribution:** E: 40, D: 79, C: 40, B: 40, S: 40
- **Format:** Feature-engineered from scanner, rule_id, severity, title, description
- **Missing:** No operational K8s events (CrashLoopBackOff, OPA denies, ArgoCD). These are handled by the rule-based classifier's `OPERATIONAL_PATTERNS` but not in the ML training data.

## Evaluation

| Rank | Precision | Recall | F1 | Support |
|------|-----------|--------|----|---------|
| E | 1.00 | 1.00 | 1.00 | 40 |
| D | 1.00 | 1.00 | 1.00 | 79 |
| C | 1.00 | 1.00 | 1.00 | 40 |
| B | 1.00 | 1.00 | 1.00 | 40 |
| S | 1.00 | 1.00 | 1.00 | 40 |

Cross-validation: 5-fold, 100% accuracy, 0.0 std.

**Honest assessment:** 100% on 239 examples is overfitting. The training set is small and likely too clean (no ambiguous cases). Real-world accuracy is unknown because the rule-based classifier handles everything before the ML model is consulted.

## Limitations

- 239 training examples is small — model hasn't seen edge cases
- 100% accuracy = overfit. Real-world ambiguous cases untested.
- No operational events in ML training data (rule-based covers these, ML doesn't)
- No held-out test set — eval is on training set only
- Confidence calibration not validated (predicted probabilities may not match actual accuracy)

## Ethical Considerations

- Classification directly determines if a fix is auto-applied (E/D) or requires human review (B/S)
- Misclassifying a B-rank as D-rank → unsafe auto-fix on infrastructure with blast radius
- Misclassifying a D-rank as B-rank → unnecessary human bottleneck (annoying but safe)
- Default to C-rank for unknowns is a safe fallback (requires approval)

## Next Steps

- [ ] Add 7,095 real JSA findings to ML training data (from `GP-PROJECTS/*/jsa/inbox/`)
- [ ] Add operational K8s events to ML training data
- [ ] Retrain with 500+ examples
- [ ] Evaluate on held-out set (not training set)
- [ ] Measure real-world rule-based vs ML agreement rate
- [ ] Add calibrated probabilities for confidence scoring
