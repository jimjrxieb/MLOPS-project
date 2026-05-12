#!/usr/bin/env python3
"""
Training Scenarios - Usage Examples

Demonstrates how to use the JADE training scenarios system.
"""

from pathlib import Path
from training_scenarios import (
    TrainingPipeline,
    TrainingGenerator,
    GenerationConfig,
    get_template,
    list_templates,
    validate_training_file
)


def example_1_run_full_pipeline():
    """
    Example 1: Run full pipeline to generate training data from all instances.
    """
    print("=" * 60)
    print("Example 1: Run Full Pipeline")
    print("=" * 60)

    pipeline = TrainingPipeline()
    result = pipeline.run_full_pipeline()

    print(f"\nResults:")
    print(f"  Total examples: {result['total_examples']}")
    print(f"  Pass rate: {result['quality_stats']['pass_rate']:.1f}%")
    print(f"  Output file: {result['output_file']}")


def example_2_generate_from_instance():
    """
    Example 2: Generate training data from specific instance.
    """
    print("\n" + "=" * 60)
    print("Example 2: Generate from Specific Instance")
    print("=" * 60)

    config = GenerationConfig(
        min_quality_score=70.0,
        max_examples_per_batch=500
    )

    pipeline = TrainingPipeline(config=config)
    result = pipeline.run_for_instance("02-instance")

    print(f"\nResults:")
    print(f"  Instance: {result.get('instance', 'N/A')}")
    print(f"  Total examples: {result['total_examples']}")


def example_3_generate_from_slot():
    """
    Example 3: Generate from single slot using generator.
    """
    print("\n" + "=" * 60)
    print("Example 3: Generate from Single Slot")
    print("=" * 60)

    generator = TrainingGenerator()
    batch = generator.generate_from_slot("02-instance", "slot-2")

    print(f"\nGenerated {len(batch.examples)} examples")
    print(f"\nBatch statistics:")
    stats = batch.get_stats()
    print(f"  By domain: {stats['by_domain']}")
    print(f"  By skill level: {stats['by_skill_level']}")

    # Save batch
    output_path = Path("/tmp/training_example.jsonl")
    generator.save_batch(batch, output_path)
    print(f"\nSaved to: {output_path}")


def example_4_use_templates():
    """
    Example 4: Use templates to generate examples from custom data.
    """
    print("\n" + "=" * 60)
    print("Example 4: Use Templates Directly")
    print("=" * 60)

    # List available templates
    print("\nAvailable templates:")
    for name in list_templates():
        print(f"  - {name}")

    # Use Trivy scan template
    print("\nUsing trivy-scan template...")
    template = get_template("trivy-scan")

    data = {
        "scanner": "trivy",
        "severity": "HIGH",
        "package": "lodash",
        "vulnerability_id": "CVE-2024-1234",
        "current_version": "4.17.0",
        "fixed_version": "4.17.21",
        "description": "Prototype pollution vulnerability allowing arbitrary code execution",
        "action": "UPGRADE",
        "fix_command": "npm update lodash@4.17.21",
        "rank": "D",
        "rank_justification": "Automated dependency upgrade with 85% confidence"
    }

    example = template.generate_example(data)

    print(f"\nGenerated example:")
    print(f"  Instruction: {example.instruction[:80]}...")
    print(f"  Skill level: {example.metadata['skill_level']}")
    print(f"  Domain: {example.metadata['domain']}")


def example_5_validate_quality():
    """
    Example 5: Validate training file quality.
    """
    print("\n" + "=" * 60)
    print("Example 5: Validate Training File Quality")
    print("=" * 60)

    # First generate a small batch
    generator = TrainingGenerator()
    batch = generator.generate_from_slot("02-instance", "slot-2")

    # Save to temp file
    test_file = Path("/tmp/test_training.jsonl")
    generator.save_batch(batch, test_file)

    # Validate
    if test_file.exists():
        result = validate_training_file(str(test_file), min_quality_score=70.0)

        print(f"\nValidation Results:")
        print(f"  Total examples: {result['total']}")
        print(f"  Passed: {len(result['passed'])} ({result['stats']['pass_rate']:.1f}%)")
        print(f"  Failed: {len(result['failed'])}")
        print(f"  Avg score: {result['stats']['avg_score']:.1f}/100")

        print(f"\nQuality distribution:")
        for level, items in result['by_quality'].items():
            print(f"  {level}: {len(items)}")

        # Show first failed example issues
        if result['failed']:
            print(f"\nFirst failed example issues:")
            first_failed = result['failed'][0]
            for issue in first_failed['metrics'].issues[:3]:
                print(f"  - {issue}")
    else:
        print("No test file found - run example 3 first")


def example_6_custom_config():
    """
    Example 6: Use custom generation configuration.
    """
    print("\n" + "=" * 60)
    print("Example 6: Custom Configuration")
    print("=" * 60)

    config = GenerationConfig(
        min_quality_score=80.0,           # Higher quality threshold
        max_examples_per_batch=100,       # Smaller batches
        include_metadata=True,
        deduplicate=True,
        shuffle=True,
        min_instruction_length=20,        # Longer instructions
        min_output_length=100,            # Longer outputs
        skill_distribution={               # Custom skill distribution
            "E-rank": 0.10,  # 10%
            "D-rank": 0.40,  # 40%
            "C-rank": 0.30,  # 30%
            "B-rank": 0.15,  # 15%
            "A-rank": 0.04,  # 4%
            "S-rank": 0.01   # 1%
        }
    )

    pipeline = TrainingPipeline(config=config)

    print(f"\nConfiguration:")
    print(f"  Min quality: {config.min_quality_score}")
    print(f"  Max batch size: {config.max_examples_per_batch}")
    print(f"  Skill distribution: {config.skill_distribution}")

    # Run for single instance with custom config
    # result = pipeline.run_for_instance("02-instance")
    # print(f"\nGenerated {result['total_examples']} high-quality examples")


def main():
    """Run all examples."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     JADE Training Scenarios - Usage Examples              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    try:
        # Run examples
        example_4_use_templates()
        example_3_generate_from_slot()
        example_5_validate_quality()
        example_6_custom_config()

        # Uncomment to run full pipeline examples (takes longer)
        # example_2_generate_from_instance()
        # example_1_run_full_pipeline()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Review generated files in /tmp/")
        print("  2. Run full pipeline: python3 -m pipeline")
        print("  3. Integrate with training corpus")
        print()

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
