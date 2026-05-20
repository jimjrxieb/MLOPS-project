#!/usr/bin/env python3
"""
NPC: Format Conversion
======================

Convert all formats to normalized JSONL for consistent ingestion.

Assembly Line Position: #3 (after sanitize_npc)
Next NPC: labeling_npc

What this NPC does:
- Converts .md → .jsonl
- Converts .txt → .jsonl
- Converts .json → .jsonl
- Normalizes .jsonl structure
- Preserves metadata
- Handles special formats (code blocks, tables, lists)
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import re
from datetime import datetime

class FormatConversionNPC:
    """
    NPC for format normalization.

    Input Formats: .md, .txt, .json, .jsonl
    Output Format: .jsonl (always)

    JSONL Structure:
    {
        "content": "main content here",
        "metadata": {
            "source": "original_file.md",
            "original_format": ".md",
            "converted_at": "2025-11-17T12:00:00",
            "chunk_index": 0,
            "total_chunks": 1
        }
    }

    Chunking Strategy:
    - Target: 512 tokens per chunk (~2048 chars)
    - Overlap: 64 tokens (~256 chars) — 12.5% overlap
    - Markdown: split by headers first, then sub-split long sections
    - Text: overlap chunking instead of naive paragraph splitting
    """

    # Token estimation: 1 token ≈ 4 characters (conservative for English)
    CHARS_PER_TOKEN = 4
    TARGET_CHUNK_TOKENS = 512
    OVERLAP_TOKENS = 64

    def __init__(self):
        self.target_chunk_chars = self.TARGET_CHUNK_TOKENS * self.CHARS_PER_TOKEN  # 2048
        self.overlap_chars = self.OVERLAP_TOKENS * self.CHARS_PER_TOKEN  # 256
        self.stats = {
            'processed': 0,
            'converted': 0,
            'already_jsonl': 0,
            'failed': 0,
            'json_repaired': 0,
            'chunks_created': 0,
            'overlap_splits': 0,
        }

    def _repair_malformed_json(self, raw_text: str) -> Tuple[Dict | None, List[str]]:
        """
        Attempt to repair malformed JSON from LLM output (e.g., LLaMA)

        Common issues:
        - Unescaped quotes in code strings
        - Unescaped backslashes
        - Markdown code blocks
        - Trailing commas

        Returns:
            (parsed_json_or_None, list_of_repairs_applied)
        """
        repairs = []

        # Try as-is first
        try:
            return json.loads(raw_text), []
        except json.JSONDecodeError:
            pass

        # Repair 1: Strip markdown code blocks
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
            repairs.append('removed_markdown_json_block')
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
            repairs.append('removed_markdown_block')

        raw_text = raw_text.strip()

        # Try again
        try:
            return json.loads(raw_text), repairs
        except json.JSONDecodeError:
            pass

        # Repair 2: Fix LLM double-escaping problem
        # Some LLMs generate \\n and \\" (double backslashes) instead of proper JSON escapes
        try:
            # LLM output: \\" means it wants \" (escaped quote)
            # But it wrote TWO backslashes, causing invalid JSON
            # Fix: \\" → \" and \\n → \n

            fixed = raw_text

            # Replace double-backslash patterns:
            # \\n (4 chars) → \n (2 chars) for newlines
            # \\" (3 chars) → \" (2 chars) for quotes
            # \\' (3 chars) → \' (2 chars) for single quotes

            # This regex finds \\X patterns and reduces them to \X
            fixed = re.sub(r'\\\\([n"\'])', r'\\\1', fixed)

            result = json.loads(fixed)
            repairs.append('fixed_double_escaping')
            return result, repairs
        except json.JSONDecodeError:
            pass

        # Repair 3: Remove trailing commas
        try:
            fixed = re.sub(r',(\s*[}\]])', r'\1', raw_text)
            result = json.loads(fixed)
            repairs.append('removed_trailing_commas')
            return result, repairs
        except json.JSONDecodeError:
            pass

        # Repair 4: Combine fixes (backslashes + trailing commas)
        try:
            fixed = raw_text
            fixed = fixed.replace('\\\\n', '\\n')
            fixed = re.sub(r'\\\\(["\'])', r'\\\1', fixed)
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            result = json.loads(fixed)
            repairs.append('combined_fixes')
            return result, repairs
        except json.JSONDecodeError:
            pass

        # Give up - too broken to repair automatically
        return None, repairs

    def process(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert item to normalized JSONL format.

        Returns:
            {
                'data': list[dict],  # Always JSONL (list of dicts)
                'format': '.jsonl',   # Always
                'original_format': str,
                'conversion_applied': bool,
                'error': str | None
            }
        """
        self.stats['processed'] += 1

        format_type = item.get('format', '')
        source = item.get('source', 'unknown')

        try:
            if format_type == '.jsonl':
                # Already JSONL, just normalize structure
                jsonl_data = self._normalize_jsonl(item['data'], source, format_type)
                self.stats['already_jsonl'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': False
                }

            elif format_type == '.json':
                jsonl_data = self._json_to_jsonl(item['data'], source, format_type)
                self.stats['converted'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': True
                }

            elif format_type == '.md':
                jsonl_data = self._markdown_to_jsonl(item['data'], source, format_type)
                self.stats['converted'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': True
                }

            elif format_type == '.txt':
                jsonl_data = self._text_to_jsonl(item['data'], source, format_type)
                self.stats['converted'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': True
                }

            elif format_type == '.rego':
                jsonl_data = self._rego_to_jsonl(item['data'], source, format_type)
                self.stats['converted'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': True
                }

            elif format_type in ['.yaml', '.yml']:
                jsonl_data = self._yaml_to_jsonl(item['data'], source, format_type)
                self.stats['converted'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': True
                }

            else:
                # Unknown format, treat as text
                jsonl_data = self._text_to_jsonl(str(item['data']), source, format_type)
                self.stats['converted'] += 1
                return {
                    **item,
                    'data': jsonl_data,
                    'format': '.jsonl',
                    'original_format': format_type,
                    'conversion_applied': True
                }

        except Exception as e:
            self.stats['failed'] += 1
            return {
                **item,
                'error': f'Conversion failed: {e}',
                'conversion_applied': False
            }

    def _normalize_jsonl(self, data: List[Dict], source: str, original_format: str) -> List[Dict]:
        """
        Normalize existing JSONL to standard structure.
        """
        normalized = []

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                # Convert non-dict items to dict
                normalized_item = {
                    'content': str(item),
                    'metadata': self._create_metadata(source, original_format, i, len(data))
                }
            elif 'content' not in item:
                # Has dict but no 'content' field - add it
                normalized_item = {
                    'content': json.dumps(item),  # Serialize the whole dict as content
                    'metadata': {
                        **item.get('metadata', {}),
                        **self._create_metadata(source, original_format, i, len(data))
                    }
                }
            else:
                # Already has content, just ensure metadata
                normalized_item = {
                    'content': item['content'],
                    'metadata': {
                        **item.get('metadata', {}),
                        **self._create_metadata(source, original_format, i, len(data))
                    }
                }

            normalized.append(normalized_item)

        return normalized

    def _json_to_jsonl(self, data: Any, source: str, original_format: str) -> List[Dict]:
        """
        Convert JSON to JSONL.

        Strategy:
        - If dict: wrap in array
        - If list of dicts: keep as is
        - If list of non-dicts: convert each to dict
        """
        if isinstance(data, dict):
            # Single dict → single JSONL item
            return [{
                'content': json.dumps(data, indent=2),
                'metadata': self._create_metadata(source, original_format, 0, 1)
            }]

        elif isinstance(data, list):
            # List → multiple JSONL items
            jsonl_items = []
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    # Dict item - use as content
                    jsonl_items.append({
                        'content': json.dumps(item, indent=2),
                        'metadata': self._create_metadata(source, original_format, i, len(data))
                    })
                else:
                    # Non-dict item - convert to string
                    jsonl_items.append({
                        'content': str(item),
                        'metadata': self._create_metadata(source, original_format, i, len(data))
                    })
            return jsonl_items

        else:
            # Primitive type → single JSONL item
            return [{
                'content': str(data),
                'metadata': self._create_metadata(source, original_format, 0, 1)
            }]

    def _markdown_to_jsonl(self, text: str, source: str, original_format: str) -> List[Dict]:
        """
        Convert Markdown to JSONL.

        Strategy:
        - Split by headers (# sections)
        - Sub-split long sections with token-aware overlap chunking
        - Each chunk → one JSONL item
        """
        if not text or not text.strip():
            return []

        # Split by top-level headers (# or ##)
        sections = self._split_markdown_by_headers(text)

        if not sections:
            # No headers found — use overlap chunking on the full document
            chunks = self._chunk_with_overlap(text)
            self.stats['chunks_created'] += len(chunks)
            return [{
                'content': chunk,
                'metadata': self._create_metadata(source, original_format, i, len(chunks), {'type': 'markdown_doc'})
            } for i, chunk in enumerate(chunks)]

        # Convert each section to JSONL items, sub-splitting long sections
        jsonl_items = []
        chunk_idx = 0
        # First pass: count total chunks for metadata
        all_chunks = []
        for section in sections:
            sub_chunks = self._chunk_with_overlap(section['content'])
            for sub in sub_chunks:
                all_chunks.append((sub, section['header'], section['level']))

        total_chunks = len(all_chunks)
        self.stats['chunks_created'] += total_chunks

        for chunk_text, header, level in all_chunks:
            jsonl_items.append({
                'content': chunk_text,
                'metadata': self._create_metadata(
                    source,
                    original_format,
                    chunk_idx,
                    total_chunks,
                    {
                        'type': 'markdown_section',
                        'header': header,
                        'header_level': level
                    }
                )
            })
            chunk_idx += 1

        return jsonl_items

    def _split_markdown_by_headers(self, text: str) -> List[Dict[str, Any]]:
        """
        Split markdown by headers.

        Returns:
            [{'header': str, 'level': int, 'content': str}, ...]
        """
        lines = text.split('\n')
        sections = []
        current_section = None

        for line in lines:
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                # Save previous section
                if current_section is not None:
                    sections.append(current_section)

                # Start new section
                level = len(header_match.group(1))
                header_text = header_match.group(2)
                current_section = {
                    'header': header_text,
                    'level': level,
                    'content': line + '\n'
                }
            else:
                # Add line to current section
                if current_section is not None:
                    current_section['content'] += line + '\n'
                else:
                    # No header yet, create default section
                    current_section = {
                        'header': '',
                        'level': 0,
                        'content': line + '\n'
                    }

        # Save last section
        if current_section is not None:
            sections.append(current_section)

        return sections

    def _text_to_jsonl(self, text: str, source: str, original_format: str) -> List[Dict]:
        """
        Convert plain text to JSONL.

        Strategy:
        1. Try to parse as JSON first (for LLM output repair)
        2. If JSON, return as-is
        3. Otherwise, split by paragraphs

        This allows the pipeline to automatically repair malformed JSON
        from Foundation Generator failures.
        """
        if not text or not text.strip():
            return []

        # FIRST: Try JSON repair (for LLM outputs)
        repaired_json, repairs = self._repair_malformed_json(text)

        if repaired_json:
            # Successfully repaired/parsed as JSON!
            self.stats['json_repaired'] += 1
            print(f"      🔧 Repaired JSON from {source}")
            if repairs:
                print(f"         Repairs: {', '.join(repairs)}")

            # Return as single JSONL item
            return [{
                **repaired_json,  # The actual training data
                'metadata': {
                    'source': source,
                    'original_format': original_format,
                    'converted_at': datetime.now().isoformat(),
                    'repaired': True,
                    'repairs_applied': repairs
                }
            }]

        # FALLBACK: Treat as plain text, use overlap chunking
        if not text.strip():
            return []

        chunks = self._chunk_with_overlap(text)
        self.stats['chunks_created'] += len(chunks)

        return [{
            'content': chunk,
            'metadata': self._create_metadata(
                source,
                original_format,
                i,
                len(chunks),
                {'type': 'text_chunk'}
            )
        } for i, chunk in enumerate(chunks)]

    def _rego_to_jsonl(self, data: Any, source: str, original_format: str) -> List[Dict]:
        """
        Convert parsed Rego policy to JSONL.

        Rego data from preprocess.parse_rego:
        {'content': str, 'package': str, 'rules': list, 'documentation': str,
         'policy_type': str, 'filename': str}
        """
        if isinstance(data, dict) and 'content' in data:
            # Build rich embedding text from Rego structure
            parts = []
            if data.get('documentation'):
                parts.append(data['documentation'])
            if data.get('package'):
                parts.append(f"Package: {data['package']}")
            if data.get('rules'):
                parts.append(f"Rules: {', '.join(data['rules'])}")
            if data.get('policy_type'):
                parts.append(f"Policy type: {data['policy_type']}")
            parts.append(data['content'])

            content = '\n\n'.join(parts)
            chunks = self._chunk_with_overlap(content)
            self.stats['chunks_created'] += len(chunks)

            return [{
                'content': chunk,
                'metadata': self._create_metadata(
                    source, original_format, i, len(chunks),
                    {
                        'type': 'rego_policy',
                        'package': data.get('package', ''),
                        'policy_type': data.get('policy_type', 'opa'),
                        'rules': ', '.join(data.get('rules', []))
                    }
                )
            } for i, chunk in enumerate(chunks)]

        # Fallback: treat as text
        return self._text_to_jsonl(str(data), source, original_format)

    def _yaml_to_jsonl(self, data: Any, source: str, original_format: str) -> List[Dict]:
        """
        Convert parsed YAML to JSONL.

        YAML data from preprocess.parse_yaml:
        {'content': str, 'data': Any, 'filename': str,
         'kind': str, 'api_version': str, 'name': str}
        """
        if isinstance(data, dict) and 'content' in data:
            # Build rich embedding text from YAML structure
            parts = []
            if data.get('kind') and data['kind'] != 'unknown':
                parts.append(f"Kind: {data['kind']}")
            if data.get('api_version'):
                parts.append(f"API Version: {data['api_version']}")
            if data.get('name'):
                parts.append(f"Name: {data['name']}")
            parts.append(data['content'])

            content = '\n\n'.join(parts)
            chunks = self._chunk_with_overlap(content)
            self.stats['chunks_created'] += len(chunks)

            return [{
                'content': chunk,
                'metadata': self._create_metadata(
                    source, original_format, i, len(chunks),
                    {
                        'type': 'yaml_manifest',
                        'kind': data.get('kind', ''),
                        'api_version': data.get('api_version', ''),
                        'resource_name': data.get('name', '')
                    }
                )
            } for i, chunk in enumerate(chunks)]

        # Fallback: treat as text
        return self._text_to_jsonl(str(data), source, original_format)

    def _chunk_with_overlap(self, text: str) -> List[str]:
        """Split text into overlapping chunks using token-aware boundaries.

        Strategy:
        - Target ~512 tokens (2048 chars) per chunk
        - 64 tokens (256 chars) overlap between consecutive chunks
        - Split on sentence boundaries when possible (. ! ? followed by space/newline)
        - If text is shorter than target, return as single chunk

        Returns:
            List of text chunks with overlap
        """
        if len(text) <= self.target_chunk_chars:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.target_chunk_chars

            if end >= text_len:
                # Last chunk — take everything remaining
                chunks.append(text[start:])
                break

            # Try to split on a sentence boundary within the last 20% of the chunk
            # to avoid cutting mid-sentence
            search_start = end - (self.target_chunk_chars // 5)  # last 20%
            best_break = None

            for boundary in re.finditer(r'[.!?]\s', text[search_start:end]):
                # Position relative to full text
                best_break = search_start + boundary.end()

            if best_break and best_break > start:
                end = best_break
            else:
                # Fall back to splitting on any whitespace near the target
                space_pos = text.rfind(' ', start + (self.target_chunk_chars // 2), end)
                if space_pos > start:
                    end = space_pos + 1

            chunks.append(text[start:end])

            # Advance with overlap
            start = end - self.overlap_chars
            # Ensure we always advance at least half the chunk size to avoid infinite loops
            if start <= (end - self.target_chunk_chars):
                start = end - (self.target_chunk_chars // 2)

        self.stats['overlap_splits'] += len(chunks) - 1
        return chunks

    def _create_metadata(
        self,
        source: str,
        original_format: str,
        chunk_index: int,
        total_chunks: int,
        extra: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create standardized metadata"""
        metadata = {
            'source': source,
            'original_format': original_format,
            'converted_at': datetime.now().isoformat(),
            'chunk_index': chunk_index,
            'total_chunks': total_chunks
        }

        if extra:
            metadata.update(extra)

        return metadata

    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of items"""
        return [self.process(item) for item in items]

    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        return {
            **self.stats,
            'conversion_rate': self.stats['converted'] / max(self.stats['processed'], 1) * 100,
            'avg_chunks_per_doc': self.stats['chunks_created'] / max(self.stats['converted'] + self.stats['already_jsonl'], 1),
        }


def main():
    """Test format conversion NPC"""
    print("\n🔄 Format Conversion NPC - Normalization Test")
    print("=" * 70)

    npc = FormatConversionNPC()

    # Test cases
    test_items = [
        # Markdown
        {
            'data': "# Header 1\nContent under header 1.\n\n## Header 2\nContent under header 2.",
            'format': '.md',
            'source': 'test.md'
        },
        # Plain text
        {
            'data': "First paragraph here.\n\nSecond paragraph here.",
            'format': '.txt',
            'source': 'test.txt'
        },
        # JSON dict
        {
            'data': {'title': 'Test', 'content': 'Example content'},
            'format': '.json',
            'source': 'test.json'
        },
        # JSON list
        {
            'data': [{'item': 1}, {'item': 2}],
            'format': '.json',
            'source': 'test_list.json'
        },
        # Already JSONL
        {
            'data': [{'content': 'Already JSONL', 'metadata': {}}],
            'format': '.jsonl',
            'source': 'test.jsonl'
        }
    ]

    for i, item in enumerate(test_items, 1):
        print(f"\n[Test {i}] Converting: {item['source']} ({item['format']})")
        result = npc.process(item)

        if 'error' in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ✅ Output format: {result['format']}")
            print(f"  📦 JSONL items: {len(result['data'])}")
            print(f"  🔧 Conversion applied: {result['conversion_applied']}")

            # Show first item
            if result['data']:
                first_item = result['data'][0]
                content_preview = first_item['content'][:60] + '...' if len(first_item['content']) > 60 else first_item['content']
                print(f"  📝 First item content: {content_preview}")

    print("\n" + "=" * 70)
    print("📊 Statistics:")
    stats = npc.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 70)


if __name__ == "__main__":
    main()
