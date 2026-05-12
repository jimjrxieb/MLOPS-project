#!/usr/bin/env python3
"""
Stage 2: Preprocess Files
Validate, parse, and convert file formats
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import validators
try:
    from stages.validators import FormatValidator
    HAS_VALIDATORS = True
except ImportError:
    HAS_VALIDATORS = False

def preprocess_file(file_path: Path, category: str) -> Optional[Dict[str, Any]]:
    """
    Preprocess a single file based on its type and category

    Returns:
        {
            'file': Path,
            'category': str,
            'format': str,
            'data': Any,
            'valid': bool,
            'error': Optional[str],
            'formatted_data': Any,  # Cleaned/validated data
            'validation_warnings': List[str]
        }
    """
    try:
        # Determine file type
        suffix = file_path.suffix.lower()

        if suffix == '.jsonl':
            data = parse_jsonl(file_path)
            valid = validate_jsonl_structure(data)

        elif suffix == '.json':
            data = parse_json(file_path)
            valid = validate_json_structure(data, category)

        elif suffix in ['.md', '.txt']:
            data = parse_text(file_path)
            valid = bool(data.strip())

        elif suffix == '.rego':
            data = parse_rego(file_path)
            valid = bool(data.get('content', '').strip())

        elif suffix in ['.yaml', '.yml']:
            data = parse_yaml(file_path)
            valid = bool(data.get('content', '').strip()) and 'error' not in data

        else:
            return {
                'file': file_path,
                'category': category,
                'format': suffix,
                'data': None,
                'valid': False,
                'error': f'Unsupported file type: {suffix}'
            }

        result = {
            'file': file_path,
            'category': category,
            'format': suffix,
            'data': data,
            'valid': valid,
            'error': None
        }

        # Run format validators if available
        if HAS_VALIDATORS and valid:
            validator = FormatValidator()
            validation_result = validator.validate_all(data, suffix, category)

            result['formatted_data'] = validation_result['formatted']
            result['validation_warnings'] = validation_result['warnings']

            if not validation_result['valid']:
                result['valid'] = False
                result['error'] = '; '.join(validation_result['errors'])
        else:
            result['formatted_data'] = data
            result['validation_warnings'] = []

        return result

    except Exception as e:
        return {
            'file': file_path,
            'category': category,
            'format': file_path.suffix,
            'data': None,
            'valid': False,
            'error': str(e),
            'formatted_data': None,
            'validation_warnings': []
        }


def parse_jsonl(file_path: Path) -> list:
    """Parse JSONL file (one JSON object per line)"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                data.append(obj)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}: {e}")
    return data


def parse_json(file_path: Path) -> Any:
    """Parse JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_text(file_path: Path) -> str:
    """Parse text/markdown file"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def parse_rego(file_path: Path) -> Dict[str, Any]:
    """
    Parse Rego policy file into RAG-friendly structure.

    Extracts:
    - Package name
    - Rule names
    - Comments/documentation
    - Full content for RAG retrieval
    """
    import re

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract package name
    package_match = re.search(r'^package\s+([\w.]+)', content, re.MULTILINE)
    package_name = package_match.group(1) if package_match else 'unknown'

    # Extract rule names (deny, violation, allow, etc.)
    rules = re.findall(r'^(deny|violation|allow|warn)\s*\[', content, re.MULTILINE)

    # Extract comments (potential documentation)
    comments = re.findall(r'^#\s*(.+)$', content, re.MULTILINE)

    # Determine policy type
    if 'gatekeeper' in file_path.parts or 'violation' in content:
        policy_type = 'gatekeeper'
    elif 'conftest' in file_path.parts or 'deny' in content:
        policy_type = 'conftest'
    else:
        policy_type = 'opa'

    return {
        'content': content,
        'package': package_name,
        'rules': list(set(rules)),
        'documentation': '\n'.join(comments[:10]),  # First 10 comments
        'policy_type': policy_type,
        'filename': file_path.name
    }


def parse_yaml(file_path: Path) -> Dict[str, Any]:
    """Parse YAML file (policies, k8s manifests, GHA workflows, etc.)

    Handles:
    - Multi-document YAML (--- separators) via safe_load_all
    - GHA workflows where PyYAML parses 'on:' as boolean True
    """
    try:
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            return {'content': '', 'error': 'YAML file has no content', 'filename': file_path.name}

        # Parse all documents (handles multi-doc YAML with --- separators)
        all_docs = [doc for doc in yaml.safe_load_all(content) if doc is not None]

        if not all_docs:
            # File has content but YAML parsed to nothing (comment-only docs)
            # Treat raw content as the data — still valuable for RAG
            return {
                'content': content,
                'data': None,
                'filename': file_path.name,
                'kind': 'raw-yaml',
                'multi_doc': False
            }

        # Single doc vs multi-doc
        if len(all_docs) == 1:
            data = all_docs[0]
            multi_doc = False
        else:
            data = all_docs
            multi_doc = True

        result = {
            'content': content,
            'data': data,
            'filename': file_path.name,
            'multi_doc': multi_doc
        }

        # Extract K8s metadata from first meaningful doc
        first_doc = all_docs[0] if all_docs else {}
        if isinstance(first_doc, dict):
            result['kind'] = str(first_doc.get('kind', 'unknown'))
            result['api_version'] = str(first_doc.get('apiVersion', ''))
            if 'metadata' in first_doc and isinstance(first_doc['metadata'], dict):
                result['name'] = str(first_doc['metadata'].get('name', ''))

            # Detect GHA workflows (have 'on' key parsed as True by PyYAML)
            if True in first_doc or 'jobs' in first_doc:
                result['kind'] = 'github-actions-workflow'

        if multi_doc:
            # Summarize doc kinds for multi-doc manifests
            kinds = []
            for doc in all_docs:
                if isinstance(doc, dict) and 'kind' in doc:
                    kinds.append(str(doc['kind']))
            if kinds:
                result['doc_kinds'] = kinds

        return result
    except Exception as e:
        return {'content': '', 'error': str(e), 'filename': file_path.name}


def validate_jsonl_structure(data: list) -> bool:
    """
    Validate JSONL structure for training and knowledge data

    Accepts any JSON object (dict) with at least 2 keys and some meaningful content.
    This lenient validation allows diverse knowledge formats while filtering out
    empty or malformed data.

    Common formats include:
    - Training: {"messages": [...]}
    - Instruction: {"instruction": "...", "output": "..."}
    - Q&A: {"question": "...", "answer": "..."}
    - Documents: {"doc_id": "...", "text": "..."}
    - Troubleshooting: {"problem": "...", "solution": "..."}
    - Entities: {"entity_id": "...", "type": "..."}
    - Relationships: {"head": "...", "relation": "...", "tail": "..."}
    - And many more...
    """
    if not data:
        return False

    for item in data:
        # Must be a dictionary
        if not isinstance(item, dict):
            return False

        # Must have at least one key
        if len(item) < 1:
            return False

        # Must have at least one non-empty value (meaningful content)
        has_content = False
        for value in item.values():
            if isinstance(value, str) and value.strip():
                has_content = True
                break
            elif isinstance(value, (list, dict)) and value:
                has_content = True
                break

        if not has_content:
            return False

    return True


def validate_json_structure(data: Any, category: str) -> bool:
    """
    Validate JSON structure based on category

    For scan results (category='sync'):
        - Should have 'findings' or 'results' key
        - Should have 'metadata' key
    """
    if category == 'sync':
        # Scan results validation
        if isinstance(data, dict):
            has_findings = 'findings' in data or 'results' in data
            has_metadata = 'metadata' in data
            return has_findings or has_metadata
        return False

    # General JSON validation (just check it's valid JSON)
    return data is not None


def preprocess_batch(discovered: Dict[str, list]) -> list:
    """Preprocess all discovered files"""
    preprocessed = []

    for category, files in discovered.items():
        for file_path in files:
            result = preprocess_file(file_path, category)
            if result:
                preprocessed.append(result)

    return preprocessed


if __name__ == "__main__":
    # Test preprocessing
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from stages import discover

    discovered = discover.discover_files()
    preprocessed = preprocess_batch(discovered)

    print(f"\n🔧 Preprocessing Report")
    print(f"{'='*60}")
    print(f"Files preprocessed: {len(preprocessed)}")
    print(f"Valid: {sum(1 for p in preprocessed if p['valid'])}")
    print(f"Invalid: {sum(1 for p in preprocessed if not p['valid'])}")
    print(f"{'='*60}\n")

    # Show errors
    errors = [p for p in preprocessed if not p['valid']]
    if errors:
        print("❌ Errors:")
        for item in errors[:5]:
            print(f"  - {item['file'].name}: {item['error']}")
