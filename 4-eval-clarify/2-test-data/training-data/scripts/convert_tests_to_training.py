#!/usr/bin/env python3
"""
Convert existing test files to training data format.
Processes: agent_scenarios.jsonl, log_diagnosis_tests.jsonl, tool_use_tests.jsonl
"""

import json
from datetime import datetime
from pathlib import Path

FAULTY_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-GP-CLARIFY/2-test-data/training-data/faulty-examples")
OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE/00-processed/benchmark-training")


def convert_log_diagnosis(test: dict) -> dict:
    """Convert log diagnosis test to training format."""
    return {
        "instruction": test["question"],
        "input": f"""Category: {test['category']}
Severity: {test['severity'].upper()}
Log: {test['log_snippet']}""",
        "output": f"""**Diagnosis:** {test['expected_diagnosis']}

**Fix Type:** {test['expected_fix_type']}

**Required Actions:**
{chr(10).join(f"- {action}" for action in test['expected_actions'])}

**Recommended Tools:** {', '.join(test.get('expected_npcs', ['Manual review']))}"""
    }


def convert_agent_scenario(test: dict) -> dict:
    """Convert agent scenario test to training format."""
    context_str = "\n".join(f"- {k}: {v}" for k, v in test['context'].items())
    steps_str = "\n".join(test['expected_steps'])

    return {
        "instruction": f"As a security agent, handle this scenario: {test['scenario']}",
        "input": f"""Scenario Type: {test['type']}
Context:
{context_str}""",
        "output": f"""**Execution Plan:**

{steps_str}

**Success Criteria:** {test['success_criteria']}
**Tool Budget:** {test['max_tool_calls']} tool calls maximum"""
    }


def convert_tool_use(test: dict) -> dict:
    """Convert tool use test to training format."""
    return {
        "instruction": test.get("task", "Complete this security task"),
        "input": test.get("input", ""),
        "output": test.get("expected_output", test.get("expected_tools", ""))
    }


def load_and_convert(filepath: Path, converter_func) -> list:
    """Load JSONL file and convert each entry."""
    results = []
    with open(filepath) as f:
        for line in f:
            if line.strip():
                test = json.loads(line)
                results.append(converter_func(test))
    return results


def main():
    print("=" * 60)
    print("Converting Test Files to Training Data")
    print("=" * 60)

    all_examples = []

    # Convert log diagnosis tests
    log_diag_path = FAULTY_DIR / "log_diagnosis_tests.jsonl"
    if log_diag_path.exists():
        print(f"\n[1/3] Converting {log_diag_path.name}...")
        examples = load_and_convert(log_diag_path, convert_log_diagnosis)
        all_examples.extend(examples)
        print(f"  ✓ {len(examples)} log diagnosis examples")

    # Convert agent scenarios
    agent_path = FAULTY_DIR / "agent_scenarios.jsonl"
    if agent_path.exists():
        print(f"\n[2/3] Converting {agent_path.name}...")
        examples = load_and_convert(agent_path, convert_agent_scenario)
        all_examples.extend(examples)
        print(f"  ✓ {len(examples)} agent scenario examples")

    # Convert tool use tests
    tool_path = FAULTY_DIR / "tool_use_tests.jsonl"
    if tool_path.exists():
        print(f"\n[3/3] Converting {tool_path.name}...")
        try:
            examples = load_and_convert(tool_path, convert_tool_use)
            all_examples.extend(examples)
            print(f"  ✓ {len(examples)} tool use examples")
        except Exception as e:
            print(f"  ⚠ Skipped tool_use_tests.jsonl: {e}")

    # Save output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"converted_tests_{timestamp}.jsonl"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')

    summary = {
        "timestamp": timestamp,
        "total_examples": len(all_examples),
        "source_files": [
            "log_diagnosis_tests.jsonl",
            "agent_scenarios.jsonl",
            "tool_use_tests.jsonl"
        ],
        "output_file": str(output_file)
    }

    summary_file = output_file.with_suffix('.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"✓ Converted {len(all_examples)} test examples to training format")
    print(f"✓ Saved to: {output_file}")


if __name__ == "__main__":
    main()
