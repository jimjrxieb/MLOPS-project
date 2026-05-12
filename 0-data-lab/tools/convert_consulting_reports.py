#!/usr/bin/env python3
"""
Consulting Reports → Katie Training Data Converter
====================================================
Reads real engagement reports from GP-S3/5-consulting-reports/ and converts
them into high-quality ChatML training pairs for Katie 3B.

Handles 8 report formats:
  1. Developer findings (MD) — finding + fix YAML → Q&A pairs
  2. Remediation plans (MD) — scanner finding + bash command → Q&A pairs
  3. Engagement summaries (YAML) — structured state → operational Q&A
  4. Engagement summaries (MD) — before/after + playbook log → Q&A
  5. Gateway API migration (MD) — incident narrative → troubleshooting Q&A
  6. K8s audit reports (MD) — scanner scores + RBAC + resources → Q&A
  7. Structured finding JSON — self-contained finding → Q&A
  8. Scan summaries (MD) — tooling knowledge → Q&A

All outputs are PII-scrubbed before writing.

Usage:
    python3 convert_consulting_reports.py                  # Convert all
    python3 convert_consulting_reports.py --dry-run         # Preview counts
"""

import json
import re
import yaml
import argparse
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
REPORTS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-S3/5-consulting-reports")
OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline/01-raw-data-lake")

KATIE_SYSTEM_PROMPT = (
    "You are Katie, a CKA/CKS/CKAD/CNPA-certified autonomous Kubernetes engineer "
    "for GP-Copilot. You diagnose and fix production issues at 2 AM without human "
    "intervention. You provide complete, working fixes with exact commands and YAML "
    "manifests. You check ArgoCD ownership before any fix. You route by rank "
    "(E/D/C/B/S). You reference real tools: kubectl, Falco, Trivy, Kubescape, "
    "Kyverno, OPA/Rego, Helm, ArgoCD. You never hallucinate commands."
)

# ── PII Scrubbing ─────────────────────────────────────────────────────────
PII_REPLACEMENTS = [
    # Secrets — nuke anything that looks like an API key value
    (r'6LelWk4UAAAAAGaBJWFusnIlAVoaCK8DWnRBDE4g', 'REDACTED_API_KEY'),
    (r"key='[A-Za-z0-9_\-]{20,}'", "key='REDACTED_API_KEY'"),
    # IP addresses
    (r'100\.116\.11\.56', '10.0.1.100'),
    (r'192\.168\.1\.110', '10.0.1.101'),
    # GitHub username/repo
    (r'jimjrxieb/Portfolio\.git', 'client-org/client-app.git'),
    (r'jimjrxieb/Portfolio', 'client-org/client-app'),
    (r'jimjrxieb', 'client-user'),
    # Domain
    (r'linksmlm\.com', 'client-app.example.com'),
    # Home directory paths
    (r'/home/jimmie/linkops-industries/GP-copilot/', '/opt/gp-copilot/'),
    (r'/home/jimmie/', '/opt/'),
    # Cloudflare tunnel IDs
    (r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'REDACTED-TUNNEL-ID'),
    # Git commit hashes (40 char)
    (r'\b[0-9a-f]{40}\b', 'REDACTED_COMMIT_HASH'),
    # Git short hashes in specific contexts (keep ones in kubectl output)
    (r'main-[0-9a-f]{8}', 'main-abc12345'),
    # Author emails from gitleaks
    (r'"Email":\s*"[^"]*"', '"Email": "redacted@example.com"'),
    (r'"Author":\s*"[^"]*"', '"Author": "redacted"'),
    # Raw secrets in JSON
    (r'"Secret":\s*"[^"]*"', '"Secret": "REDACTED"'),
    (r'"Match":\s*"[^"]*key[^"]*"', '"Match": "key=REDACTED"'),
    (r'"Fingerprint":\s*"[^"]*"', '"Fingerprint": "REDACTED"'),
]


def scrub_pii(text: str) -> str:
    """Remove all PII/secrets from text."""
    for pattern, replacement in PII_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def make_example(user: str, assistant: str) -> dict:
    """Create a ChatML training example with PII scrubbing."""
    return {
        "messages": [
            {"role": "system", "content": KATIE_SYSTEM_PROMPT},
            {"role": "user", "content": scrub_pii(user.strip())},
            {"role": "assistant", "content": scrub_pii(assistant.strip())},
        ]
    }


# ── Converter: Developer Findings (MD) ────────────────────────────────────
def convert_developer_findings(filepath: Path) -> list[dict]:
    """Convert findings-for-developers.md into Q&A pairs."""
    examples = []
    content = filepath.read_text()
    sections = re.split(r'\n## ', content)

    for section in sections:
        if not section.startswith("Finding"):
            continue

        # Extract finding title, severity, control, what, fix
        lines = section.strip().split("\n")
        title = lines[0].strip().rstrip("#").strip()

        severity = ""
        control = ""
        what = ""
        fix_yaml = ""
        owners = []

        in_fix = False
        fix_lines = []
        current_code_block = []
        in_code = False

        for line in lines[1:]:
            if line.startswith("**Severity:**"):
                severity = line.split("**Severity:**")[1].strip()
            elif line.startswith("**Control:**"):
                control = line.split("**Control:**")[1].strip()
            elif line.startswith("**What:**"):
                what = line.split("**What:**")[1].strip()
            elif line.startswith("**Fix:**"):
                in_fix = True
            elif line.startswith("| ") and "Owner" not in line and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3:
                    owners.append({"owner": parts[0], "namespace": parts[1], "workload": parts[2]})
            elif "```" in line and in_fix:
                if in_code:
                    current_code_block.append("```")
                    fix_lines.append("\n".join(current_code_block))
                    current_code_block = []
                    in_code = False
                else:
                    in_code = True
                    current_code_block.append(line)
            elif in_code:
                current_code_block.append(line)
            elif in_fix and line.strip():
                fix_lines.append(line)

        if not what:
            continue

        fix_text = "\n".join(fix_lines)
        owner_text = ", ".join(f"{o['workload']} in {o['namespace']}" for o in owners[:3])

        # Create Q&A pair
        question = (
            f"Kubescape audit found: {title.split(': ', 1)[-1] if ': ' in title else title}\n"
            f"Severity: {severity}, Control: {control}\n"
            f"Affected: {owner_text}\n"
            f"What should I fix and how?"
        )

        answer = f"**{what}**\n\n{fix_text}"

        examples.append(make_example(question, answer))

    # Helm Security Baseline as a standalone example
    if "Helm Chart Security Baseline" in content:
        baseline_start = content.index("Helm Chart Security Baseline")
        baseline_section = content[baseline_start:].split("---")[0]

        examples.append(make_example(
            "What is the minimum security baseline for Helm charts on a hardened Kubernetes cluster with Gatekeeper admission control?",
            baseline_section.strip()
        ))

    # Exceptions as training data
    if "Exceptions (No Fix Required)" in content:
        exc_start = content.index("Exceptions (No Fix Required)")
        exc_section = content[exc_start:].split("---")[0]

        examples.append(make_example(
            "Which workloads should be exempt from pod security policies in a hardened cluster, and why?",
            exc_section.strip()
        ))

    return examples


# ── Converter: Remediation Plans (MD) ─────────────────────────────────────
def convert_remediation_plan(filepath: Path) -> list[dict]:
    """Convert REMEDIATION-PLAN.md into scanner-finding + fix-command pairs."""
    examples = []
    content = filepath.read_text()
    lines = content.split("\n")

    current_finding = None
    current_file = None
    current_command = None
    in_code = False
    code_lines = []

    for line in lines:
        # Finding header: **[scanner] rule** — description
        match = re.match(r'\*\*\[(\w+)\]\s+(.+?)\*\*\s*—\s*(.+)', line)
        if match:
            # Save previous finding
            if current_finding and current_command:
                examples.append(_make_remediation_pair(
                    current_finding, current_file, current_command
                ))

            scanner, rule, desc = match.groups()
            current_finding = {
                "scanner": scanner,
                "rule": rule,
                "description": desc.strip(),
            }
            current_file = None
            current_command = None
            continue

        # File path line
        if line.startswith("`") and not line.startswith("```"):
            path_match = re.match(r'`(.+?)`', line)
            if path_match:
                current_file = path_match.group(1)
            continue

        # Code block
        if line.startswith("```"):
            if in_code:
                current_command = "\n".join(code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)

    # Last finding
    if current_finding and current_command:
        examples.append(_make_remediation_pair(
            current_finding, current_file, current_command
        ))

    return examples


def _make_remediation_pair(finding: dict, file_path: str, command: str) -> dict:
    """Create a Q&A pair from a remediation finding."""
    question = (
        f"[{finding['scanner']}] found {finding['rule']}: {finding['description']}\n"
        f"File: {file_path or 'unknown'}\n"
        f"How do I fix this?"
    )

    answer = (
        f"**Scanner:** {finding['scanner']}\n"
        f"**Rule:** {finding['rule']}\n"
        f"**Fix:**\n```bash\n{command}\n```\n\n"
        f"After fixing, re-scan to verify the finding is resolved."
    )

    return make_example(question, answer)


# ── Converter: Engagement Summary (YAML) ──────────────────────────────────
def convert_engagement_yaml(filepath: Path) -> list[dict]:
    """Convert engagement-summary.yaml into operational Q&A pairs."""
    examples = []
    content = filepath.read_text()
    data = yaml.safe_load(content)

    if not data:
        return examples

    engagement = data.get("engagement", {})
    scores = data.get("scores", {})
    gitops = data.get("gitops", {})
    constraints = data.get("constraints", {})
    quirks = data.get("platform_quirks", [])
    findings = data.get("findings", {})
    deployed = data.get("deployed", {})
    next_actions = data.get("next_actions", [])

    # Scores progression Q&A
    if scores:
        ks = scores.get("kubescape", {})
        if ks:
            examples.append(make_example(
                f"Kubescape score is {ks.get('baseline', '?')}% on a {engagement.get('platform', 'k8s')} "
                f"{engagement.get('k8s_version', '')} cluster. Target is {ks.get('target', 80)}%. "
                f"What's the current state and what should we prioritize?",
                f"Current Kubescape NSA score: {ks.get('current', '?')}% (baseline was {ks.get('baseline', '?')}%).\n\n"
                f"Gatekeeper constraints: {constraints.get('total', '?')} total "
                f"({constraints.get('deny', '?')} deny, {constraints.get('dryrun', '?')} dryrun).\n\n"
                f"Enforcing policies:\n" +
                "\n".join(f"- {p}" for p in constraints.get("enforcing", [])) +
                f"\n\nTo reach {ks.get('target', 80)}%, prioritize:\n" +
                "\n".join(f"- [{a.get('priority', '?')}] {a.get('action', '?')} — {a.get('reason', '')}"
                         for a in next_actions)
            ))

    # Platform quirks Q&A (each is a learning example)
    for quirk in quirks:
        examples.append(make_example(
            f"I'm working on a {engagement.get('platform', 'k8s')} cluster and hit this issue: "
            f"{quirk.get('description', '')}. What's the impact and how do I work around it?",
            f"**Platform quirk: {quirk.get('id', '')}**\n\n"
            f"**Impact:** {quirk.get('impact', '')}\n\n"
            f"**Mitigation:** {quirk.get('mitigation', '')}"
        ))

    # GitOps routing Q&A
    if gitops:
        apps_text = ""
        for app in gitops.get("apps", []):
            resources = ", ".join(app.get("managed_resources", [])[:5])
            apps_text += f"- **{app.get('name', '?')}**: {resources}\n"

        examples.append(make_example(
            f"How do I know if a resource is managed by ArgoCD before patching it on this cluster?",
            f"**Routing rule:** {gitops.get('rule', 'Check ArgoCD app label')}\n\n"
            f"**ArgoCD controller:** {gitops.get('controller', 'argocd')}\n\n"
            f"**Managed apps:**\n{apps_text}\n"
            f"Check ownership:\n```bash\n"
            f"kubectl get <resource> <name> -n <ns> -o jsonpath='{{.metadata.labels.app\\.kubernetes\\.io/instance}}'\n"
            f"# Returns app name → fix in git. Empty → kubectl OK.\n```"
        ))

    # Developer findings as scenarios
    for owner_group in findings.get("developer_owned", []):
        owner = owner_group.get("owner", "unknown")
        ns = owner_group.get("namespace", "default")
        for item in owner_group.get("items", []):
            finding_text = item.get("finding", "")
            severity = item.get("severity", "medium")
            containers = item.get("containers", [])

            container_text = f" (containers: {', '.join(containers)})" if containers else ""
            detail = item.get("detail", "")

            examples.append(make_example(
                f"Cluster audit found: {finding_text}{container_text}\n"
                f"Owner: {owner}, Namespace: {ns}, Severity: {severity}\n"
                f"{f'Detail: {detail}' if detail else ''}\n"
                f"Is this ArgoCD-managed? What's the fix?",
                f"Check ArgoCD ownership first:\n"
                f"```bash\n"
                f"kubectl get deployment -n {ns} -o jsonpath='{{.metadata.labels.app\\.kubernetes\\.io/instance}}'\n"
                f"```\n\n"
                f"If ArgoCD-managed → fix in the {owner} Helm values, push to git, let ArgoCD sync.\n"
                f"If NOT ArgoCD-managed → apply kubectl patch directly.\n\n"
                f"**Finding:** {finding_text}\n"
                f"**Severity:** {severity}\n"
                f"**Rank:** {'C' if severity == 'high' else 'D'}-rank "
                f"{'— needs JADE approval' if severity == 'high' else '— auto-fixable'}"
            ))

    # Exceptions as learning data
    for exc in findings.get("exceptions", []):
        examples.append(make_example(
            f"Security scan flags {exc.get('workload', '?')} as non-compliant. Should I fix it?",
            f"**No — this is an accepted exception.**\n\n"
            f"Workload: {exc.get('workload', '?')}\n"
            f"Reason: {exc.get('reason', 'No reason given')}\n\n"
            f"Document the exception and move on. Some workloads require elevated privileges by design."
        ))

    return examples


# ── Converter: Engagement Summary (MD) ────────────────────────────────────
def convert_engagement_md(filepath: Path) -> list[dict]:
    """Convert engagement-summary markdown into Q&A pairs."""
    examples = []
    content = filepath.read_text()

    # Before/After as a single teaching example
    if "Before" in content and "After" in content:
        examples.append(make_example(
            "What does a typical cluster hardening engagement improve? Show me before/after metrics.",
            scrub_pii(content)
        ))

    # Policy bugs section
    if "Policy Bugs Found" in content or "Bugs Found" in content:
        bug_start = content.find("Policy Bugs Found")
        if bug_start == -1:
            bug_start = content.find("Bugs Found")
        if bug_start >= 0:
            bug_section = content[bug_start:].split("\n##")[0]
            examples.append(make_example(
                "What are common Kyverno/Gatekeeper policy bugs found during cluster hardening?",
                bug_section.strip()
            ))

    # Exceptions section
    if "Documented Exceptions" in content:
        exc_start = content.find("Documented Exceptions")
        exc_section = content[exc_start:].split("\n##")[0]
        examples.append(make_example(
            "What workloads commonly need policy exceptions in a hardened cluster?",
            exc_section.strip()
        ))

    return examples


# ── Converter: Gateway API Migration (MD) ─────────────────────────────────
def convert_gateway_migration(filepath: Path) -> list[dict]:
    """Convert gateway-api-migration.md into incident response Q&A pairs."""
    examples = []
    content = filepath.read_text()

    # Full migration as a comprehensive example
    examples.append(make_example(
        "We're getting 502 Bad Gateway errors after a cluster change. ArgoCD shows apps OutOfSync "
        "with Missing status. The cluster uses Traefik as ingress. How do I diagnose and fix this?",
        content
    ))

    # Extract specific sub-scenarios
    if "Changes Made" in content:
        changes_start = content.find("Changes Made")
        changes_section = content[changes_start:].split("\n## ")[0]
        examples.append(make_example(
            "How do you migrate from Kubernetes Ingress to Gateway API with Traefik?",
            changes_section.strip()
        ))

    if "Compliance Mapping" in content or "Compliance" in content:
        comp_start = content.find("Compliance")
        if comp_start >= 0:
            comp_section = content[comp_start:].split("\n## ")[0]
            examples.append(make_example(
                "What NIST/FedRAMP compliance controls does Gateway API satisfy?",
                comp_section.strip()
            ))

    if "Validation" in content:
        val_start = content.find("Validation")
        val_section = content[val_start:].split("\n## ")[0]
        examples.append(make_example(
            "What are the pre-deploy and post-deploy validation steps for a Gateway API migration?",
            val_section.strip()
        ))

    return examples


# ── Converter: K8s Audit Report (MD) ──────────────────────────────────────
def convert_k8s_audit(filepath: Path) -> list[dict]:
    """Convert k8s-audit.md into Q&A pairs."""
    examples = []
    content = filepath.read_text()

    # Full audit as a reference
    examples.append(make_example(
        "Show me a complete Kubernetes cluster security audit report with Kubescape, Polaris, "
        "kube-bench scores, RBAC analysis, and resource usage.",
        content
    ))

    # RBAC section
    if "RBAC" in content:
        rbac_start = content.find("RBAC")
        rbac_section = content[rbac_start:].split("\n## ")[0]
        examples.append(make_example(
            "How do you audit RBAC in a Kubernetes cluster? What should I look for?",
            rbac_section.strip()
        ))

    # Resource section
    if "Resource" in content:
        res_start = content.find("Resource")
        res_section = content[res_start:].split("\n## ")[0]
        if len(res_section) > 100:
            examples.append(make_example(
                "How do you identify pods without resource limits and right-size them?",
                res_section.strip()
            ))

    return examples


# ── Converter: Structured Finding JSON ────────────────────────────────────
def convert_finding_json(filepath: Path) -> list[dict]:
    """Convert a structured finding JSON into a Q&A pair."""
    try:
        data = json.loads(filepath.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []

    context = data.get("context", {})
    scanner = data.get("scanner", "unknown")
    severity = data.get("severity", "unknown")
    rank = data.get("rank", "?")
    title = data.get("title", "")
    rule_id = data.get("rule_id", "")
    file_path = data.get("file_path", "")
    line = data.get("line", "")
    remediation = context.get("remediation", "")
    references = context.get("references", [])

    if not title or not remediation:
        return []

    # Strip raw secrets from context before using
    question = (
        f"[{scanner}] {rule_id}: {title}\n"
        f"File: {file_path}:{line}\n"
        f"Severity: {severity}, Rank: {rank}\n"
        f"How do I remediate this?"
    )

    ref_text = "\n".join(f"- {r}" for r in references) if references else ""
    answer = (
        f"**Scanner:** {scanner}\n"
        f"**Rule:** {rule_id}\n"
        f"**Severity:** {severity}\n"
        f"**Rank:** {rank}-rank\n\n"
        f"**Remediation:**\n{remediation}\n\n"
        f"{'**References:**' + chr(10) + ref_text if ref_text else ''}"
    )

    return [make_example(question, answer)]


# ── Converter: Compliance/Final Report (MD) ───────────────────────────────
def convert_compliance_report(filepath: Path) -> list[dict]:
    """Convert final compliance reports into Q&A pairs."""
    examples = []
    content = filepath.read_text()

    if len(content) > 200:
        examples.append(make_example(
            "Show me a final compliance report for a Kubernetes cluster hardening engagement "
            "including CIS, NIST, SOC2, PCI-DSS, and FedRAMP control mappings.",
            content
        ))

    return examples


# ── Main Pipeline ─────────────────────────────────────────────────────────
def find_and_convert(dry_run: bool = False) -> dict:
    """Find all report files and convert them."""
    stats = {
        "developer_findings": 0,
        "remediation_plans": 0,
        "engagement_yaml": 0,
        "engagement_md": 0,
        "gateway_migration": 0,
        "k8s_audit": 0,
        "finding_json": 0,
        "compliance_report": 0,
        "total": 0,
    }

    all_examples = []

    # 1. Developer findings
    for f in REPORTS_DIR.rglob("findings-for-developers.md"):
        examples = convert_developer_findings(f)
        all_examples.extend(examples)
        stats["developer_findings"] += len(examples)
        print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    # 2. Remediation plans
    for f in REPORTS_DIR.rglob("REMEDIATION-PLAN.md"):
        examples = convert_remediation_plan(f)
        all_examples.extend(examples)
        stats["remediation_plans"] += len(examples)
        print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    # 3. Engagement YAML
    for f in REPORTS_DIR.rglob("engagement-summary.yaml"):
        examples = convert_engagement_yaml(f)
        all_examples.extend(examples)
        stats["engagement_yaml"] += len(examples)
        print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    # 4. Engagement MD summaries
    for f in REPORTS_DIR.rglob("engagement-summary*.md"):
        examples = convert_engagement_md(f)
        all_examples.extend(examples)
        stats["engagement_md"] += len(examples)
        print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    # 5. Gateway migration
    for f in REPORTS_DIR.rglob("gateway-api-migration.md"):
        examples = convert_gateway_migration(f)
        all_examples.extend(examples)
        stats["gateway_migration"] += len(examples)
        print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    # 6. K8s audit reports
    for f in REPORTS_DIR.rglob("k8s-audit.md"):
        examples = convert_k8s_audit(f)
        all_examples.extend(examples)
        stats["k8s_audit"] += len(examples)
        print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    # 7. Structured finding JSON (baseline-20260212 pattern)
    for d in REPORTS_DIR.rglob("baseline-*"):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            # Skip raw scanner output files (they have known names)
            if f.stem in ("bandit", "semgrep", "trivy-fs", "grype", "gitleaks",
                          "hadolint-api", "hadolint-ui", "hadolint-services",
                          "hadolint-chromadb-config", "checkov", "conftest",
                          "polaris", "kubescape", "kubescape-cluster",
                          "kube-bench", "results_json", "nuclei"):
                continue
            # Numbered finding files
            if f.stem.isdigit():
                examples = convert_finding_json(f)
                all_examples.extend(examples)
                stats["finding_json"] += len(examples)

    if stats["finding_json"]:
        print(f"  structured findings: {stats['finding_json']} pairs")

    # 8. Final compliance / pre-fix / post-fix reports
    for pattern in ("final-compliance*.md", "pre-fix-audit*.md", "post-fix-audit*.md"):
        for f in REPORTS_DIR.rglob(pattern):
            examples = convert_compliance_report(f)
            all_examples.extend(examples)
            stats["compliance_report"] += len(examples)
            print(f"  {f.relative_to(REPORTS_DIR)}: {len(examples)} pairs")

    stats["total"] = len(all_examples)

    # Verify PII scrubbing
    pii_check_patterns = [
        r'jimjrxieb',
        r'linksmlm\.com',
        r'100\.116\.11\.56',
        r'6LelWk4UAAAA',
    ]
    pii_found = 0
    for ex in all_examples:
        text = json.dumps(ex)
        for pattern in pii_check_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                pii_found += 1
                break

    if pii_found:
        print(f"\n  WARNING: {pii_found} examples still contain PII after scrubbing!")
    else:
        print(f"\n  PII check passed: 0 examples contain known PII patterns")

    # Write output
    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"consulting_reports_{timestamp}.jsonl"

        with open(output_file, "w") as f:
            for ex in all_examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        print(f"\n  Wrote {len(all_examples)} examples to {output_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Convert consulting reports to Katie training data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    print()
    print("=" * 65)
    print("  CONSULTING REPORTS → KATIE TRAINING DATA")
    print("  Real engagements, PII-scrubbed, ChatML format")
    print("=" * 65)
    print()

    stats = find_and_convert(dry_run=args.dry_run)

    print()
    print("=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  Developer findings:    {stats['developer_findings']:>4}")
    print(f"  Remediation plans:     {stats['remediation_plans']:>4}")
    print(f"  Engagement YAML:       {stats['engagement_yaml']:>4}")
    print(f"  Engagement MD:         {stats['engagement_md']:>4}")
    print(f"  Gateway migration:     {stats['gateway_migration']:>4}")
    print(f"  K8s audit:             {stats['k8s_audit']:>4}")
    print(f"  Structured findings:   {stats['finding_json']:>4}")
    print(f"  Compliance reports:    {stats['compliance_report']:>4}")
    print(f"  {'─' * 30}")
    print(f"  TOTAL:                 {stats['total']:>4}")
    print("=" * 65)

    if args.dry_run:
        print("\n  [DRY RUN] No files written.")
    print()


if __name__ == "__main__":
    main()
