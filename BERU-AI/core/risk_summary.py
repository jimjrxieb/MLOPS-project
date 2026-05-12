"""
Risk Summary Generator — CISO-Ready Output

Generates structured JSON + narrative summaries from triaged findings.
Three tiers: executive, technical, compliance (per risk_templates.yaml).

When an LLM provider is available, BERU generates natural language summaries.
Without an LLM, produces template-based summaries from structured data.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_risk_templates() -> Dict[str, Any]:
    path = _CONFIG_DIR / "risk_templates.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    return {"templates": {}}


class RiskSummaryGenerator:
    """Generate CISO-ready risk summaries from triaged findings."""

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: Optional BERU OllamaProvider for LLM-enhanced summaries.
                          Works without it (template-based fallback).
        """
        self.templates = _load_risk_templates().get("templates", {})
        self.llm = llm_provider

    def summarize_finding(self, triage_result: Dict[str, Any],
                          tier: str = "executive") -> Dict[str, Any]:
        """
        Generate a risk summary for a single triaged finding.

        Args:
            triage_result: Output from TriageEngine.triage()
            tier: Summary tier — "executive", "technical", or "compliance"

        Returns:
            triage_result enriched with ciso_summary field
        """
        if self.llm and self.llm.is_available():
            summary = self._llm_summary(triage_result, tier)
        else:
            summary = self._template_summary(triage_result, tier)

        triage_result["ciso_summary"] = summary
        return triage_result

    def summarize_batch(self, triage_results: List[Dict[str, Any]],
                        tier: str = "executive") -> Dict[str, Any]:
        """
        Generate a risk summary for a batch of triaged findings.

        Args:
            triage_results: List of outputs from TriageEngine.triage_batch()
            tier: Summary tier

        Returns:
            Batch summary dict with aggregate stats and narrative
        """
        p1_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P1")
        p2_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P2")
        p3_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P3")
        p4_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P4")

        # Collect all NIST controls
        all_controls = set()
        for r in triage_results:
            all_controls.update(r["triage"].get("nist_controls", []))

        # Collect scanners
        scanners = set(r["evidence"]["scanner"] for r in triage_results)

        batch_summary = {
            "total_findings": len(triage_results),
            "by_priority": {"P1": p1_count, "P2": p2_count, "P3": p3_count, "P4": p4_count},
            "scanners": sorted(scanners),
            "nist_controls_affected": sorted(all_controls),
            "findings": triage_results,
        }

        if self.llm and self.llm.is_available():
            batch_summary["narrative"] = self._llm_batch_summary(batch_summary, tier)
        else:
            batch_summary["narrative"] = self._template_batch_summary(batch_summary, tier)

        return batch_summary

    def _llm_summary(self, triage_result: Dict, tier: str) -> str:
        """Generate LLM-enhanced summary for a single finding."""
        template = self.templates.get(tier, {})
        sections = template.get("sections", [])
        section_prompts = "\n".join(
            f"- {s['name']}: {s['prompt']}" for s in sections
        )

        prompt = (
            f"Generate a {tier} risk summary for this security finding.\n\n"
            f"Finding: {triage_result['evidence']['finding_type']}\n"
            f"Scanner: {triage_result['evidence']['scanner']}\n"
            f"Priority: {triage_result['triage']['priority']}\n"
            f"Severity Context: {triage_result['triage']['severity_context']}\n"
            f"Blast Radius: {triage_result['triage']['blast_radius']}\n"
            f"NIST Controls: {triage_result['triage']['nist_controls']}\n"
            f"Immediate Action: {triage_result['triage']['immediate_action']}\n\n"
            f"Required sections:\n{section_prompts}\n\n"
            f"Write as a single coherent paragraph. No bullet points. "
            f"Business impact language for executives."
        )
        return self.llm.generate(prompt)

    def _template_summary(self, triage_result: Dict, tier: str) -> str:
        """Template-based summary fallback when no LLM is available."""
        t = triage_result["triage"]
        e = triage_result["evidence"]
        controls = ", ".join(t["nist_controls"][:3])

        if tier == "executive":
            return (
                f"{e['finding_type']} detected by {e['scanner']}. "
                f"Priority: {t['priority']}. {t['severity_context']}. "
                f"{t['blast_radius']}. "
                f"Immediate action: {t['immediate_action']} "
                f"Maps to NIST controls: {controls}."
            )
        elif tier == "technical":
            return (
                f"Scanner: {e['scanner']} | Finding: {e['finding_type']} | "
                f"Priority: {t['priority']} | Severity: {t['severity_context']}\n"
                f"Blast Radius: {t['blast_radius']}\n"
                f"Action: {t['immediate_action']}\n"
                f"Remediation: {t['remediation']}\n"
                f"NIST: {controls}"
            )
        else:  # compliance
            return (
                f"Finding: {e['finding_type']}\n"
                f"NIST 800-53 Controls: {controls}\n"
                f"Gap: {t['severity_context']}\n"
                f"Remediation: {t['remediation']}\n"
                f"Evidence: {e['scanner']} scan at {e.get('timestamp', 'N/A')}"
            )

    def _llm_batch_summary(self, batch: Dict, tier: str) -> str:
        """Generate LLM-enhanced batch summary."""
        prompt = (
            f"Generate a {tier} risk summary for a batch of {batch['total_findings']} security findings.\n\n"
            f"Priority breakdown: {batch['by_priority']}\n"
            f"Scanners: {batch['scanners']}\n"
            f"NIST controls affected: {batch['nist_controls_affected']}\n\n"
            f"Top P1 findings:\n"
        )
        for f in batch["findings"][:5]:
            if f["triage"]["priority"] == "P1":
                prompt += f"- {f['evidence']['finding_type']} ({f['triage']['severity_context']})\n"

        prompt += (
            f"\nWrite a concise executive summary (3-5 sentences). "
            f"Lead with the most critical risk. Include remediation timeline recommendation."
        )
        return self.llm.generate(prompt)

    def _template_batch_summary(self, batch: Dict, tier: str) -> str:
        """Template-based batch summary fallback."""
        bp = batch["by_priority"]
        controls = ", ".join(batch["nist_controls_affected"][:5])
        return (
            f"Scan cycle produced {batch['total_findings']} findings across "
            f"{', '.join(batch['scanners'])}. "
            f"Priority breakdown: {bp['P1']} critical, {bp['P2']} high, "
            f"{bp['P3']} medium, {bp['P4']} low. "
            f"NIST controls affected: {controls}. "
            f"{'Immediate action required for P1 findings.' if bp['P1'] > 0 else 'No critical findings requiring immediate action.'}"
        )
