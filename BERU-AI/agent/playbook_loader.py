"""Playbook + control + template loader.

Reads from GP-CONSULTING/NIST-800-53/ at runtime. Single source of truth — do
not copy these files into BERU-AI/. If a playbook changes upstream, BERU picks
it up on the next run.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional


# Resolve GP-CONSULTING/NIST-800-53. Two ways:
#   1. BERU_NIST_DIR env var (set this inside containers — the repo layout
#      doesn't exist at the same relative path once BERU-AI is COPY'd alone)
#   2. Fall back to the in-repo relative path:
#      BERU-AI/agent/playbook_loader.py
#        parents[1] = BERU-AI, parents[2] = GP-MODEL-OPS, parents[3] = GP-copilot (repo root)
def _repo_root_or_none() -> Optional[Path]:
    """The repo root if we're running inside the source tree; None if not deep enough."""
    p = Path(__file__).resolve()
    return p.parents[3] if len(p.parents) > 3 else None


_REPO_ROOT = _repo_root_or_none()


def _default_nist_dir() -> str:
    if _REPO_ROOT is not None:
        return str(_REPO_ROOT / "GP-CONSULTING" / "NIST-800-53")
    # No repo layout (e.g. container without BERU_NIST_DIR set) — last-resort path.
    return "/nist"


def _default_crosswalk_path() -> str:
    if _REPO_ROOT is not None:
        return str(_REPO_ROOT / "GP-MODEL-OPS" / "CAPSTONE-PROJECT" / "frameworks" / "crosswalk" / "800-53-to-ai-rmf.md")
    return "/crosswalk/800-53-to-ai-rmf.md"


NIST_DIR = Path(os.environ.get("BERU_NIST_DIR", _default_nist_dir()))
PLAYBOOK_DIR = NIST_DIR / "playbooks"
CONTROL_DIR = NIST_DIR / "controls"
TEMPLATE_DIR = NIST_DIR / "templates"
SSP_EXAMPLE_DIR = NIST_DIR / "ssp-examples"
CROSSWALK_PATH = Path(os.environ.get("BERU_CROSSWALK_PATH", _default_crosswalk_path()))


def _family_for(control_id: str) -> str:
    """AC-2 -> AC, SI-2 -> SI."""
    m = re.match(r"^([A-Z]{2})-", control_id)
    if not m:
        raise ValueError(f"Not a NIST 800-53 control ID: {control_id!r}")
    return m.group(1)


# Map family code -> playbook filename
_FAMILY_PLAYBOOK = {
    "AC": "01-audit-AC.md",
    "AU": "01-audit-AU.md",
    "CM": "01-audit-CM.md",
    "SC": "01-audit-SC.md",
    "SI": "01-audit-SI.md",
    "RA": "01-audit-RA-IR-CP.md",
    "IR": "01-audit-RA-IR-CP.md",
    "CP": "01-audit-RA-IR-CP.md",
    "CA": "01-audit-RA-IR-CP.md",
    "IA": "01-audit-RA-IR-CP.md",
    "SA": "01-audit-RA-IR-CP.md",
}


@lru_cache(maxsize=32)
def load_start_here() -> str:
    return (PLAYBOOK_DIR / "00-beru-start-here.md").read_text()


@lru_cache(maxsize=32)
def load_family_playbook(family: str) -> str:
    fname = _FAMILY_PLAYBOOK.get(family)
    if not fname:
        raise FileNotFoundError(f"No family playbook for {family!r}")
    return (PLAYBOOK_DIR / fname).read_text()


def family_playbook_path(control_id: str) -> Path:
    family = _family_for(control_id)
    fname = _FAMILY_PLAYBOOK.get(family)
    if not fname:
        raise FileNotFoundError(f"No family playbook for {family!r} (control {control_id})")
    return PLAYBOOK_DIR / fname


@lru_cache(maxsize=128)
def load_control(control_id: str) -> str:
    """Return contents of controls/<ID>.md. Raises if missing.

    The validate_citations node uses control_exists() instead — this raises
    so we don't silently write findings against controls we cannot quote.
    """
    p = CONTROL_DIR / f"{control_id}.md"
    if not p.exists():
        raise FileNotFoundError(f"Control file missing: {p}")
    return p.read_text()


def control_exists(control_id: str) -> bool:
    return (CONTROL_DIR / f"{control_id}.md").exists()


def available_control_ids() -> List[str]:
    return sorted(p.stem for p in CONTROL_DIR.glob("*.md"))


@lru_cache(maxsize=8)
def load_template(name: str) -> str:
    """name: 'beru-finding' or 'poam-item' (without .md)."""
    return (TEMPLATE_DIR / f"{name}.md").read_text()


@lru_cache(maxsize=64)
def load_ssp_example(family: str, tier: str) -> Optional[str]:
    """family: 'AC'/'AU'/.../'SI'. tier: 'bad'/'good'/'great'. None if not present."""
    p = SSP_EXAMPLE_DIR / f"{family}-ssp-{tier}.md"
    return p.read_text() if p.exists() else None


@lru_cache(maxsize=1)
def load_crosswalk() -> str:
    """800-53 ↔ AI RMF crosswalk markdown. Used to pair AI RMF IDs at citation time."""
    if not CROSSWALK_PATH.exists():
        return ""
    return CROSSWALK_PATH.read_text()


_AI_RMF_RE = re.compile(r"\b(GOVERN|MAP|MEASURE|MANAGE)-\d+\.\d+\b")


def ai_rmf_subcategories_for(control_id: str) -> List[str]:
    """Look up AI RMF subcategories paired with a 800-53 control via crosswalk.

    Crosswalk is parsed naively: scan for a section heading containing the
    control_id, then collect any AI RMF subcategory IDs (e.g. GOVERN-1.1)
    until the next heading. Empty list if no entry.
    """
    text = load_crosswalk()
    if not text:
        return []
    lines = text.splitlines()
    in_section = False
    found: List[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            if control_id in stripped:
                in_section = True
                continue
            if in_section:
                break
        if in_section:
            for m in _AI_RMF_RE.finditer(line):
                ident = m.group(0)
                if ident not in found:
                    found.append(ident)
    return found
