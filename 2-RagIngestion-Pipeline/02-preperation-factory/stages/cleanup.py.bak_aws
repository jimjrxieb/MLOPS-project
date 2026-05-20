#!/usr/bin/env python3
"""
Stage 7: Cleanup
Move processed files to GP-DATA/processed/
"""

from pathlib import Path
from typing import Dict, Any, List
import shutil
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

GP_DATA_PATH = Path("/home/jimmie/linkops-industries/GP-copilot/GP-DATA")


def cleanup_item(ingested_item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """
    Move processed file to appropriate GP-DATA/processed/ directory

    Returns updated item with cleanup status
    """
    source_file = ingested_item['file']

    # Determine destination based on what was ingested
    rag_ingested = ingested_item.get('rag_ingested', False)
    sql_ingested = ingested_item.get('sql_ingested', False)

    if not rag_ingested and not sql_ingested:
        return {
            **ingested_item,
            'cleaned_up': False,
            'cleanup_reason': 'Not ingested into any database'
        }

    try:
        # Choose processed directory based on ingestion type
        if rag_ingested:
            processed_dir = GP_DATA_PATH / "1-rag-knowledge" / "rag-processed"
        elif sql_ingested:
            processed_dir = GP_DATA_PATH / "2-structured-data" / "sql-processed"
        else:
            processed_dir = GP_DATA_PATH / "1-rag-knowledge" / "rag-processed"  # Default

        # Create category subdirectory
        category = ingested_item['category']
        dest_dir = processed_dir / category
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Destination file path
        dest_file = dest_dir / source_file.name

        # Handle duplicate filenames
        if dest_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = source_file.stem
            suffix = source_file.suffix
            dest_file = dest_dir / f"{stem}_{timestamp}{suffix}"

        # Move file
        if not dry_run:
            shutil.move(str(source_file), str(dest_file))
            moved = True
        else:
            moved = False  # Dry run, don't actually move

        return {
            **ingested_item,
            'cleaned_up': moved,
            'dest_path': str(dest_file),
            'cleanup_reason': 'Moved to processed' if moved else 'Dry run - not moved'
        }

    except Exception as e:
        return {
            **ingested_item,
            'cleaned_up': False,
            'cleanup_reason': f'Cleanup error: {e}'
        }


def cleanup_batch(ingested: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
    """
    Clean up all ingested files

    Returns summary statistics
    """
    results = []

    for item in ingested:
        result = cleanup_item(item, dry_run=dry_run)
        results.append(result)

    # Calculate statistics
    cleaned = sum(1 for r in results if r.get('cleaned_up'))
    skipped = sum(1 for r in results if not r.get('cleaned_up'))

    return {
        'results': results,
        'total': len(results),
        'cleaned': cleaned,
        'skipped': skipped,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test cleanup
    test_item = {
        'file': Path('/tmp/test_file.jsonl'),
        'category': 'domain-SME',
        'rag_ingested': True,
        'sql_ingested': False
    }

    # Create test file
    test_item['file'].touch()

    result = cleanup_item(test_item, dry_run=True)
    print("\n🧽 Cleanup Test")
    print("="*60)
    print(f"Cleaned up: {result['cleaned_up']}")
    print(f"Destination: {result.get('dest_path')}")
    print(f"Reason: {result.get('cleanup_reason')}")
    print("="*60)

    # Clean up test file
    test_item['file'].unlink()
