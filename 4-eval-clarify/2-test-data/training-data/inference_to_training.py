#!/usr/bin/env python3
"""
JADE v0.8 Inference Tests to Training Data Converter
=====================================================
Converts the entire inference-tests directory into training data:
  - FAULTY/FIXED file pairs (manifests, terraform, docker, GHA)
  - inference_tests.jsonl structured tests
  - Rego FAULTY/FIXED policy pairs
  - Scan/fix logs with interpretations
  - Policy violation logs with analysis

Output: Training data in JSONL format for GP-GLUE pipeline

Usage:
    python3 inference_to_training.py                    # Process everything
    python3 inference_to_training.py --dry-run          # Preview without writing
    python3 inference_to_training.py --source fixtures  # Only fixtures
    python3 inference_to_training.py --source jsonl     # Only inference_tests.jsonl
    python3 inference_to_training.py --source rego      # Only Rego policies
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Directories
BASE_DIR = Path(__file__).parent
FIXTURES_DIR = BASE_DIR / "fixtures"
POLICIES_DIR = BASE_DIR / "policies"
DEFAULT_OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE/01-raw-data-lake")

# System prompt for JADE
JADE_SYSTEM = """You are JADE (Junior Automated DevSecOps Engineer), a security-focused AI assistant specializing in Kubernetes, cloud security, policy-as-code (OPA/Rego, Kyverno, Gatekeeper), and DevSecOps practices. When presented with security issues, provide accurate analysis, remediation steps, and corrected configurations when applicable."""


def detect_file_type(filepath: Path, content: str) -> str:
    """Detect the type/domain of a configuration file"""
    filename = filepath.name.lower()
    suffix = filepath.suffix.lower()

    if suffix == ".rego":
        return "opa"
    if suffix == ".tf":
        return "terraform"
    if suffix in [".yml", ".yaml"]:
        if "on:" in content and "jobs:" in content:
            return "github-actions"
        if "services:" in content and ("version:" in content or "networks:" in content):
            return "docker-compose"
        return "kubernetes"
    if filename.startswith("dockerfile"):
        return "docker"
    if ".log" in filename:
        return "log"
    return "unknown"


def detect_skill_level(content: str, file_type: str, category: str = "") -> str:
    """Assign skill level based on content complexity"""
    content_lower = content.lower()

    # A-rank: MITRE ATT&CK, threat modeling, incident response
    if any(kw in content_lower for kw in ["mitre att&ck", "attack vector", "incident response", "threat model"]):
        return "A"

    # B-rank: CIS benchmarks, control plane, complex troubleshooting
    if any(kw in content_lower for kw in ["cis", "control plane", "kube-bench", "kubescape", "rollout stuck"]):
        return "B"

    # C-rank: Policy-as-code, network policies, RBAC, Terraform
    if any(kw in content_lower for kw in ["gatekeeper", "kyverno", "opa", "rego", "networkpolicy", "rbac", "clusterrole"]):
        return "C"

    # D-rank: Basic violations, logs, container security
    if any(kw in content_lower for kw in ["privileged", "latest", "secrets", "dockerfile", "scan", "findings"]):
        return "D"

    return "D"


def extract_issues_from_comments(content: str) -> List[str]:
    """Extract issue descriptions from file comments"""
    issues = []
    patterns = [
        r'#\s*BUG\s*#?\d*:?\s*(.+?)(?:\n|$)',
        r'#\s*VIOLATION:?\s*(.+?)(?:\n|$)',
        r'#\s*Issue:?\s*(.+?)(?:\n|$)',
        r'#\s*CRITICAL:?\s*(.+?)(?:\n|$)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        issues.extend([m.strip() for m in matches if m.strip()])
    return list(set(issues))


def extract_fixes_from_comments(content: str) -> List[str]:
    """Extract fix descriptions from file comments"""
    fixes = []
    patterns = [
        r'#\s*FIXED?:?\s*(.+?)(?:\n|$)',
        r'#\s*Fix\s*(?:Applied)?:?\s*(.+?)(?:\n|$)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        fixes.extend([m.strip() for m in matches if m.strip() and len(m.strip()) > 5])
    return list(set(fixes))


# =============================================================================
# SECTION 1: FAULTY/FIXED File Pairs (Manifests, Terraform, Docker, GHA)
# =============================================================================

def find_fixture_pairs() -> List[Tuple[Path, Path]]:
    """Find all FAULTY/FIXED file pairs in fixtures directory"""
    pairs = []

    # Pattern 1: FAULTY/ and FAULTYFIXED/ directories
    faulty_dir = FIXTURES_DIR / "FAULTY"
    fixed_dir = FIXTURES_DIR / "FAULTYFIXED"

    if faulty_dir.exists():
        for faulty_file in faulty_dir.iterdir():
            if faulty_file.is_file() and not faulty_file.name.startswith('.'):
                name = faulty_file.name
                candidates = []

                if name.startswith("insecure-"):
                    candidates.append(name.replace("insecure-", "secure-"))
                if "-FAULTY" in name:
                    candidates.append(name.replace("-FAULTY", "-FIXED"))

                base = faulty_file.stem.replace("-FAULTY", "").replace("insecure-", "")
                candidates.append(f"secure-{base}{faulty_file.suffix}")
                candidates.append(f"{base}-FIXED{faulty_file.suffix}")

                if "-wildcard" in name:
                    base_no_wildcard = base.replace("-wildcard", "")
                    candidates.append(f"secure-{base_no_wildcard}{faulty_file.suffix}")
                candidates.append(f"{base}{faulty_file.suffix}")

                if "Dockerfile" in name:
                    candidates.append(name.replace("FAULTY", "FIXED"))

                for candidate in candidates:
                    fixed_file = fixed_dir / candidate
                    if fixed_file.exists():
                        pairs.append((faulty_file, fixed_file))
                        break

    # Pattern 2: terraform/ directory with -FAULTY/-FIXED suffixes
    terraform_dir = FIXTURES_DIR / "terraform"
    if terraform_dir.exists():
        for faulty_file in terraform_dir.glob("*-FAULTY.tf"):
            fixed_name = faulty_file.name.replace("-FAULTY.tf", "-FIXED.tf")
            fixed_file = terraform_dir / fixed_name
            if fixed_file.exists():
                pairs.append((faulty_file, fixed_file))

    return pairs


def create_fixture_example(faulty_path: Path, faulty_content: str, fixed_path: Path, fixed_content: str) -> Dict:
    """Create training example from FAULTY/FIXED pair"""
    file_type = detect_file_type(faulty_path, faulty_content)
    skill_level = detect_skill_level(fixed_content, file_type)
    issues = extract_issues_from_comments(faulty_content)
    fixes = extract_fixes_from_comments(fixed_content)

    file_type_friendly = {
        "kubernetes": "Kubernetes manifest",
        "terraform": "Terraform configuration",
        "docker": "Dockerfile",
        "docker-compose": "Docker Compose file",
        "github-actions": "GitHub Actions workflow",
    }.get(file_type, "configuration file")

    user_prompt = f"""Analyze this {file_type_friendly} for security issues and provide a corrected version:

```{faulty_path.suffix.lstrip('.') or 'yaml'}
{faulty_content}
```"""

    issue_summary = ""
    if issues:
        issue_summary = "## Security Issues Found\n\n"
        for i, issue in enumerate(issues[:10], 1):
            issue_summary += f"{i}. {issue}\n"
        issue_summary += "\n"

    fix_summary = ""
    if fixes:
        fix_summary = "## Fixes Applied\n\n"
        for i, fix in enumerate(fixes[:10], 1):
            fix_summary += f"{i}. {fix}\n"
        fix_summary += "\n"

    assistant_response = f"""{issue_summary}{fix_summary}## Corrected Configuration

```{fixed_path.suffix.lstrip('.') or 'yaml'}
{fixed_content}
```"""

    return {
        "messages": [
            {"role": "system", "content": JADE_SYSTEM},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ],
        "metadata": {
            "source": f"fixtures/{faulty_path.name}",
            "type": "applied_skill_fix",
            "domain": file_type,
            "skill_level": skill_level,
            "category": "fix_generation"
        }
    }


def process_fixtures() -> List[Dict]:
    """Process all FAULTY/FIXED fixture pairs"""
    examples = []
    pairs = find_fixture_pairs()

    print(f"\n[Fixtures] Found {len(pairs)} FAULTY/FIXED pairs")

    for faulty_path, fixed_path in pairs:
        try:
            faulty_content = faulty_path.read_text()
            fixed_content = fixed_path.read_text()
            example = create_fixture_example(faulty_path, faulty_content, fixed_path, fixed_content)
            examples.append(example)
            print(f"  {faulty_path.name} -> {fixed_path.name}")
        except Exception as e:
            print(f"  ERROR: {faulty_path.name}: {e}")

    return examples


# =============================================================================
# SECTION 2: Rego FAULTY/FIXED Policy Pairs
# =============================================================================

def find_rego_pairs() -> List[Tuple[Path, Path]]:
    """Find all Rego FAULTY/FIXED pairs"""
    pairs = []
    faulty_dir = POLICIES_DIR / "faulty-examples"

    if faulty_dir.exists():
        for faulty_file in faulty_dir.glob("*-FAULTY.rego"):
            fixed_name = faulty_file.name.replace("-FAULTY.rego", "-FIXED.rego")
            fixed_file = faulty_dir / fixed_name
            if fixed_file.exists():
                pairs.append((faulty_file, fixed_file))

    return pairs


def create_rego_example(faulty_path: Path, faulty_content: str, fixed_path: Path, fixed_content: str) -> Dict:
    """Create training example from Rego FAULTY/FIXED pair"""
    # Extract bug description from filename or comments
    bug_type = faulty_path.stem.replace("-FAULTY", "").split("-", 1)[-1].replace("-", " ")

    user_prompt = f"""This Rego policy has a bug ({bug_type}). Find and fix the issue:

```rego
{faulty_content}
```"""

    assistant_response = f"""The issue is: {bug_type}

## Fixed Policy

```rego
{fixed_content}
```"""

    return {
        "messages": [
            {"role": "system", "content": JADE_SYSTEM},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ],
        "metadata": {
            "source": f"policies/faulty-examples/{faulty_path.name}",
            "type": "applied_skill_fix",
            "domain": "opa",
            "skill_level": "C",
            "category": "rego_fix",
            "bug_type": bug_type
        }
    }


def process_rego_pairs() -> List[Dict]:
    """Process all Rego FAULTY/FIXED pairs"""
    examples = []
    pairs = find_rego_pairs()

    print(f"\n[Rego] Found {len(pairs)} FAULTY/FIXED pairs")

    for faulty_path, fixed_path in pairs:
        try:
            faulty_content = faulty_path.read_text()
            fixed_content = fixed_path.read_text()
            example = create_rego_example(faulty_path, faulty_content, fixed_path, fixed_content)
            examples.append(example)
            print(f"  {faulty_path.name} -> {fixed_path.name}")
        except Exception as e:
            print(f"  ERROR: {faulty_path.name}: {e}")

    return examples


# =============================================================================
# SECTION 3: inference_tests.jsonl Structured Tests
# =============================================================================

def process_inference_tests_jsonl() -> List[Dict]:
    """Process inference_tests.jsonl - structured test cases with prompts"""
    examples = []
    jsonl_path = BASE_DIR / "inference_tests.jsonl"

    if not jsonl_path.exists():
        print(f"\n[JSONL] Not found: {jsonl_path}")
        return examples

    with open(jsonl_path) as f:
        tests = [json.loads(line) for line in f if line.strip()]

    print(f"\n[JSONL] Found {len(tests)} structured tests")

    for test in tests:
        try:
            example = create_jsonl_example(test)
            if example:
                examples.append(example)
                print(f"  {test.get('id', 'unknown')}: {test.get('category', 'unknown')}")
        except Exception as e:
            print(f"  ERROR: {test.get('id', 'unknown')}: {e}")

    return examples


def create_jsonl_example(test: Dict) -> Optional[Dict]:
    """Create training example from inference_tests.jsonl test case"""
    test_id = test.get("id", "")
    category = test.get("category", "")
    prompt = test.get("prompt", "")
    rank = test.get("rank", "D")
    metadata = test.get("metadata", {})

    # Get input content if file specified
    input_content = ""
    input_file = test.get("input_file", "")
    if input_file:
        input_path = BASE_DIR / input_file
        if input_path.exists():
            input_content = input_path.read_text()

    # Get answer/reference content if file specified
    answer_content = ""
    answer_file = test.get("answer_file", "") or test.get("reference_policy", "")
    if answer_file:
        answer_path = BASE_DIR / answer_file
        if answer_path.exists():
            answer_content = answer_path.read_text()

    # Build user prompt
    if input_content:
        suffix = Path(input_file).suffix.lstrip('.') or 'yaml'
        user_prompt = f"""{prompt}

```{suffix}
{input_content}
```"""
    else:
        user_prompt = prompt

    # Build assistant response based on category
    assistant_response = build_expected_response(test, input_content, answer_content)

    if not assistant_response:
        return None

    return {
        "messages": [
            {"role": "system", "content": JADE_SYSTEM},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ],
        "metadata": {
            "source": f"inference_tests.jsonl:{test_id}",
            "type": "applied_skill",
            "domain": metadata.get("domain", "unknown"),
            "skill_level": rank,
            "category": category,
            "task_type": metadata.get("task_type", category)
        }
    }


def build_expected_response(test: Dict, input_content: str, answer_content: str) -> str:
    """Build expected response based on test category and available data"""
    category = test.get("category", "")
    expected_keywords = test.get("expected_keywords", [])
    expected_violations = test.get("expected_violations", [])
    expected_fixes = test.get("expected_fixes", [])
    expected_actions = test.get("expected_actions", [])
    expected_policies = test.get("expected_policies", [])

    response = ""

    if category == "violation_detection":
        if expected_violations:
            response = "## Security Violations Found\n\n"
            for i, v in enumerate(expected_violations, 1):
                response += f"{i}. **{v.replace('_', ' ').title()}**\n"
            response += "\n"
        if answer_content:
            suffix = Path(test.get("answer_file", "")).suffix.lstrip('.') or 'yaml'
            response += f"## Recommended Fix\n\n```{suffix}\n{answer_content}\n```"

    elif category == "fix_generation":
        if expected_fixes:
            response = "## Fixes Applied\n\n"
            for i, f in enumerate(expected_fixes, 1):
                response += f"{i}. `{f}`\n"
            response += "\n"
        if answer_content:
            suffix = Path(test.get("answer_file", "")).suffix.lstrip('.') or 'yaml'
            response += f"## Corrected Configuration\n\n```{suffix}\n{answer_content}\n```"

    elif category == "policy_generation":
        if answer_content:
            response = f"Here's the OPA/Rego policy:\n\n```rego\n{answer_content}\n```"
        else:
            response = "## Policy Implementation\n\n"
            if expected_keywords:
                response += "Key elements to include:\n"
                for kw in expected_keywords[:5]:
                    response += f"- `{kw}`\n"

    elif category == "policy_classification":
        if expected_policies:
            response = "## Policies Violated\n\n"
            for p in expected_policies:
                response += f"- `{p}`\n"

    elif category in ["log_interpretation", "jsa_decision"]:
        if expected_actions:
            response = f"## Recommended Action: {expected_actions[0].upper()}\n\n"
            response += "Reasoning:\n"
            for kw in expected_keywords[:5]:
                response += f"- {kw}\n"

    elif category in ["k8s_troubleshooting", "gha_troubleshooting"]:
        response = "## Analysis\n\n"
        if expected_keywords:
            response += "Key findings:\n"
            for kw in expected_keywords[:5]:
                response += f"- {kw}\n"
        if expected_fixes:
            response += "\n## Remediation\n\n"
            for fix in expected_fixes:
                response += f"- {fix}\n"

    elif category == "incident_response":
        if expected_actions:
            response = "## Incident Response Plan\n\n"
            for i, action in enumerate(expected_actions, 1):
                response += f"{i}. **{action.title()}**\n"

    elif category in ["gatekeeper_analysis", "conftest_analysis", "kubebench_analysis", "kubescape_analysis"]:
        response = "## Analysis\n\n"
        if expected_keywords:
            for kw in expected_keywords[:5]:
                response += f"- {kw}\n"
        if expected_fixes:
            response += "\n## Remediation Steps\n\n"
            for fix in expected_fixes:
                response += f"- {fix}\n"

    elif category == "rego_fix":
        if answer_content:
            response = f"## Fixed Policy\n\n```rego\n{answer_content}\n```"

    else:
        # Generic response based on keywords
        if expected_keywords:
            response = "## Key Points\n\n"
            for kw in expected_keywords:
                response += f"- {kw}\n"

    return response


# =============================================================================
# SECTION 4: Log Files with Expected Interpretations
# =============================================================================

def process_log_files() -> List[Dict]:
    """Process log files that are referenced in inference_tests.jsonl"""
    examples = []

    # Scan logs
    scan_logs = [
        ("fixtures/logs/scans/gitleaks-clean.log", "Clean scan - no secrets found", "D", "SKIP_FIX_PHASE"),
        ("fixtures/logs/scans/gitleaks-findings.log", "5 secrets detected - critical findings", "C", "PROCEED_WITH_FIX"),
        ("fixtures/logs/scans/trivy-vulns.log", "Vulnerability scan with critical CVEs", "C", "PROCEED_WITH_FIX"),
    ]

    # Fix logs
    fix_logs = [
        ("fixtures/logs/fixes/gitleaks-fix-success.log", "Successful secret remediation", "D", None),
        ("fixtures/logs/fixes/trivy-fix-partial.log", "Partial fix - 58% success, needs escalation", "C", "ESCALATE_TO_HUMAN"),
    ]

    # K8s event logs
    k8s_logs = [
        ("fixtures/logs/k8s-events/pod-crashloop.log", "OOMKilled causing CrashLoopBackOff", "C", None),
        ("fixtures/logs/k8s-events/pod-imagepull.log", "ImagePullBackOff - authentication issue", "C", None),
        ("fixtures/logs/k8s-events/deployment-rollout-stuck.log", "Rollout stuck - infrastructure issue", "B", "ESCALATE_TO_HUMAN"),
    ]

    all_logs = scan_logs + fix_logs + k8s_logs

    print(f"\n[Logs] Processing {len(all_logs)} log files")

    for log_file, description, rank, jsa_decision in all_logs:
        log_path = BASE_DIR / log_file
        if log_path.exists():
            try:
                content = log_path.read_text()
                example = create_log_example(log_path, content, description, rank, jsa_decision)
                examples.append(example)
                print(f"  {log_path.name}: {description}")
            except Exception as e:
                print(f"  ERROR: {log_path.name}: {e}")

    return examples


def create_log_example(log_path: Path, content: str, description: str, rank: str, jsa_decision: Optional[str]) -> Dict:
    """Create training example from log file"""
    log_type = log_path.parent.name  # scans, fixes, k8s-events

    if "gitleaks" in log_path.name:
        domain = "jsa-operations"
        prompt = "Analyze this Gitleaks scan log. What is the result and what should be done next?"
    elif "trivy" in log_path.name:
        domain = "jsa-operations"
        prompt = "Analyze this Trivy scan log. What vulnerabilities were found and what's the fix strategy?"
    elif "k8s-events" in log_type or "pod" in log_path.name or "deployment" in log_path.name:
        domain = "kubernetes"
        prompt = "Analyze this Kubernetes event log. What's causing the issue and how should it be fixed?"
    else:
        domain = "jsa-operations"
        prompt = "Analyze this log and provide recommendations."

    user_prompt = f"""{prompt}

```
{content}
```"""

    response = f"## Analysis\n\n{description}\n\n"

    if jsa_decision:
        response += f"## JSA Decision: {jsa_decision}\n\n"
        if jsa_decision == "SKIP_FIX_PHASE":
            response += "No issues found, proceeding to next scanner or completing cycle.\n"
        elif jsa_decision == "PROCEED_WITH_FIX":
            response += "Issues detected. Initiating automated remediation.\n"
        elif jsa_decision == "ESCALATE_TO_HUMAN":
            response += "Issue requires human intervention or is beyond automated fix capability.\n"

    return {
        "messages": [
            {"role": "system", "content": JADE_SYSTEM},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response}
        ],
        "metadata": {
            "source": f"{log_path.parent.name}/{log_path.name}",
            "type": "log_interpretation",
            "domain": domain,
            "skill_level": rank,
            "category": "log_interpretation",
            "jsa_decision": jsa_decision
        }
    }


# =============================================================================
# SECTION 5: Policy Violation Logs
# =============================================================================

def process_policy_violations() -> List[Dict]:
    """Process policy violation log files"""
    examples = []
    violations_dir = FIXTURES_DIR / "policy-violations"

    if not violations_dir.exists():
        return examples

    print(f"\n[Policy Violations] Scanning {violations_dir}")

    for tool_dir in violations_dir.iterdir():
        if tool_dir.is_dir():
            for log_file in tool_dir.glob("*.log"):
                try:
                    content = log_file.read_text()
                    example = create_policy_violation_example(log_file, content, tool_dir.name)
                    examples.append(example)
                    print(f"  {tool_dir.name}/{log_file.name}")
                except Exception as e:
                    print(f"  ERROR: {log_file.name}: {e}")

    return examples


def create_policy_violation_example(log_path: Path, content: str, tool: str) -> Dict:
    """Create training example from policy violation log"""
    tool_prompts = {
        "gatekeeper": "Analyze this Gatekeeper admission denial. What policy was violated and how should the manifest be fixed?",
        "conftest": "Review this Conftest output. What policies failed and what's the priority for fixes?",
        "kube-bench": "Analyze this kube-bench CIS benchmark report. What are the critical failures?",
        "kubescape": "Analyze this Kubescape scan. What are the critical findings and priority remediation steps?",
    }

    prompt = tool_prompts.get(tool, f"Analyze this {tool} output and provide remediation steps.")

    # Determine skill level based on tool
    skill_levels = {
        "gatekeeper": "C",
        "conftest": "C",
        "kube-bench": "B",
        "kubescape": "B",
    }
    rank = skill_levels.get(tool, "C")

    # Check for advanced topics
    if "mitre" in content.lower() or "attack" in content.lower():
        rank = "A"
    elif "control plane" in content.lower() or "control-plane" in content.lower():
        rank = "B"

    user_prompt = f"""{prompt}

```
{content}
```"""

    # Build response based on content analysis
    response = f"## {tool.title()} Analysis\n\n"

    if "DENIED" in content or "FAIL" in content:
        response += "**Status:** Policy violation detected\n\n"
    if "PASS" in content:
        response += "**Status:** Compliant\n\n"

    response += "## Remediation\n\nReview the specific violations above and:\n"
    response += "1. Identify the affected resources\n"
    response += "2. Apply the recommended configuration changes\n"
    response += "3. Re-run the scan to verify compliance\n"

    return {
        "messages": [
            {"role": "system", "content": JADE_SYSTEM},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response}
        ],
        "metadata": {
            "source": f"policy-violations/{tool}/{log_path.name}",
            "type": "policy_violation_analysis",
            "domain": tool,
            "skill_level": rank,
            "category": f"{tool}_analysis"
        }
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Convert inference-tests to training data")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--source", type=str, choices=["all", "fixtures", "jsonl", "rego", "logs", "violations"],
                        default="all", help="Which sources to process")
    args = parser.parse_args()

    print("=" * 60)
    print("JADE v0.8 Inference Tests to Training Data Converter")
    print("=" * 60)
    print(f"Base directory: {BASE_DIR}")
    print(f"Source: {args.source}")
    print("=" * 60)

    all_examples = []

    # Process requested sources
    if args.source in ["all", "fixtures"]:
        all_examples.extend(process_fixtures())

    if args.source in ["all", "rego"]:
        all_examples.extend(process_rego_pairs())

    if args.source in ["all", "jsonl"]:
        all_examples.extend(process_inference_tests_jsonl())

    if args.source in ["all", "logs"]:
        all_examples.extend(process_log_files())

    if args.source in ["all", "violations"]:
        all_examples.extend(process_policy_violations())

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    print(f"Total examples: {len(all_examples)}")

    # Stats by domain
    domains = {}
    levels = {}
    categories = {}

    for ex in all_examples:
        d = ex["metadata"]["domain"]
        l = ex["metadata"]["skill_level"]
        c = ex["metadata"]["category"]
        domains[d] = domains.get(d, 0) + 1
        levels[l] = levels.get(l, 0) + 1
        categories[c] = categories.get(c, 0) + 1

    print(f"\nBy domain:")
    for d, count in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"  {d}: {count}")

    print(f"\nBy skill level:")
    for l in ["E", "D", "C", "B", "A", "S"]:
        if l in levels:
            print(f"  {l}-rank: {levels[l]}")

    print(f"\nBy category:")
    for c, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
        print(f"  {c}: {count}")

    if args.dry_run:
        print("\n[DRY RUN] Would write training data")
        return

    # Write output
    if args.output:
        output_file = Path(args.output)
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = DEFAULT_OUTPUT_DIR / f"inference_training_{timestamp}.jsonl"

    with open(output_file, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\n✅ Written {len(all_examples)} examples to {output_file}")


if __name__ == "__main__":
    main()
