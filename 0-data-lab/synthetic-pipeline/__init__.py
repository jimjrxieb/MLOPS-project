"""
JADE Training Scenarios

Automated training data generation from operational security workflows.

This module provides:
- Scenario templates for different security tasks
- Training data generator from operational logs
- Quality validation for training examples
- End-to-end pipeline orchestration

Usage:
    # Quick start - run full pipeline
    >>> from training_scenarios import TrainingPipeline
    >>> pipeline = TrainingPipeline()
    >>> result = pipeline.run_full_pipeline()
    >>> print(f"Generated {result['total_examples']} examples")

    # Generate from specific instance
    >>> result = pipeline.run_for_instance("02-instance")

    # Generate from single slot
    >>> from training_scenarios import TrainingGenerator
    >>> generator = TrainingGenerator()
    >>> batch = generator.generate_from_slot("02-instance", "slot-2")
    >>> generator.save_batch(batch, Path("training.jsonl"))

    # Validate quality
    >>> from training_scenarios import validate_training_file
    >>> result = validate_training_file("training.jsonl", min_quality_score=70.0)
    >>> print(f"Pass rate: {result['stats']['pass_rate']:.1f}%")

    # Use templates directly
    >>> from training_scenarios import get_template
    >>> template = get_template("trivy-scan")
    >>> example = template.generate_example({
    ...     "scanner": "trivy",
    ...     "severity": "HIGH",
    ...     "package": "lodash",
    ...     ...
    ... })
"""

from .models import (
    SkillLevel,
    TaskType,
    Domain,
    ExampleQuality,
    TrainingExample,
    ScenarioTemplate,
    QualityMetrics,
    TrainingBatch,
    GenerationConfig
)

from .templates import (
    TEMPLATE_REGISTRY,
    get_template,
    list_templates,
    get_templates_by_domain,
    get_templates_by_skill_level
)

from .generator import TrainingGenerator

from .quality_validator import (
    QualityValidator,
    validate_training_file
)

from .pipeline import (
    TrainingPipeline,
    run_pipeline_cli
)


__all__ = [
    # Models
    "SkillLevel",
    "TaskType",
    "Domain",
    "ExampleQuality",
    "TrainingExample",
    "ScenarioTemplate",
    "QualityMetrics",
    "TrainingBatch",
    "GenerationConfig",

    # Templates
    "TEMPLATE_REGISTRY",
    "get_template",
    "list_templates",
    "get_templates_by_domain",
    "get_templates_by_skill_level",

    # Generator
    "TrainingGenerator",

    # Validator
    "QualityValidator",
    "validate_training_file",

    # Pipeline
    "TrainingPipeline",
    "run_pipeline_cli",
]

__version__ = "1.0.0"
