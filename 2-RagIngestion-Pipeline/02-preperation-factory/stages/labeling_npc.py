#!/usr/bin/env python3
"""
NPC: Labeling & Metadata Enhancement
=====================================

Add intelligent labels for enhanced LangChain/LangGraph retrieval.

Assembly Line Position: #4 (after format_conversion_npc)
Next NPC: preprocess_npc

What this NPC does:
- Detects domain (kubernetes, terraform, opa, docker, cloud)
- Detects type (documentation, troubleshooting, policy, example, fix)
- Assigns difficulty (beginner, intermediate, advanced)
- Extracts tags for retrieval
- Critical for LangChain/LangGraph filtering
"""

from pathlib import Path
from typing import Dict, Any, List, Set
import json
import re
import sys
from datetime import datetime

# Import security ontology for concept extraction (Tier 1 labeling)
ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "04-ingesting"
sys.path.insert(0, str(ONTOLOGY_PATH))

try:
    from security_ontology import (
        extract_security_concepts,
        get_related_concepts,
        enrich_document_with_concepts
    )
    HAS_SECURITY_ONTOLOGY = True
except ImportError:
    HAS_SECURITY_ONTOLOGY = False

# Tier 3: Claude API for semantic labeling (slow, paid, high quality)
import os
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Claude labeling prompt template
CLAUDE_LABELING_PROMPT = """Analyze this security-related content and provide structured labels.

Content:
{content}

Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "domain": ["<primary domain>", "<secondary if applicable>"],
    "type": ["<content type>"],
    "difficulty": "<beginner|intermediate|advanced>",
    "tags": ["<tag1>", "<tag2>", "<tag3>", "<tag4>", "<tag5>"]
}}

Domains: kubernetes, terraform, opa, docker, cloud, security, sast, secrets, compliance, cicd, aws, azure, gcp
Types: documentation, troubleshooting, policy, example, fix, configuration, best-practice, vulnerability, tutorial
Tags: Extract 3-5 specific technical terms from the content (e.g., "NetworkPolicy", "CVE-2021-44228", "runAsNonRoot")"""


class LabelingNPC:
    """
    NPC for intelligent labeling and metadata enhancement.

    Input: Normalized JSONL from format_conversion_npc
    Output: JSONL with enhanced metadata labels

    Enhanced Metadata Structure:
    {
        "content": "...",
        "metadata": {
            ...existing metadata...,
            "domain": ["kubernetes", "docker"],
            "type": ["documentation", "troubleshooting"],
            "difficulty": "intermediate",
            "tags": ["pod", "security", "networkpolicy"],
            "labeled_at": "2025-11-17T12:00:00"
        }
    }
    """

    def __init__(self, use_claude_api: bool = False, claude_model: str = "claude-3-5-haiku-latest"):
        """
        Initialize LabelingNPC.

        Args:
            use_claude_api: Enable Tier 3 Claude API labeling for docs with no concepts
            claude_model: Claude model to use (default: haiku for cost efficiency)
        """
        self.use_claude_api = use_claude_api and HAS_ANTHROPIC
        self.claude_model = claude_model
        self.claude_client = None

        # Initialize Claude client if enabled
        if self.use_claude_api:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                self.claude_client = anthropic.Anthropic(api_key=api_key)
            else:
                print("Warning: ANTHROPIC_API_KEY not set, Claude labeling disabled")
                self.use_claude_api = False

        self.stats = {
            'processed': 0,
            'labeled': 0,
            'failed': 0,
            'claude_labeled': 0,
            'ontology_labeled': 0
        }

        # Domain detection patterns
        self.domain_patterns = {
            'kubernetes': [
                r'\bkubernetes\b', r'\bk8s\b', r'\bkubectl\b', r'\bpod\b',
                r'\bdeployment\b', r'\bservice\b', r'\bingress\b',
                r'\bnamespace\b', r'\bhelm\b', r'\bkustomize\b',
                r'\bstatefulset\b', r'\bdaemonset\b', r'\bconfigmap\b'
            ],
            'terraform': [
                r'\bterraform\b', r'\b\.tf\b', r'\bresource\b',
                r'\bvariable\b', r'\bmodule\b', r'\bprovider\b',
                r'\baws_\w+', r'\bazure_\w+', r'\bgcp_\w+'
            ],
            'opa': [
                r'\bopa\b', r'\brego\b', r'\bopen policy agent\b',
                r'\bpolicy\b', r'\bconstraint\b', r'\bgatekeeper\b',
                r'\bconftest\b', r'\bdeny\b.*\brule\b'
            ],
            'docker': [
                r'\bdocker\b', r'\bcontainer\b', r'\bimage\b',
                r'\bdockerfile\b', r'\bdocker-compose\b',
                r'\bdocker\s+build\b', r'\bdocker\s+run\b'
            ],
            'cloud': [
                r'\baws\b', r'\bazure\b', r'\bgcp\b', r'\bcloud\b',
                r'\bs3\b', r'\bec2\b', r'\blambda\b', r'\bvpc\b',
                r'\biam\b', r'\bsecurity\s+group\b'
            ],
            'security': [
                r'\bsecurity\b', r'\bvulnerability\b', r'\bcve\b',
                r'\bscan\b', r'\btrivy\b', r'\bbandit\b', r'\bsemgrep\b',
                r'\bsql injection\b', r'\bxss\b', r'\brbac\b'
            ]
        }

        # Type detection patterns
        self.type_patterns = {
            'documentation': [
                r'^#\s+.*\b(guide|overview|introduction|readme)\b',
                r'\bthis document\b', r'\bdocumentation\b',
                r'\breference\b.*\bguide\b'
            ],
            'troubleshooting': [
                r'\berror\b', r'\bfailed\b', r'\btroubleshoot\b',
                r'\bproblem\b', r'\bissue\b', r'\bdebug\b',
                r'\bcrash\b', r'\bfixing\b', r'\bhow to fix\b'
            ],
            'policy': [
                r'package\s+\w+', r'deny\s*\[', r'violation\s*\[',
                r'apiVersion:\s*constraints', r'kind:\s*ConstraintTemplate',
                r'\bpolicy\s+enforcement\b'
            ],
            'example': [
                r'\bexample\b', r'\bsample\b', r'\btemplate\b',
                r'\bdemo\b', r'##\s*Example', r'```.*example'
            ],
            'fix': [
                r'\bfix\b', r'\bremediation\b', r'\bsolution\b',
                r'\brepair\b', r'\bresolve\b', r'how to fix'
            ],
            'configuration': [
                r'\bconfig\b', r'\bconfiguration\b', r'\.yaml\b',
                r'\.json\b', r'\bsettings\b'
            ]
        }

        # Difficulty indicators
        self.difficulty_indicators = {
            'beginner': [
                r'\bbasic\b', r'\bgetting started\b', r'\bintroduction\b',
                r'\bbeginner\b', r'\bsimple\b', r'\bquick start\b'
            ],
            'intermediate': [
                r'\bintermediate\b', r'\bconfiguration\b', r'\bcustomize\b',
                r'\bintegration\b', r'\badvanced config\b'
            ],
            'advanced': [
                r'\badvanced\b', r'\bcomplex\b', r'\bproduction\b',
                r'\boptimization\b', r'\bperformance tuning\b',
                r'\bcustom implementation\b'
            ]
        }

    def process(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add intelligent labels to JSONL item.

        Returns:
            {
                ...item,
                'data': [  # Enhanced JSONL items
                    {
                        'content': '...',
                        'metadata': {
                            ...existing...,
                            'domain': [...],
                            'type': [...],
                            'difficulty': '...',
                            'tags': [...]
                        }
                    }
                ]
            }
        """
        self.stats['processed'] += 1

        try:
            # Get JSONL data from previous NPC
            if 'data' not in item or not isinstance(item['data'], list):
                self.stats['failed'] += 1
                return {
                    **item,
                    'error': 'Invalid data format - expected JSONL list',
                    'labeled': False
                }

            # Process each JSONL item
            labeled_items = []
            for jsonl_item in item['data']:
                labeled_item = self._label_item(jsonl_item, item.get('source', 'unknown'))
                labeled_items.append(labeled_item)

            self.stats['labeled'] += 1

            return {
                **item,
                'data': labeled_items,
                'labeled': True,
                'labeling_applied': True
            }

        except Exception as e:
            self.stats['failed'] += 1
            return {
                **item,
                'error': f'Labeling failed: {e}',
                'labeled': False
            }

    def _label_item(self, item: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Add labels to a single JSONL item"""
        content = item.get('content', '')
        metadata = item.get('metadata', {})

        # Tier 1: Security Ontology extraction (fast, precise)
        security_concepts = []
        related_concepts = []
        if HAS_SECURITY_ONTOLOGY:
            # Extract CVE, CWE, scanner codes, K8s resources, etc.
            extracted = extract_security_concepts(content)
            for concept_type, concepts in extracted.items():
                security_concepts.extend([f"{concept_type}:{c}" for c in concepts])

            # Get related concepts for enhanced retrieval
            for concept_type, concepts in extracted.items():
                for concept in concepts:
                    related = get_related_concepts(concept, depth=1)
                    related_concepts.extend(list(related)[:5])  # Limit per concept

        # Tier 2: Pattern-based labeling (existing regex)
        domains = self._detect_domains(content)
        types = self._detect_types(content)
        difficulty = self._determine_difficulty(content)
        tags = self._extract_tags(content, domains, types)

        # Merge ontology concepts into tags
        if security_concepts:
            tags = list(set(tags + security_concepts[:20]))  # Limit total

        # Enhance metadata
        enhanced_metadata = {
            **metadata,
            'domain': domains,
            'type': types,
            'difficulty': difficulty,
            'tags': tags,
            'labeled_at': datetime.now().isoformat()
        }

        # Add security ontology fields if concepts found
        if security_concepts:
            enhanced_metadata['security_concepts'] = security_concepts
            enhanced_metadata['has_security_concepts'] = True
            self.stats['ontology_labeled'] += 1
        if related_concepts:
            enhanced_metadata['related_concepts'] = list(set(related_concepts))[:15]

        # Tier 3: Claude API fallback for docs with no concepts extracted
        if not security_concepts and self.use_claude_api and self.claude_client:
            claude_labels = self._claude_label(content)
            if claude_labels:
                # Merge Claude labels (override weak pattern matches)
                if claude_labels.get('domain'):
                    enhanced_metadata['domain'] = claude_labels['domain']
                if claude_labels.get('type'):
                    enhanced_metadata['type'] = claude_labels['type']
                if claude_labels.get('difficulty'):
                    enhanced_metadata['difficulty'] = claude_labels['difficulty']
                if claude_labels.get('tags'):
                    enhanced_metadata['tags'] = list(set(tags + claude_labels['tags']))[:20]
                enhanced_metadata['claude_labeled'] = True
                self.stats['claude_labeled'] += 1

        return {
            'content': content,
            'metadata': enhanced_metadata
        }

    def _claude_label(self, content: str) -> Dict[str, Any]:
        """
        Tier 3: Use Claude API for semantic labeling.
        Only called when no security concepts were extracted by ontology.

        Args:
            content: Document content to label

        Returns:
            Dict with domain, type, difficulty, tags or empty dict on failure
        """
        if not self.claude_client:
            return {}

        try:
            # Truncate content to avoid token limits (first 2000 chars)
            truncated = content[:2000] if len(content) > 2000 else content

            message = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=256,
                messages=[
                    {"role": "user", "content": CLAUDE_LABELING_PROMPT.format(content=truncated)}
                ]
            )

            # Parse JSON response
            response_text = message.content[0].text.strip()
            # Handle potential markdown code blocks
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            labels = json.loads(response_text)
            return labels

        except json.JSONDecodeError:
            return {}
        except Exception as e:
            # Silently fail - Claude labeling is optional enhancement
            return {}

    def _detect_domains(self, content: str) -> List[str]:
        """Detect domain labels from content"""
        content_lower = content.lower()
        detected = []

        for domain, patterns in self.domain_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    detected.append(domain)
                    break  # Domain found, no need to check other patterns

        return detected if detected else ['general']

    def _detect_types(self, content: str) -> List[str]:
        """Detect type labels from content"""
        content_lower = content.lower()
        detected = []

        for type_name, patterns in self.type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    detected.append(type_name)
                    break  # Type found, no need to check other patterns

        return detected if detected else ['general']

    def _determine_difficulty(self, content: str) -> str:
        """Determine difficulty level"""
        content_lower = content.lower()

        # Check for explicit difficulty markers
        for level, patterns in self.difficulty_indicators.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return level

        # Heuristic: Use complexity indicators
        # Advanced indicators
        if any(word in content_lower for word in ['production', 'enterprise', 'scale', 'optimization']):
            return 'advanced'

        # Beginner indicators
        if any(word in content_lower for word in ['getting started', 'introduction', 'basics', 'simple']):
            return 'beginner'

        # Default to intermediate
        return 'intermediate'

    def _extract_tags(self, content: str, domains: List[str], types: List[str]) -> List[str]:
        """Extract relevant tags from content"""
        tags = set()

        # Add domain-specific tags
        content_lower = content.lower()

        if 'kubernetes' in domains:
            k8s_tags = ['pod', 'deployment', 'service', 'ingress', 'configmap',
                        'secret', 'networkpolicy', 'rbac', 'psp', 'pdb']
            tags.update([tag for tag in k8s_tags if tag in content_lower])

        if 'terraform' in domains:
            tf_tags = ['resource', 'module', 'variable', 'output', 'provider',
                       'state', 'plan', 'apply']
            tags.update([tag for tag in tf_tags if tag in content_lower])

        if 'opa' in domains:
            opa_tags = ['policy', 'rego', 'constraint', 'deny', 'allow',
                        'violation', 'gatekeeper', 'conftest']
            tags.update([tag for tag in opa_tags if tag in content_lower])

        if 'security' in domains:
            sec_tags = ['vulnerability', 'cve', 'scan', 'compliance',
                        'hardening', 'encryption', 'secrets']
            tags.update([tag for tag in sec_tags if tag in content_lower])

        # Extract important technical terms (capitalized words, acronyms)
        # Match words like "CIS", "RBAC", "NGINX"
        acronyms = re.findall(r'\b[A-Z]{2,}\b', content)
        tags.update([a.lower() for a in acronyms[:5]])  # Limit to top 5

        return sorted(list(tags))[:10]  # Return top 10 tags

    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of items"""
        return [self.process(item) for item in items]

    def get_stats(self) -> Dict[str, Any]:
        """Get labeling statistics"""
        return {
            **self.stats,
            'success_rate': self.stats['labeled'] / max(self.stats['processed'], 1) * 100
        }


def main():
    """Test labeling NPC"""
    print("\n🏷️  Labeling NPC - Metadata Enhancement Test")
    print("=" * 70)

    npc = LabelingNPC()

    # Test cases (simulating output from format_conversion_npc)
    test_items = [
        # Kubernetes documentation
        {
            'data': [
                {
                    'content': '# Kubernetes Pod Security\n\nThis guide covers Pod Security Standards (PSS) and how to configure security contexts for pods.',
                    'metadata': {
                        'source': 'k8s-security.md',
                        'original_format': '.md',
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                }
            ],
            'format': '.jsonl',
            'source': 'k8s-security.md'
        },
        # OPA policy
        {
            'data': [
                {
                    'content': 'package kubernetes.admission\n\ndeny[msg] {\n  input.kind == "Pod"\n  not input.spec.securityContext.runAsNonRoot\n  msg = "Pods must not run as root"\n}',
                    'metadata': {
                        'source': 'deny-root.rego',
                        'original_format': '.txt',
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                }
            ],
            'format': '.jsonl',
            'source': 'deny-root.rego'
        },
        # Troubleshooting guide
        {
            'data': [
                {
                    'content': 'Error: CrashLoopBackOff\n\nHow to fix: Check pod logs with kubectl logs <pod> and verify container image exists.',
                    'metadata': {
                        'source': 'troubleshooting.txt',
                        'original_format': '.txt',
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                }
            ],
            'format': '.jsonl',
            'source': 'troubleshooting.txt'
        },
        # Terraform AWS example
        {
            'data': [
                {
                    'content': 'resource "aws_security_group" "example" {\n  name = "example"\n  vpc_id = var.vpc_id\n\n  ingress {\n    from_port = 443\n    to_port = 443\n    protocol = "tcp"\n  }\n}',
                    'metadata': {
                        'source': 'aws-sg.tf',
                        'original_format': '.txt',
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                }
            ],
            'format': '.jsonl',
            'source': 'aws-sg.tf'
        }
    ]

    for i, item in enumerate(test_items, 1):
        print(f"\n[Test {i}] Labeling: {item['source']}")
        result = npc.process(item)

        if 'error' in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ✅ Labeled: {result['labeled']}")

            # Show labels for first item
            if result['data']:
                first_item = result['data'][0]
                meta = first_item['metadata']

                print(f"  🏷️  Domains: {', '.join(meta.get('domain', []))}")
                print(f"  📋 Types: {', '.join(meta.get('type', []))}")
                print(f"  🎯 Difficulty: {meta.get('difficulty', 'unknown')}")
                print(f"  🏷️  Tags: {', '.join(meta.get('tags', [])[:5])}...")  # Show first 5

    print("\n" + "=" * 70)
    print("📊 Statistics:")
    stats = npc.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 70)

    # Demo: LangChain/LangGraph filtering
    print("\n🔍 LangChain/LangGraph Filtering Examples:")
    print("=" * 70)
    print("Filter by domain:")
    print("  chromadb.query(filter={'metadata.domain': {'$contains': 'kubernetes'}})")
    print("\nFilter by type:")
    print("  chromadb.query(filter={'metadata.type': {'$contains': 'troubleshooting'}})")
    print("\nFilter by difficulty:")
    print("  chromadb.query(filter={'metadata.difficulty': 'beginner'})")
    print("\nComplex filter:")
    print("  chromadb.query(filter={")
    print("    '$and': [")
    print("      {'metadata.domain': {'$contains': 'kubernetes'}},")
    print("      {'metadata.type': {'$contains': 'policy'}},")
    print("      {'metadata.difficulty': {'$in': ['intermediate', 'advanced']}}")
    print("    ]")
    print("  })")
    print("=" * 70)


if __name__ == "__main__":
    main()
