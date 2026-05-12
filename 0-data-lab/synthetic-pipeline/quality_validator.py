"""
Training Example Quality Validator

Validates training examples to ensure they meet quality standards
before being added to the training corpus.
"""

import re
from typing import List, Dict, Any
from .models import TrainingExample, QualityMetrics, ExampleQuality


class QualityValidator:
    """
    Validate training example quality.

    The validator checks:
    - Instruction clarity and completeness
    - Input data completeness
    - Output quality and formatting
    - Metadata completeness
    - Overall quality score

    Example:
        >>> validator = QualityValidator()
        >>> example = TrainingExample(...)
        >>> metrics = validator.validate(example)
        >>> if metrics.quality_level == ExampleQuality.EXCELLENT:
        ...     print("High-quality example!")
    """

    def __init__(
        self,
        min_instruction_length: int = 10,
        max_instruction_length: int = 500,
        min_output_length: int = 50,
        max_output_length: int = 5000
    ):
        """
        Initialize validator.

        Args:
            min_instruction_length: Minimum instruction characters
            max_instruction_length: Maximum instruction characters
            min_output_length: Minimum output characters
            max_output_length: Maximum output characters
        """
        self.min_instruction_length = min_instruction_length
        self.max_instruction_length = max_instruction_length
        self.min_output_length = min_output_length
        self.max_output_length = max_output_length

    def validate(self, example: TrainingExample) -> QualityMetrics:
        """
        Validate training example quality.

        Args:
            example: Training example to validate

        Returns:
            QualityMetrics with scores and issues

        Example:
            >>> metrics = validator.validate(example)
            >>> print(f"Overall score: {metrics.overall_score}/100")
        """
        metrics = QualityMetrics()

        # Validate instruction
        instruction_score, instruction_issues = self._validate_instruction(example.instruction)
        metrics.instruction_clarity = instruction_score
        metrics.issues.extend(instruction_issues)

        # Validate input
        input_score, input_issues = self._validate_input(example.input)
        metrics.input_completeness = input_score
        metrics.issues.extend(input_issues)

        # Validate output
        output_score, output_issues = self._validate_output(example.output)
        metrics.output_quality = output_score
        metrics.issues.extend(output_issues)

        # Validate metadata
        metadata_score, metadata_issues = self._validate_metadata(example.metadata)
        metrics.metadata_completeness = metadata_score
        metrics.issues.extend(metadata_issues)

        # Calculate overall score
        metrics.calculate_overall_score()

        # Generate suggestions
        metrics.suggestions = self._generate_suggestions(metrics)

        return metrics

    def _validate_instruction(self, instruction: str) -> tuple[float, List[str]]:
        """Validate instruction quality."""
        score = 100.0
        issues = []

        # Check length
        if len(instruction) < self.min_instruction_length:
            score -= 30
            issues.append(f"Instruction too short ({len(instruction)} chars, min {self.min_instruction_length})")
        elif len(instruction) > self.max_instruction_length:
            score -= 20
            issues.append(f"Instruction too long ({len(instruction)} chars, max {self.max_instruction_length})")

        # Check clarity
        if not instruction.strip():
            score -= 50
            issues.append("Instruction is empty")
        elif instruction.lower() == instruction:
            score -= 10
            issues.append("Instruction lacks proper capitalization")

        # Check for action words
        action_words = ["analyze", "fix", "remediate", "detect", "scan", "generate", "create", "review"]
        if not any(word in instruction.lower() for word in action_words):
            score -= 15
            issues.append("Instruction lacks clear action verb")

        # Check for security context
        security_words = ["security", "vulnerability", "finding", "scan", "fix", "compliance", "policy"]
        if not any(word in instruction.lower() for word in security_words):
            score -= 10
            issues.append("Instruction lacks security context")

        return max(0.0, score), issues

    def _validate_input(self, input_text: str) -> tuple[float, List[str]]:
        """Validate input completeness."""
        score = 100.0
        issues = []

        # Check if empty
        if not input_text or not input_text.strip():
            score -= 50
            issues.append("Input is empty")
            return max(0.0, score), issues

        # Check for structured data
        lines = input_text.strip().split("\n")
        if len(lines) < 3:
            score -= 20
            issues.append(f"Input lacks structure ({len(lines)} lines)")

        # Check for key fields
        common_fields = ["scanner:", "severity:", "file:", "description:", "vulnerability:"]
        found_fields = sum(1 for field in common_fields if field.lower() in input_text.lower())
        if found_fields < 2:
            score -= 15
            issues.append("Input missing common contextual fields")

        # Check for code blocks
        if "```" in input_text:
            # Verify code blocks are closed
            code_blocks = input_text.count("```")
            if code_blocks % 2 != 0:
                score -= 25
                issues.append("Unclosed code block in input")

        return max(0.0, score), issues

    def _validate_output(self, output: str) -> tuple[float, List[str]]:
        """Validate output quality."""
        score = 100.0
        issues = []

        # Check length
        if len(output) < self.min_output_length:
            score -= 40
            issues.append(f"Output too short ({len(output)} chars, min {self.min_output_length})")
        elif len(output) > self.max_output_length:
            score -= 15
            issues.append(f"Output very long ({len(output)} chars, max {self.max_output_length})")

        # Check for structure
        if not output.strip():
            score -= 50
            issues.append("Output is empty")
            return max(0.0, score), issues

        # Check for markdown headers
        if not re.search(r'^#+\s+\w+', output, re.MULTILINE):
            score -= 10
            issues.append("Output lacks markdown structure")

        # Check for code blocks
        code_blocks = output.count("```")
        if code_blocks > 0:
            if code_blocks % 2 != 0:
                score -= 30
                issues.append("Unclosed code block in output")
            else:
                # Bonus for well-formatted code examples
                score = min(100.0, score + 5)

        # Check for explanation/reasoning
        reasoning_words = ["because", "since", "therefore", "this means", "explanation", "reason"]
        if not any(word in output.lower() for word in reasoning_words):
            score -= 15
            issues.append("Output lacks explanation/reasoning")

        # Check for actionable steps
        if re.search(r'^\d+\.\s+', output, re.MULTILINE):
            # Bonus for numbered steps
            score = min(100.0, score + 5)
        elif not re.search(r'^[-*]\s+', output, re.MULTILINE):
            score -= 10
            issues.append("Output lacks actionable steps (bullets/numbers)")

        # Check for security best practices
        best_practice_words = ["secure", "recommended", "best practice", "validation", "verify"]
        if not any(word in output.lower() for word in best_practice_words):
            score -= 10
            issues.append("Output lacks security best practices")

        return max(0.0, score), issues

    def _validate_metadata(self, metadata: Dict[str, Any]) -> tuple[float, List[str]]:
        """Validate metadata completeness."""
        score = 100.0
        issues = []

        # Required fields
        required_fields = ["domain", "task_type", "skill_level"]
        missing_fields = [f for f in required_fields if f not in metadata]

        if missing_fields:
            score -= 30 * len(missing_fields)
            issues.append(f"Missing metadata fields: {', '.join(missing_fields)}")

        # Optional but recommended fields
        recommended_fields = ["created_at", "template", "confidence"]
        missing_recommended = [f for f in recommended_fields if f not in metadata]

        if missing_recommended:
            score -= 5 * len(missing_recommended)
            # Don't add issue for missing recommended fields

        # Validate skill_level value
        if "skill_level" in metadata:
            valid_levels = ["E-rank", "D-rank", "C-rank", "B-rank", "A-rank", "S-rank"]
            if metadata["skill_level"] not in valid_levels:
                score -= 15
                issues.append(f"Invalid skill_level: {metadata['skill_level']}")

        return max(0.0, score), issues

    def _generate_suggestions(self, metrics: QualityMetrics) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if metrics.instruction_clarity < 70:
            suggestions.append("Improve instruction clarity: Use clear action verbs and security context")

        if metrics.input_completeness < 70:
            suggestions.append("Add more context to input: Include scanner, severity, file paths, etc.")

        if metrics.output_quality < 70:
            suggestions.append("Improve output quality: Add markdown structure, code examples, and reasoning")

        if metrics.metadata_completeness < 70:
            suggestions.append("Complete metadata: Ensure domain, task_type, and skill_level are set")

        if metrics.overall_score < 50:
            suggestions.append("CRITICAL: Example quality is poor - consider regenerating from template")

        return suggestions

    def batch_validate(
        self,
        examples: List[TrainingExample],
        min_quality_score: float = 50.0
    ) -> Dict[str, Any]:
        """
        Validate a batch of examples.

        Args:
            examples: List of training examples
            min_quality_score: Minimum acceptable score

        Returns:
            Validation summary with stats and filtered examples

        Example:
            >>> result = validator.batch_validate(examples, min_quality_score=70.0)
            >>> print(f"Passed: {len(result['passed'])}/{len(examples)}")
        """
        results = {
            "total": len(examples),
            "passed": [],
            "failed": [],
            "by_quality": {
                "excellent": [],
                "good": [],
                "acceptable": [],
                "poor": []
            },
            "stats": {
                "avg_score": 0.0,
                "pass_rate": 0.0,
                "excellent_rate": 0.0
            }
        }

        total_score = 0.0

        for example in examples:
            metrics = self.validate(example)
            total_score += metrics.overall_score

            # Add to quality buckets
            results["by_quality"][metrics.quality_level.value].append({
                "example": example,
                "metrics": metrics
            })

            # Pass/fail
            if metrics.overall_score >= min_quality_score:
                results["passed"].append({
                    "example": example,
                    "metrics": metrics
                })
            else:
                results["failed"].append({
                    "example": example,
                    "metrics": metrics,
                    "issues": metrics.issues
                })

        # Calculate stats
        results["stats"]["avg_score"] = total_score / len(examples) if examples else 0.0
        results["stats"]["pass_rate"] = len(results["passed"]) / len(examples) * 100 if examples else 0.0
        results["stats"]["excellent_rate"] = len(results["by_quality"]["excellent"]) / len(examples) * 100 if examples else 0.0

        return results


def validate_training_file(file_path: str, min_quality_score: float = 50.0) -> Dict[str, Any]:
    """
    Validate all examples in a training file.

    Args:
        file_path: Path to JSONL training file
        min_quality_score: Minimum acceptable score

    Returns:
        Validation summary

    Example:
        >>> result = validate_training_file("training.jsonl", min_quality_score=70.0)
        >>> print(f"Pass rate: {result['stats']['pass_rate']:.1f}%")
    """
    import json
    from pathlib import Path

    examples = []
    file = Path(file_path)

    if not file.exists():
        raise FileNotFoundError(f"Training file not found: {file_path}")

    with open(file) as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    example = TrainingExample(
                        instruction=data.get("instruction", ""),
                        input=data.get("input", ""),
                        output=data.get("output", ""),
                        metadata=data.get("metadata", {})
                    )
                    examples.append(example)
                except json.JSONDecodeError:
                    continue

    validator = QualityValidator()
    return validator.batch_validate(examples, min_quality_score)


__all__ = [
    "QualityValidator",
    "validate_training_file"
]
