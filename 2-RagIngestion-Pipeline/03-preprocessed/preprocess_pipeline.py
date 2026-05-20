#!/usr/bin/env python3
"""
RAG Preprocessing Pipeline - Part 1 of 2
=========================================

Multi-stage preprocessing pipeline for RAG data.

Flow:
    01-unprocessed/ → [discover → preprocess → sanitize → format → label → route] → 03-preprocessed/

After running, inspect the output in 03-preprocessed/ before running Part 2 (ingestion).

Usage:
    python3 preprocess_pipeline.py                    # Process all data
    python3 preprocess_pipeline.py --dry-run          # Preview only
    python3 preprocess_pipeline.py --category night-learning  # Process specific category
    python3 preprocess_pipeline.py --verbose          # Show detailed output

Output:
    - processed_{timestamp}.jsonl   # Cleaned data ready for ingestion
    - manifest_{timestamp}.json     # Summary for human review
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse

# Setup paths - Centralized in GP-OPENSEARCH
SCRIPT_DIR = Path(__file__).parent  # 03-preprocessed/
OPENSEARCH_ROOT = SCRIPT_DIR.parent  # GP-OPENSEARCH/
GP_ROOT = OPENSEARCH_ROOT.parent  # GP-copilot/

# Pipeline directories (all within GP-OPENSEARCH)
STAGES_DIR = OPENSEARCH_ROOT / "02-preperation-factory" / "stages"
UNPROCESSED_DIR = OPENSEARCH_ROOT / "01-unprocessed"
OUTPUT_DIR = SCRIPT_DIR  # 03-preprocessed/ (quality check window)
RAW_ARCHIVE_DIR = OPENSEARCH_ROOT / "05-ragged-data" / "raw-data"  # Archive after processing
PROCESSED_ARCHIVE_DIR = OPENSEARCH_ROOT / "05-ragged-data" / "rag-processed"  # Final JSONL home

# Add stages to path
sys.path.insert(0, str(STAGES_DIR.parent))
sys.path.insert(0, str(STAGES_DIR))

# Import stage NPCs
try:
    from stages.discover import discover_files, print_discovery_report
    from stages.preprocess import preprocess_file, preprocess_batch
    from stages.sanitize_npc import SanitizeNPC
    from stages.format_conversion_npc import FormatConversionNPC
    from stages.labeling_npc import LabelingNPC
    from stages.route import route_item, route_batch
    STAGES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import stages: {e}")
    STAGES_AVAILABLE = False


class PreprocessingPipeline:
    """
    Multi-stage preprocessing pipeline.

    Stages:
    1. Discover - Find files in 01-unprocessed/
    2. Preprocess - Parse and validate formats
    3. Sanitize - Remove PII, dedup, quality gates
    4. Format - Convert all to normalized JSONL
    5. Label - Add domain/type/difficulty metadata
    6. Route - Determine destination (RAG collection)
    """

    def __init__(self, verbose: bool = False, use_claude_api: bool = False):
        self.verbose = verbose
        self.use_claude_api = use_claude_api
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize NPCs
        self.sanitize_npc = SanitizeNPC()
        self.format_npc = FormatConversionNPC()
        self.labeling_npc = LabelingNPC(use_claude_api=use_claude_api)

        # Statistics
        self.stats = {
            'discovered': 0,
            'preprocessed': 0,
            'sanitized': 0,
            'formatted': 0,
            'labeled': 0,
            'routed': 0,
            'passed': 0,
            'failed': 0,
            'repaired': 0,
            'duplicates': 0,
            'by_category': {},
            'by_destination': {}
        }

    def run(self,
            dry_run: bool = False,
            category_filter: Optional[str] = None,
            include_existing: bool = False) -> Dict[str, Any]:
        """
        Run the full preprocessing pipeline.

        Args:
            dry_run: If True, only preview without writing files
            category_filter: Process only specific category
            include_existing: Also process 4-ingested-data/rag-processed/

        Returns:
            Summary dict with stats and output files
        """
        print("\n" + "="*70)
        print("🔄 RAG PREPROCESSING PIPELINE - Part 1 of 2")
        print("="*70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print("="*70 + "\n")

        # Stage 1: Discover
        print("📂 Stage 1: DISCOVER")
        print("-"*40)
        discovered = self._stage_discover(category_filter, include_existing)

        if not any(files for files in discovered.values()):
            print("⚠️  No files found to process")
            return {'status': 'empty', 'stats': self.stats}

        # Stage 2-6: Process each file through pipeline
        all_processed = []
        successfully_processed_files = []  # Track files for archiving

        for category, files in discovered.items():
            if not files:
                continue

            print(f"\n📁 Processing category: {category} ({len(files)} files)")
            print("-"*40)

            for file_path in files:
                result = self._process_file(file_path, category)
                if result:
                    all_processed.extend(result)
                    successfully_processed_files.append(file_path)

        # Generate output
        if not dry_run and all_processed:
            output_file, manifest_file = self._write_output(all_processed)
            # Archive raw files after successful preprocessing
            self._archive_raw_files(successfully_processed_files)
        else:
            output_file = None
            manifest_file = None

        # Print summary
        self._print_summary(dry_run, output_file, manifest_file)

        return {
            'status': 'success',
            'stats': self.stats,
            'output_file': str(output_file) if output_file else None,
            'manifest_file': str(manifest_file) if manifest_file else None,
            'total_items': len(all_processed)
        }

    def _stage_discover(self,
                        category_filter: Optional[str],
                        include_existing: bool) -> Dict[str, List[Path]]:
        """Stage 1: Discover files"""
        discovered = discover_files(UNPROCESSED_DIR)

        # Also include existing rag-processed if requested
        if include_existing:
            existing_dir = PROCESSED_ARCHIVE_DIR  # GP-OPENSEARCH/05-ragged-data/rag-processed
            if existing_dir.exists():
                for subdir in existing_dir.iterdir():
                    if subdir.is_dir():
                        category = subdir.name
                        files = list(subdir.glob("**/*.jsonl")) + list(subdir.glob("**/*.json")) + list(subdir.glob("**/*.md"))
                        if files:
                            discovered[f"existing_{category}"] = files

        # Apply category filter
        if category_filter:
            discovered = {k: v for k, v in discovered.items() if category_filter in k}

        # Count discovered
        for category, files in discovered.items():
            if files:
                self.stats['discovered'] += len(files)
                self.stats['by_category'][category] = len(files)
                print(f"  {category}/: {len(files)} files")

        print(f"\n  Total: {self.stats['discovered']} files")
        return discovered

    def _process_file(self, file_path: Path, category: str) -> List[Dict[str, Any]]:
        """Process a single file through all stages"""
        if self.verbose:
            print(f"\n  Processing: {file_path.name}")

        try:
            # Stage 2: Preprocess (parse file)
            preprocessed = preprocess_file(file_path, category)
            if not preprocessed or not preprocessed.get('valid'):
                if self.verbose:
                    print(f"    ❌ Preprocess failed: {preprocessed.get('error', 'unknown')}")
                self.stats['failed'] += 1
                return []
            self.stats['preprocessed'] += 1

            # Stage 3: Sanitize
            sanitized = self.sanitize_npc.process(preprocessed)
            if sanitized.get('quality_gate') == 'FAIL':
                if self.verbose:
                    print(f"    ❌ Sanitize failed: {sanitized.get('issues_found', [])}")
                if sanitized.get('duplicate'):
                    self.stats['duplicates'] += 1
                else:
                    self.stats['failed'] += 1
                return []

            if sanitized.get('quality_gate') == 'REPAIR':
                self.stats['repaired'] += 1
            self.stats['sanitized'] += 1

            # Stage 4: Format conversion (normalize to JSONL)
            formatted = self.format_npc.process(sanitized)
            if formatted.get('error'):  # Check for truthy error value
                if self.verbose:
                    print(f"    ❌ Format failed: {formatted['error']}")
                self.stats['failed'] += 1
                return []
            self.stats['formatted'] += 1

            # Stage 5: Labeling
            labeled = self.labeling_npc.process(formatted)
            if not labeled.get('labeled'):
                if self.verbose:
                    print(f"    ⚠️  Labeling skipped: {labeled.get('error', 'unknown')}")
            else:
                self.stats['labeled'] += 1

            # Stage 6: Route
            routed = route_item({
                **labeled,
                'valid': True,
                'sanitized': True,
                'category': category
            })
            self.stats['routed'] += 1

            # Track destination
            dest = routed.get('rag_collection', 'unknown')
            self.stats['by_destination'][dest] = self.stats['by_destination'].get(dest, 0) + 1

            # Extract final JSONL items
            final_items = []
            data = routed.get('data', [])

            if isinstance(data, list):
                for item in data:
                    # Ensure content exists
                    if isinstance(item, dict) and item.get('content'):
                        final_item = {
                            'content': item['content'],
                            'metadata': {
                                **item.get('metadata', {}),
                                'source_file': str(file_path.name),
                                'source_category': category,
                                'rag_collection': dest,
                                'processed_at': datetime.now().isoformat(),
                                'quality_gate': sanitized.get('quality_gate', 'UNKNOWN')
                            }
                        }
                        final_items.append(final_item)
                        self.stats['passed'] += 1

            if self.verbose and final_items:
                print(f"    ✅ {len(final_items)} items → {dest}")

            return final_items

        except Exception as e:
            if self.verbose:
                print(f"    ❌ Error: {e}")
            self.stats['failed'] += 1
            return []

    def _write_output(self, items: List[Dict[str, Any]]) -> tuple:
        """Write processed items to JSONL and manifest"""
        # Output JSONL
        output_file = OUTPUT_DIR / f"processed_{self.timestamp}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        # Manifest for human review
        manifest = {
            'timestamp': self.timestamp,
            'total_items': len(items),
            'stats': self.stats,
            'by_collection': self.stats['by_destination'],
            'by_category': self.stats['by_category'],
            'sample_items': items[:5] if items else [],  # First 5 for preview
            'approval_status': 'PENDING',
            'notes': 'Review this file before running ingestion (Part 2)'
        }

        manifest_file = OUTPUT_DIR / f"manifest_{self.timestamp}.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return output_file, manifest_file

    def _archive_raw_files(self, processed_files: List[Path]):
        """Archive successfully processed raw files to 4-ingested-data/raw-data/"""
        if not processed_files:
            return

        # Create timestamped archive directory
        archive_dir = RAW_ARCHIVE_DIR / self.timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)

        archived_count = 0
        for file_path in processed_files:
            try:
                # Preserve category structure in archive
                rel_path = file_path.relative_to(UNPROCESSED_DIR)
                dest_dir = archive_dir / rel_path.parent
                dest_dir.mkdir(parents=True, exist_ok=True)

                dest_file = dest_dir / file_path.name
                shutil.move(str(file_path), str(dest_file))
                archived_count += 1
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  Could not archive {file_path.name}: {e}")

        print(f"\n  📦 Archived {archived_count} raw files to: {archive_dir.relative_to(OPENSEARCH_ROOT)}")

    def _print_summary(self, dry_run: bool, output_file: Optional[Path], manifest_file: Optional[Path]):
        """Print final summary"""
        print("\n" + "="*70)
        print("📊 PREPROCESSING SUMMARY")
        print("="*70)

        print(f"\n  Files discovered:    {self.stats['discovered']}")
        print(f"  Files preprocessed:  {self.stats['preprocessed']}")
        print(f"  Files sanitized:     {self.stats['sanitized']}")
        print(f"  Files formatted:     {self.stats['formatted']}")
        print(f"  Files labeled:       {self.stats['labeled']}")
        print(f"  Files routed:        {self.stats['routed']}")

        print(f"\n  Quality Gates:")
        print(f"    ✅ PASSED:   {self.stats['passed']}")
        print(f"    🔧 REPAIRED: {self.stats['repaired']}")
        print(f"    ❌ FAILED:   {self.stats['failed']}")
        print(f"    🔄 DUPES:    {self.stats['duplicates']}")

        if self.stats['by_destination']:
            print(f"\n  By RAG Collection:")
            for dest, count in sorted(self.stats['by_destination'].items()):
                print(f"    {dest}: {count}")

        if not dry_run and output_file:
            print(f"\n  📁 Output Files:")
            print(f"    Data:     {output_file.name}")
            print(f"    Manifest: {manifest_file.name}")
            print(f"\n  ⏳ NEXT STEP:")
            print(f"    1. Review the manifest and data files")
            print(f"    2. Run: python3 04-ingesting/ingest_to_chromadb.py")
        elif dry_run:
            print(f"\n  (DRY RUN - no files written)")

        print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description='RAG Preprocessing Pipeline')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing files')
    parser.add_argument('--category', type=str, help='Process specific category only')
    parser.add_argument('--include-existing', action='store_true', help='Also process 4-ingested-data/rag-processed/')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--use-claude-api', action='store_true', help='Enable Claude API for semantic labeling (requires ANTHROPIC_API_KEY)')

    args = parser.parse_args()

    if not STAGES_AVAILABLE:
        print("❌ Cannot run: Stage modules not available")
        print("   Check that 02-preperation-factory/stages/ exists")
        return 1

    pipeline = PreprocessingPipeline(verbose=args.verbose, use_claude_api=args.use_claude_api)
    result = pipeline.run(
        dry_run=args.dry_run,
        category_filter=args.category,
        include_existing=args.include_existing
    )

    return 0 if result['status'] == 'success' else 1


if __name__ == "__main__":
    sys.exit(main())