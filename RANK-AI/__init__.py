"""
RANK-AI — E/D/C/B/S Rank Classification System

Two classifiers:
1. Rule-based (rank_classifier.py) — pattern matching, no ML, sub-ms latency
2. ML-based (ml/rank_classifier_ml.py) — sklearn RandomForest, trained on 239 examples

The rule-based classifier handles 90%+ of findings.
The ML classifier is called by JADE for ambiguous cases.
"""

from .rank_classifier import RankClassifier, ClassificationResult, Rank, classify_finding
