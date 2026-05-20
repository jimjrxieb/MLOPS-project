"""
Training Scenario Templates

Pre-defined templates for generating training examples from operational data.
"""

from typing import Dict, List, Optional
from .models import ScenarioTemplate, Domain, TaskType, SkillLevel


# ==================== SCAN ANALYSIS TEMPLATES ====================

TRIVY_SCAN_TEMPLATE = ScenarioTemplate(
    name="trivy-vulnerability-analysis",
    description="Analyze Trivy scan results and triage vulnerabilities",
    domain=Domain.DEPENDENCIES,
    task_type=TaskType.SCAN_ANALYSIS,
    skill_level=SkillLevel.D_RANK,
    instruction_template="Analyze this {scanner} vulnerability scan result and recommend the appropriate action.",
    input_template="""Scanner: {scanner}
Severity: {severity}
Package: {package}
Vulnerability: {vulnerability_id}
Current Version: {current_version}
Fixed Version: {fixed_version}

Description: {description}""",
    output_template="""**Analysis:**
This is a {severity} severity vulnerability ({vulnerability_id}) in the {package} package. The current version ({current_version}) is affected, and the issue is fixed in version {fixed_version}.

**Recommended Action:**
{action}

**Fix Command:**
```bash
{fix_command}
```

**Rank:** {rank} - {rank_justification}""",
    required_fields=[
        "scanner", "severity", "package", "vulnerability_id",
        "current_version", "fixed_version", "description",
        "action", "fix_command", "rank", "rank_justification"
    ]
)


GITLEAKS_SECRET_TEMPLATE = ScenarioTemplate(
    name="gitleaks-secret-detection",
    description="Detect and remediate hardcoded secrets",
    domain=Domain.SECRETS,
    task_type=TaskType.FIX_EXECUTION,
    skill_level=SkillLevel.E_RANK,
    instruction_template="A {scanner} scan detected a hardcoded secret. Remediate this security issue.",
    input_template="""Scanner: {scanner}
Secret Type: {secret_type}
File: {file_path}
Line: {line_number}

Detected Pattern: {pattern}""",
    output_template="""**Remediation Steps:**

1. **Remove the hardcoded secret:**
   - Delete the secret from `{file_path}:{line_number}`
   - Replace with environment variable: `{env_var_name}`

2. **Update .gitignore:**
   - Add pattern to prevent future commits: `{gitignore_pattern}`

3. **Set environment variable:**
   ```bash
   export {env_var_name}="your-secret-value"
   ```

4. **Update code to use environment variable:**
   ```python
   import os
   {code_example}
   ```

**Rank:** E - Fully automated fix (95-100% confidence)""",
    required_fields=[
        "scanner", "secret_type", "file_path", "line_number",
        "pattern", "env_var_name", "gitignore_pattern", "code_example"
    ]
)


KUBESCAPE_POLICY_TEMPLATE = ScenarioTemplate(
    name="kubescape-policy-violation",
    description="Fix Kubernetes security policy violations",
    domain=Domain.KUBERNETES,
    task_type=TaskType.FIX_EXECUTION,
    skill_level=SkillLevel.C_RANK,
    instruction_template="A {scanner} scan found a Kubernetes security policy violation. Fix this issue.",
    input_template="""Scanner: {scanner}
Control: {control_id} - {control_name}
Severity: {severity}
Resource: {resource_type}/{resource_name}
Namespace: {namespace}

Failed Check: {failed_check}
Current Configuration: {current_config}""",
    output_template="""**Issue:**
The {resource_type} `{resource_name}` in namespace `{namespace}` violates CIS Kubernetes Benchmark control {control_id}.

**Fix:**
{fix_explanation}

**Updated Manifest:**
```yaml
{fixed_manifest}
```

**Approval Required:** Yes (C-rank - network/security policy change)

**Risk Level:** {risk_level}
**Confidence:** {confidence}%

**Validation:**
After applying, verify with:
```bash
kubescape scan control {control_id} --namespace {namespace}
```""",
    required_fields=[
        "scanner", "control_id", "control_name", "severity",
        "resource_type", "resource_name", "namespace",
        "failed_check", "current_config", "fix_explanation",
        "fixed_manifest", "risk_level", "confidence"
    ]
)


# ==================== ESCALATION DECISION TEMPLATES ====================

ESCALATION_B_RANK_TEMPLATE = ScenarioTemplate(
    name="escalation-b-rank-decision",
    description="Decide whether to escalate a B-rank finding",
    domain=Domain.GENERAL,
    task_type=TaskType.ESCALATION_DECISION,
    skill_level=SkillLevel.B_RANK,
    instruction_template="Analyze this {rank}-rank security finding and determine if escalation is needed.",
    input_template="""Finding: {finding_title}
Severity: {severity}
Scanner: {scanner}
Rank: {rank}
Automation Confidence: {confidence}%

Description:
{description}

Attempted Fixes: {fix_attempts}
Fix Results: {fix_results}""",
    output_template="""**Analysis:**
{analysis}

**Escalation Decision:** {decision}

**Reasoning:**
{reasoning}

**Recommended Next Steps:**
{next_steps}

**Assign To:** {assign_to}
**Priority:** {priority}""",
    required_fields=[
        "finding_title", "severity", "scanner", "rank",
        "confidence", "description", "fix_attempts", "fix_results",
        "analysis", "decision", "reasoning", "next_steps",
        "assign_to", "priority"
    ]
)


# ==================== FIX EXECUTION TEMPLATES ====================

SQL_INJECTION_FIX_TEMPLATE = ScenarioTemplate(
    name="sql-injection-fix",
    description="Fix SQL injection vulnerability",
    domain=Domain.SAST,
    task_type=TaskType.FIX_EXECUTION,
    skill_level=SkillLevel.D_RANK,
    instruction_template="Fix this SQL injection vulnerability detected by {scanner}.",
    input_template="""Scanner: {scanner}
CWE: CWE-89 (SQL Injection)
File: {file_path}
Line: {line_number}

Vulnerable Code:
```{language}
{vulnerable_code}
```

User Input Source: {input_source}""",
    output_template="""**Vulnerability:**
SQL injection via unsanitized user input from `{input_source}`.

**Fix:**
Use parameterized queries instead of string concatenation:

**Secure Code:**
```{language}
{secure_code}
```

**Explanation:**
{explanation}

**Rank:** D - Automated fix with pattern matching (70-90% confidence)

**Testing:**
```{language}
{test_code}
```""",
    required_fields=[
        "scanner", "file_path", "line_number", "language",
        "vulnerable_code", "input_source", "secure_code",
        "explanation", "test_code"
    ]
)


XSS_FIX_TEMPLATE = ScenarioTemplate(
    name="xss-vulnerability-fix",
    description="Fix Cross-Site Scripting (XSS) vulnerability",
    domain=Domain.SAST,
    task_type=TaskType.FIX_EXECUTION,
    skill_level=SkillLevel.D_RANK,
    instruction_template="Fix this XSS vulnerability detected by {scanner}.",
    input_template="""Scanner: {scanner}
CWE: CWE-79 (Cross-Site Scripting)
File: {file_path}
Line: {line_number}

Vulnerable Code:
```{language}
{vulnerable_code}
```

Sink: {sink}
Source: {source}""",
    output_template="""**Vulnerability:**
Reflected XSS via unescaped user input ({source}) rendered in {sink}.

**Fix:**
Sanitize output before rendering:

**Secure Code:**
```{language}
{secure_code}
```

**Explanation:**
{explanation}

**Rank:** D - Automated fix (70-90% confidence)

**Additional Recommendations:**
- {recommendation_1}
- {recommendation_2}""",
    required_fields=[
        "scanner", "file_path", "line_number", "language",
        "vulnerable_code", "sink", "source", "secure_code",
        "explanation", "recommendation_1", "recommendation_2"
    ]
)


# ==================== COMPLIANCE TEMPLATES ====================

CIS_BENCHMARK_TEMPLATE = ScenarioTemplate(
    name="cis-benchmark-remediation",
    description="Remediate CIS benchmark violations",
    domain=Domain.COMPLIANCE,
    task_type=TaskType.FIX_EXECUTION,
    skill_level=SkillLevel.C_RANK,
    instruction_template="Remediate this CIS benchmark violation detected by {scanner}.",
    input_template="""Scanner: {scanner}
Benchmark: {benchmark}
Control: {control_id} - {control_name}
Severity: {severity}
Status: FAIL

Current State:
{current_state}

Recommendation:
{recommendation}""",
    output_template="""**CIS Control:** {control_id} - {control_name}

**Current State:**
{current_state}

**Required State:**
{required_state}

**Remediation:**
{remediation_steps}

**Implementation:**
```bash
{implementation_commands}
```

**Verification:**
```bash
{verification_commands}
```

**Rank:** C - Requires approval (40-70% automation)
**Risk:** {risk_level}""",
    required_fields=[
        "scanner", "benchmark", "control_id", "control_name",
        "severity", "current_state", "recommendation",
        "required_state", "remediation_steps",
        "implementation_commands", "verification_commands",
        "risk_level"
    ]
)


# ==================== REPORT GENERATION TEMPLATES ====================

EXECUTIVE_REPORT_TEMPLATE = ScenarioTemplate(
    name="executive-security-report",
    description="Generate executive security report",
    domain=Domain.GENERAL,
    task_type=TaskType.REPORT_GENERATION,
    skill_level=SkillLevel.C_RANK,
    instruction_template="Generate an executive summary report for {instance}/{slot}.",
    input_template="""Instance: {instance}
Slot: {slot}
Scan Date: {scan_date}

Total Findings: {total_findings}
Critical: {critical_count}
High: {high_count}
Medium: {medium_count}
Low: {low_count}

Findings by Scanner:
{findings_by_scanner}

Recent Fixes: {recent_fixes}
Escalations: {escalations_count}""",
    output_template="""# Security Assessment Report

**Instance:** {instance}
**Slot:** {slot}
**Assessment Date:** {scan_date}

## Executive Summary

{executive_summary}

## Security Posture

- **Risk Score:** {risk_score}/100
- **Total Findings:** {total_findings}
- **Critical Issues:** {critical_count} ({critical_trend})
- **High-Priority Issues:** {high_count} ({high_trend})

## Key Findings

{key_findings}

## Remediation Progress

{remediation_progress}

## Recommendations

{recommendations}

**Rank:** C - Requires domain expertise (40-70% automation)""",
    required_fields=[
        "instance", "slot", "scan_date", "total_findings",
        "critical_count", "high_count", "medium_count", "low_count",
        "findings_by_scanner", "recent_fixes", "escalations_count",
        "executive_summary", "risk_score", "critical_trend",
        "high_trend", "key_findings", "remediation_progress",
        "recommendations"
    ]
)


# ==================== CKS RUNTIME & CCSP CLOUD TEMPLATES ====================

FALCO_RUNTIME_TEMPLATE = ScenarioTemplate(
    name="falco-runtime-violation",
    description="Analyze and respond to Falco runtime security alerts (CKS)",
    domain=Domain.KUBERNETES,
    task_type=TaskType.INCIDENT_RESPONSE,
    skill_level=SkillLevel.C_RANK,
    instruction_template="A Falco runtime alert was triggered. Analyze the event and execute the response playbook.",
    input_template="""Alert: {alert_name}
Priority: {priority}
Namespace: {namespace}
Pod: {pod_name}
Container: {container_id}

Event Details:
{event_output}

Process Tree:
{process_tree}

User: {user}
Command: {command}""",
    output_template="""**Incident Analysis:**
{analysis}

**Threat Level:** {threat_level}
**CKS Control:** {cks_control}

**Response Actions:**
1. **Isolation:** {isolation_step}
2. **Investigation:** {investigation_step}
3. **Remediation:** {remediation_step}

**Automated Response Executed:**
```bash
{response_command}
```

**Rank:** C - Automated response with supervisor approval required (40-70% confidence)""",
    required_fields=[
        "alert_name", "priority", "namespace", "pod_name",
        "container_id", "event_output", "process_tree", "user",
        "command", "analysis", "threat_level", "cks_control",
        "isolation_step", "investigation_step", "remediation_step",
        "response_command"
    ]
)


TERRAFORM_DRIFT_TEMPLATE = ScenarioTemplate(
    name="terraform-drift-detection",
    description="Detect and remediate infrastructure drift (CCSP)",
    domain=Domain.IAC,
    task_type=TaskType.SCAN_ANALYSIS,
    skill_level=SkillLevel.C_RANK,
    instruction_template="Terraform drift detected in {cloud_provider}. Align state with security-hardened baseline.",
    input_template="""Cloud Provider: {cloud_provider}
Resource: {resource_id}
Region: {region}

Drift Details:
Attribute: {attribute}
Expected (IaC): {expected_value}
Actual (Runtime): {actual_value}

Security Impact: {impact_description}""",
    output_template="""**Drift Analysis:**
The runtime configuration for {resource_id} has drifted from the approved IaC baseline.
**Impact:** {impact_description}

**CCSP Compliance:** {ccsp_domain}

**Remediation Plan:**
{remediation_plan}

**Fix (Terraform):**
```hcl
{hcl_fix}
```

**Fix (CLI Reversion):**
```bash
{cli_fix}
```

**Rank:** C - Requires drift analysis and IaC update (40-70% automation)""",
    required_fields=[
        "cloud_provider", "resource_id", "region", "attribute",
        "expected_value", "actual_value", "impact_description",
        "ccsp_domain", "remediation_plan", "hcl_fix", "cli_fix"
    ]
)


# ==================== TEMPLATE REGISTRY ====================

TEMPLATE_REGISTRY = {
    # Scan Analysis
    "trivy-scan": TRIVY_SCAN_TEMPLATE,
    "gitleaks-secret": GITLEAKS_SECRET_TEMPLATE,
    "kubescape-policy": KUBESCAPE_POLICY_TEMPLATE,

    # Escalation
    "escalation-b-rank": ESCALATION_B_RANK_TEMPLATE,

    # Fix Execution
    "sql-injection": SQL_INJECTION_FIX_TEMPLATE,
    "xss-fix": XSS_FIX_TEMPLATE,

    # Compliance
    "cis-benchmark": CIS_BENCHMARK_TEMPLATE,

    # Reports
    "executive-report": EXECUTIVE_REPORT_TEMPLATE,

    # CKS & CCSP (Iron Legion)
    "falco-runtime": FALCO_RUNTIME_TEMPLATE,
    "terraform-drift": TERRAFORM_DRIFT_TEMPLATE,
}


def get_template(name: str) -> ScenarioTemplate:
    """
    Get template by name.

    Args:
        name: Template name

    Returns:
        ScenarioTemplate

    Raises:
        KeyError: If template not found

    Example:
        >>> template = get_template("trivy-scan")
        >>> example = template.generate_example({...})
    """
    if name not in TEMPLATE_REGISTRY:
        raise KeyError(f"Template '{name}' not found. Available: {list(TEMPLATE_REGISTRY.keys())}")
    return TEMPLATE_REGISTRY[name]


def list_templates() -> List[str]:
    """List all available template names."""
    return list(TEMPLATE_REGISTRY.keys())


def get_templates_by_domain(domain: Domain) -> List[ScenarioTemplate]:
    """Get all templates for a specific domain."""
    return [t for t in TEMPLATE_REGISTRY.values() if t.domain == domain]


def get_templates_by_skill_level(skill_level: SkillLevel) -> List[ScenarioTemplate]:
    """Get all templates for a specific skill level."""
    return [t for t in TEMPLATE_REGISTRY.values() if t.skill_level == skill_level]


__all__ = [
    "TEMPLATE_REGISTRY",
    "get_template",
    "list_templates",
    "get_templates_by_domain",
    "get_templates_by_skill_level",
]
