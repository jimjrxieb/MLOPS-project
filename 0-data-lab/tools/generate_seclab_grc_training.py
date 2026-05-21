#!/usr/bin/env python3
"""
GP-SECLAB GRC-HAT → BERU training data generator.

Sources:
  GRC-HAT/*/scenarios/*/governance.md  — CISO governance briefs (full + sections)
  GRC-HAT/*/scenarios/*/break.md       — finding context (used to enrich user prompt)
  GRC-HAT/*/control-map.md            — per-layer NIST control mappings
  docs/controls/*.md                   — individual control definitions
  docs/poam-template.md               — POA&M format reference

Output: 1-FineTuning-Pipeline/01-raw-data-lake/seclab_grc_training.jsonl

Usage:
    python3 tools/generate_seclab_grc_training.py
    python3 tools/generate_seclab_grc_training.py --dry-run
"""

import json
import re
import argparse
import yaml
from pathlib import Path

_DATA_LAB  = Path(__file__).resolve().parent.parent
_REPO_ROOT  = _DATA_LAB.parents[1]
GP_SECLAB  = _REPO_ROOT / "GP-SECLAB"
OUTPUT_DIR = _DATA_LAB.parent / "1-FineTuning-Pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "seclab_grc_training.jsonl"

BERU_SYSTEM = (
    "You are BERU, a GRC analyst specializing in NIST 800-53 Rev 5 and NIST AI RMF / "
    "AI 600-1 audits. You assess systems, document findings with dual citations where AI "
    "is in scope, and produce POA&M items, CISO governance briefs, SSP narratives, and "
    "risk assessments. You do not build or fix systems — you audit, document, and advise. "
    "Your analysis always includes: the specific control violated, likelihood × impact risk "
    "score, business impact with dollar estimates where applicable, proportionality analysis "
    "(Gordon-Loeb), and a clear leadership recommendation."
)


def msg(user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system",  "content": BERU_SYSTEM},
            {"role": "user",    "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def extract_section(text: str, heading: str) -> str:
    """Pull the content under a markdown ## heading."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r"\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def control_id_from_path(path: Path) -> str:
    """Derive control ID from scenario directory name (e.g. 'PE-3-physical-access' → 'PE-3')."""
    name = path.parent.name  # e.g. "PE-3-physical-access"
    return re.match(r"([A-Z]+-\d+[a-z]?)", name).group(1) if re.match(r"[A-Z]+-\d+", name) else name


def layer_name_from_path(path: Path) -> str:
    """Derive OSI layer label from the GRC-HAT subdirectory."""
    for part in path.parts:
        m = re.match(r"\d+-(.+)", part)
        if m:
            return m.group(1).replace("-", " ").title()
    return "Network"


# ─── 1. Governance brief examples ────────────────────────────────────────────

def examples_from_governance(gov_path: Path) -> list[dict]:
    examples = []
    gov_text = gov_path.read_text(encoding="utf-8", errors="replace").strip()
    if len(gov_text) < 200:
        return examples

    control_id   = control_id_from_path(gov_path)
    layer        = layer_name_from_path(gov_path)
    scenario_dir = gov_path.parent

    # Pull finding context from break.md if available
    break_path = scenario_dir / "break.md"
    finding_context = ""
    if break_path.exists():
        break_text = break_path.read_text(encoding="utf-8", errors="replace").strip()
        # First paragraph after the title
        paras = [p.strip() for p in break_text.split("\n\n") if p.strip() and not p.startswith("#")]
        finding_context = paras[0] if paras else ""

    # Extract title from governance.md h1
    title_match = re.search(r"^#\s+(.+)", gov_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else f"{control_id} Finding"

    # ── Example 1: full governance brief ──
    user1 = (
        f"A security assessment of our {layer} infrastructure identified a {control_id} finding. "
        f"Produce a complete CISO governance brief including risk score, business impact, "
        f"Gordon-Loeb proportionality analysis, and leadership recommendation."
    )
    if finding_context:
        user1 += f"\n\nFinding context: {finding_context}"
    examples.append(msg(user1, gov_text))

    # ── Example 2: risk score section ──
    risk_section = extract_section(gov_text, "Risk Assessment")
    if len(risk_section) > 50:
        user2 = (
            f"What is the risk score for the {control_id} finding identified during the "
            f"{layer} security assessment? Provide likelihood, impact, inherent risk score, "
            f"and risk level."
        )
        examples.append(msg(user2, risk_section))

    # ── Example 3: ROSI / proportionality ──
    rosi_section = extract_section(gov_text, "Proportionality Analysis (Gordon-Loeb)")
    if len(rosi_section) > 50:
        user3 = (
            f"Calculate the return on security investment (ROSI) and Gordon-Loeb "
            f"proportionality for remediating the {control_id} finding. Is the remediation "
            f"cost justified?"
        )
        examples.append(msg(user3, rosi_section))

    # ── Example 4: leadership recommendation ──
    rec_section = extract_section(gov_text, "Recommendation to Leadership")
    if len(rec_section) > 30:
        user4 = (
            f"What is the recommended leadership decision for the {control_id} finding? "
            f"Should we mitigate, accept, or transfer this risk? Justify the recommendation."
        )
        examples.append(msg(user4, rec_section))

    # ── Example 5: business impact ──
    impact_section = extract_section(gov_text, "Business Impact")
    if len(impact_section) > 50:
        user5 = (
            f"What is the business impact of the {control_id} finding? Include the attack path, "
            f"data exposure scope, estimated breach cost, and regulatory exposure."
        )
        examples.append(msg(user5, impact_section))

    # ── Example 6: control requirement ──
    control_section = extract_section(gov_text, "NIST 800-53 Control Requirement")
    if len(control_section) > 50:
        user6 = (
            f"Which NIST 800-53 controls are violated by the {control_id} finding? "
            f"Quote the control requirement and list the regulatory frameworks that require it."
        )
        examples.append(msg(user6, control_section))

    return examples


# ─── 2. Control map examples ─────────────────────────────────────────────────

def examples_from_control_map(cmap_path: Path) -> list[dict]:
    examples = []
    text = cmap_path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) < 100:
        return examples

    layer = layer_name_from_path(cmap_path)

    # Full control map
    user1 = (
        f"What NIST 800-53 controls apply to the {layer} of the OSI model? "
        f"List each control, the tool used to satisfy it, the enterprise equivalent, "
        f"and what a misconfiguration looks like."
    )
    examples.append(msg(user1, text))

    # Row-level: extract individual controls from the table
    rows = re.findall(r"\|\s*([A-Z]+-\d+[a-z]?)\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|", text)
    for control_id, control_name, tool, enterprise, misconfig in rows:
        control_id = control_id.strip()
        control_name = control_name.strip()
        misconfig = misconfig.strip()
        if len(misconfig) < 10:
            continue
        user2 = (
            f"At the {layer}, what does a {control_id} ({control_name}) misconfiguration "
            f"look like? What tool detects it?"
        )
        answer2 = (
            f"**{control_id} — {control_name}**\n\n"
            f"Detection tool: {tool.strip()}\n\n"
            f"Misconfiguration pattern: {misconfig}"
        )
        examples.append(msg(user2, answer2))

    return examples


# ─── 3. Individual control definition examples ────────────────────────────────

def examples_from_control_doc(ctrl_path: Path) -> list[dict]:
    examples = []
    text = ctrl_path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) < 100:
        return examples

    # Parse YAML frontmatter
    fm = {}
    fm_match = re.match(r"^---\n(.+?)\n---\n", text, re.DOTALL)
    body = text
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1))
        except Exception:
            pass
        body = text[fm_match.end():].strip()

    control_id   = fm.get("id", ctrl_path.stem)
    control_name = fm.get("name", "")
    audit_q      = fm.get("question", "")
    description  = fm.get("description", "")
    if isinstance(description, str):
        description = description.strip()

    # ── Example 1: explain the control ──
    user1 = f"Explain NIST 800-53 {control_id} ({control_name}). What does it require and why does it matter?"
    answer1 = body if len(body) > 100 else f"**{control_id} — {control_name}**\n\n{description}"
    examples.append(msg(user1, answer1))

    # ── Example 2: audit question ──
    if audit_q and len(str(audit_q)) > 20:
        user2 = f"What is the primary audit question for NIST 800-53 {control_id}?"
        answer2 = f"**{control_id} Audit Question:**\n\n{audit_q}\n\n{description}" if description else str(audit_q)
        examples.append(msg(user2, answer2))

    return examples


# ─── 4. POA&M template example ───────────────────────────────────────────────

def examples_from_poam_template(poam_path: Path) -> list[dict]:
    text = poam_path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) < 50:
        return []
    user = (
        "What is the standard POA&M (Plan of Action and Milestones) format for documenting "
        "security findings? Show me the required fields and an example entry."
    )
    return [msg(user, text)]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not GP_SECLAB.exists():
        print(f"ERROR: GP-SECLAB not found at {GP_SECLAB}")
        return

    all_examples = []

    # 1. Governance briefs
    gov_files = sorted(GP_SECLAB.rglob("governance.md"))
    print(f"Governance briefs:  {len(gov_files)} files")
    for f in gov_files:
        examples_from_governance(f)
        exs = examples_from_governance(f)
        all_examples.extend(exs)

    # 2. Control maps
    cmap_files = sorted(GP_SECLAB.rglob("control-map.md"))
    print(f"Control maps:       {len(cmap_files)} files")
    for f in cmap_files:
        all_examples.extend(examples_from_control_map(f))

    # 3. Individual control docs
    ctrl_docs = sorted((GP_SECLAB / "docs" / "controls").glob("*.md"))
    print(f"Control docs:       {len(ctrl_docs)} files")
    for f in ctrl_docs:
        all_examples.extend(examples_from_control_doc(f))

    # 4. POA&M template
    poam = GP_SECLAB / "docs" / "poam-template.md"
    if poam.exists():
        all_examples.extend(examples_from_poam_template(poam))
        print(f"POA&M template:     1 file")

    # Deduplicate
    seen = set()
    unique = []
    for ex in all_examples:
        key = ex["messages"][1]["content"][:120]
        if key not in seen:
            seen.add(key)
            unique.append(ex)

    print(f"\nTotal examples:     {len(unique)}")
    print(f"Output:             {OUTPUT_FILE}")

    if args.dry_run:
        print("\n--- DRY RUN — first 2 examples ---")
        for ex in unique[:2]:
            print(json.dumps(ex, indent=2))
            print()
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in unique:
            f.write(json.dumps(ex) + "\n")

    print(f"\nWrote {len(unique)} examples → {OUTPUT_FILE}")
    print("Next: python3 -m pytest 8-tests/test_beru_data_quality.py -v")


if __name__ == "__main__":
    main()
