"""
NIST 800-53 + AI RMF Control Mapper

Maps security findings to NIST 800-53 control families (all findings) and
NIST AI RMF subcategories (AI-context findings). Uses scanner_mappings.yaml
for initial hints, then refines based on finding content.

AI RMF subcategories are added when finding['ai_context'] is True or
the scanner is listed as ai_context: true in scanner_mappings.yaml.
Reference: NIST AI RMF 1.0 (Jan 2023) + NIST AI 600-1 (Jul 2024)
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_scanner_mappings() -> Dict[str, Any]:
    mappings_path = _CONFIG_DIR / "scanner_mappings.yaml"
    if mappings_path.exists():
        with open(mappings_path) as f:
            return yaml.safe_load(f)
    return {"scanners": {}, "nist_control_families": {}}


# Keyword -> 800-53 control mapping for content-based refinement
_KEYWORD_CONTROLS = {
    "access control": ["AC-2", "AC-3", "AC-6"],
    "authentication": ["IA-2", "IA-5"],
    "mfa": ["IA-2"],
    "multi-factor": ["IA-2"],
    "audit": ["AU-2", "AU-6", "AU-12"],
    "logging": ["AU-2", "AU-3", "AU-12"],
    "cloudtrail": ["AU-2", "AU-12"],
    "encryption": ["SC-8", "SC-13", "SC-28"],
    "tls": ["SC-8"],
    "ssl": ["SC-8"],
    "kms": ["SC-12", "SC-28"],
    "at rest": ["SC-28"],
    "in transit": ["SC-8"],
    "firewall": ["SC-7"],
    "security group": ["SC-7"],
    "network acl": ["SC-7"],
    "vpc": ["SC-7"],
    "patch": ["SI-2"],
    "update": ["SI-2"],
    "vulnerability": ["RA-5", "SI-2"],
    "cve": ["RA-5", "SI-2"],
    "malware": ["SI-3"],
    "antivirus": ["SI-3"],
    "monitoring": ["SI-4"],
    "ids": ["SI-4"],
    "ips": ["SI-4"],
    "intrusion": ["SI-4"],
    "guardduty": ["SI-4"],
    "incident": ["IR-4", "IR-5", "IR-6"],
    "containment": ["IR-4"],
    "backup": ["CP-9"],
    "recovery": ["CP-10"],
    "configuration": ["CM-6", "CM-7"],
    "baseline": ["CM-2", "CM-6"],
    "hardening": ["CM-6", "CM-7"],
    "least privilege": ["AC-6"],
    "iam": ["AC-2", "AC-6"],
    "role": ["AC-2", "AC-6"],
    "rbac": ["AC-3", "AC-6"],
    "secret": ["IA-5", "SC-28"],
    "credential": ["IA-5"],
    "session": ["AC-12", "SC-23"],
    "integrity": ["SI-7"],
    "file integrity": ["SI-7"],
    "supply chain": ["SR-3", "SR-4"],
    "dependency": ["SR-3"],
}

# AI-specific keywords -> AI RMF subcategory mapping
# Only applied when ai_context is True
_AI_KEYWORD_SUBCATEGORIES = {
    # Prompt injection and adversarial inputs
    "prompt injection": ["MEASURE-2.11", "MAP-3.5", "MANAGE-2.2"],
    "jailbreak": ["MEASURE-2.11", "MANAGE-2.2"],
    "adversarial": ["MEASURE-2.11", "MAP-3.5"],
    "input manipulation": ["MEASURE-2.11", "MANAGE-2.2"],
    # Output safety and reliability
    "hallucination": ["MEASURE-2.5", "GOVERN-1.4", "MANAGE-2.1"],
    "hallucinate": ["MEASURE-2.5", "GOVERN-1.4"],
    "fabricated": ["MEASURE-2.5"],
    "incorrect output": ["MEASURE-2.5", "MEASURE-2.1"],
    "output bias": ["MEASURE-2.9", "MAP-3.2"],
    "bias": ["MEASURE-2.9"],
    # Training data
    "training data": ["MAP-2.3", "MEASURE-2.10", "MAP-4.1"],
    "data poisoning": ["MAP-4.1", "MANAGE-2.2", "MEASURE-2.11"],
    "label poisoning": ["MAP-4.1", "MANAGE-2.2"],
    "data lineage": ["MAP-2.2", "GOVERN-1.6"],
    "pii in training": ["MEASURE-2.10", "MAP-2.3"],
    # RAG and retrieval
    "rag": ["MEASURE-2.6", "MAP-2.3"],
    "retrieval": ["MEASURE-2.6"],
    "embedding": ["MEASURE-2.6", "MAP-4.1"],
    "collection poisoning": ["MEASURE-2.11", "MANAGE-2.2"],
    "vector database": ["MEASURE-2.6"],
    # Model governance and lifecycle
    "model card": ["GOVERN-1.3", "MAP-2.3", "MANAGE-4.2"],
    "model version": ["CM-3", "MANAGE-4.2"],
    "model drift": ["MEASURE-2.7", "MANAGE-4.1"],
    "model inventory": ["GOVERN-5.2", "CM-8"],
    "unregistered": ["GOVERN-1.1"],
    "no registration": ["GOVERN-1.1"],
    # MLOps pipeline
    "mlflow": ["MEASURE-2.7", "GOVERN-6.1"],
    "experiment tracking": ["MEASURE-2.7", "GOVERN-6.1"],
    "checkpoint": ["MANAGE-4.2", "MAP-4.1"],
    "pipeline": ["MAP-4.1", "MANAGE-2.3"],
    # Human oversight
    "no human review": ["MANAGE-2.2", "GOVERN-1.5"],
    "hitl": ["MANAGE-2.2", "MAP-4.2"],
    "autonomous decision": ["GOVERN-1.5", "MANAGE-1.3"],
    # Model supply chain
    "unsigned model": ["MAP-4.1", "SR-4"],
    "unsigned weights": ["MAP-4.1", "SR-4"],
    "model signature": ["MAP-4.1"],
    "base model": ["MAP-2.2", "SR-3"],
    # Transparency
    "not explainable": ["MEASURE-2.5", "GOVERN-1.3"],
    "black box": ["MEASURE-2.5"],
    "no model card": ["GOVERN-1.3", "MAP-2.3"],
}

# Canonical AI RMF function for each subcategory prefix
_AI_RMF_FUNCTIONS = {
    "GOVERN": "GOVERN",
    "MAP": "MAP",
    "MEASURE": "MEASURE",
    "MANAGE": "MANAGE",
}


class NISTMapper:
    """Map security findings to NIST 800-53 controls and AI RMF subcategories."""

    def __init__(self):
        config = _load_scanner_mappings()
        self.scanners = config.get("scanners", {})
        self.control_families = config.get("nist_control_families", {})

    def map_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a normalized finding to NIST 800-53 controls and (if AI context) AI RMF subcategories.

        Args:
            finding: Normalized finding dict from FindingsIngestion.
                     finding['ai_context'] = True triggers AI RMF mapping.

        Returns:
            Dict with:
            - controls: List of 800-53 control IDs
            - primary_control: Most relevant 800-53 control
            - control_families: Mapped family names
            - reasoning: Why these controls were selected
            - ai_rmf_subcategories: List of AI RMF subcategories (empty if not AI context)
            - ai_rmf_primary: Primary AI RMF subcategory
            - ai_rmf_function: GOVERN / MAP / MEASURE / MANAGE (or None)
            - ai_context: bool — whether AI RMF was applied
        """
        controls = set()
        scanner = finding.get("scanner", "")
        scanner_config = self.scanners.get(scanner, {})

        # Determine if this is an AI-context finding
        # Either the finding explicitly sets ai_context, or the scanner config declares it
        ai_context = bool(
            finding.get("ai_context", False)
            or scanner_config.get("ai_context", False)
        )

        # 800-53: Start with scanner-level hints
        hint_controls = scanner_config.get("primary_controls", [])
        controls.update(hint_controls)

        # 800-53: Refine with content-based keyword matching
        searchable = " ".join([
            finding.get("title", ""),
            finding.get("description", ""),
            str(finding.get("raw_fields", {})),
        ]).lower()

        matched_keywords = []
        for keyword, keyword_controls in _KEYWORD_CONTROLS.items():
            if keyword in searchable:
                controls.update(keyword_controls)
                matched_keywords.append(keyword)

        controls_list = sorted(controls)
        primary = controls_list[0] if controls_list else "CM-6"

        # Build 800-53 reasoning
        reasons = []
        if hint_controls:
            reasons.append(f"Scanner '{scanner}' maps to {hint_controls}")
        if matched_keywords:
            reasons.append(f"Keywords matched: {matched_keywords[:5]}")

        # Map to family names
        families = {}
        for ctrl in controls_list:
            family_code = re.match(r"^([A-Z]{2})", ctrl)
            if family_code:
                code = family_code.group(1)
                families[ctrl] = self.control_families.get(code, "Unknown")

        # AI RMF mapping — only when ai_context is True
        ai_rmf_subcategories: List[str] = []
        ai_rmf_primary: Optional[str] = None
        ai_rmf_function: Optional[str] = None
        ai_matched_keywords: List[str] = []

        if ai_context:
            ai_rmf_set: set = set()

            # Start with scanner-level AI RMF hints
            scanner_ai_subcats = scanner_config.get("ai_rmf_subcategories", [])
            ai_rmf_set.update(scanner_ai_subcats)

            # Refine with AI-specific keyword matching
            for keyword, subcats in _AI_KEYWORD_SUBCATEGORIES.items():
                if keyword in searchable:
                    ai_rmf_set.update(subcats)
                    ai_matched_keywords.append(keyword)

            ai_rmf_subcategories = sorted(ai_rmf_set)

            if ai_rmf_subcategories:
                ai_rmf_primary = ai_rmf_subcategories[0]
                # Extract function from primary subcategory (e.g., "MEASURE-2.5" -> "MEASURE")
                func_match = re.match(r"^([A-Z]+)", ai_rmf_primary)
                if func_match:
                    ai_rmf_function = _AI_RMF_FUNCTIONS.get(func_match.group(1))

            if ai_matched_keywords:
                reasons.append(f"AI RMF keywords matched: {ai_matched_keywords[:3]}")

        return {
            "controls": controls_list,
            "primary_control": primary,
            "control_families": families,
            "ai_rmf_subcategories": ai_rmf_subcategories,
            "ai_rmf_primary": ai_rmf_primary,
            "ai_rmf_function": ai_rmf_function,
            "ai_context": ai_context,
            "reasoning": "; ".join(reasons) if reasons else "Default configuration management control",
        }

    def validate_control_id(self, control_id: str) -> bool:
        """Check if a control ID matches the NIST 800-53 format (e.g., AC-6, SI-2)."""
        match = re.match(r"^([A-Z]{2})-\d+$", control_id)
        if not match:
            return False
        family = match.group(1)
        return family in self.control_families

    def validate_ai_rmf_id(self, subcategory_id: str) -> bool:
        """Check if a subcategory ID matches the AI RMF format (e.g., MEASURE-2.5, GOVERN-1.1)."""
        match = re.match(r"^(GOVERN|MAP|MEASURE|MANAGE)-\d+\.\d+$", subcategory_id)
        return match is not None
