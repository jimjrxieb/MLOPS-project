#!/usr/bin/env python3
"""
Kubernetes Failure Training Data Generator

Generates JADE training data from K8s operational playbooks.
Parses the YAML playbooks to create instruction-output pairs
covering troubleshooting, diagnosis, and remediation.

Usage:
    python generate_k8s_training_data.py --playbooks-dir ../jade-knowledge/k8s-playbooks
    python generate_k8s_training_data.py --output k8s-failures-training.jsonl
    python generate_k8s_training_data.py --stats
"""

import argparse
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Generator, Optional
from dataclasses import dataclass
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default paths
SCRIPT_DIR = Path(__file__).parent
DEFAULT_PLAYBOOKS_DIR = SCRIPT_DIR.parent / "jade-knowledge" / "k8s-playbooks"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "training-data"


@dataclass
class PlaybookData:
    """Parsed playbook data."""
    name: str
    category: str
    severity: str
    frequency: str
    trigger_patterns: List[str]
    description: str
    gameplan: Dict[str, Any]
    common_auto_fixes: List[Dict]
    escalation_triggers: List[Dict]
    related_playbooks: List[str]
    raw_yaml: Dict


class PlaybookParser:
    """Parse K8s operational playbooks from YAML files."""

    def __init__(self, playbooks_dir: Path):
        self.playbooks_dir = playbooks_dir

    def find_playbooks(self) -> List[Path]:
        """Find all YAML playbook files."""
        playbooks = []
        for yaml_file in self.playbooks_dir.rglob("*.yaml"):
            # Skip non-playbook files
            if yaml_file.name.startswith("."):
                continue
            playbooks.append(yaml_file)
        return sorted(playbooks)

    def parse_playbook(self, path: Path) -> Optional[PlaybookData]:
        """Parse a single playbook YAML file."""
        try:
            with open(path, "r") as f:
                raw = yaml.safe_load(f)

            if not raw:
                return None

            return PlaybookData(
                name=raw.get("name", path.stem),
                category=raw.get("category", "unknown"),
                severity=raw.get("severity", "MEDIUM"),
                frequency=raw.get("frequency", "COMMON"),
                trigger_patterns=raw.get("trigger_patterns", []),
                description=raw.get("description", ""),
                gameplan=raw.get("gameplan", {}),
                common_auto_fixes=raw.get("common_auto_fixes", []),
                escalation_triggers=raw.get("escalation_triggers", []),
                related_playbooks=raw.get("related_playbooks", []),
                raw_yaml=raw
            )

        except Exception as e:
            logger.warning(f"Failed to parse {path}: {e}")
            return None

    def parse_all(self) -> Generator[PlaybookData, None, None]:
        """Parse all playbooks in directory."""
        playbook_files = self.find_playbooks()
        logger.info(f"Found {len(playbook_files)} playbook files")

        for path in playbook_files:
            playbook = self.parse_playbook(path)
            if playbook:
                yield playbook


class K8sTrainingDataGenerator:
    """Generate training data from K8s playbooks."""

    # Map severity/frequency to rank
    SEVERITY_RANK = {
        "CRITICAL": "C",
        "HIGH": "C",
        "MEDIUM": "D",
        "LOW": "E"
    }

    def __init__(self, playbooks_dir: Path, output_dir: Path):
        self.playbooks_dir = playbooks_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = PlaybookParser(playbooks_dir)

    def generate_training_pairs(self, playbook: PlaybookData) -> List[Dict[str, Any]]:
        """Generate multiple training pairs from a playbook."""
        pairs = []
        name = playbook.name.replace("-", " ").replace("_", " ").title()

        # Pair 1: What does this error mean?
        pairs.append({
            "instruction": f"What does Kubernetes error '{name}' mean?",
            "input": "",
            "output": playbook.description.strip()
        })

        # Pair 2: How to debug this error?
        debug_output = self._generate_debug_instructions(playbook)
        pairs.append({
            "instruction": f"How do I debug a pod in {name} state?",
            "input": "",
            "output": debug_output
        })

        # Pair 3: What triggers this error?
        if playbook.trigger_patterns:
            triggers = ", ".join(f'"{p}"' for p in playbook.trigger_patterns[:5])
            pairs.append({
                "instruction": f"What error messages indicate {name}?",
                "input": "",
                "output": f"Look for these patterns in kubectl output or events: {triggers}"
            })

        # Pair 4: Step-by-step troubleshooting
        steps_output = self._generate_gameplan_steps(playbook)
        if steps_output:
            pairs.append({
                "instruction": f"Walk me through troubleshooting {name} step by step.",
                "input": "",
                "output": steps_output
            })

        # Pair 5: Auto-fixes for this error
        for auto_fix in playbook.common_auto_fixes[:3]:
            fix_id = auto_fix.get("id", "unknown")
            trigger = auto_fix.get("trigger", "")
            action = auto_fix.get("action", "")
            rank = auto_fix.get("rank", "D")

            pairs.append({
                "instruction": f"Can {name} be automatically fixed?",
                "input": f"Finding trigger: {trigger}",
                "output": f"Yes, this can be auto-fixed with {rank}-rank action '{action}'. The fix ID is {fix_id}."
            })

        # Pair 6: When to escalate
        for escalation in playbook.escalation_triggers[:2]:
            condition = escalation.get("condition", "")
            escalate_to = escalation.get("escalate_to", "JADE")
            reason = escalation.get("reason", "")

            pairs.append({
                "instruction": f"When should I escalate a {name} issue?",
                "input": f"Condition: {condition}",
                "output": f"Escalate to {escalate_to} when: {condition}. Reason: {reason}"
            })

        # Pair 7: Related issues
        if playbook.related_playbooks:
            related = ", ".join(playbook.related_playbooks[:5])
            pairs.append({
                "instruction": f"What issues are related to {name}?",
                "input": "",
                "output": f"Related Kubernetes issues include: {related}. Check these playbooks if initial debugging doesn't resolve the issue."
            })

        # Pair 8: Severity classification
        rank = self.SEVERITY_RANK.get(playbook.severity, "D")
        pairs.append({
            "instruction": f"How severe is a {name} error and what rank should it be?",
            "input": "",
            "output": f"{name} has {playbook.severity} severity and occurs with {playbook.frequency} frequency. This should be classified as {rank}-rank for automation decisions."
        })

        # Generate pairs from gameplan branches if present
        branch_pairs = self._generate_branch_pairs(playbook)
        pairs.extend(branch_pairs)

        return pairs

    def _generate_debug_instructions(self, playbook: PlaybookData) -> str:
        """Generate debugging instructions from gameplan."""
        instructions = []

        for step_name, step_data in playbook.gameplan.items():
            if not isinstance(step_data, dict):
                continue

            step_title = step_data.get("name", step_name)
            commands = step_data.get("commands", [])

            if commands:
                instructions.append(f"**{step_title}**")
                for cmd in commands[:3]:
                    instructions.append(f"  - `{cmd}`")

        if not instructions:
            return f"Use `kubectl describe pod <pod> -n <ns>` and `kubectl logs <pod> -n <ns>` to investigate {playbook.name}."

        return "\n".join(instructions)

    def _generate_gameplan_steps(self, playbook: PlaybookData) -> str:
        """Generate step-by-step instructions from gameplan."""
        steps = []
        step_num = 1

        for step_name, step_data in playbook.gameplan.items():
            if not isinstance(step_data, dict):
                continue

            step_title = step_data.get("name", step_name)
            steps.append(f"{step_num}. **{step_title}**")

            commands = step_data.get("commands", [])
            for cmd in commands[:2]:
                steps.append(f"   - Run: `{cmd}`")

            extract = step_data.get("extract", [])
            if extract:
                steps.append(f"   - Look for: {', '.join(extract[:3])}")

            step_num += 1

        return "\n".join(steps) if steps else ""

    def _generate_branch_pairs(self, playbook: PlaybookData) -> List[Dict[str, Any]]:
        """Generate training pairs from gameplan branches."""
        pairs = []
        name = playbook.name.replace("-", " ").replace("_", " ").title()

        for step_name, step_data in playbook.gameplan.items():
            if not isinstance(step_data, dict):
                continue

            # Look for branches in the step
            branches = step_data.get("branches", {})
            if not branches and isinstance(step_data, dict):
                # Check for nested branch structures
                for key, value in step_data.items():
                    if isinstance(value, dict) and "meaning" in value:
                        branches[key] = value

            for branch_name, branch_data in branches.items():
                if not isinstance(branch_data, dict):
                    continue

                meaning = branch_data.get("meaning", "")
                fixes = branch_data.get("fixes", [])
                fix_rank = branch_data.get("fix_rank", "D")

                if meaning:
                    # Create symptom → diagnosis pair
                    pairs.append({
                        "instruction": f"Pod shows {name} with {branch_name}. What does this mean?",
                        "input": "",
                        "output": meaning
                    })

                    # Create symptom → fix pair
                    if fixes:
                        fix_text = fixes[0] if isinstance(fixes[0], str) else fixes[0].get("action", str(fixes[0]))
                        pairs.append({
                            "instruction": f"How do I fix {name} when {branch_name}?",
                            "input": meaning,
                            "output": f"This is a {fix_rank}-rank fix: {fix_text}"
                        })

        return pairs

    def generate(
        self,
        output_file: Optional[str] = None,
        dry_run: bool = False
    ) -> Path:
        """Generate training data from all playbooks."""
        all_pairs = []

        playbooks = list(self.parser.parse_all())
        logger.info(f"Processing {len(playbooks)} playbooks...")

        for playbook in tqdm(playbooks, desc="Generating training pairs"):
            pairs = self.generate_training_pairs(playbook)
            all_pairs.extend(pairs)

        logger.info(f"Generated {len(all_pairs)} training pairs total")

        if dry_run:
            logger.info("Dry run - not writing to file")
            return None

        # Write to file
        output_file = output_file or "k8s-failures-training.jsonl"
        output_path = self.output_dir / output_file

        with open(output_path, "w") as f:
            for pair in all_pairs:
                f.write(json.dumps(pair) + "\n")

        logger.info(f"Wrote training data to: {output_path}")
        return output_path

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about available playbooks."""
        playbooks = list(self.parser.parse_all())

        stats = {
            "total_playbooks": len(playbooks),
            "by_category": {},
            "by_severity": {},
            "total_auto_fixes": 0,
            "total_escalation_triggers": 0,
            "estimated_training_pairs": 0
        }

        for pb in playbooks:
            stats["by_category"][pb.category] = stats["by_category"].get(pb.category, 0) + 1
            stats["by_severity"][pb.severity] = stats["by_severity"].get(pb.severity, 0) + 1
            stats["total_auto_fixes"] += len(pb.common_auto_fixes)
            stats["total_escalation_triggers"] += len(pb.escalation_triggers)

        # Estimate pairs: ~8 base pairs + 2 per auto_fix + 2 per branch
        stats["estimated_training_pairs"] = len(playbooks) * 12

        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Generate JADE training data from K8s operational playbooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate_k8s_training_data.py
    python generate_k8s_training_data.py --playbooks-dir /path/to/playbooks
    python generate_k8s_training_data.py --output custom-output.jsonl
    python generate_k8s_training_data.py --stats
    python generate_k8s_training_data.py --dry-run
        """
    )

    parser.add_argument(
        "--playbooks-dir",
        type=str,
        default=str(DEFAULT_PLAYBOOKS_DIR),
        help=f"Directory containing playbook YAML files (default: {DEFAULT_PLAYBOOKS_DIR})"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file name (default: k8s-failures-training.jsonl)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics about available playbooks"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count pairs without writing to file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    playbooks_dir = Path(args.playbooks_dir)
    output_dir = Path(args.output_dir)

    if not playbooks_dir.exists():
        logger.error(f"Playbooks directory not found: {playbooks_dir}")
        logger.info(f"Expected path: {DEFAULT_PLAYBOOKS_DIR}")
        return 1

    generator = K8sTrainingDataGenerator(playbooks_dir, output_dir)

    if args.stats:
        stats = generator.get_stats()
        print("\n=== K8s Playbook Statistics ===\n")
        print(f"Total playbooks: {stats['total_playbooks']}")
        print(f"Total auto-fixes: {stats['total_auto_fixes']}")
        print(f"Total escalation triggers: {stats['total_escalation_triggers']}")
        print(f"Estimated training pairs: {stats['estimated_training_pairs']}")
        print("\nBy Category:")
        for category, count in sorted(stats["by_category"].items()):
            print(f"  {category}: {count}")
        print("\nBy Severity:")
        for severity, count in sorted(stats["by_severity"].items()):
            print(f"  {severity}: {count}")
    else:
        output = generator.generate(
            output_file=args.output,
            dry_run=args.dry_run
        )
        if output:
            print(f"\nTraining data generated: {output}")

    return 0


if __name__ == "__main__":
    exit(main())
