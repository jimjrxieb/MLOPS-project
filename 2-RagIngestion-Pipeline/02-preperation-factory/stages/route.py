#!/usr/bin/env python3
"""
Stage 4: Route Data
Intelligently decide: SQL, RAG, or BOTH
"""

from pathlib import Path
from typing import Dict, Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def route_item(sanitized_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route item to SQL, RAG, or BOTH

    Routing Rules:
    - Scan results (sync/) → SQL + RAG summary
    - People/reports (client-intake/) → SQL
    - Training data (domain-SME/) → RAG
    - Documentation (projects-docs/) → RAG
    - Sessions → RAG
    - Troubleshooting → RAG
    """
    if not sanitized_item['valid'] or not sanitized_item['sanitized']:
        return {**sanitized_item, 'destination': 'SKIP', 'reason': 'Invalid or unsanitized'}

    category = sanitized_item['category']
    data = sanitized_item['data']
    file_format = sanitized_item['format']

    # Apply routing rules
    if category == 'sync':
        # Scan results
        if is_scan_result(data):
            return {
                **sanitized_item,
                'destination': 'BOTH',
                'sql_table': 'findings',
                'rag_collection': 'jade-projects',
                'create_summary': True,
                'reason': 'Scan results need SQL (exact queries) + RAG (semantic queries)'
            }
        else:
            return {
                **sanitized_item,
                'destination': 'RAG',
                'rag_collection': 'jade-projects',
                'reason': 'Sync data without findings → RAG only'
            }

    elif category == 'client-intake':
        # Check data type
        if is_people_data(data):
            return {
                **sanitized_item,
                'destination': 'SQL',
                'sql_table': 'people',
                'reason': 'People data → SQL for structured queries'
            }
        elif is_report_data(data):
            return {
                **sanitized_item,
                'destination': 'SQL',
                'sql_table': 'reports',
                'reason': 'Report data → SQL for tracking'
            }
        else:
            return {
                **sanitized_item,
                'destination': 'RAG',
                'rag_collection': 'clients',
                'reason': 'Client info without structure → RAG'
            }

    elif category == 'compliance' or category == 'nist-800-53':
        # Check if it's CCSP data
        if any('ccsp' in str(item).lower() for item in data) if isinstance(data, list) else 'ccsp' in str(data).lower():
            return {
                **sanitized_item,
                'destination': 'RAG',
                'rag_collection': 'jade-ccsp',
                'reason': 'CCSP domain summaries → Dedicated CCSP collection'
            }
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-nist-800-53',
            'reason': 'NIST 800-53 controls → Dedicated compliance collection'
        }

    elif category == 'domain-SME':
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-domain-sme',
            'reason': 'Training data → RAG for semantic search'
        }

    elif category == 'projects-docs':
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-projects',
            'reason': 'Project documentation → RAG'
        }

    elif category in ['sessions', 'session-docs', 'chat-session-docs']:
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-sessions',
            'reason': 'Session notes → RAG'
        }

    elif category == 'troubleshooting':
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-troubleshooting',
            'reason': 'Debugging guides → RAG'
        }

    elif category == 'consulting-knowledge':
        # Platform engineering playbooks, cheatsheets, PBPs — high-value for dev support
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-consulting',
            'reason': 'Consulting knowledge (PBPs, cheatsheets, guides) → Dedicated consulting collection'
        }

    elif category in ['opa-policies']:
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-policy-as-code',
            'reason': 'OPA/Rego policies → Dedicated policy-as-code collection'
        }

    elif category in ['claudecode-sessions', 'claudecode-as-jade-sessions', 'jade-chat-session']:
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-sessions',
            'reason': 'Claude/JADE sessions → Sessions collection'
        }

    elif category == 'operational-training-data':
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-operational',
            'reason': 'JSA operational training data → Operational knowledge collection'
        }

    elif category == 'webscraper':
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-general',
            'reason': 'Scraped security docs → General collection'
        }

    elif category == 'yt-transcripts':
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-general',
            'reason': 'YouTube transcripts → General collection'
        }

    elif category in ['windows-sync', 'night-learning', 'agent-research', 'meeting-notes']:
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-general',
            'reason': f'{category} data → RAG (general collection)'
        }

    else:
        # Unknown category - use LLM-assisted routing (future)
        return {
            **sanitized_item,
            'destination': 'RAG',
            'rag_collection': 'jade-general',
            'reason': f'Unknown category ({category}) → RAG (default)'
        }


def is_scan_result(data: Any) -> bool:
    """Check if data is a security scan result"""
    if isinstance(data, dict):
        # Check for common scan result keys
        has_findings = 'findings' in data
        has_results = 'results' in data
        has_metadata = 'metadata' in data
        has_scanner = 'scanner' in data if 'metadata' in data else False

        return has_findings or (has_metadata and (has_results or has_scanner))

    return False


def is_people_data(data: Any) -> bool:
    """Check if data contains people information"""
    if isinstance(data, dict):
        people_keys = {'name', 'email', 'company', 'contact', 'person', 'client'}
        return bool(people_keys & set(data.keys()))

    elif isinstance(data, str):
        # Check for patterns in text
        people_indicators = ['contact', 'email', 'phone', 'name:', 'client:']
        return any(indicator in data.lower() for indicator in people_indicators)

    return False


def is_report_data(data: Any) -> bool:
    """Check if data is a report"""
    if isinstance(data, dict):
        report_keys = {'report', 'assessment', 'audit', 'compliance', 'summary'}
        return bool(report_keys & set(data.keys()))

    elif isinstance(data, str):
        report_indicators = ['report', 'assessment', 'audit', 'compliance']
        return any(indicator in data.lower() for indicator in report_indicators)

    return False


def route_batch(sanitized: list) -> list:
    """Route all sanitized items"""
    routed = []

    for item in sanitized:
        result = route_item(item)
        routed.append(result)

    return routed


if __name__ == "__main__":
    # Test routing
    test_cases = [
        {
            'category': 'sync',
            'format': '.json',
            'data': {'findings': [], 'metadata': {'scanner': 'bandit'}},
            'valid': True,
            'sanitized': True
        },
        {
            'category': 'domain-SME',
            'format': '.jsonl',
            'data': [{'messages': []}],
            'valid': True,
            'sanitized': True
        },
        {
            'category': 'client-intake',
            'format': '.json',
            'data': {'name': 'John Doe', 'email': 'john@example.com'},
            'valid': True,
            'sanitized': True
        }
    ]

    print("\n🧭 Routing Test")
    print("="*60)
    for case in test_cases:
        routed = route_item(case)
        print(f"\nCategory: {case['category']}")
        print(f"Destination: {routed['destination']}")
        print(f"Reason: {routed['reason']}")
        if routed.get('rag_collection'):
            print(f"RAG Collection: {routed['rag_collection']}")
        if routed.get('sql_table'):
            print(f"SQL Table: {routed['sql_table']}")
    print("="*60)
