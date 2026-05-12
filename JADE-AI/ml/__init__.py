"""
JADE-AI Machine Learning Module
sklearn-based classifiers and feature engineering for security decisions

Components:
- rank_classifier_ml: sklearn RandomForest classifier
- hybrid_classifier: Rules + ML ensemble
- rank_definitions: E/D/C/B/S rank patterns
- feature_engineering: Text→features extraction
- training: Model training pipeline
- rank_decision: Bridge to JADE decision flow
"""

from .rank_classifier_ml import MLRankClassifier, RankPipeline, Rank
from .feature_engineering import FindingFeatureExtractor
from .training import RankClassifierTrainer
from .hybrid_classifier import HybridRankClassifier, HybridClassificationResult
from .rank_decision import RankDecisionCapability, RankDecision

__all__ = [
    'MLRankClassifier',
    'RankPipeline',
    'Rank',
    'FindingFeatureExtractor',
    'RankClassifierTrainer',
    'HybridRankClassifier',
    'HybridClassificationResult',
    'RankDecisionCapability',
    'RankDecision',
]
