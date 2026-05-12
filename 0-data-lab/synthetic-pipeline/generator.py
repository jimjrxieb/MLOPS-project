"""
Training Data Generator

Generates training examples from operational logs, scan results,
and security remediation workflows.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import TrainingExample, TrainingBatch, GenerationConfig, SkillLevel
from .templates import get_template, list_templates, TEMPLATE_REGISTRY
from .quality_validator import QualityValidator


class TrainingGenerator:
    """
    Generate training examples from operational data.

    The generator:
    - Reads operational logs (scans, fixes, escalations)
    - Applies templates to generate training examples
    - Validates quality
    - Deduplicates
    - Outputs to JSONL format

    Example:
        >>> generator = TrainingGenerator()
        >>> batch = generator.generate_from_slot("02-instance", "slot-2")
        >>> batch.save("/path/to/training.jsonl")
    """

    def __init__(
        self,
        config: Optional[GenerationConfig] = None,
        base_path: Optional[Path] = None
    ):
        """
        Initialize generator.

        Args:
            config: Generation configuration
            base_path: Base path to GP-PROJECTS
        """
        self.config = config or GenerationConfig()
        self.validator = QualityValidator(
            min_instruction_length=self.config.min_instruction_length,
            max_instruction_length=self.config.max_instruction_length,
            min_output_length=self.config.min_output_length,
            max_output_length=self.config.max_output_length
        )

        if base_path is None:
            base_path = Path("/home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS")
        self.base_path = Path(base_path)

        # Logs path
        self.logs_path = Path("/home/jimmie/linkops-industries/GP-copilot/GP-BEDROCK-AGENTS")

    def generate_from_slot(
        self,
        instance: str,
        slot: str,
        batch_id: Optional[str] = None
    ) -> TrainingBatch:
        """
        Generate training examples from a slot's operational data.

        Args:
            instance: Instance ID (e.g., "02-instance")
            slot: Slot ID (e.g., "slot-2")
            batch_id: Optional batch ID

        Returns:
            TrainingBatch with generated examples

        Example:
            >>> batch = generator.generate_from_slot("02-instance", "slot-2")
            >>> print(f"Generated {len(batch.examples)} examples")
        """
        if batch_id is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            batch_id = f"training_{instance}_{slot}_{timestamp}"

        batch = TrainingBatch(batch_id=batch_id)

        # Generate from different sources
        batch.examples.extend(self._generate_from_jsa_inbox(instance, slot))
        batch.examples.extend(self._generate_from_scans(instance, slot))
        batch.examples.extend(self._generate_from_fixes(instance, slot))
        batch.examples.extend(self._generate_from_escalations(instance, slot))
        batch.examples.extend(self._generate_from_workflow(instance, slot))

        # Filter by quality
        if self.config.min_quality_score > 0:
            batch.examples = self._filter_by_quality(batch.examples)

        # Deduplicate
        if self.config.deduplicate:
            batch.examples = self._deduplicate(batch.examples)

        # Shuffle
        if self.config.shuffle:
            import random
            random.shuffle(batch.examples)

        # Limit batch size
        if len(batch.examples) > self.config.max_examples_per_batch:
            batch.examples = batch.examples[:self.config.max_examples_per_batch]

        return batch

    def _generate_from_jsa_inbox(self, instance: str, slot: str) -> List[TrainingExample]:
        """
        Generate training examples from real JSA finding inbox.

        Reads JSON findings from GP-PROJECTS/{instance}/{slot}/jsa/inbox/
        and converts them into training examples that teach Katie how to
        triage, route, and remediate security findings.
        """
        examples = []
        inbox_path = self.base_path / instance / slot / "jsa" / "inbox"

        if not inbox_path.exists():
            return examples

        for finding_file in sorted(inbox_path.glob("*.json"))[:50]:
            try:
                with open(finding_file) as f:
                    finding = json.load(f)

                scanner = finding.get("scanner", "unknown")
                severity = finding.get("severity", "MEDIUM")
                rank = finding.get("rank", "D")
                title = finding.get("title", "Unknown finding")
                rule_id = finding.get("rule_id", "")
                context = finding.get("context", {})
                description = context.get("description", "")
                remediation = context.get("remediation", "")
                file_path = finding.get("file_path", "")

                if not title or not description:
                    continue

                # Generate triage example: given finding → route to correct handler
                triage_instruction = (
                    f"A {severity} severity finding was detected by {scanner}. "
                    f"Triage this finding and determine the appropriate response."
                )
                triage_input = (
                    f"Scanner: {scanner}\n"
                    f"Rule: {rule_id}\n"
                    f"Severity: {severity}\n"
                    f"Title: {title}\n"
                    f"Description: {description}\n"
                    f"File: {file_path}"
                )

                # Build response based on rank
                if rank in ("E", "D"):
                    route = "runbook"
                    response = (
                        f"**Rank: {rank}** — Route to automated runbook.\n\n"
                        f"This is a {rank}-rank finding (pattern match, automated fix).\n\n"
                        f"**Remediation:** {remediation}\n\n"
                        f"**Action:** Apply fix automatically via JSA agent. No human approval needed."
                    )
                elif rank == "C":
                    route = "jade"
                    response = (
                        f"**Rank: C** — Forward to JADE for approval.\n\n"
                        f"This finding requires C-rank review. The fix is known but "
                        f"needs approval before applying.\n\n"
                        f"**Remediation:** {remediation}\n\n"
                        f"**Action:** JADE reviews context, similar past findings, "
                        f"and risk assessment before approving."
                    )
                else:
                    route = "human_dashboard"
                    response = (
                        f"**Rank: {rank}** — Escalate to human dashboard.\n\n"
                        f"This finding exceeds automated authority. "
                        f"Requires human security review.\n\n"
                        f"**Remediation:** {remediation}\n\n"
                        f"**Action:** Queue for human review with full context."
                    )

                example = TrainingExample(
                    instruction=triage_instruction,
                    input=triage_input,
                    output=response,
                    metadata={
                        "domain": self._infer_domain(scanner, title),
                        "task_type": "vulnerability-triage",
                        "skill_level": rank,
                        "source": f"jsa-inbox/{finding_file.name}",
                        "scanner": scanner,
                        "severity": severity,
                    }
                )
                examples.append(example)

            except (json.JSONDecodeError, KeyError, Exception):
                continue

        return examples

    def _infer_domain(self, scanner: str, title: str) -> str:
        """Infer training domain from scanner and finding title."""
        title_lower = title.lower()
        if scanner in ("trivy", "grype", "snyk"):
            if "image" in title_lower or "container" in title_lower:
                return "kubernetes"
            return "dependencies"
        elif scanner in ("gitleaks",):
            return "secrets"
        elif scanner in ("kubescape", "polaris", "kube-bench"):
            return "kubernetes"
        elif scanner in ("bandit", "semgrep"):
            return "sast"
        elif scanner in ("checkov", "tfsec"):
            return "iac"
        return "general"

    def _generate_from_scans(self, instance: str, slot: str) -> List[TrainingExample]:
        """Generate examples from scan logs."""
        examples = []
        scans_path = self.logs_path / instance / "scans"

        if not scans_path.exists():
            return examples

        # Process scan logs
        for scan_file in sorted(scans_path.glob(f"*{slot}*.json")):
            try:
                with open(scan_file) as f:
                    scan_data = json.load(f)

                # Generate examples based on scanner type
                scanner = scan_data.get("scanner", "unknown")

                if scanner == "trivy":
                    examples.extend(self._generate_trivy_examples(scan_data))
                elif scanner == "gitleaks":
                    examples.extend(self._generate_gitleaks_examples(scan_data))
                elif scanner == "kubescape":
                    examples.extend(self._generate_kubescape_examples(scan_data))

            except (json.JSONDecodeError, KeyError, Exception):
                continue

        return examples

    def _generate_from_fixes(self, instance: str, slot: str) -> List[TrainingExample]:
        """Generate examples from fix logs."""
        examples = []
        fixes_path = self.logs_path / instance / "fixes"

        if not fixes_path.exists():
            return examples

        for fix_file in sorted(fixes_path.glob(f"*{slot}*.json")):
            try:
                with open(fix_file) as f:
                    fix_data = json.load(f)

                # Generate examples based on fix type
                fix_type = fix_data.get("fix_type", "unknown")

                if fix_type == "dependency":
                    examples.extend(self._generate_dependency_fix_examples(fix_data))
                elif fix_type == "secrets":
                    examples.extend(self._generate_secret_fix_examples(fix_data))
                elif fix_type == "sast":
                    examples.extend(self._generate_sast_fix_examples(fix_data))

            except (json.JSONDecodeError, KeyError, Exception):
                continue

        return examples

    def _generate_from_escalations(self, instance: str, slot: str) -> List[TrainingExample]:
        """Generate examples from escalation logs."""
        examples = []
        slot_path = self.base_path / instance / slot
        escalations_path = slot_path / "escalations" / "pending"

        if not escalations_path.exists():
            return examples

        for esc_file in sorted(escalations_path.glob("*.json")):
            try:
                with open(esc_file) as f:
                    esc_data = json.load(f)

                # Generate escalation decision examples
                template = get_template("escalation-b-rank")
                finding = esc_data.get("finding", {})

                data = {
                    "finding_title": finding.get("title", "Unknown"),
                    "severity": finding.get("severity", "MEDIUM"),
                    "scanner": finding.get("scanner", "unknown"),
                    "rank": finding.get("rank", "B"),
                    "confidence": esc_data.get("confidence", 0),
                    "description": finding.get("description", ""),
                    "fix_attempts": esc_data.get("fix_attempts", 0),
                    "fix_results": esc_data.get("error_messages", []),
                    "analysis": esc_data.get("context", {}).get("analysis", "Complex security policy requiring manual review"),
                    "decision": "ESCALATE",
                    "reasoning": esc_data.get("reason", ""),
                    "next_steps": "Manual security review required",
                    "assign_to": "Security Team",
                    "priority": "HIGH" if finding.get("severity") in ["CRITICAL", "HIGH"] else "MEDIUM"
                }

                example = template.generate_example(data)
                examples.append(example)

            except (json.JSONDecodeError, KeyError, Exception):
                continue

        return examples

    def _generate_from_workflow(self, instance: str, slot: str) -> List[TrainingExample]:
        """Generate examples from workflow state transitions."""
        examples = []
        slot_path = self.base_path / instance / slot
        workflow_path = slot_path / "workflow"

        if not workflow_path.exists():
            return examples

        # Process findings that transitioned to resolved state
        resolved_path = workflow_path / "resolved"
        if resolved_path.exists():
            for finding_file in sorted(resolved_path.glob("*.json"))[:20]:  # Limit to 20
                try:
                    with open(finding_file) as f:
                        finding_data = json.load(f)

                    # Generate fix execution example
                    scanner = finding_data.get("scanner", "unknown")
                    severity = finding_data.get("severity", "MEDIUM")
                    rank = finding_data.get("rank", "D")

                    # Only generate for D-rank (automated fixes)
                    if rank == "D":
                        # Use appropriate template based on scanner
                        # This is a simplified example
                        example = TrainingExample(
                            instruction=f"Fix this {severity} severity issue detected by {scanner}.",
                            input=json.dumps(finding_data, indent=2),
                            output=f"Successfully resolved {severity} finding using automated fix pattern.",
                            metadata={
                                "domain": "general",
                                "task_type": "fix-execution",
                                "skill_level": SkillLevel.D_RANK.value,
                                "source": "workflow-resolved"
                            }
                        )
                        examples.append(example)

                except (json.JSONDecodeError, KeyError, Exception):
                    continue

        return examples

    def _generate_trivy_examples(self, scan_data: Dict[str, Any]) -> List[TrainingExample]:
        """Generate examples from Trivy scan results."""
        examples = []
        template = get_template("trivy-scan")

        vulnerabilities = scan_data.get("vulnerabilities", [])
        for vuln in vulnerabilities[:10]:  # Limit to 10 per scan
            try:
                data = {
                    "scanner": "trivy",
                    "severity": vuln.get("severity", "MEDIUM"),
                    "package": vuln.get("package", "unknown"),
                    "vulnerability_id": vuln.get("id", "CVE-XXXX-XXXX"),
                    "current_version": vuln.get("installed_version", "0.0.0"),
                    "fixed_version": vuln.get("fixed_version", "latest"),
                    "description": vuln.get("description", "No description"),
                    "action": "UPGRADE" if vuln.get("fixed_version") else "REVIEW",
                    "fix_command": f"npm update {vuln.get('package')} # or appropriate package manager",
                    "rank": "D",
                    "rank_justification": "Automated dependency upgrade"
                }

                example = template.generate_example(data)
                examples.append(example)
            except (KeyError, ValueError):
                continue

        return examples

    def _generate_gitleaks_examples(self, scan_data: Dict[str, Any]) -> List[TrainingExample]:
        """Generate examples from Gitleaks scan results."""
        examples = []
        template = get_template("gitleaks-secret")

        findings = scan_data.get("findings", [])
        for finding in findings[:5]:  # Limit to 5 per scan
            try:
                secret_type = finding.get("rule", "generic-secret")
                file_path = finding.get("file", "unknown")

                data = {
                    "scanner": "gitleaks",
                    "secret_type": secret_type,
                    "file_path": file_path,
                    "line_number": finding.get("line", 1),
                    "pattern": finding.get("match", "***"),
                    "env_var_name": f"{secret_type.upper().replace('-', '_')}_KEY",
                    "gitignore_pattern": "*.env\n.env*\nsecrets/",
                    "code_example": f"secret = os.getenv('{secret_type.upper().replace('-', '_')}_KEY')"
                }

                example = template.generate_example(data)
                examples.append(example)
            except (KeyError, ValueError):
                continue

        return examples

    def _generate_kubescape_examples(self, scan_data: Dict[str, Any]) -> List[TrainingExample]:
        """Generate examples from Kubescape scan results."""
        examples = []
        template = get_template("kubescape-policy")

        controls = scan_data.get("controls", [])
        for control in controls[:5]:  # Limit to 5 per scan
            if control.get("status") == "failed":
                try:
                    data = {
                        "scanner": "kubescape",
                        "control_id": control.get("id", "C-0000"),
                        "control_name": control.get("name", "Unknown control"),
                        "severity": control.get("severity", "MEDIUM"),
                        "resource_type": "Deployment",
                        "resource_name": "example-app",
                        "namespace": "default",
                        "failed_check": control.get("description", ""),
                        "current_config": "# Current insecure configuration",
                        "fix_explanation": control.get("remediation", "Apply security policy"),
                        "fixed_manifest": "# Fixed manifest with security controls",
                        "risk_level": "MEDIUM",
                        "confidence": "75"
                    }

                    example = template.generate_example(data)
                    examples.append(example)
                except (KeyError, ValueError):
                    continue

        return examples

    def _generate_dependency_fix_examples(self, fix_data: Dict[str, Any]) -> List[TrainingExample]:
        """Generate examples from dependency fix logs."""
        # Implementation similar to other generators
        return []

    def _generate_secret_fix_examples(self, fix_data: Dict[str, Any]) -> List[TrainingExample]:
        """Generate examples from secret fix logs."""
        # Implementation similar to other generators
        return []

    def _generate_sast_fix_examples(self, fix_data: Dict[str, Any]) -> List[TrainingExample]:
        """Generate examples from SAST fix logs."""
        # Implementation similar to other generators
        return []

    def _filter_by_quality(self, examples: List[TrainingExample]) -> List[TrainingExample]:
        """Filter examples by quality score."""
        filtered = []

        for example in examples:
            metrics = self.validator.validate(example)
            if metrics.overall_score >= self.config.min_quality_score:
                filtered.append(example)

        return filtered

    def _deduplicate(self, examples: List[TrainingExample]) -> List[TrainingExample]:
        """Remove duplicate examples based on instruction+input hash."""
        seen = set()
        deduplicated = []

        for example in examples:
            # Create hash from instruction + input
            content_hash = hash(example.instruction + example.input)
            if content_hash not in seen:
                seen.add(content_hash)
                deduplicated.append(example)

        return deduplicated

    def save_batch(self, batch: TrainingBatch, output_path: Path):
        """
        Save training batch to JSONL file.

        Args:
            batch: Training batch
            output_path: Output file path

        Example:
            >>> generator.save_batch(batch, Path("training.jsonl"))
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for example in batch.examples:
                f.write(json.dumps(example.to_dict()) + "\n")

        # Save batch stats
        stats_path = output_path.with_suffix(".stats.json")
        with open(stats_path, 'w') as f:
            json.dump(batch.get_stats(), f, indent=2)


__all__ = [
    "TrainingGenerator"
]
