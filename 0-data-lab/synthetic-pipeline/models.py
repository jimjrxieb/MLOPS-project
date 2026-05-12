"""
Training Scenario Models

Data models for training scenario generation and validation.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class SkillLevel(str, Enum):
    """Skill level classification for training examples."""
    E_RANK = "E-rank"  # 95-100% automation (hardcoded secrets, missing limits)
    D_RANK = "D-rank"  # 70-90% automation (SQL injection, XSS, CVEs)
    C_RANK = "C-rank"  # 40-70% automation (network policies, multi-file IaC)
    B_RANK = "B-rank"  # 20-40% automation (architecture changes)
    A_RANK = "A-rank"  # 5-20% automation (org-wide policy)
    S_RANK = "S-rank"  # 0-5% automation (zero-trust architecture)


class TaskType(str, Enum):
    """Type of security task."""
    SCAN_ANALYSIS = "scan-analysis"
    VULNERABILITY_TRIAGE = "vulnerability-triage"
    FIX_EXECUTION = "fix-execution"
    ESCALATION_DECISION = "escalation-decision"
    APPROVAL_WORKFLOW = "approval-workflow"
    REPORT_GENERATION = "report-generation"
    POLICY_CREATION = "policy-creation"
    ARCHITECTURE_DESIGN = "architecture-design"
    INCIDENT_RESPONSE = "incident-response"


class Domain(str, Enum):
    """Security domain."""
    SECRETS = "secrets"
    SAST = "sast"
    DEPENDENCIES = "dependencies"
    KUBERNETES = "kubernetes"
    IAC = "iac"
    CLOUD = "cloud"
    NETWORK = "network"
    COMPLIANCE = "compliance"
    GENERAL = "general"


class ExampleQuality(str, Enum):
    """Training example quality level."""
    EXCELLENT = "excellent"  # 90-100% quality score
    GOOD = "good"            # 70-89% quality score
    ACCEPTABLE = "acceptable"  # 50-69% quality score
    POOR = "poor"            # <50% quality score


@dataclass
class TrainingExample:
    """
    A single training example for JADE fine-tuning.

    Format follows Alpaca/ChatML structure:
    - instruction: What to do
    - input: Context/constraints
    - output: How to do it with reasoning
    """
    instruction: str
    input: str
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure metadata has required fields."""
        if "domain" not in self.metadata:
            self.metadata["domain"] = Domain.GENERAL.value
        if "task_type" not in self.metadata:
            self.metadata["task_type"] = TaskType.SCAN_ANALYSIS.value
        if "skill_level" not in self.metadata:
            self.metadata["skill_level"] = SkillLevel.D_RANK.value
        if "created_at" not in self.metadata:
            self.metadata["created_at"] = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_alpaca(self) -> Dict[str, str]:
        """Convert to Alpaca format (instruction, input, output only)."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output
        }

    def to_chatml(self) -> List[Dict[str, str]]:
        """Convert to ChatML format (messages array)."""
        return [
            {"role": "system", "content": "You are JADE, a DevSecOps security expert."},
            {"role": "user", "content": f"{self.instruction}\n\n{self.input}"},
            {"role": "assistant", "content": self.output}
        ]


@dataclass
class ScenarioTemplate:
    """
    Template for generating training scenarios.

    Templates define the structure for converting operational data
    into training examples.
    """
    name: str
    description: str
    domain: Domain
    task_type: TaskType
    skill_level: SkillLevel
    instruction_template: str
    input_template: str
    output_template: str
    required_fields: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def generate_example(self, data: Dict[str, Any]) -> TrainingExample:
        """
        Generate training example from operational data.

        Args:
            data: Operational data matching required_fields

        Returns:
            TrainingExample

        Example:
            >>> template = ScenarioTemplate(...)
            >>> data = {"scanner": "trivy", "severity": "HIGH", ...}
            >>> example = template.generate_example(data)
        """
        # Validate required fields
        missing = [f for f in self.required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Fill templates
        instruction = self.instruction_template.format(**data)
        input_text = self.input_template.format(**data)
        output_text = self.output_template.format(**data)

        # Create example
        return TrainingExample(
            instruction=instruction,
            input=input_text,
            output=output_text,
            metadata={
                "domain": self.domain.value,
                "task_type": self.task_type.value,
                "skill_level": self.skill_level.value,
                "template": self.name,
                "source_data": data
            }
        )


@dataclass
class QualityMetrics:
    """
    Quality metrics for training example validation.

    Scores range from 0-100.
    """
    instruction_clarity: float = 0.0
    input_completeness: float = 0.0
    output_quality: float = 0.0
    metadata_completeness: float = 0.0
    overall_score: float = 0.0
    quality_level: ExampleQuality = ExampleQuality.POOR

    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def calculate_overall_score(self):
        """Calculate overall quality score."""
        self.overall_score = (
            self.instruction_clarity * 0.25 +
            self.input_completeness * 0.25 +
            self.output_quality * 0.35 +
            self.metadata_completeness * 0.15
        )

        # Set quality level
        if self.overall_score >= 90:
            self.quality_level = ExampleQuality.EXCELLENT
        elif self.overall_score >= 70:
            self.quality_level = ExampleQuality.GOOD
        elif self.overall_score >= 50:
            self.quality_level = ExampleQuality.ACCEPTABLE
        else:
            self.quality_level = ExampleQuality.POOR

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrainingBatch:
    """
    A batch of training examples.

    Used for organizing and tracking training data generation.
    """
    batch_id: str
    examples: List[TrainingExample] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_example(self, example: TrainingExample):
        """Add example to batch."""
        self.examples.append(example)

    def get_stats(self) -> Dict[str, Any]:
        """Get batch statistics."""
        stats = {
            "batch_id": self.batch_id,
            "total_examples": len(self.examples),
            "by_domain": {},
            "by_task_type": {},
            "by_skill_level": {},
            "created_at": self.created_at.isoformat()
        }

        # Count by domain
        for example in self.examples:
            domain = example.metadata.get("domain", "unknown")
            stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1

        # Count by task type
        for example in self.examples:
            task_type = example.metadata.get("task_type", "unknown")
            stats["by_task_type"][task_type] = stats["by_task_type"].get(task_type, 0) + 1

        # Count by skill level
        for example in self.examples:
            skill_level = example.metadata.get("skill_level", "unknown")
            stats["by_skill_level"][skill_level] = stats["by_skill_level"].get(skill_level, 0) + 1

        return stats

    def to_jsonl(self) -> str:
        """Convert batch to JSONL format."""
        import json
        lines = []
        for example in self.examples:
            lines.append(json.dumps(example.to_dict()))
        return "\n".join(lines)


@dataclass
class GenerationConfig:
    """
    Configuration for training data generation.
    """
    min_quality_score: float = 50.0
    max_examples_per_batch: int = 1000
    include_metadata: bool = True
    deduplicate: bool = True
    shuffle: bool = True

    # Quality filters
    min_instruction_length: int = 10
    max_instruction_length: int = 500
    min_output_length: int = 50
    max_output_length: int = 5000

    # Skill level distribution (percentages)
    skill_distribution: Dict[str, float] = field(default_factory=lambda: {
        "E-rank": 0.05,  # 5%
        "D-rank": 0.30,  # 30%
        "C-rank": 0.40,  # 40%
        "B-rank": 0.20,  # 20%
        "A-rank": 0.04,  # 4%
        "S-rank": 0.01   # 1%
    })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


__all__ = [
    "SkillLevel",
    "TaskType",
    "Domain",
    "ExampleQuality",
    "TrainingExample",
    "ScenarioTemplate",
    "QualityMetrics",
    "TrainingBatch",
    "GenerationConfig"
]
