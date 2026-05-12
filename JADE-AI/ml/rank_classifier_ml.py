"""
ML-Based Rank Classifier
sklearn-powered classification of security findings into E/D/C/B/S ranks
"""

import json
import pickle
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from .feature_engineering import FindingFeatureExtractor


class Rank(Enum):
    """Automation rank levels (ordinal: E < D < C < B < S)"""
    E = 0  # 95-100% automated - trivial fixes
    D = 1  # 70-90% automated - standard fixes
    C = 2  # 40-70% automated - needs approval
    B = 3  # 20-40% automated - escalate
    S = 4  # 0-5% automated - escalate

    @classmethod
    def from_string(cls, s: str) -> 'Rank':
        return cls[s.upper()]

    def __lt__(self, other):
        return self.value < other.value


@dataclass
class MLClassificationResult:
    """Result of ML-based rank classification"""
    rank: Rank
    confidence: float           # Calibrated probability
    probabilities: Dict[str, float]  # Per-class probabilities
    reason: str
    auto_fixable: bool
    requires_approval: bool
    escalate: bool
    suggested_action: str
    feature_importance: Optional[Dict[str, float]] = None


class MLRankClassifier:
    """
    ML-based security finding rank classifier.

    Uses:
    - Feature engineering from FindingFeatureExtractor
    - RandomForest or GradientBoosting for classification
    - Calibrated probabilities for confidence scores
    - Class weights for imbalanced data (S-rank is rare)

    Can work standalone or augment rule-based classifier.
    """

    RANK_ACTIONS = {
        Rank.E: ("Auto-fix immediately", True, False, False),
        Rank.D: ("Auto-fix with logging", True, False, False),
        Rank.C: ("Request approval", False, True, False),
        Rank.B: ("Escalate to human", False, False, True),
        Rank.S: ("Escalate immediately", False, False, True),
    }

    def __init__(
        self,
        model_type: str = "random_forest",
        calibrate: bool = True,
        n_estimators: int = 100,
        max_text_features: int = 100,
        model_path: Optional[Path] = None
    ):
        """
        Initialize ML Rank Classifier.

        Args:
            model_type: "random_forest", "gradient_boosting", or "logistic"
            calibrate: Whether to calibrate probabilities
            n_estimators: Number of trees for ensemble methods
            max_text_features: Max TF-IDF features
            model_path: Path to load pre-trained model
        """
        self.model_type = model_type
        self.calibrate = calibrate
        self.n_estimators = n_estimators

        # Feature extractor
        self.feature_extractor = FindingFeatureExtractor(max_text_features=max_text_features)

        # Label encoder
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit([r.name for r in Rank])

        # Build classifier
        self.classifier = self._build_classifier()

        # Full pipeline
        self.pipeline = None
        self._fitted = False

        # Load pre-trained if path provided
        if model_path and Path(model_path).exists():
            self.load(model_path)

    def _build_classifier(self):
        """Build the base classifier."""
        # Class weights to handle imbalanced data
        # S-rank is rare (~1%), E-rank is common (~60%)
        class_weight = {
            0: 1.0,   # E
            1: 1.5,   # D
            2: 2.0,   # C
            3: 3.0,   # B
            4: 5.0,   # S (heavily weighted)
        }

        if self.model_type == "random_forest":
            base = RandomForestClassifier(
                n_estimators=self.n_estimators,
                class_weight=class_weight,
                max_depth=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == "gradient_boosting":
            base = GradientBoostingClassifier(
                n_estimators=self.n_estimators,
                max_depth=5,
                min_samples_leaf=10,
                random_state=42
            )
        else:  # logistic
            base = LogisticRegression(
                class_weight=class_weight,
                max_iter=1000,
                random_state=42,
                multi_class='multinomial'
            )

        # Calibrate probabilities for better confidence estimates
        if self.calibrate:
            return CalibratedClassifierCV(base, cv=3, method='isotonic')
        return base

    def fit(self, findings: List[Dict[str, Any]], labels: List[str]) -> 'MLRankClassifier':
        """
        Train the classifier on labeled findings.

        Args:
            findings: List of finding dicts
            labels: List of rank labels (E/D/C/B/S)

        Returns:
            self for chaining
        """
        # Fit feature extractor and transform
        X = self.feature_extractor.fit_transform(findings)

        # Encode labels
        y = self.label_encoder.transform([l.upper() for l in labels])

        # Fit classifier
        self.classifier.fit(X, y)
        self._fitted = True

        return self

    def predict(self, finding: Dict[str, Any]) -> MLClassificationResult:
        """
        Classify a single finding.

        Args:
            finding: Security finding dict

        Returns:
            MLClassificationResult with rank and metadata
        """
        if not self._fitted:
            raise ValueError("Classifier not fitted. Call fit() first or load a model.")

        # Extract features
        X = self.feature_extractor.transform([finding])

        # Get prediction and probabilities
        pred = self.classifier.predict(X)[0]
        proba = self.classifier.predict_proba(X)[0]

        # Decode rank
        rank_name = self.label_encoder.inverse_transform([pred])[0]
        rank = Rank.from_string(rank_name)

        # Build probability dict
        probabilities = {
            self.label_encoder.inverse_transform([i])[0]: float(p)
            for i, p in enumerate(proba)
        }

        # Get confidence (calibrated probability of predicted class)
        confidence = float(proba[pred])

        # Get action metadata
        action, auto_fixable, requires_approval, escalate = self.RANK_ACTIONS[rank]

        # Get feature importance if available
        feature_importance = self._get_feature_importance(finding)

        # Build reason string
        reason = self._build_reason(rank, confidence, probabilities, finding)

        return MLClassificationResult(
            rank=rank,
            confidence=confidence,
            probabilities=probabilities,
            reason=reason,
            auto_fixable=auto_fixable,
            requires_approval=requires_approval,
            escalate=escalate,
            suggested_action=action,
            feature_importance=feature_importance
        )

    def predict_batch(self, findings: List[Dict[str, Any]]) -> List[MLClassificationResult]:
        """Classify multiple findings efficiently."""
        return [self.predict(f) for f in findings]

    def evaluate(self, findings: List[Dict[str, Any]], labels: List[str]) -> Dict[str, Any]:
        """
        Evaluate classifier performance.

        Returns:
            Dict with accuracy, per-class metrics, confusion matrix
        """
        X = self.feature_extractor.transform(findings)
        y_true = self.label_encoder.transform([l.upper() for l in labels])
        y_pred = self.classifier.predict(X)

        report = classification_report(
            y_true, y_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True
        )

        cm = confusion_matrix(y_true, y_pred)

        return {
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'accuracy': report['accuracy'],
            'macro_f1': report['macro avg']['f1-score'],
            'weighted_f1': report['weighted avg']['f1-score']
        }

    def cross_validate(
        self,
        findings: List[Dict[str, Any]],
        labels: List[str],
        cv: int = 5
    ) -> Dict[str, float]:
        """
        Perform cross-validation.

        Returns:
            Dict with mean and std of accuracy
        """
        X = self.feature_extractor.fit_transform(findings)
        y = self.label_encoder.transform([l.upper() for l in labels])

        # Use stratified K-fold to preserve class distribution
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

        scores = cross_val_score(
            self._build_classifier(),  # Fresh classifier
            X, y,
            cv=skf,
            scoring='accuracy'
        )

        return {
            'mean_accuracy': float(scores.mean()),
            'std_accuracy': float(scores.std()),
            'scores': scores.tolist()
        }

    def _get_feature_importance(self, finding: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Get feature importance for interpretability."""
        if not hasattr(self.classifier, 'feature_importances_'):
            # For calibrated classifiers, try to access base estimator
            if hasattr(self.classifier, 'estimator') and hasattr(self.classifier.estimator, 'feature_importances_'):
                importances = self.classifier.estimator.feature_importances_
            else:
                return None
        else:
            importances = self.classifier.feature_importances_

        feature_names = self.feature_extractor.get_feature_names()

        # Get top 10 most important features
        if len(importances) == len(feature_names):
            importance_pairs = list(zip(feature_names, importances))
            importance_pairs.sort(key=lambda x: x[1], reverse=True)
            return {name: float(imp) for name, imp in importance_pairs[:10]}

        return None

    def _build_reason(
        self,
        rank: Rank,
        confidence: float,
        probabilities: Dict[str, float],
        finding: Dict[str, Any]
    ) -> str:
        """Build human-readable classification reason."""
        scanner = finding.get('scanner', 'unknown')
        severity = finding.get('severity', 'unknown')

        if confidence > 0.8:
            certainty = "High confidence"
        elif confidence > 0.6:
            certainty = "Moderate confidence"
        else:
            certainty = "Low confidence"

        reason = f"{certainty} {rank.name}-rank classification. "
        reason += f"Scanner: {scanner}, Severity: {severity}. "

        # Add secondary prediction if close
        sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_probs) > 1:
            second_rank, second_prob = sorted_probs[1]
            if second_prob > 0.2:
                reason += f"Also considered: {second_rank} ({second_prob:.0%})"

        return reason

    def save(self, path: Path):
        """Save trained model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            'classifier': self.classifier,
            'feature_extractor': self.feature_extractor,
            'label_encoder': self.label_encoder,
            'model_type': self.model_type,
            'fitted': self._fitted
        }

        with open(path, 'wb') as f:
            import json; json.dump({k: v for k, v in state.items() if isinstance(v, (int, float, str, list, dict))}, f)

    @classmethod
    def load(cls, path: Path) -> 'MLRankClassifier':
        """Load trained model from disk."""
        with open(path, 'rb') as f:
            import json
state = json.load(f)

        # Create new instance with saved model type
        instance = cls(model_type=state['model_type'], calibrate=False)
        instance.classifier = state['classifier']
        instance.feature_extractor = state['feature_extractor']
        instance.label_encoder = state['label_encoder']
        instance._fitted = state['fitted']

        return instance


class RankPipeline:
    """
    Combined rule-based + ML rank classification pipeline.

    Uses rules for high-confidence patterns, ML for ambiguous cases.
    """

    def __init__(
        self,
        ml_classifier: Optional[MLRankClassifier] = None,
        ml_threshold: float = 0.7,
        prefer_rules: bool = True
    ):
        """
        Initialize hybrid pipeline.

        Args:
            ml_classifier: Trained ML classifier (optional)
            ml_threshold: Confidence threshold for ML predictions
            prefer_rules: If True, use rules when available, ML as fallback
        """
        self.ml_classifier = ml_classifier
        self.ml_threshold = ml_threshold
        self.prefer_rules = prefer_rules

        # Import rule-based classifier if available
        self.rule_classifier = self._load_rule_classifier()

    def _load_rule_classifier(self):
        """Try to load the existing rule-based classifier."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "GP-CONSULTING" / "3-Runtime-Scans-NPC"))
            from rank_classifier import RankClassifier
            return RankClassifier(use_jade_fallback=False)
        except ImportError:
            return None

    def classify(self, finding: Dict[str, Any]) -> MLClassificationResult:
        """
        Classify a finding using hybrid approach.

        1. Try rules if prefer_rules=True
        2. If rule confidence < threshold, use ML
        3. If ML confidence < threshold, return with warning
        """
        ml_result = None
        rule_result = None

        # Try rule-based first if preferred
        if self.prefer_rules and self.rule_classifier:
            rule_result = self.rule_classifier.classify(finding)
            if rule_result.confidence >= self.ml_threshold:
                # Convert to ML result format
                return self._convert_rule_result(rule_result)

        # Try ML classifier
        if self.ml_classifier and self.ml_classifier._fitted:
            ml_result = self.ml_classifier.predict(finding)
            if ml_result.confidence >= self.ml_threshold:
                return ml_result

        # Both low confidence - return best available
        if ml_result and rule_result:
            if ml_result.confidence >= rule_result.confidence:
                ml_result.reason += " [Low confidence - verify manually]"
                return ml_result
            return self._convert_rule_result(rule_result)

        if ml_result:
            return ml_result
        if rule_result:
            return self._convert_rule_result(rule_result)

        # Fallback
        return MLClassificationResult(
            rank=Rank.C,
            confidence=0.5,
            probabilities={'C': 0.5},
            reason="Could not classify - defaulting to C-rank for manual review",
            auto_fixable=False,
            requires_approval=True,
            escalate=False,
            suggested_action="Request approval"
        )

    def _convert_rule_result(self, rule_result) -> MLClassificationResult:
        """Convert rule-based result to ML result format."""
        rank = Rank.from_string(rule_result.rank.name)
        return MLClassificationResult(
            rank=rank,
            confidence=rule_result.confidence,
            probabilities={rank.name: rule_result.confidence},
            reason=f"[Rule-based] {rule_result.reason}",
            auto_fixable=rule_result.auto_fixable,
            requires_approval=rule_result.requires_approval,
            escalate=rule_result.escalate,
            suggested_action=rule_result.suggested_action
        )
