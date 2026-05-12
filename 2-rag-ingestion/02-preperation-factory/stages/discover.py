#!/usr/bin/env python3
"""
Stage 1: Discover Files
Find all files in unprocessed/ directories
"""

from pathlib import Path
from typing import Dict, List
import sys

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def discover_files(base_path: Path = None) -> Dict[str, List[Path]]:
    """
    Scan unprocessed/ for new files to process

    Returns:
        Dictionary of files by category:
        {
            'domain-SME': [Path(...)],
            'projects-docs': [Path(...)],
            ...
        }
    """
    if base_path is None:
        # Default to GP-OPENSEARCH/01-unprocessed
        base_path = Path(__file__).parent.parent.parent / "01-unprocessed"

    # Categories to scan (standardized to lowercase to match disk)
    categories = {
        'domain-sme': 'Training data (JSONL Q&A pairs)',
        'projects-docs': 'Project documentation',
        'sessions': 'Session notes and summaries',
        'troubleshooting': 'Debugging guides',
        'sync': 'Security scan results',
        'client-intake': 'People, meetings, reports',
        'windows-sync': 'Windows sync data',
        'chat-session-docs': 'Chat session documentation',
        'session-docs': 'Session documentation',
        'night-learning': 'Night learning notes',
        'agent-research': 'Agent research outputs',
        'meeting-notes': 'Meeting notes',
        'build-sessions': 'Build session documentation',
        'claudecode-sessions': 'Claude Code session documentation',
        'jade-chat-session': 'Jade chat session documentation',
        'jsa-logs': 'JSA operational logs (escalations, successes, failures, cycles)',
        # Additional data sources
        'webscraper': 'Web scraped documentation',
        'npc-templates': 'NPC pattern templates',
        'gp-instances-docs': 'GP instance documentation',
        'yt-transcripts': 'YouTube transcripts',
        'operational-training-data': 'JSA operational training data from overnight runs',
        'claudecode-as-jade-sessions': 'ClaudeCode sessions documented as JADE training examples',
        # Policy/Rego sources
        'opa-policies': 'OPA/Rego policy files for CI/CD and runtime (Gatekeeper, Conftest)',
        # Consulting knowledge base
        'consulting-knowledge': 'JSA agent capabilities, deployment guides, architecture docs',
        # Legacy data re-processing
        'legacy-reprocess': 'Legacy docs being re-processed through new pipeline',
        # Compliance sources
        'compliance': 'General compliance documentation and controls',
        'nist-800-53': 'NIST 800-53 control definitions and mappings'
    }

    discovered = {}
    
    # 1. First scan explicitly defined categories
    for category, description in categories.items():
        category_path = base_path / category

        if not category_path.exists():
            discovered[category] = []
            continue

        # Find all files (recursively)
        files = []
        for pattern in ['**/*.jsonl', '**/*.json', '**/*.md', '**/*.txt', '**/*.rego', '**/*.yaml', '**/*.yml']:
            files.extend(category_path.glob(pattern))

        # Filter out hidden files and directories
        files = [f for f in files if not any(part.startswith('.') for part in f.parts)]

        discovered[category] = sorted(files)

    # 2. Dynamic Discovery: Scan for directories in base_path NOT in categories
    if base_path.exists():
        for item in base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name not in categories:
                # This is an unlisted category
                files = []
                for pattern in ['**/*.jsonl', '**/*.json', '**/*.md', '**/*.txt', '**/*.rego', '**/*.yaml', '**/*.yml']:
                    files.extend(item.glob(pattern))
                
                files = [f for f in files if not any(part.startswith('.') for part in f.parts)]
                
                if files:
                    discovered[item.name] = sorted(files)

    # Also scan for root-level files (not in subdirectories)
    root_files = []
    for pattern in ['*.jsonl', '*.json', '*.md', '*.txt']:
        root_files.extend(base_path.glob(pattern))

    # Filter out hidden files and Python scripts
    root_files = [f for f in root_files if not f.name.startswith('.') and not f.name.endswith('.py')]

    if root_files:
        discovered['root-level'] = sorted(root_files)

    return discovered


def print_discovery_report(discovered: Dict[str, List[Path]]):
    """Print summary of discovered files"""
    total_files = sum(len(files) for files in discovered.values())

    print(f"\n📂 Discovery Report")
    print(f"{'='*60}")
    print(f"Total files found: {total_files}")
    print()

    for category, files in discovered.items():
        if files:
            print(f"  {category}/: {len(files)} files")
            for file in files[:3]:  # Show first 3
                print(f"    - {file.name}")
            if len(files) > 3:
                print(f"    ... and {len(files) - 3} more")
            print()

    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Test discovery
    discovered = discover_files()
    print_discovery_report(discovered)
