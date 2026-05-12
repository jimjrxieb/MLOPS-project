import json
from pathlib import Path
from typing import Dict
import pandas as pd

# Paths
BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE")
CLEANED_DIR = BASE_DIR / "03-chunked-cleaned"
RAW_DATA_LAKE = BASE_DIR / "01-raw-data-lake"
CKS_3B_DIR = RAW_DATA_LAKE / "3b-cks"

SUBDOMAIN_KEYWORDS = {
    "NetworkPolicy": ["networkpolicy", "netpol", "ingress", "egress", "podselector", "port 53", "dns"],
    "RBAC/ServiceAccount": ["rbac", "rolebinding", "clusterrole", "serviceaccount", "automountserviceaccounttoken", "cluster-admin"],
    "AdmissionControl": ["admission controller", "gatekeeper", "kyverno", "constrainttemplate", "rego", "admissionconfiguration", "imagepolicywebhook"],
    "Seccomp/AppArmor": ["seccomp", "apparmor", "securitycontext.seccompprofile", "container.apparmor.security.beta.kubernetes.io"],
    "Falco/Runtime": ["falco", "sysdig", "runtime security", "behavioral monitoring", "audit log", "syscall", "execve"]
}

def detect_subdomain(text: str) -> str:
    text_lower = text.lower()
    scores = {sub: 0 for sub in SUBDOMAIN_KEYWORDS}
    for sub, keywords in SUBDOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[sub] += text_lower.count(kw)
    
    max_sub = max(scores, key=scores.get)
    if scores[max_sub] > 0:
        return max_sub
    return "Other K8s"

def analyze_all_data():
    records = []
    
    # 1. Cleaned Chunks
    chunk_files = sorted(CLEANED_DIR.glob("chunk_*.jsonl"))
    
    # 2. New Targeted Batches
    targeted_files = [
        CKS_3B_DIR / "netpol_500.jsonl",
        CKS_3B_DIR / "rbac_500.jsonl",
        CKS_3B_DIR / "seccomp_apparmor_500.jsonl",
        CKS_3B_DIR / "falco_runtime_500.jsonl",
        RAW_DATA_LAKE / "cks_training_batch_v1.jsonl"
    ]
    
    all_files = chunk_files + targeted_files
    
    print(f"Analyzing {len(all_files)} total files...")
    
    for filepath in all_files:
        if not filepath.exists():
            print(f"  Warning: {filepath} not found.")
            continue
            
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    metadata = data.get("metadata", {})
                    domain = metadata.get("domain", "")
                    if isinstance(domain, list): domain = " ".join([str(d) for d in domain])
                    domain = str(domain).lower()
                    
                    # New targeted data doesn't always have domain metadata yet, but we know it's K8s
                    is_k8s = "kubernetes" in domain or "k8s" in domain or "netpol" in str(filepath) or "rbac" in str(filepath) or "seccomp" in str(filepath) or "falco" in str(filepath) or "cks" in str(filepath)
                    
                    if is_k8s:
                        messages = data.get("messages", [])
                        content = ""
                        for msg in messages:
                            content += msg["content"]
                        
                        subdomain = detect_subdomain(content)
                        records.append({"subdomain": subdomain})
                except:
                    continue
                    
    df = pd.DataFrame(records)
    print("\nCOMBINED KUBERNETES SUBDOMAIN BREAKDOWN:")
    counts = df["subdomain"].value_counts()
    for sub, count in counts.items():
        print(f"  {sub:20}: {count:6,} ({count/len(df)*100:5.1f}%)")
    
    print(f"\nTotal K8s Examples: {len(df):,}")

if __name__ == "__main__":
    analyze_all_data()
