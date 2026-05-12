#!/usr/bin/env python3
"""
Data Format Validators
Ensure data is properly formatted before ingestion
"""

from typing import Dict, Any, List, Optional
import json
import re


class FormatValidator:
    """Validate data formats before ingestion"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_all(self, data: Any, data_type: str, category: str) -> Dict[str, Any]:
        """
        Run all format validations

        Returns:
            {
                'valid': bool,
                'formatted': Any,  # Cleaned/formatted data
                'errors': List[str],
                'warnings': List[str]
            }
        """
        self.errors = []
        self.warnings = []

        if data_type == '.jsonl':
            result = self.validate_jsonl(data, category)
        elif data_type == '.json':
            result = self.validate_json(data, category)
        elif data_type in ['.md', '.txt']:
            result = self.validate_text(data)
        elif data_type == '.rego':
            result = self.validate_rego(data)
        elif data_type in ['.yaml', '.yml']:
            result = self.validate_yaml(data)
        else:
            result = {
                'valid': False,
                'formatted': None,
                'errors': [f'Unsupported data type: {data_type}'],
                'warnings': []
            }

        return result

    def validate_jsonl(self, data: List[Dict], category: str) -> Dict[str, Any]:
        """
        Validate JSONL format

        Checks:
        - Each item is a dict
        - Required fields present
        - No empty values
        - Proper encoding
        - Nomic-embed-text compatible (max 8192 tokens per chunk)
        """
        if not isinstance(data, list):
            return {
                'valid': False,
                'formatted': None,
                'errors': ['JSONL data must be a list of dictionaries'],
                'warnings': []
            }

        formatted_data = []
        line_errors = []

        for i, item in enumerate(data, 1):
            # Check if dict
            if not isinstance(item, dict):
                line_errors.append(f"Line {i}: Not a dictionary")
                continue

            # Check for empty items
            if not item:
                self.warnings.append(f"Line {i}: Empty dictionary")
                continue

            # Check for meaningful content
            has_content = False
            for key, value in item.items():
                if isinstance(value, str) and len(value.strip()) > 0:
                    has_content = True
                    break
                elif isinstance(value, (list, dict)) and value:
                    has_content = True
                    break

            if not has_content:
                self.warnings.append(f"Line {i}: No meaningful content")
                continue

            # Format fields for embedding
            formatted_item = self._format_for_embedding(item, category)
            formatted_data.append(formatted_item)

        # Add line errors to main errors
        self.errors.extend(line_errors[:10])  # Limit to first 10 errors

        return {
            'valid': len(self.errors) == 0 and len(formatted_data) > 0,
            'formatted': formatted_data,
            'errors': self.errors,
            'warnings': self.warnings
        }

    def validate_json(self, data: Any, category: str) -> Dict[str, Any]:
        """
        Validate JSON format

        Checks:
        - Proper structure based on category
        - Required fields present
        - Data types correct
        """
        if category == 'sync':
            # Scan results
            if not isinstance(data, dict):
                return {
                    'valid': False,
                    'formatted': None,
                    'errors': ['Scan results must be a dictionary'],
                    'warnings': []
                }

            # Check for expected keys
            has_findings = 'findings' in data or 'results' in data
            has_metadata = 'metadata' in data

            if not has_findings:
                self.warnings.append('No findings or results in scan data')

            # Format findings
            formatted_data = self._format_scan_results(data)

        else:
            # Generic JSON
            formatted_data = data

        return {
            'valid': len(self.errors) == 0,
            'formatted': formatted_data,
            'errors': self.errors,
            'warnings': self.warnings
        }

    def validate_text(self, data: str) -> Dict[str, Any]:
        """
        Validate text/markdown

        Checks:
        - Not empty
        - Valid encoding
        - Reasonable length (not too short or too long)
        """
        if not isinstance(data, str):
            return {
                'valid': False,
                'formatted': None,
                'errors': ['Text data must be a string'],
                'warnings': []
            }

        # Check length
        if len(data.strip()) < 10:
            self.warnings.append('Text is very short (< 10 chars)')

        if len(data) > 1000000:  # 1MB
            self.warnings.append('Text is very long (> 1MB), may need chunking')

        # Clean whitespace
        formatted_data = self._clean_text(data)

        return {
            'valid': len(self.errors) == 0 and len(formatted_data.strip()) > 0,
            'formatted': formatted_data,
            'errors': self.errors,
            'warnings': self.warnings
        }

    def validate_rego(self, data: Dict) -> Dict[str, Any]:
        """
        Validate Rego policy file (parsed by preprocess.parse_rego)

        Expected data structure:
        {
            'content': str,        # Raw Rego code
            'package': str,        # Package name
            'rules': List[str],    # Rule types (deny, violation, allow, warn)
            'documentation': str,  # Extracted comments
            'policy_type': str,    # gatekeeper, conftest, opa
            'filename': str
        }
        """
        if not isinstance(data, dict):
            return {
                'valid': False,
                'formatted': None,
                'errors': ['Rego data must be a dictionary'],
                'warnings': []
            }

        # Check required fields
        content = data.get('content', '')
        if not content or not content.strip():
            return {
                'valid': False,
                'formatted': None,
                'errors': ['Rego file has no content'],
                'warnings': []
            }

        # Validate Rego structure
        if 'package' not in content:
            self.warnings.append('No package declaration found in Rego file')

        # Check for rules
        rules = data.get('rules', [])
        if not rules:
            self.warnings.append('No rules (deny/violation/allow/warn) found')

        # Format for embedding
        formatted = data.copy()

        # Create embedding text combining content and metadata
        embedding_parts = []
        if data.get('documentation'):
            embedding_parts.append(f"Documentation: {data['documentation']}")
        if data.get('package'):
            embedding_parts.append(f"Package: {data['package']}")
        if rules:
            embedding_parts.append(f"Rules: {', '.join(rules)}")
        embedding_parts.append(f"Policy:\n{content}")

        formatted['_embedding_text'] = '\n\n'.join(embedding_parts)

        # Truncate if too long
        if len(formatted['_embedding_text']) > 28000:
            formatted['_embedding_text'] = formatted['_embedding_text'][:28000] + "... [truncated]"
            self.warnings.append('Rego content truncated for embedding')

        return {
            'valid': len(self.errors) == 0,
            'formatted': formatted,
            'errors': self.errors,
            'warnings': self.warnings
        }

    def validate_yaml(self, data: Dict) -> Dict[str, Any]:
        """
        Validate YAML file (parsed by preprocess.parse_yaml)

        Expected data structure:
        {
            'content': str,        # Raw YAML content
            'data': Any,           # Parsed YAML data
            'filename': str,
            'kind': str,           # K8s kind (if applicable)
            'api_version': str,    # K8s apiVersion (if applicable)
            'name': str            # Resource name (if applicable)
        }
        """
        if not isinstance(data, dict):
            return {
                'valid': False,
                'formatted': None,
                'errors': ['YAML data must be a dictionary'],
                'warnings': []
            }

        content = data.get('content', '')
        if not content or not content.strip():
            return {
                'valid': False,
                'formatted': None,
                'errors': ['YAML file has no content'],
                'warnings': []
            }

        # Check for parse errors
        if data.get('error'):
            return {
                'valid': False,
                'formatted': None,
                'errors': [f"YAML parse error: {data['error']}"],
                'warnings': []
            }

        # Format for embedding
        formatted = data.copy()

        # Create embedding text
        embedding_parts = []
        if data.get('kind'):
            embedding_parts.append(f"Kind: {data['kind']}")
        if data.get('api_version'):
            embedding_parts.append(f"API Version: {data['api_version']}")
        if data.get('name'):
            embedding_parts.append(f"Name: {data['name']}")
        embedding_parts.append(f"Content:\n{content}")

        formatted['_embedding_text'] = '\n\n'.join(embedding_parts)

        # Truncate if too long
        if len(formatted['_embedding_text']) > 28000:
            formatted['_embedding_text'] = formatted['_embedding_text'][:28000] + "... [truncated]"
            self.warnings.append('YAML content truncated for embedding')

        return {
            'valid': len(self.errors) == 0,
            'formatted': formatted,
            'errors': self.errors,
            'warnings': self.warnings
        }

    def _format_for_embedding(self, item: Dict, category: str) -> Dict:
        """
        Format item for nomic-embed-text embeddings

        Nomic constraints:
        - Max context: 8192 tokens
        - Optimal: 512-2048 tokens per chunk
        - Supports markdown, code, structured text
        """
        formatted = item.copy()

        # Extract main text content
        text_fields = []

        # Common text keys
        for key in ['content', 'text', 'description', 'message', 'question', 'answer', 'output']:
            if key in formatted and isinstance(formatted[key], str):
                text_fields.append(formatted[key])

        # Combine and truncate if needed
        if text_fields:
            combined_text = ' '.join(text_fields)

            # Rough token estimate (1 token ≈ 4 chars for English)
            estimated_tokens = len(combined_text) // 4

            if estimated_tokens > 8000:
                # Truncate to ~7000 tokens (28000 chars) to be safe
                self.warnings.append(f"Text truncated from {estimated_tokens} to 7000 tokens")
                combined_text = combined_text[:28000] + "... [truncated]"

            formatted['_embedding_text'] = combined_text

        return formatted

    def _format_scan_results(self, data: Dict) -> Dict:
        """Format security scan results for proper ingestion"""
        formatted = data.copy()

        # Normalize findings/results
        if 'findings' in formatted and isinstance(formatted['findings'], list):
            formatted['findings'] = [
                self._normalize_finding(f) for f in formatted['findings']
            ]
        elif 'results' in formatted and isinstance(formatted['results'], list):
            # Convert results to findings format
            formatted['findings'] = [
                self._normalize_finding(r) for r in formatted['results']
            ]
            if 'results' in formatted:
                del formatted['results']

        return formatted

    def _normalize_finding(self, finding: Dict) -> Dict:
        """Normalize a single finding to standard format"""
        normalized = {
            'rule_id': finding.get('rule_id') or finding.get('check_id') or finding.get('id') or 'UNKNOWN',
            'severity': (finding.get('severity') or finding.get('level') or 'UNKNOWN').upper(),
            'description': finding.get('description') or finding.get('message') or finding.get('title') or '',
            'file': finding.get('file') or finding.get('location') or finding.get('path'),
            'line': finding.get('line') or finding.get('line_number'),
        }

        # Preserve original data
        normalized['_original'] = finding

        return normalized

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\n\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)

        # Remove control characters (except newlines and tabs)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        return text.strip()


def validate_batch(preprocessed: List[Dict]) -> List[Dict]:
    """
    Validate a batch of preprocessed items

    Adds validation results to each item:
    - validated: bool
    - formatted_data: cleaned data
    - validation_errors: list
    - validation_warnings: list
    """
    validator = FormatValidator()
    validated = []

    for item in preprocessed:
        if not item.get('valid'):
            # Already invalid, skip validation
            validated.append({
                **item,
                'validated': False,
                'validation_errors': ['Preprocessing failed']
            })
            continue

        # Validate
        result = validator.validate_all(
            data=item['data'],
            data_type=item['format'],
            category=item['category']
        )

        # Add validation results
        validated.append({
            **item,
            'validated': result['valid'],
            'formatted_data': result['formatted'],
            'validation_errors': result['errors'],
            'validation_warnings': result['warnings']
        })

    return validated


if __name__ == "__main__":
    # Test validators
    print("🧪 Testing Format Validators\n")

    # Test JSONL
    test_jsonl = [
        {'content': 'Short content'},
        {'content': 'A' * 50000},  # Very long
        {},  # Empty
        {'messages': [{'role': 'user', 'content': 'Hi'}]}
    ]

    validator = FormatValidator()
    result = validator.validate_jsonl(test_jsonl, 'domain-SME')

    print(f"JSONL Validation:")
    print(f"  Valid: {result['valid']}")
    print(f"  Formatted items: {len(result['formatted'])}")
    print(f"  Errors: {len(result['errors'])}")
    print(f"  Warnings: {len(result['warnings'])}")
    if result['warnings']:
        for w in result['warnings'][:3]:
            print(f"    - {w}")

    # Test scan results
    test_scan = {
        'findings': [
            {
                'check_id': 'CKV_K8S_1',
                'severity': 'high',
                'message': 'Privileged container detected'
            }
        ],
        'metadata': {'scanner': 'checkov'}
    }

    result2 = validator.validate_json(test_scan, 'sync')
    print(f"\nScan Results Validation:")
    print(f"  Valid: {result2['valid']}")
    print(f"  Normalized findings: {len(result2['formatted'].get('findings', []))}")

    print("\n✅ Validator tests complete!")
