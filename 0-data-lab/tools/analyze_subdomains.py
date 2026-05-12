import json
from pathlib import Path
from typing import Dict
import pandas as pd

# Paths
BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE")
CLEANED_DIR = BASE_DIR / "03-chunked-cleaned"

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

def analyze_cleaned_data():
    records = []
    chunk_files = sorted(CLEANED_DIR.glob("chunk_*.jsonl"))
    
    print(f"Analyzing {len(chunk_files)} cleaned chunks...")
    
    for chunk_file in chunk_files:
        with open(chunk_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    metadata = data.get("metadata", {})
                    domain = metadata.get("domain", "")
                    if isinstance(domain, list): domain = " ".join([str(d) for d in domain])
                    domain = str(domain).lower()
                    
                    if "kubernetes" in domain or "k8s" in domain:
                        messages = data.get("messages", [])
                        content = ""
                        for msg in messages:
                            content += msg["content"]
                        
                        subdomain = detect_subdomain(content)
                        records.append({"subdomain": subdomain})
                except:
                    continue
                    
    df = pd.DataFrame(records)
    print("\nKUBERNETES SUBDOMAIN BREAKDOWN (CLEANED DATA):")
    counts = df["subdomain"].value_counts()
    for sub, count in counts.items():
        print(f"  {sub:20}: {count:6,} ({count/len(df)*100:5.1f}%)")
    
    print(f"\nTotal K8s Examples: {len(df):,}")

if __name__ == "__main__":
    analyze_cleaned_data()
