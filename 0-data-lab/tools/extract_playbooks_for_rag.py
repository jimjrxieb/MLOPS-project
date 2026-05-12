#!/usr/bin/env python3
"""
GP-CONSULTING Reference → RAG Ingestion Extractor
===================================================
Extracts reference materials (configs, templates, examples) from
GP-CONSULTING 01-03 into the RAG ingestion pipeline.

Copies files to: 2-rag-ingestion/01-unprocessed/consulting-knowledge/
The RAG pipeline (preprocess → sanitize → chunk → label → embed) handles the rest.

Reference material = things that change, need to be cited, or are looked up:
  - Scanner configs (.checkov.yaml, semgrep.yaml, trivy.yaml)
  - CI templates (GitHub Actions)
  - Helm chart values
  - Deployment configs (cloud-specific)
  - Remediation template YAML snippets
  - Compliance mappings
  - Example scanner outputs
  - Pre-commit hook configs
"""
import shutil
from pathlib import Path

GP_CONSULTING = Path("/home/jimmie/linkops-industries/GP-copilot/GP-CONSULTING")
RAG_OUTPUT = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/2-rag-ingestion/01-unprocessed/consulting-knowledge")

# What goes to RAG (NOT training):
# Pattern: (source_glob_relative_to_package, rag_subdirectory)
RAG_PATTERNS = {
    "01-APP-SEC": [
        ("scanning-configs/*", "appsec-configs"),
        ("scanners/CAPABILITIES.md", "appsec-reference"),
        ("ci-templates/**/*", "appsec-ci-templates"),
        ("pre-commit/**/*", "appsec-pre-commit"),
        ("tools/README.md", "appsec-reference"),
    ],
    "02-CLUSTER-HARDENING": [
        ("templates/remediation-templates/*", "k8s-remediation"),
        ("templates/golden-path/**/*", "k8s-golden-path"),
        ("templates/compliance-mappings/*", "k8s-compliance"),
        ("templates/namespace-operator/**/*", "k8s-namespace-operator"),
        ("templates/gateway-api/**/*", "k8s-gateway-api"),
        ("templates/external-secrets/**/*", "k8s-external-secrets"),
        ("templates/policies/conftest/*", "k8s-conftest-policies"),
        ("templates/policies/gatekeeper/*", "k8s-gatekeeper-policies"),
        ("templates/policies/terraform/*", "k8s-terraform-policies"),
        ("examples/*", "k8s-examples"),
        ("monitoring/*", "k8s-monitoring"),
        ("POLICY-MATRIX.md", "k8s-reference"),
    ],
    "03-DEPLOY-RUNTIME": [
        ("templates/helm-chart/**/*", "runtime-helm"),
        ("templates/alertmanager/**/*", "runtime-alertmanager"),
        ("templates/grafana/**/*", "runtime-grafana"),
        ("templates/prometheus/**/*", "runtime-prometheus"),
        ("templates/istio/**/*", "runtime-istio"),
        ("templates/logging/**/*", "runtime-logging"),
        ("templates/loki/**/*", "runtime-loki"),
        ("templates/tracing/**/*", "runtime-tracing"),
        ("templates/deployment-configs/*", "runtime-deployment"),
        ("monitoring/*", "runtime-monitoring"),
        ("tools/README.md", "runtime-reference"),
    ],
}


def copy_to_rag(src_path, dest_subdir):
    """Copy a file to the RAG ingestion directory."""
    dest_dir = RAG_OUTPUT / dest_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src_path.name

    # Avoid overwriting — add package prefix if collision
    if dest.exists():
        dest = dest_dir / f"{src_path.parent.name}_{src_path.name}"

    shutil.copy2(src_path, dest)
    return dest


def main():
    total_copied = 0

    for pkg_name, patterns in RAG_PATTERNS.items():
        pkg_dir = GP_CONSULTING / pkg_name
        if not pkg_dir.exists():
            print(f"  WARNING: {pkg_dir} not found, skipping")
            continue

        print(f"\n=== {pkg_name} → RAG ===")
        pkg_count = 0

        for pattern, rag_subdir in patterns:
            matches = list(pkg_dir.glob(pattern))
            for src in matches:
                if src.is_dir():
                    continue
                if src.suffix in ('.pyc', '.pyo', '.DS_Store'):
                    continue
                if src.stat().st_size < 10:
                    continue

                dest = copy_to_rag(src, rag_subdir)
                pkg_count += 1

            if matches:
                file_matches = [m for m in matches if m.is_file()]
                if file_matches:
                    print(f"  {pattern}: {len(file_matches)} files → {rag_subdir}/")

        total_copied += pkg_count
        print(f"  Subtotal: {pkg_count} files")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_copied} reference files copied to RAG pipeline")
    print(f"Output: {RAG_OUTPUT}")
    print(f"{'='*60}")
    print(f"\nNext: Run the RAG prep factory stages:")
    print(f"  cd GP-MODEL-OPS/2-rag-ingestion/02-preperation-factory/")
    print(f"  python -m stages.discover")
    print(f"  python -m stages.preprocess")
    print(f"  # ... through stages.validators")
    print(f"  python 2-rag-ingestion/04-ingesting/ingest_to_chromadb.py")


if __name__ == "__main__":
    main()
