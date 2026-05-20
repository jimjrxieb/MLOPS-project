#!/usr/bin/env python3
"""
NPC: Sanitize Data (Enhanced)
=============================

Quality-focused data cleaning with PASS/FAIL/REPAIR gates.

Assembly Line Position: #2 (after discover_npc)
Next NPC: format_conversion_npc

What this NPC does:
- Validates JSON structure
- Detects encoding issues
- Removes invalid/malformed data
- Deduplicates content
- Repairs fixable issues
- Quality gates: PASS/FAIL/REPAIR
"""

from pathlib import Path
from typing import Dict, Any, Tuple, List
import json
import hashlib
import re
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from shared.sanitization import remove_sensitive_patterns, clean_text
    HAS_SANITIZATION = True
except ImportError:
    HAS_SANITIZATION = False


class SanitizeNPC:
    """
    NPC for data quality and sanitization.

    Quality Gates:
    - PASS: Data is clean and valid
    - REPAIR: Data has issues but can be fixed
    - FAIL: Data is irreparably broken
    """

    def __init__(self):
        self.seen_hashes = set()  # For deduplication
        self.stats = {
            'processed': 0,
            'passed': 0,
            'repaired': 0,
            'failed': 0,
            'duplicates': 0,
            'json_repairs': 0
        }

    def repair_malformed_json(self, raw_text: str) -> tuple[dict | None, list[str]]:
        """
        Attempt to repair common JSON issues from LLM output (e.g., LLaMA)

        Common issues:
        - Unescaped quotes in code strings
        - Unescaped backslashes
        - Missing commas
        - Trailing commas

        Returns:
            (parsed_json_or_None, list_of_repairs_applied)
        """
        repairs_applied = []

        # Try parsing as-is first
        try:
            return json.loads(raw_text), []
        except json.JSONDecodeError:
            pass  # Continue to repairs

        # Repair 1: Strip markdown code blocks
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
            repairs_applied.append('removed_markdown_json_block')
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
            repairs_applied.append('removed_markdown_block')

        raw_text = raw_text.strip()

        # Try again
        try:
            return json.loads(raw_text), repairs_applied
        except json.JSONDecodeError:
            pass

        # Repair 2: Fix common escape issues in code fields
        # This is heuristic - looks for patterns like: "code": "unescaped string"
        # and attempts to fix unescaped quotes within string values

        # For now, just return None - full JSON repair is complex
        # Would need a proper JSON-aware parser
        return None, repairs_applied

    def process(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single item through quality gates.

        Returns:
            {
                ...item,
                'sanitized': bool,
                'quality_gate': 'PASS'|'REPAIR'|'FAIL',
                'issues_found': list,
                'issues_fixed': list,
                'duplicate': bool,
                'content_hash': str
            }
        """
        self.stats['processed'] += 1

        # Quality Gate 1: Validate structure
        is_valid, validation_issues = self._validate_structure(item)

        if not is_valid:
            self.stats['failed'] += 1
            return {
                **item,
                'sanitized': False,
                'quality_gate': 'FAIL',
                'issues_found': validation_issues,
                'issues_fixed': [],
                'duplicate': False
            }

        # Quality Gate 2: Check for duplicates
        is_duplicate, content_hash = self._check_duplicate(item)

        if is_duplicate:
            self.stats['duplicates'] += 1
            return {
                **item,
                'sanitized': True,
                'quality_gate': 'FAIL',
                'issues_found': ['duplicate_content'],
                'issues_fixed': [],
                'duplicate': True,
                'content_hash': content_hash
            }

        # Quality Gate 3: Detect and repair issues
        cleaned_item, issues_found, issues_fixed = self._clean_and_repair(item)

        # Determine quality gate
        if issues_fixed:
            quality_gate = 'REPAIR'
            self.stats['repaired'] += 1
        else:
            quality_gate = 'PASS'
            self.stats['passed'] += 1

        return {
            **cleaned_item,
            'sanitized': True,
            'quality_gate': quality_gate,
            'issues_found': issues_found,
            'issues_fixed': issues_fixed,
            'duplicate': False,
            'content_hash': content_hash
        }

    def _validate_structure(self, item: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate item structure.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check required fields
        if 'data' not in item:
            issues.append('missing_data_field')

        if 'format' not in item:
            issues.append('missing_format_field')

        # Check data is not empty
        if 'data' in item:
            data = item['data']
            if data is None:
                issues.append('null_data')
            elif isinstance(data, str) and not data.strip():
                issues.append('empty_string_data')
            elif isinstance(data, (list, dict)) and not data:
                issues.append('empty_collection_data')

        # Check encoding
        if 'data' in item and isinstance(item['data'], str):
            try:
                item['data'].encode('utf-8')
            except UnicodeEncodeError:
                issues.append('encoding_error')

        is_valid = len(issues) == 0
        return is_valid, issues

    def _check_duplicate(self, item: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if content is duplicate.

        Returns:
            (is_duplicate, content_hash)
        """
        # Create hash of content
        data = item.get('data', '')

        if isinstance(data, (dict, list)):
            # Use default=str to handle non-string keys (e.g. PyYAML parses
            # GHA 'on:' as boolean True) that crash sort_keys=True
            content_str = json.dumps(data, sort_keys=False, default=str)
        else:
            content_str = str(data)

        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        is_duplicate = content_hash in self.seen_hashes

        if not is_duplicate:
            self.seen_hashes.add(content_hash)

        return is_duplicate, content_hash

    def _clean_and_repair(self, item: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Clean and repair data.

        Returns:
            (cleaned_item, issues_found, issues_fixed)
        """
        issues_found = []
        issues_fixed = []
        cleaned_item = item.copy()

        data = item['data']
        format_type = item.get('format', '')

        # Handle different formats
        if format_type == '.jsonl':
            cleaned_data, found, fixed = self._clean_jsonl(data)
            cleaned_item['data'] = cleaned_data
            issues_found.extend(found)
            issues_fixed.extend(fixed)

        elif format_type == '.json':
            cleaned_data, found, fixed = self._clean_json(data)
            cleaned_item['data'] = cleaned_data
            issues_found.extend(found)
            issues_fixed.extend(fixed)

        elif format_type in ['.md', '.txt']:
            cleaned_data, found, fixed = self._clean_text(data)
            cleaned_item['data'] = cleaned_data
            issues_found.extend(found)
            issues_fixed.extend(fixed)

        return cleaned_item, issues_found, issues_fixed

    def _clean_jsonl(self, data: List[Dict]) -> Tuple[List[Dict], List[str], List[str]]:
        """Clean JSONL data (list of dicts)"""
        issues_found = []
        issues_fixed = []
        cleaned_items = []

        for item in data:
            if not isinstance(item, dict):
                issues_found.append('non_dict_item_in_jsonl')
                continue

            cleaned_item, found, fixed = self._clean_dict(item)
            cleaned_items.append(cleaned_item)
            issues_found.extend(found)
            issues_fixed.extend(fixed)

        return cleaned_items, issues_found, issues_fixed

    def _clean_json(self, data: Any) -> Tuple[Any, List[str], List[str]]:
        """Clean JSON data"""
        if isinstance(data, dict):
            return self._clean_dict(data)
        elif isinstance(data, list):
            issues_found = []
            issues_fixed = []
            cleaned_list = []
            for item in data:
                if isinstance(item, dict):
                    cleaned, found, fixed = self._clean_dict(item)
                    cleaned_list.append(cleaned)
                    issues_found.extend(found)
                    issues_fixed.extend(fixed)
                else:
                    cleaned_list.append(item)
            return cleaned_list, issues_found, issues_fixed
        else:
            return data, [], []

    def _clean_dict(self, data: Dict) -> Tuple[Dict, List[str], List[str]]:
        """Clean dictionary data"""
        issues_found = []
        issues_fixed = []
        cleaned = {}

        for key, value in data.items():
            if isinstance(value, str):
                cleaned_value, found, fixed = self._clean_string(value)
                cleaned[key] = cleaned_value
                issues_found.extend(found)
                issues_fixed.extend(fixed)

            elif isinstance(value, dict):
                cleaned_value, found, fixed = self._clean_dict(value)
                cleaned[key] = cleaned_value
                issues_found.extend(found)
                issues_fixed.extend(fixed)

            elif isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if isinstance(item, str):
                        cleaned_item, found, fixed = self._clean_string(item)
                        cleaned_list.append(cleaned_item)
                        issues_found.extend(found)
                        issues_fixed.extend(fixed)
                    elif isinstance(item, dict):
                        cleaned_item, found, fixed = self._clean_dict(item)
                        cleaned_list.append(cleaned_item)
                        issues_found.extend(found)
                        issues_fixed.extend(fixed)
                    else:
                        cleaned_list.append(item)
                cleaned[key] = cleaned_list

            else:
                cleaned[key] = value

        return cleaned, issues_found, issues_fixed

    def _clean_text(self, text: str) -> Tuple[str, List[str], List[str]]:
        """Clean text/markdown data"""
        return self._clean_string(text)

    def _clean_string(self, text: str) -> Tuple[str, List[str], List[str]]:
        """
        Clean and sanitize string content.

        Removes:
        - Email addresses
        - API keys
        - Passwords
        - Absolute paths with usernames
        - Excessive whitespace
        - Control characters
        """
        if not text:
            return text, [], []

        original = text
        issues_found = []
        issues_fixed = []

        # Remove email addresses (PII)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text):
            text = re.sub(email_pattern, '[EMAIL_REDACTED]', text)
            issues_found.append('contains_email')
            issues_fixed.append('redacted_email')

        # Remove API keys
        api_key_patterns = [
            (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_-]{20,}["\']?', 'api_key'),
            (r'["\']?token["\']?\s*[:=]\s*["\']?[A-Za-z0-9_-]{20,}["\']?', 'token'),
            (r'Bearer\s+[A-Za-z0-9_-]{20,}', 'bearer_token'),
            (r'sk_live_[A-Za-z0-9]{20,}', 'stripe_key'),
            (r'ghp_[A-Za-z0-9]{36}', 'github_pat'),
        ]

        for pattern, key_type in api_key_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, f'[{key_type.upper()}_REDACTED]', text, flags=re.IGNORECASE)
                if f'contains_{key_type}' not in issues_found:
                    issues_found.append(f'contains_{key_type}')
                    issues_fixed.append(f'redacted_{key_type}')

        # Remove passwords
        password_patterns = [
            (r'["\']?password["\']?\s*[:=]\s*["\']?[^"\'\s]{6,}["\']?', 'password'),
            (r'["\']?passwd["\']?\s*[:=]\s*["\']?[^"\'\s]{6,}["\']?', 'passwd'),
            (r'["\']?pwd["\']?\s*[:=]\s*["\']?[^"\'\s]{6,}["\']?', 'pwd'),
        ]

        for pattern, pwd_type in password_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, '[PASSWORD_REDACTED]', text, flags=re.IGNORECASE)
                if 'contains_password' not in issues_found:
                    issues_found.append('contains_password')
                    issues_fixed.append('redacted_password')

        # Remove absolute paths with usernames (PII)
        username_path_pattern = r'/home/[a-z_][a-z0-9_-]*/'
        if re.search(username_path_pattern, text):
            text = re.sub(username_path_pattern, '/home/user/', text)
            issues_found.append('contains_username_path')
            issues_fixed.append('sanitized_paths')

        # Remove control characters (except newlines and tabs)
        control_char_pattern = r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]'
        if re.search(control_char_pattern, text):
            text = re.sub(control_char_pattern, '', text)
            issues_found.append('contains_control_chars')
            issues_fixed.append('removed_control_chars')

        # Clean excessive whitespace
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        # Replace 3+ newlines with 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing/leading whitespace
        text = text.strip()

        if text != original and 'cleaned_whitespace' not in issues_fixed:
            issues_found.append('excessive_whitespace')
            issues_fixed.append('cleaned_whitespace')

        return text, issues_found, issues_fixed

    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of items"""
        return [self.process(item) for item in items]

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.stats,
            'success_rate': (self.stats['passed'] + self.stats['repaired']) / max(self.stats['processed'], 1) * 100
        }


def main():
    """Test sanitize NPC"""
    print("\n🧹 Sanitize NPC - Quality Gates Test")
    print("=" * 70)

    npc = SanitizeNPC()

    # Test cases
    test_items = [
        # PASS case - clean data
        {
            'data': {'content': 'This is clean content', 'title': 'Clean Example'},
            'format': '.json',
            'source': 'test1.json'
        },
        # REPAIR case - has issues but fixable
        {
            'data': 'Contact me at john.doe@example.com for the API key: sk_live_abc123xyz789',
            'format': '.txt',
            'source': 'test2.txt'
        },
        # FAIL case - empty data
        {
            'data': '',
            'format': '.txt',
            'source': 'test3.txt'
        },
        # FAIL case - duplicate (same as first)
        {
            'data': {'content': 'This is clean content', 'title': 'Clean Example'},
            'format': '.json',
            'source': 'test4.json'
        },
    ]

    for i, item in enumerate(test_items, 1):
        print(f"\n[Test {i}] Processing: {item['source']}")
        result = npc.process(item)

        print(f"  Quality Gate: {result['quality_gate']}")
        if result['issues_found']:
            print(f"  Issues Found: {', '.join(result['issues_found'])}")
        if result['issues_fixed']:
            print(f"  Issues Fixed: {', '.join(result['issues_fixed'])}")
        if result['duplicate']:
            print(f"  Duplicate: Yes (hash: {result['content_hash'][:16]}...)")

    print("\n" + "=" * 70)
    print("📊 Statistics:")
    stats = npc.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 70)


if __name__ == "__main__":
    main()
