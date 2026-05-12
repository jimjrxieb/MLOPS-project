"""
Training Pipeline for ML Rank Classifier
Extracts training data from JSA logs and trains the classifier
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sklearn.model_selection import train_test_split

from .rank_classifier_ml import MLRankClassifier, Rank
from .feature_engineering import FindingFeatureExtractor


@dataclass
class TrainingExample:
    """A labeled training example"""
    finding: Dict[str, Any]
    rank: str
    source: str  # Where this label came from
    timestamp: Optional[str] = None


class RankClassifierTrainer:
    """
    Train ML rank classifier from historical data.

    Data sources:
    1. JSA cycle logs (target-slot-logs/)
    2. Approval queue history (approved/rejected)
    3. Manual annotations
    4. Rule-based classifier output (for bootstrapping)
    """

    def __init__(self, gp_root: Path = None):
        """
        Initialize trainer.

        Args:
            gp_root: Path to GP-copilot root directory
        """
        self.gp_root = gp_root or Path(__file__).parent.parent.parent
        self.jsa_logs = self.gp_root / "GP-BEDROCK-AGENTS" / "jadeSecureAgent" / "target-slot-logs"
        self.approval_queue = self.gp_root / "GP-CLOUDWATCH" / "approval-queue"
        self.training_data_dir = self.gp_root / "GP-MODEL-OPS" / "1-GP-GLUE" / "rank-training-data"

    def extract_from_jsa_logs(self, limit: int = None) -> List[TrainingExample]:
        """
        Extract training examples from JSA cycle logs.

        JSA logs contain findings with assigned_rank from the rule classifier.
        These can be used to bootstrap ML training.
        """
        examples = []

        # Look for cycle files
        cycle_files = list(self.jsa_logs.glob("**/cycles.jsonl"))
        cycle_files.extend(self.jsa_logs.glob("**/state/cycles.jsonl"))

        for cycle_file in cycle_files:
            try:
                with open(cycle_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            cycle = json.loads(line)
                            # Extract finding and rank
                            if 'finding' in cycle or 'findings' in cycle:
                                findings = cycle.get('findings', [cycle.get('finding')])
                                for finding in findings:
                                    if finding and 'assigned_rank' in cycle:
                                        examples.append(TrainingExample(
                                            finding=finding,
                                            rank=cycle['assigned_rank'],
                                            source='jsa_cycle',
                                            timestamp=cycle.get('timestamp')
                                        ))
                        except json.JSONDecodeError:
                            continue

                        if limit and len(examples) >= limit:
                            return examples

            except Exception as e:
                print(f"Error reading {cycle_file}: {e}")

        return examples

    def extract_from_approval_queue(self) -> List[TrainingExample]:
        """
        Extract training examples from approval queue.

        Approved items are confirmed correct, rejected items need adjustment.
        """
        examples = []

        if not self.approval_queue.exists():
            return examples

        for approval_file in self.approval_queue.glob("*.json"):
            try:
                with open(approval_file) as f:
                    data = json.load(f)

                status = data.get('status')
                finding = data.get('finding', {})

                if status == 'approved':
                    # Approved C-rank stays C-rank
                    rank = data.get('rank', 'C')
                    examples.append(TrainingExample(
                        finding=finding,
                        rank=rank,
                        source='approved',
                        timestamp=data.get('approved_at')
                    ))
                elif status == 'rejected':
                    # Rejected C-rank might be D (auto-fix) or B (escalate)
                    # Use rejection reason to determine
                    reason = data.get('rejection_reason', '').lower()
                    if 'auto' in reason or 'simple' in reason:
                        rank = 'D'
                    elif 'escalate' in reason or 'complex' in reason:
                        rank = 'B'
                    else:
                        continue  # Skip ambiguous rejections

                    examples.append(TrainingExample(
                        finding=finding,
                        rank=rank,
                        source='rejected',
                        timestamp=data.get('rejected_at')
                    ))

            except Exception as e:
                print(f"Error reading {approval_file}: {e}")

        return examples

    def extract_from_scan_results(self, scan_dirs: List[Path] = None) -> List[TrainingExample]:
        """
        Extract findings from scan result files and label with rule classifier.

        This bootstraps training data using the existing rule-based system.
        """
        examples = []

        # Try to import rule classifier
        try:
            import sys
            sys.path.insert(0, str(self.gp_root / "GP-CONSULTING" / "3-Runtime-Scans-NPC"))
            from rank_classifier import RankClassifier
            rule_classifier = RankClassifier(use_jade_fallback=False)
        except ImportError:
            print("Could not import rule classifier for bootstrapping")
            return examples

        # Default scan directories
        if scan_dirs is None:
            scan_dirs = [
                self.gp_root / "GP-PROJECTS",
                self.jsa_logs / "scans"
            ]

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue

            # Look for scan result files
            for result_file in scan_dir.glob("**/*_results.json"):
                try:
                    with open(result_file) as f:
                        data = json.load(f)

                    findings = data.get('findings', data.get('results', []))
                    if isinstance(findings, dict):
                        findings = findings.get('findings', [])

                    for finding in findings:
                        if not isinstance(finding, dict):
                            continue

                        # Use rule classifier to label
                        result = rule_classifier.classify(finding)

                        # Only use high-confidence classifications
                        if result.confidence >= 0.8:
                            examples.append(TrainingExample(
                                finding=finding,
                                rank=result.rank.name,
                                source='rule_bootstrap',
                                timestamp=str(result_file.stat().st_mtime)
                            ))

                except Exception as e:
                    print(f"Error reading {result_file}: {e}")

        return examples

    def generate_synthetic_examples(self, count: int = 1000) -> List[TrainingExample]:
        """
        Generate synthetic training examples using rank_definitions.py patterns.

        Class distribution targets:
        - E-rank: 20% (trivial, common)
        - D-rank: 40% (JSA specialties - most common)
        - C-rank: 20% (junior approval)
        - B-rank: 15% (senior review)
        - S-rank: 5% (rare but critical)
        """
        from .rank_definitions import SYNTHETIC_PATTERNS

        examples = []

        # Target distribution
        distribution = {
            "E": int(count * 0.20),
            "D": int(count * 0.40),  # D-rank is JSA specialty - most common
            "C": int(count * 0.20),
            "B": int(count * 0.15),
            "S": int(count * 0.05),
        }

        for rank, target_count in distribution.items():
            patterns = SYNTHETIC_PATTERNS.get(rank, [])
            if not patterns:
                continue

            # Generate variations of each pattern
            per_pattern = max(1, target_count // len(patterns))

            for pattern in patterns:
                for i in range(per_pattern):
                    finding = pattern.copy()

                    # Add variation to file paths
                    base_file = finding.get('file', 'unknown.txt')
                    if '/' in base_file:
                        dir_part, file_part = base_file.rsplit('/', 1)
                        finding['file'] = f"{dir_part}/variant{i}/{file_part}"
                    else:
                        finding['file'] = f"src/variant{i}/{base_file}"

                    # Add random line number
                    finding['line'] = np.random.randint(1, 500)

                    examples.append(TrainingExample(finding, rank, 'synthetic'))

        # Shuffle to mix ranks
        np.random.shuffle(examples)

        print(f"Generated {len(examples)} synthetic examples:")
        rank_counts = {}
        for ex in examples:
            rank_counts[ex.rank] = rank_counts.get(ex.rank, 0) + 1
        print(f"  Distribution: {rank_counts}")

        return examples

    def prepare_training_data(
        self,
        include_synthetic: bool = True,
        balance_classes: bool = True,
        min_examples_per_class: int = 50
    ) -> Tuple[List[Dict], List[str]]:
        """
        Prepare complete training dataset.

        Returns:
            Tuple of (findings, labels)
        """
        all_examples = []

        # Collect from all sources
        print("Extracting from JSA logs...")
        all_examples.extend(self.extract_from_jsa_logs())

        print("Extracting from approval queue...")
        all_examples.extend(self.extract_from_approval_queue())

        print("Extracting from scan results...")
        all_examples.extend(self.extract_from_scan_results())

        if include_synthetic:
            print("Generating synthetic examples...")
            all_examples.extend(self.generate_synthetic_examples())

        print(f"Total examples collected: {len(all_examples)}")

        # Count by class
        class_counts = {}
        for ex in all_examples:
            class_counts[ex.rank] = class_counts.get(ex.rank, 0) + 1
        print(f"Class distribution: {class_counts}")

        # Balance if needed
        if balance_classes:
            all_examples = self._balance_classes(all_examples, min_examples_per_class)

        # Convert to lists
        findings = [ex.finding for ex in all_examples]
        labels = [ex.rank for ex in all_examples]

        return findings, labels

    def _balance_classes(
        self,
        examples: List[TrainingExample],
        min_per_class: int
    ) -> List[TrainingExample]:
        """Balance classes by oversampling minority classes."""
        by_class = {}
        for ex in examples:
            if ex.rank not in by_class:
                by_class[ex.rank] = []
            by_class[ex.rank].append(ex)

        # Find max class size
        max_size = max(len(exs) for exs in by_class.values())
        target_size = max(min_per_class, max_size // 2)  # Don't over-sample too much

        balanced = []
        for rank, exs in by_class.items():
            if len(exs) < target_size:
                # Oversample with replacement
                indices = np.random.choice(len(exs), target_size, replace=True)
                balanced.extend([exs[i] for i in indices])
            else:
                balanced.extend(exs)

        np.random.shuffle(balanced)
        return balanced

    def train(
        self,
        model_type: str = "random_forest",
        test_size: float = 0.2,
        save_path: Path = None
    ) -> Tuple[MLRankClassifier, Dict[str, Any]]:
        """
        Train and evaluate classifier.

        Returns:
            Tuple of (trained_classifier, evaluation_metrics)
        """
        # Prepare data
        findings, labels = self.prepare_training_data()

        if len(findings) < 100:
            print(f"Warning: Only {len(findings)} examples. Consider adding more data.")

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            findings, labels, test_size=test_size, stratify=labels, random_state=42
        )

        print(f"Training on {len(X_train)} examples, testing on {len(X_test)}")

        # Train
        classifier = MLRankClassifier(model_type=model_type)
        classifier.fit(X_train, y_train)

        # Evaluate
        metrics = classifier.evaluate(X_test, y_test)
        print(f"\nAccuracy: {metrics['accuracy']:.3f}")
        print(f"Macro F1: {metrics['macro_f1']:.3f}")
        print(f"Weighted F1: {metrics['weighted_f1']:.3f}")

        # Cross-validate on full dataset
        cv_results = classifier.cross_validate(findings, labels, cv=5)
        print(f"\nCross-validation: {cv_results['mean_accuracy']:.3f} ± {cv_results['std_accuracy']:.3f}")

        metrics['cross_validation'] = cv_results

        # Save if path provided
        if save_path:
            save_path = Path(save_path)
            classifier.save(save_path)
            print(f"\nModel saved to {save_path}")

            # Also save metrics
            metrics_path = save_path.with_suffix('.metrics.json')
            with open(metrics_path, 'w') as f:
                # Convert numpy arrays to lists for JSON
                metrics_json = {k: v if not isinstance(v, np.ndarray) else v.tolist()
                               for k, v in metrics.items()}
                json.dump(metrics_json, f, indent=2, default=str)

        return classifier, metrics


def main():
    """CLI for training the classifier."""
    import argparse

    parser = argparse.ArgumentParser(description="Train ML Rank Classifier")
    parser.add_argument("--model", choices=["random_forest", "gradient_boosting", "logistic"],
                       default="random_forest", help="Model type")
    parser.add_argument("--output", type=Path, default=None,
                       help="Output path for trained model")
    parser.add_argument("--no-synthetic", action="store_true",
                       help="Don't include synthetic examples")

    args = parser.parse_args()

    trainer = RankClassifierTrainer()
    classifier, metrics = trainer.train(
        model_type=args.model,
        save_path=args.output
    )

    print("\nTraining complete!")


if __name__ == "__main__":
    main()
