#!/usr/bin/env python3
"""
Curate JADE Training Data (Task 1)
=====================================
Categorizes and scores 39k training examples by domain and quality rank.

Domain categories: kubernetes, cloud, devsecops, compliance, terraform, secrets, general.
Quality ranks: S, B, C, D, E.
"""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

# Paths
BASE_DIR = Path(__file__).parent
CHUNKED_DIR = BASE_DIR / "03-chunked-untrained"
REPORT_PATH = BASE_DIR / "curation_report.txt"

# Domain Mapping Keywords
DOMAIN_KEYWORDS = {
    "kubernetes": ["k8s", "pod", "deployment", "namespace", "helm", "kubectl", "polaris", "checkov-k8s", "kubescape", "falco", "rego", "kyverno", "gatekeeper", "cks", "cka", "kubelet", "api-server", "etcd"],
    "cloud": ["aws", "azure", "gcp", "iam", "vpc", "s3", "lambda", "kms", "rds", "ccsp", "cloudwatch", "cloudtrail", "guardduty"],
    "devsecops": ["sast", "dast", "sca", "ci/cd", "github", "gitlab", "trivy", "semgrep", "checkov", "terrascan", "sonar", "pipeline", "jenkins", "actions"],
    "compliance": ["nist", "cis", "fedramp", "soc2", "pci-dss", "hipaa", "iso27001", "audit", "compliance", "regulatory"],
    "terraform": ["terraform", "hcl", "tf ", "tf_", "module", "terraform plan", "terraform apply"],
    "secrets": ["vault", "secrets manager", "rotation", "secrets", "sealedsecrets", "eso", "hashicorp vault", "aws secrets"],
}

def detect_domain(text: str, metadata: Dict) -> str:
    # 1. Check existing metadata
    meta_domain = metadata.get("domain", "")
    if isinstance(meta_domain, list):
        meta_domain = " ".join([str(d) for d in meta_domain])
    meta_domain = meta_domain.lower()
    
    if meta_domain in DOMAIN_KEYWORDS or "kubernetes" in meta_domain:
        return meta_domain if "kubernetes" not in meta_domain else "kubernetes"
    
    # Check category metadata
    meta_category = metadata.get("category", "")
    if isinstance(meta_category, list):
        meta_category = " ".join([str(c) for c in meta_category])
    meta_category = meta_category.lower()
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if domain in meta_category:
            return domain
        for kw in keywords:
            if kw in meta_category:
                return domain

    # 2. Check content
    text_lower = text.lower()
    scores = {domain: 0 for domain in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[domain] += text_lower.count(kw)
    
    # Return domain with highest score if > 0
    max_domain = max(scores, key=scores.get)
    if scores[max_domain] > 0:
        return max_domain
    
    return "general"

def compute_rank(user: str, assistant: str, metadata: Dict) -> str:
    score = 0
    
    # 1. Use existing rank/skill_level as baseline
    meta_rank = metadata.get("rank", metadata.get("skill_level", "")).upper()
    if "S" in meta_rank: score += 90
    elif "B" in meta_rank: score += 75
    elif "C" in meta_rank: score += 50
    elif "D" in meta_rank: score += 30
    elif "E" in meta_rank: score += 10
    
    # 2. Length-based bonus
    asst_len = len(assistant)
    if asst_len > 2000: score += 15
    elif asst_len > 1000: score += 10
    elif asst_len > 500: score += 5
    
    # 3. Code presence bonus
    if "```" in assistant:
        score += 10
        # Check for multiple code blocks (multi-step)
        if assistant.count("```") >= 4:
            score += 10
            
    # 4. Multi-step keywords
    multi_step_kws = ["step 1", "first", "second", "then", "finally", "remediation:", "analysis:"]
    if any(kw in assistant.lower() for kw in multi_step_kws):
        score += 5
        
    # 5. Complexity markers
    if "**" in assistant: score += 2
    if assistant.count("\n") > 10: score += 3
    
    # Final Rank Mapping
    if score >= 90: return "S"
    if score >= 75: return "B"
    if score >= 50: return "C"
    if score >= 20: return "D"
    return "E"

def process_chunks():
    records = []
    chunk_files = sorted(CHUNKED_DIR.glob("*.jsonl"))
    
    print(f"Processing {len(chunk_files)} files...")
    
    for chunk_file in chunk_files:
        print(f"  Reading {chunk_file.name}...")
        with open(chunk_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    messages = data.get("messages", [])
                    metadata = data.get("metadata", {})
                    
                    user_content = ""
                    assistant_content = ""
                    for msg in messages:
                        if msg["role"] == "user": user_content = msg["content"]
                        if msg["role"] == "assistant": assistant_content = msg["content"]
                    
                    full_text = user_content + " " + assistant_content
                    domain = detect_domain(full_text, metadata)
                    rank = compute_rank(user_content, assistant_content, metadata)
                    
                    records.append({
                        "domain": domain,
                        "rank": rank
                    })
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    
    df = pd.DataFrame(records)
    return df

def generate_report(df: pd.DataFrame):
    report = []
    report.append("="*50)
    report.append("JADE TRAINING DATA CURATION REPORT")
    report.append("="*50)
    report.append(f"Total Examples: {len(df):,}")
    report.append("\nCOUNTS BY DOMAIN:")
    domain_counts = df["domain"].value_counts()
    for domain, count in domain_counts.items():
        report.append(f"  {domain:15}: {count:6,} ({count/len(df)*100:5.1f}%)")
        
    report.append("\nCOUNTS BY RANK:")
    rank_counts = df["rank"].value_counts().sort_index(ascending=False)
    for rank, count in rank_counts.items():
        report.append(f"  {rank:15}: {count:6,} ({count/len(df)*100:5.1f}%)")
        
    report.append("\nMATRIX (DOMAIN vs RANK):")
    matrix = pd.crosstab(df["domain"], df["rank"])
    # Reorder columns to S, B, C, D, E
    cols = [c for c in ["S", "B", "C", "D", "E"] if c in matrix.columns]
    matrix = matrix[cols]
    report.append(matrix.to_string())
    
    report_text = "\n".join(report)
    print(report_text)
    
    with open(REPORT_PATH, 'w') as f:
        f.write(report_text)
    print(f"\nReport saved to: {REPORT_PATH}")

if __name__ == "__main__":
    df = process_chunks()
    generate_report(df)
