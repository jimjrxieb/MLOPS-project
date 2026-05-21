#!/usr/bin/env python3
"""
RAG Cleanup & Concept Linking
=============================

Phase 1: Remove redundant basic definitions JADE already knows
Phase 2: Build concept links (errors→fixes, CVE→remediation, finding→JSA)

Usage:
    python3 rag_cleanup.py --analyze          # Preview what would be removed
    python3 rag_cleanup.py --clean            # Remove basic definitions
    python3 rag_cleanup.py --link             # Add concept relationships
    python3 rag_cleanup.py --clean --link     # Both
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import argparse

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
RAG_ROOT = SCRIPT_DIR.parent  # GP-MODEL-OPS/2-RagIngestion-Pipeline/
MODEL_OPS_ROOT = RAG_ROOT.parent
GP_ROOT = MODEL_OPS_ROOT.parent
CHROMA_PATH = RAG_ROOT / "05-ragged-data" / "chroma"

# Basic definitions JADE v0.9 already knows from training
BASIC_PATTERNS = [
    # Kubernetes basics
    r"what is a (kubernetes )?pod\b",
    r"what is a (kubernetes )?deployment\b",
    r"what is a (kubernetes )?service\b",
    r"what is a (kubernetes )?namespace\b",
    r"what is a (kubernetes )?configmap\b",
    r"what is a (kubernetes )?secret\b",
    r"what is a (kubernetes )?node\b",
    r"what is a (kubernetes )?cluster\b",
    r"what is kubernetes\b",
    r"explain (kubernetes|k8s)\b",
    r"define (kubernetes|k8s)\b",
    # Generic definitions
    r"what is a container\b",
    r"what is docker\b",
    r"what is yaml\b",
    r"what is json\b",
    r"what is an api\b",
    r"what is rest\b",
    # Cloud basics
    r"what is aws\b",
    r"what is azure\b",
    r"what is gcp\b",
    r"what is cloud computing\b",
]

# Domain-specific content to KEEP (GuidePoint expertise)
KEEP_PATTERNS = [
    # JSA specific
    r"jsa-ci", r"jsa-devsecops", r"jsa agent",
    # Policy as Code
    r"gatekeeper", r"kyverno", r"opa", r"rego", r"conftest",
    r"constraint\s*template", r"cluster\s*policy",
    # Security tools
    r"trivy", r"bandit", r"semgrep", r"gitleaks", r"checkov",
    r"kubescape", r"polaris", r"grype", r"snyk",
    # Fixes and remediation
    r"how to fix", r"remediat", r"patch", r"CVE-\d+",
    r"securityContext", r"runAsNonRoot", r"readOnlyRootFilesystem",
    # GP-Copilot specific
    r"gp-copilot", r"jade", r"npc", r"fixer",
]


def load_chromadb():
    """Load ChromaDB client"""
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client


def analyze_collection(client, collection_name: str) -> Dict:
    """Analyze a collection for cleanup candidates"""
    try:
        coll = client.get_collection(collection_name)
    except:
        return {"error": f"Collection {collection_name} not found"}

    total = coll.count()
    if total == 0:
        return {"total": 0, "basic": 0, "keep": 0}

    # Sample in batches
    batch_size = 1000
    basic_ids = []
    keep_ids = []

    for offset in range(0, min(total, 10000), batch_size):  # Limit to 10k for speed
        sample = coll.get(
            limit=batch_size,
            offset=offset,
            include=['documents', 'metadatas']
        )

        for doc_id, doc in zip(sample['ids'], sample['documents']):
            doc_lower = doc.lower()

            # Check if it's basic content
            is_basic = any(re.search(p, doc_lower) for p in BASIC_PATTERNS)
            is_keep = any(re.search(p, doc_lower, re.I) for p in KEEP_PATTERNS)

            if is_basic and not is_keep:
                basic_ids.append(doc_id)
            elif is_keep:
                keep_ids.append(doc_id)

    return {
        "total": total,
        "sampled": min(total, 10000),
        "basic_to_remove": len(basic_ids),
        "domain_to_keep": len(keep_ids),
        "basic_ids": basic_ids[:100],  # Sample for preview
    }


def clean_collection(client, collection_name: str, dry_run: bool = True) -> Dict:
    """Remove basic definitions from collection"""
    try:
        coll = client.get_collection(collection_name)
    except:
        return {"error": f"Collection {collection_name} not found"}

    total = coll.count()
    removed_count = 0

    # Process in batches
    batch_size = 500
    ids_to_remove = []

    for offset in range(0, total, batch_size):
        sample = coll.get(
            limit=batch_size,
            offset=offset,
            include=['documents']
        )

        for doc_id, doc in zip(sample['ids'], sample['documents']):
            doc_lower = doc.lower()

            is_basic = any(re.search(p, doc_lower) for p in BASIC_PATTERNS)
            is_keep = any(re.search(p, doc_lower, re.I) for p in KEEP_PATTERNS)

            if is_basic and not is_keep:
                ids_to_remove.append(doc_id)

    if not dry_run and ids_to_remove:
        # Delete in batches
        for i in range(0, len(ids_to_remove), 100):
            batch = ids_to_remove[i:i+100]
            coll.delete(ids=batch)
            removed_count += len(batch)

    return {
        "total_before": total,
        "removed": removed_count if not dry_run else 0,
        "would_remove": len(ids_to_remove),
        "total_after": total - (removed_count if not dry_run else 0),
        "dry_run": dry_run
    }


def build_concept_links() -> List[Dict]:
    """Build concept relationship data for RAG"""

    links = []

    # Error → Fix mappings
    error_fix_links = [
        {
            "concept": "CKV_K8S_22",
            "type": "checkov_rule",
            "description": "Container does not have readOnlyRootFilesystem",
            "fix": "Add securityContext.readOnlyRootFilesystem: true to container spec",
            "jsa_agent": "jsa-devsecops",
            "rank": "D",
            "yaml_example": "securityContext:\n  readOnlyRootFilesystem: true"
        },
        {
            "concept": "CKV_K8S_40",
            "type": "checkov_rule",
            "description": "Container is running with low UID",
            "fix": "Set securityContext.runAsUser to 10000 or higher",
            "jsa_agent": "jsa-devsecops",
            "rank": "D",
            "yaml_example": "securityContext:\n  runAsUser: 10000"
        },
        {
            "concept": "CKV_K8S_43",
            "type": "checkov_rule",
            "description": "Image uses mutable tag instead of digest",
            "fix": "Replace image tag with SHA256 digest: image@sha256:abc123...",
            "jsa_agent": "jsa-devsecops",
            "rank": "D",
            "command": "docker manifest inspect IMAGE:TAG --verbose | jq '.Descriptor.digest'"
        },
        {
            "concept": "B602",
            "type": "bandit_rule",
            "description": "subprocess call with shell=True",
            "fix": "Use subprocess.run() with shell=False and pass args as list",
            "jsa_agent": "jsa-ci",
            "rank": "C",
            "code_example": "subprocess.run(['cmd', 'arg1'], shell=False)"
        },
        {
            "concept": "B101",
            "type": "bandit_rule",
            "description": "Use of assert detected",
            "fix": "Replace assert with proper exception handling",
            "jsa_agent": "jsa-ci",
            "rank": "D"
        },
    ]

    for item in error_fix_links:
        content = f"""Error/Finding: {item['concept']} ({item['type']})

Problem: {item['description']}

Fix: {item['fix']}

JSA Agent: {item['jsa_agent']} (Rank {item['rank']})"""

        if item.get('yaml_example'):
            content += f"\n\nYAML Fix:\n```yaml\n{item['yaml_example']}\n```"
        if item.get('code_example'):
            content += f"\n\nCode Fix:\n```python\n{item['code_example']}\n```"
        if item.get('command'):
            content += f"\n\nCommand:\n```bash\n{item['command']}\n```"

        links.append({
            "content": content,
            "metadata": {
                "type": "error_fix_link",
                "concept": item['concept'],
                "rule_type": item['type'],
                "jsa_agent": item['jsa_agent'],
                "rank": item['rank'],
                "source": "concept-linking"
            }
        })

    # Scanner → JSA Agent mappings
    scanner_agent_links = [
        {"scanner": "gitleaks", "agent": "jsa-ci", "domain": "secrets", "action": "detect hardcoded secrets"},
        {"scanner": "bandit", "agent": "jsa-ci", "domain": "sast", "action": "Python security analysis"},
        {"scanner": "semgrep", "agent": "jsa-ci", "domain": "sast", "action": "multi-language SAST"},
        {"scanner": "trivy", "agent": "jsa-devsecops", "domain": "vulnerabilities", "action": "container/SCA scanning"},
        {"scanner": "checkov", "agent": "jsa-devsecops", "domain": "iac", "action": "Terraform/K8s scanning"},
        {"scanner": "kubescape", "agent": "jsa-devsecops", "domain": "kubernetes", "action": "K8s security posture"},
        {"scanner": "polaris", "agent": "jsa-devsecops", "domain": "kubernetes", "action": "K8s best practices"},
        {"scanner": "conftest", "agent": "jsa-devsecops", "domain": "policy", "action": "OPA policy testing"},
    ]

    for item in scanner_agent_links:
        content = f"""Scanner: {item['scanner']}
Agent: {item['agent']}
Domain: {item['domain']}
Purpose: {item['action']}

When {item['scanner']} finds issues:
1. {item['agent']} receives the findings
2. Classified by domain: {item['domain']}
3. Auto-fix attempted for D-rank findings
4. C-rank sent to Slack for approval
5. B/S-rank escalated to human"""

        links.append({
            "content": content,
            "metadata": {
                "type": "scanner_agent_link",
                "scanner": item['scanner'],
                "agent": item['agent'],
                "domain": item['domain'],
                "source": "concept-linking"
            }
        })

    # Deployment → Status check patterns
    deploy_status_links = [
        {
            "component": "jsa-ci",
            "deploy_cmd": "helm upgrade --install jsa-ci ./charts/jsa-ci -n portfolio",
            "status_cmd": "kubectl get pods -n portfolio -l app.kubernetes.io/name=jsa-ci",
            "logs_cmd": "kubectl logs -n portfolio deploy/jsa-ci -f",
            "health_check": "kubectl exec -n portfolio deploy/jsa-ci -- python3 /app/main.py health"
        },
        {
            "component": "jsa-devsecops",
            "deploy_cmd": "helm upgrade --install jsa-devsecops ./charts/jsa-devsecops -n portfolio",
            "status_cmd": "kubectl get pods -n portfolio -l app.kubernetes.io/name=jsa-devsecops",
            "logs_cmd": "kubectl logs -n portfolio deploy/jsa-devsecops -f",
            "health_check": "kubectl exec -n portfolio deploy/jsa-devsecops -- python3 /app/main.py health"
        },
    ]

    for item in deploy_status_links:
        content = f"""Component: {item['component']}

Deploy:
```bash
{item['deploy_cmd']}
```

Check Status:
```bash
{item['status_cmd']}
```

View Logs:
```bash
{item['logs_cmd']}
```

Health Check:
```bash
{item['health_check']}
```"""

        links.append({
            "content": content,
            "metadata": {
                "type": "deploy_status_link",
                "component": item['component'],
                "source": "concept-linking"
            }
        })

    # Kubectl output summarization patterns
    kubectl_summary_links = [
        {
            "task": "count_pods",
            "example_input": """NAME                                  READY   STATUS      RESTARTS   AGE
chromadb-5d7c7474df-jj56p             1/1     Running     0          47h
jsa-ci-6676f5b4bc-56dn7               1/1     Running     0          43h
jsa-ci-health-report-29458560-wd77z   0/1     Completed   0          97m
jsa-ci-log-sync-29459400-n89zg        0/1     Completed   0          44m
portfolio-api-677b679875-445xm        1/1     Running     0          45h""",
            "correct_response": """**5 pods** in namespace:
- 3 Running (chromadb, jsa-ci, portfolio-api)
- 2 Completed CronJobs (health-report, log-sync)""",
            "rules": [
                "Count each line after header = 1 pod",
                "Distinguish Running vs Completed status",
                "CronJob pods have random suffixes like -29458560-wd77z",
                "Deployment pods have hash suffixes like -5d7c7474df-jj56p",
                "Keep response concise - no verbose boilerplate"
            ]
        },
        {
            "task": "identify_pod_types",
            "example_input": "jsa-ci-6676f5b4bc-56dn7",
            "correct_response": "Deployment pod (ReplicaSet hash: 6676f5b4bc)",
            "rules": [
                "Deployment pods: name-{replicaset-hash}-{pod-hash}",
                "CronJob pods: name-{timestamp}-{random}",
                "Job pods: name-{random}",
                "StatefulSet pods: name-{ordinal} (e.g., redis-0, redis-1)"
            ]
        },
        {
            "task": "summarize_kubectl_output",
            "rules": [
                "Be CONCISE - answer the question directly",
                "Count accurately by counting output lines",
                "Do NOT add 'Created Question/Answer' sections",
                "Do NOT hallucinate timestamps",
                "Do NOT say 'Note: This answer provides...'",
                "Format: **X pods** then bullet list of key info"
            ],
            "good_example": "**9 pods** in portfolio namespace:\n- 5 Running (chromadb, jsa-ci, jsa-devsecops, api, ui)\n- 4 Completed CronJobs",
            "bad_example": "**Tool Response:**\n\n**Tool:** kubectl get pods...\n\n**Execution Time:** 2023-11-28...\n\n**Human Readable Output:**\n...(verbose)"
        }
    ]

    for item in kubectl_summary_links:
        content = f"""Kubectl Output Summarization: {item['task']}

Rules:
{chr(10).join(f"- {r}" for r in item['rules'])}"""

        if item.get('example_input'):
            content += f"\n\nExample Input:\n```\n{item['example_input']}\n```"
        if item.get('correct_response'):
            content += f"\n\nCorrect Response:\n{item['correct_response']}"
        if item.get('good_example'):
            content += f"\n\nGood Example:\n{item['good_example']}"
        if item.get('bad_example'):
            content += f"\n\nBad Example (AVOID):\n{item['bad_example']}"

        links.append({
            "content": content,
            "metadata": {
                "type": "kubectl_summary_pattern",
                "task": item['task'],
                "source": "concept-linking"
            }
        })

    return links


def ingest_concept_links(client, links: List[Dict], dry_run: bool = True) -> Dict:
    """Ingest concept links to ChromaDB"""
    if dry_run:
        return {"would_add": len(links), "dry_run": True}

    # Get or create concept-links collection
    coll = client.get_or_create_collection(
        name="concept-links",
        metadata={"description": "Error→Fix, Scanner→Agent, Deploy→Status relationships"}
    )

    # Clear existing concept links
    existing = coll.get(where={"source": "concept-linking"})
    if existing['ids']:
        coll.delete(ids=existing['ids'])

    # Use Ollama directly for embeddings (avoid RAG engine singleton conflict)
    sys.path.insert(0, str(GP_ROOT / "JADE-AI" / "core"))
    from ollama_embeddings import get_ollama_embeddings
    embed_model = get_ollama_embeddings()

    ids = [f"concept_link_{i:04d}" for i in range(len(links))]
    contents = [l['content'] for l in links]
    metadatas = [l['metadata'] for l in links]

    print(f"  Generating embeddings for {len(links)} concept links...")
    embeddings = embed_model.embed_documents(contents, show_progress=True)

    coll.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=contents,
        metadatas=metadatas
    )

    return {"added": len(links), "collection": "concept-links"}


def main():
    parser = argparse.ArgumentParser(description='RAG Cleanup & Concept Linking')
    parser.add_argument('--analyze', action='store_true', help='Analyze collections for cleanup')
    parser.add_argument('--clean', action='store_true', help='Remove basic definitions')
    parser.add_argument('--link', action='store_true', help='Add concept relationship links')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--collection', default='jade-general', help='Collection to process')

    args = parser.parse_args()

    if not any([args.analyze, args.clean, args.link]):
        args.analyze = True  # Default to analyze

    print("=" * 60)
    print("RAG CLEANUP & CONCEPT LINKING")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"ChromaDB: {CHROMA_PATH}")
    print("=" * 60)

    client = load_chromadb()

    if args.analyze:
        print(f"\n📊 ANALYZING: {args.collection}")
        print("-" * 40)
        result = analyze_collection(client, args.collection)

        if "error" in result:
            print(f"  ❌ {result['error']}")
        else:
            print(f"  Total documents: {result['total']}")
            print(f"  Sampled: {result['sampled']}")
            print(f"  Basic definitions (remove): {result['basic_to_remove']} ({result['basic_to_remove']/max(result['sampled'],1)*100:.1f}%)")
            print(f"  Domain-specific (keep): {result['domain_to_keep']} ({result['domain_to_keep']/max(result['sampled'],1)*100:.1f}%)")

            if result['basic_ids']:
                print(f"\n  Sample IDs to remove:")
                for id in result['basic_ids'][:5]:
                    print(f"    - {id}")

    if args.clean:
        print(f"\n🧹 CLEANING: {args.collection}")
        print("-" * 40)
        result = clean_collection(client, args.collection, dry_run=args.dry_run)

        if "error" in result:
            print(f"  ❌ {result['error']}")
        else:
            print(f"  Before: {result['total_before']}")
            if args.dry_run:
                print(f"  Would remove: {result['would_remove']}")
                print(f"  After (projected): {result['total_before'] - result['would_remove']}")
                print(f"  (DRY RUN - no changes made)")
            else:
                print(f"  Removed: {result['removed']}")
                print(f"  After: {result['total_after']}")

    if args.link:
        print(f"\n🔗 BUILDING CONCEPT LINKS")
        print("-" * 40)
        links = build_concept_links()
        print(f"  Generated {len(links)} concept links:")
        print(f"    - Error→Fix mappings")
        print(f"    - Scanner→Agent mappings")
        print(f"    - Deploy→Status patterns")

        result = ingest_concept_links(client, links, dry_run=args.dry_run)

        if args.dry_run:
            print(f"  Would add: {result['would_add']} links")
            print(f"  (DRY RUN - no changes made)")
        else:
            print(f"  Added: {result['added']} links to '{result['collection']}'")

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
