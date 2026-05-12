"""
Training Data Generation Pipeline

Orchestrates end-to-end training data generation from operational logs.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import GenerationConfig, TrainingBatch
from .generator import TrainingGenerator
from .quality_validator import QualityValidator, validate_training_file


class TrainingPipeline:
    """
    Orchestrate training data generation pipeline.

    The pipeline:
    1. Discovers operational data sources (scans, fixes, escalations)
    2. Generates training examples using templates
    3. Validates quality
    4. Merges batches
    5. Outputs to training corpus

    Example:
        >>> pipeline = TrainingPipeline()
        >>> pipeline.run_full_pipeline()
        >>> print(f"Generated {pipeline.total_examples} examples")
    """

    def __init__(
        self,
        config: Optional[GenerationConfig] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize pipeline.

        Args:
            config: Generation configuration
            output_dir: Output directory for training data
        """
        self.config = config or GenerationConfig()
        self.generator = TrainingGenerator(config=self.config)
        self.validator = QualityValidator()

        if output_dir is None:
            output_dir = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline/01-raw-data-lake")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self.total_examples = 0
        self.total_batches = 0
        self.stats = {}

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Run complete training data generation pipeline.

        Returns:
            Pipeline stats and summary

        Example:
            >>> result = pipeline.run_full_pipeline()
            >>> print(f"Generated {result['total_examples']} examples")
        """
        print("=" * 60)
        print("JADE Training Data Generation Pipeline")
        print("=" * 60)
        print(f"Started: {datetime.utcnow().isoformat()}")
        print()

        # Discover instances and slots
        print("Phase 1: Discovering operational data sources...")
        sources = self._discover_sources()
        print(f"Found {len(sources)} slots with operational data")
        print()

        # Generate examples from each source
        print("Phase 2: Generating training examples...")
        all_batches = []

        for source in sources:
            instance = source["instance"]
            slot = source["slot"]
            print(f"  Processing {instance}/{slot}...", end=" ")

            try:
                batch = self.generator.generate_from_slot(instance, slot)
                all_batches.append(batch)
                print(f"✓ {len(batch.examples)} examples")
            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        print()

        # Merge batches
        print("Phase 3: Merging batches...")
        merged_batch = self._merge_batches(all_batches)
        print(f"Total examples: {len(merged_batch.examples)}")
        print()

        # Validate quality
        print("Phase 4: Validating quality...")
        validation_result = self._validate_batch(merged_batch)
        print(f"  Pass rate: {validation_result['stats']['pass_rate']:.1f}%")
        print(f"  Avg score: {validation_result['stats']['avg_score']:.1f}/100")
        print(f"  Excellent: {len(validation_result['by_quality']['excellent'])}")
        print(f"  Good: {len(validation_result['by_quality']['good'])}")
        print(f"  Acceptable: {len(validation_result['by_quality']['acceptable'])}")
        print(f"  Poor: {len(validation_result['by_quality']['poor'])}")
        print()

        # Filter to passing examples
        passing_batch = TrainingBatch(
            batch_id=f"training_pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            examples=[item["example"] for item in validation_result["passed"]]
        )

        # Save output
        print("Phase 5: Saving training data...")
        output_file = self._save_output(passing_batch)
        print(f"  Saved to: {output_file}")
        print()

        # Generate summary
        print("=" * 60)
        print("Pipeline Complete")
        print("=" * 60)

        summary = {
            "total_examples": len(passing_batch.examples),
            "total_batches": len(all_batches),
            "output_file": str(output_file),
            "quality_stats": validation_result["stats"],
            "batch_stats": passing_batch.get_stats(),
            "completed_at": datetime.utcnow().isoformat()
        }

        self.total_examples = summary["total_examples"]
        self.total_batches = summary["total_batches"]
        self.stats = summary

        return summary

    def run_for_instance(self, instance: str) -> Dict[str, Any]:
        """
        Run pipeline for a specific instance.

        Args:
            instance: Instance ID (e.g., "02-instance")

        Returns:
            Pipeline stats

        Example:
            >>> result = pipeline.run_for_instance("02-instance")
        """
        print(f"Running pipeline for {instance}...")

        # Discover slots in instance
        sources = self._discover_sources(instance_filter=instance)

        if not sources:
            print(f"No operational data found for {instance}")
            return {"total_examples": 0}

        # Generate from all slots
        batches = []
        for source in sources:
            batch = self.generator.generate_from_slot(source["instance"], source["slot"])
            batches.append(batch)

        # Merge and save
        merged = self._merge_batches(batches)
        output_file = self._save_output(merged, prefix=f"{instance}_")

        return {
            "instance": instance,
            "total_examples": len(merged.examples),
            "output_file": str(output_file),
            "batch_stats": merged.get_stats()
        }

    def _discover_sources(self, instance_filter: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Discover instances and slots with operational data.

        Looks for JSA finding data in two locations:
        1. GP-PROJECTS/{instance}/{slot}/jsa/inbox/ — finding JSON files
        2. GP-PROJECTS/{instance}/{slot}/workflow/ — workflow state (legacy)

        Args:
            instance_filter: Optional instance ID to filter by

        Returns:
            List of {"instance": ..., "slot": ..., "path": ..., "findings_count": ...} dicts
        """
        projects_path = Path("/home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS")
        sources = []

        for instance_path in sorted(projects_path.glob("*-instance")):
            instance = instance_path.name

            if instance_filter and instance != instance_filter:
                continue

            for slot_path in sorted(instance_path.glob("slot-*")):
                slot = slot_path.name

                # Check for JSA inbox (primary — real finding data)
                jsa_inbox = slot_path / "jsa" / "inbox"
                if jsa_inbox.exists():
                    findings = list(jsa_inbox.glob("*.json"))
                    if findings:
                        sources.append({
                            "instance": instance,
                            "slot": slot,
                            "path": str(slot_path),
                            "jsa_inbox": str(jsa_inbox),
                            "findings_count": len(findings),
                        })
                        continue

                # Fallback: check for workflow dir (legacy)
                workflow_path = slot_path / "workflow"
                if workflow_path.exists():
                    sources.append({
                        "instance": instance,
                        "slot": slot,
                        "path": str(slot_path),
                        "findings_count": 0,
                    })

        return sources

    def _merge_batches(self, batches: List[TrainingBatch]) -> TrainingBatch:
        """Merge multiple batches into one."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        merged = TrainingBatch(batch_id=f"merged_{timestamp}")

        for batch in batches:
            merged.examples.extend(batch.examples)

        # Deduplicate if configured
        if self.config.deduplicate:
            seen = set()
            deduplicated = []
            for example in merged.examples:
                content_hash = hash(example.instruction + example.input)
                if content_hash not in seen:
                    seen.add(content_hash)
                    deduplicated.append(example)
            merged.examples = deduplicated

        # Shuffle if configured
        if self.config.shuffle:
            import random
            random.shuffle(merged.examples)

        return merged

    def _validate_batch(self, batch: TrainingBatch) -> Dict[str, Any]:
        """Validate batch quality."""
        return self.validator.batch_validate(
            batch.examples,
            min_quality_score=self.config.min_quality_score
        )

    def _save_output(self, batch: TrainingBatch, prefix: str = "") -> Path:
        """Save training batch to output directory."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}training_{timestamp}.jsonl"
        output_file = self.output_dir / filename

        # Save JSONL
        with open(output_file, 'w') as f:
            for example in batch.examples:
                f.write(json.dumps(example.to_dict()) + "\n")

        # Save stats
        stats_file = output_file.with_suffix(".stats.json")
        with open(stats_file, 'w') as f:
            json.dump(batch.get_stats(), f, indent=2)

        # Save summary report
        report_file = output_file.with_suffix(".report.md")
        self._generate_report(batch, report_file)

        return output_file

    def _generate_report(self, batch: TrainingBatch, output_file: Path):
        """Generate markdown report for batch."""
        stats = batch.get_stats()

        report = f"""# Training Data Generation Report

**Batch ID:** {batch.batch_id}
**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Total Examples:** {stats['total_examples']}

## Distribution

### By Domain
{self._format_dict_table(stats['by_domain'])}

### By Task Type
{self._format_dict_table(stats['by_task_type'])}

### By Skill Level
{self._format_dict_table(stats['by_skill_level'])}

## Quality Metrics

Run quality validation:
```bash
python3 -m quality_validator {output_file.with_suffix('.jsonl')}
```

## Next Steps

1. Review training data for quality
2. Merge with existing training corpus
3. Run fine-tuning pipeline

## Files Generated

- Training data: `{output_file.with_suffix('.jsonl').name}`
- Statistics: `{output_file.with_suffix('.stats.json').name}`
- This report: `{output_file.name}`

---
*Generated by JADE Training Pipeline v1.0*
"""

        with open(output_file, 'w') as f:
            f.write(report)

    def _format_dict_table(self, data: Dict[str, int]) -> str:
        """Format dictionary as markdown table."""
        if not data:
            return "No data"

        lines = ["| Category | Count |", "|----------|-------|"]
        for key, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {key} | {value} |")
        return "\n".join(lines)


def run_pipeline_cli():
    """Run pipeline from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="JADE Training Data Generation Pipeline")
    parser.add_argument("--instance", help="Specific instance to process")
    parser.add_argument("--min-quality", type=float, default=50.0, help="Minimum quality score")
    parser.add_argument("--max-examples", type=int, default=1000, help="Max examples per batch")
    parser.add_argument("--output-dir", help="Output directory")

    args = parser.parse_args()

    # Create config
    config = GenerationConfig(
        min_quality_score=args.min_quality,
        max_examples_per_batch=args.max_examples
    )

    # Create pipeline
    output_dir = Path(args.output_dir) if args.output_dir else None
    pipeline = TrainingPipeline(config=config, output_dir=output_dir)

    # Run pipeline
    if args.instance:
        result = pipeline.run_for_instance(args.instance)
    else:
        result = pipeline.run_full_pipeline()

    # Print summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_pipeline_cli()


__all__ = [
    "TrainingPipeline",
    "run_pipeline_cli"
]
