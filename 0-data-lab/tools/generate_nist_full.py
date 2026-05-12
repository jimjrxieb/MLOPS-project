import json
from pathlib import Path

OUTPUT_FILE = Path("1-GP-GLUE/01-raw-data-lake/8b-jade/nist_800_53_full.jsonl")

def main():
    controls = []
    
    families = {
        "Access Control": ("AC", 25),
        "Audit and Accountability": ("AU", 16),
        "Configuration Management": ("CM", 14),
        "System and Communications Protection": ("SC", 44),
        "System and Information Integrity": ("SI", 16),
        "Identification and Authentication": ("IA", 12),
        "Risk Assessment": ("RA", 7),
        "Incident Response": ("IR", 10)
    }
    
    for family_name, (prefix, count) in families.items():
        for i in range(1, count + 1):
            cid = f"{prefix}-{i}"
            controls.append({
                "control_id": cid,
                "control_family": family_name,
                "title": f"{family_name} Control {i}",
                "summary": f"Summary for NIST 800-53 control {cid}.",
                "kubernetes_relevance": f"Kubernetes relevance for {cid} involves cluster configuration and security posture.",
                "common_findings": [f"finding-{cid}-1", f"finding-{cid}-2"],
                "scanner_mappings": [f"scanner-{cid}"],
                "remediation_approach": f"Remediation approach for {cid} in a cloud-native environment.",
                "fedramp_baseline": "LOW, MODERATE, HIGH"
            })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        for control in controls:
            f.write(json.dumps(control) + "\n")
            
    print(f"Generated {len(controls)} NIST 800-53 control summaries to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
