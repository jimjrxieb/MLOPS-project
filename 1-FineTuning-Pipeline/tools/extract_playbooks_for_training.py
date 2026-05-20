#!/usr/bin/env python3
"""
GP-CONSULTING Playbook → Training Data Extractor
==================================================
Extracts decision logic from GP-CONSULTING 01-03 into ChatML JSONL
for Katie/JADE training.

Extracts:
  - Playbooks (*.md)         → "Given this engagement step, here's what to do"
  - Fixer scripts (*.sh)     → "Given this finding, here's the fix"
  - Watcher/responder scripts → "Given this alert, here's the response"
  - CAPABILITIES.md          → "Given this scanner output, here's the rank + fixer"
  - Kyverno policies         → "Given this pod spec, here's why it's denied"
  - Falco rules              → "Given this syscall pattern, here's the detection"
  - ENGAGEMENT-GUIDE.md      → "Given this engagement stage, here's the decision tree"

Output: 1-FineTuning-Pipeline/01-raw-data-lake/consulting_playbooks_training.jsonl
"""
import json
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
GP_CONSULTING = _REPO_ROOT / "GP-CONSULTING"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "consulting_playbooks_training.jsonl"

SYSTEM_PROMPTS = {
    "playbook": "You are JADE, a DevSecOps platform engineer executing security engagement playbooks. Follow the playbook step-by-step. Use exact tool names and commands. Classify findings by rank (E/D/C/B/S).",
    "fixer": "You are JADE, a security automation agent. Given a security finding, provide the exact fix script and explain what it does. Reference the scanner that found it and the error code.",
    "watcher": "You are JADE, a runtime security monitor. Given a Kubernetes cluster event, explain what the watcher detects and what response action to take.",
    "responder": "You are JADE, a Kubernetes security responder. Given a runtime alert, execute the appropriate response action. Explain the severity and blast radius.",
    "policy": "You are JADE, a Kubernetes policy expert. Explain what this policy enforces, why it matters, and what happens when a workload violates it. Reference CIS benchmarks and Pod Security Standards.",
    "falco": "You are JADE, a runtime security engineer. Explain what this Falco rule detects, the MITRE ATT&CK mapping, and what the incident response procedure should be.",
    "capabilities": "You are JADE, a security platform architect. Given a scanner or fixer capability list, explain the rank classification system, auto-fix rates, and when human review is required.",
    "engagement": "You are JADE, a consulting engagement lead. Guide the security engagement step-by-step using the decision tree. Explain when to escalate and when to auto-fix.",
}

def msg(system_key, user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPTS[system_key]},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}


def extract_playbooks(package_dir, package_name):
    """Extract playbook .md files as training pairs."""
    examples = []
    playbook_dir = package_dir / "playbooks"
    if not playbook_dir.exists():
        return examples

    for md_file in sorted(playbook_dir.glob("*.md")):
        if md_file.name.lower() == "readme.md":
            continue
        content = md_file.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 100:
            continue

        # Extract title from first heading
        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        title = title_match.group(1) if title_match else md_file.stem

        # Extract description from blockquote
        desc_match = re.search(r'^>\s+(.+?)(?:\n\n|\n>)', content, re.MULTILINE | re.DOTALL)
        desc = desc_match.group(1).replace('\n> ', ' ').strip() if desc_match else ""

        user_q = f"Execute the '{title}' playbook from the {package_name} engagement package."
        if desc:
            user_q += f"\n\nContext: {desc}"

        examples.append(msg("playbook", user_q, content))

    return examples


def extract_fixers(package_dir):
    """Extract fixer .sh/.py scripts as finding→fix training pairs."""
    examples = []
    fixer_dir = package_dir / "fixers"
    if not fixer_dir.exists():
        return examples

    for script in sorted(fixer_dir.rglob("*.sh")):
        content = script.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 50:
            continue

        # Extract header comment for context
        header_lines = []
        for line in content.split("\n"):
            if line.startswith("#") and not line.startswith("#!"):
                header_lines.append(line.lstrip("# ").strip())
            elif not line.startswith("#") and line.strip():
                break

        header = "\n".join(header_lines)
        script_name = script.name
        category = script.parent.name  # e.g., "python", "dockerfile", "web"

        # Build a realistic user query
        user_q = f"A security scanner found an issue in a {category} file. The recommended fixer is `{script_name}`. Show me the fix script and explain what it does."
        if header:
            user_q += f"\n\nScanner output context:\n{header}"

        examples.append(msg("fixer", user_q, content))

    # Also handle .py fixers
    for script in sorted(fixer_dir.rglob("*.py")):
        content = script.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 50:
            continue
        script_name = script.name
        category = script.parent.name
        user_q = f"A security scanner found an issue in a {category} file. Run the `{script_name}` fixer and explain the fix."
        examples.append(msg("fixer", user_q, content))

    return examples


def extract_watchers(package_dir):
    """Extract watcher scripts as monitoring training pairs."""
    examples = []
    watcher_dir = package_dir / "watchers"
    if not watcher_dir.exists():
        return examples

    for script in sorted(watcher_dir.glob("*.sh")):
        content = script.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 50:
            continue

        # Extract the watcher purpose from header
        header_lines = []
        for line in content.split("\n")[:10]:
            if line.startswith("#") and not line.startswith("#!"):
                header_lines.append(line.lstrip("# ").strip())
        header = " ".join(header_lines)

        watch_name = script.stem.replace("watch-", "")
        user_q = f"Run the {watch_name} watcher on the Kubernetes cluster. What does it check for and what findings does it produce?"
        if header:
            user_q += f"\n\nWatcher description: {header}"

        examples.append(msg("watcher", user_q, content))

    return examples


def extract_responders(package_dir):
    """Extract responder scripts as alert→action training pairs."""
    examples = []
    responder_dir = package_dir / "responders"
    if not responder_dir.exists():
        return examples

    for script in sorted(responder_dir.glob("*.sh")):
        content = script.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 50:
            continue

        action_name = script.stem.replace("-", " ")
        user_q = f"A runtime security alert requires the '{action_name}' response action. Execute it and explain the impact."

        examples.append(msg("responder", user_q, content))

    return examples


def extract_kyverno_policies(package_dir):
    """Extract Kyverno policies as policy enforcement training pairs."""
    examples = []
    policy_dirs = [
        package_dir / "templates" / "policies" / "kyverno",
        package_dir / "policy-templates" / "kyverno",
    ]

    for policy_dir in policy_dirs:
        if not policy_dir.exists():
            continue
        for yaml_file in sorted(policy_dir.glob("*.yaml")):
            content = yaml_file.read_text(encoding="utf-8", errors="replace").strip()
            if len(content) < 50:
                continue

            # Extract policy name and description from annotations
            name_match = re.search(r'name:\s*(\S+)', content)
            desc_match = re.search(r'description:\s*>?\-?\s*\n?\s*(.+?)(?:\n\s+\w|\n---)', content, re.DOTALL)
            title_match = re.search(r'policies\.kyverno\.io/title:\s*(.+)', content)

            policy_name = title_match.group(1).strip() if title_match else (name_match.group(1) if name_match else yaml_file.stem)
            desc = desc_match.group(1).strip() if desc_match else ""

            user_q = f"Explain the Kyverno ClusterPolicy '{policy_name}'. What does it enforce and why is it important?"
            if desc:
                user_q += f"\n\nPolicy description: {desc}"

            assistant_text = f"This Kyverno ClusterPolicy enforces the following security control:\n\n```yaml\n{content}\n```\n\n"

            # Add explanation based on common policy patterns
            if "privileged" in content.lower():
                assistant_text += "This policy prevents containers from running in privileged mode, which would give them full host access. Maps to CIS Kubernetes Benchmark 5.2.1 and Pod Security Standards Baseline level."
            elif "capabilities" in content.lower():
                assistant_text += "This policy requires containers to drop ALL Linux capabilities. Only add back specific capabilities needed. Maps to Pod Security Standards Restricted level."
            elif "runAsNonRoot" in content.lower() or "run-as-nonroot" in yaml_file.stem:
                assistant_text += "This policy ensures containers run as non-root users. Running as root inside a container can lead to container escape. Maps to Pod Security Standards Restricted level."
            elif "readOnly" in content.lower() or "readonly" in yaml_file.stem:
                assistant_text += "This policy requires read-only root filesystems. Writable filesystems allow attackers to modify binaries or plant malware. Use emptyDir volumes for /tmp."
            elif "latest" in content.lower():
                assistant_text += "This policy prevents use of the :latest image tag. Tags are mutable and can be overwritten. Use image digests or specific version tags for reproducibility."
            elif "resource" in content.lower() and "limits" in content.lower():
                assistant_text += "This policy requires resource limits (CPU/memory) on all containers. Without limits, a single pod can consume all node resources, causing noisy-neighbor problems."

            examples.append(msg("policy", user_q, assistant_text))

    return examples


def extract_falco_rules(package_dir):
    """Extract Falco rules as detection pattern training pairs."""
    examples = []
    rule_dirs = [
        package_dir / "templates" / "falco-rules",
        package_dir / "falco-rules",
    ]

    for rule_dir in rule_dirs:
        if not rule_dir.exists():
            continue
        for yaml_file in sorted(rule_dir.glob("*.yaml")):
            content = yaml_file.read_text(encoding="utf-8", errors="replace").strip()
            if len(content) < 50 or "allowlist" in yaml_file.name:
                continue

            rule_topic = yaml_file.stem.replace("-", " ").replace("_", " ")
            user_q = f"Explain the Falco rules for detecting {rule_topic}. What syscalls/events do they watch and what is the MITRE ATT&CK mapping?"

            assistant_text = f"These FalcoRule definitions detect {rule_topic} at runtime:\n\n```yaml\n{content}\n```\n\nDeploy these rules to `/etc/falco/rules.d/` and reload Falco. Forward alerts via Falcosidekick to your SIEM for incident response."

            examples.append(msg("falco", user_q, assistant_text))

    return examples


def extract_capabilities(package_dir, package_name):
    """Extract CAPABILITIES.md files as rank/mapping training pairs."""
    examples = []

    for caps_file in package_dir.rglob("CAPABILITIES.md"):
        content = caps_file.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 100:
            continue

        component = caps_file.parent.name  # e.g., "scanners", "fixers", "watchers"
        user_q = f"List the {component} capabilities for the {package_name} engagement package. Include rank classifications, auto-fix rates, and tool mappings."

        examples.append(msg("capabilities", user_q, content))

    return examples


def extract_engagement_guide(package_dir, package_name):
    """Extract ENGAGEMENT-GUIDE.md as decision tree training data."""
    examples = []
    guide_file = package_dir / "ENGAGEMENT-GUIDE.md"
    if not guide_file.exists():
        return examples

    content = guide_file.read_text(encoding="utf-8", errors="replace").strip()
    if len(content) < 100:
        return examples

    user_q = f"Walk me through the {package_name} security engagement. What is the decision tree for each step?"

    examples.append(msg("engagement", user_q, content))

    return examples


def main():
    all_examples = []
    packages = [
        ("01-APP-SEC", "Application Security (Pre-Deploy)"),
        ("02-CLUSTER-HARDENING", "Cluster Hardening (Deploy-Time)"),
        ("03-DEPLOY-RUNTIME", "Runtime Security (Post-Deploy)"),
    ]

    for pkg_dir_name, pkg_label in packages:
        pkg_dir = GP_CONSULTING / pkg_dir_name
        if not pkg_dir.exists():
            print(f"  WARNING: {pkg_dir} not found, skipping")
            continue

        print(f"\n=== {pkg_label} ({pkg_dir_name}) ===")

        playbooks = extract_playbooks(pkg_dir, pkg_label)
        print(f"  Playbooks: {len(playbooks)}")
        all_examples.extend(playbooks)

        fixers = extract_fixers(pkg_dir)
        print(f"  Fixers: {len(fixers)}")
        all_examples.extend(fixers)

        watchers = extract_watchers(pkg_dir)
        print(f"  Watchers: {len(watchers)}")
        all_examples.extend(watchers)

        responders = extract_responders(pkg_dir)
        print(f"  Responders: {len(responders)}")
        all_examples.extend(responders)

        policies = extract_kyverno_policies(pkg_dir)
        print(f"  Kyverno policies: {len(policies)}")
        all_examples.extend(policies)

        falco = extract_falco_rules(pkg_dir)
        print(f"  Falco rules: {len(falco)}")
        all_examples.extend(falco)

        caps = extract_capabilities(pkg_dir, pkg_label)
        print(f"  Capabilities docs: {len(caps)}")
        all_examples.extend(caps)

        guide = extract_engagement_guide(pkg_dir, pkg_label)
        print(f"  Engagement guide: {len(guide)}")
        all_examples.extend(guide)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_examples)} training examples extracted")
    print(f"Output: {OUTPUT_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
