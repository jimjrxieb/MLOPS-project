"""
Advanced Security Reasoning Engine
GPU-Accelerated AI for Professional Security Consulting
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SecurityFinding:
    """Structured security finding"""
    id: str  # Unique identifier for the finding
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # e.g., "Hardcoded Secrets", "Network Security"
    file_path: str
    line_number: Optional[int]
    description: str
    impact: str
    recommendation: str
    cve_refs: List[str] = None
    compliance_frameworks: List[str] = None
    ai_confidence: float = 0.0

@dataclass
class SecurityAssessment:
    """Complete security assessment results"""
    project_name: str
    files_analyzed: int
    findings: List[SecurityFinding]
    risk_level: str
    ai_summary: str
    scan_timestamp: datetime = None
    compliance_score: float = 0.0
    remediation_priority: List[str] = None

class SecurityReasoningEngine:
    """Advanced AI-powered security analysis"""

    def __init__(self):
        self.knowledge_base = self._load_security_knowledge()

        # Try to initialize real AI model
        try:
            from model_manager import model_manager
            self.model_manager = model_manager
            print("🤖 Initializing real AI model...")
        except ImportError:
            print("⚠️  Falling back to pattern-based analysis")
            self.model_manager = None

    def _load_security_knowledge(self) -> Dict[str, Any]:
        """Load security frameworks and patterns"""
        return {
            "cks_patterns": {
                "pod_security_standards": [
                    "Privileged containers detected",
                    "Missing security contexts",
                    "Unsafe capability assignments"
                ],
                "network_policies": [
                    "Default allow-all networking",
                    "Missing ingress/egress rules",
                    "Overpermissive network access"
                ],
                "rbac_issues": [
                    "Cluster-admin bindings",
                    "Wildcard permissions",
                    "Service account privilege escalation"
                ]
            },
            "terraform_patterns": {
                "aws_security": [
                    "Public S3 buckets",
                    "Overpermissive security groups",
                    "Missing encryption configurations",
                    "IAM wildcard permissions"
                ],
                "credential_leaks": [
                    "Hardcoded access keys",
                    "Plain text passwords",
                    "Exposed API tokens"
                ]
            },
            "compliance_frameworks": {
                "CIS": "Center for Internet Security benchmarks",
                "SOC2": "Service Organization Control 2",
                "NIST": "National Institute of Standards",
                "PCI-DSS": "Payment Card Industry Data Security"
            }
        }

    async def analyze_terraform(self, terraform_content: str, file_path: str) -> List[SecurityFinding]:
        """Analyze Terraform configuration for security issues"""
        findings = []

        # For now, sophisticated pattern matching
        # TODO: Replace with actual LLM reasoning

        lines = terraform_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower().strip()

            # Detect hardcoded secrets
            if any(pattern in line_lower for pattern in ['password', 'secret', 'key', 'token']):
                if '=' in line and '"' in line:
                    # Potential hardcoded credential
                    finding = SecurityFinding(
                        severity="HIGH",
                        category="Hardcoded Credentials",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Potential hardcoded credential detected: {line.strip()}",
                        impact="Credentials in source code can be exposed in version control",
                        recommendation="Use variable references or secret management systems",
                        compliance_frameworks=["SOC2", "PCI-DSS"],
                        ai_confidence=0.85
                    )
                    findings.append(finding)

            # Detect public access
            if "0.0.0.0/0" in line:
                finding = SecurityFinding(
                    severity="MEDIUM",
                    category="Network Security",
                    file_path=file_path,
                    line_number=line_num,
                    description="Security group allows unrestricted access (0.0.0.0/0)",
                    impact="Overly permissive network access increases attack surface",
                    recommendation="Restrict access to specific CIDR blocks or security groups",
                    compliance_frameworks=["CIS"],
                    ai_confidence=0.95
                )
                findings.append(finding)

            # Detect missing encryption
            if 'encryption' in line_lower and 'false' in line_lower:
                finding = SecurityFinding(
                    severity="HIGH",
                    category="Data Protection",
                    file_path=file_path,
                    line_number=line_num,
                    description="Encryption explicitly disabled",
                    impact="Unencrypted data at rest violates compliance requirements",
                    recommendation="Enable encryption for data at rest",
                    compliance_frameworks=["SOC2", "PCI-DSS", "NIST"],
                    ai_confidence=0.90
                )
                findings.append(finding)

        return findings

    async def analyze_kubernetes_yaml(self, yaml_content: str, file_path: str) -> List[SecurityFinding]:
        """Analyze Kubernetes YAML for CKS security issues"""
        findings = []
        lines = yaml_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower().strip()

            # Detect privileged containers
            if 'privileged: true' in line_lower:
                finding = SecurityFinding(
                    severity="CRITICAL",
                    category="Pod Security Standards",
                    file_path=file_path,
                    line_number=line_num,
                    description="Privileged container detected",
                    impact="Privileged containers can escape to the host system",
                    recommendation="Remove privileged: true or use specific capabilities",
                    compliance_frameworks=["CIS"],
                    ai_confidence=0.98
                )
                findings.append(finding)

            # Detect missing security context
            if 'kind: pod' in line_lower.replace(' ', ''):
                # Look for security context in next 20 lines
                has_security_context = False
                for check_line in lines[line_num:line_num+20]:
                    if 'securitycontext' in check_line.lower().replace(' ', ''):
                        has_security_context = True
                        break

                if not has_security_context:
                    finding = SecurityFinding(
                        severity="MEDIUM",
                        category="Pod Security Standards",
                        file_path=file_path,
                        line_number=line_num,
                        description="Pod missing security context",
                        impact="No security constraints applied to pod execution",
                        recommendation="Add securityContext with appropriate settings",
                        compliance_frameworks=["CIS"],
                        ai_confidence=0.75
                    )
                    findings.append(finding)

        return findings

    def calculate_compliance_score(self, findings: List[SecurityFinding]) -> float:
        """Calculate overall compliance score"""
        if not findings:
            return 100.0

        # Weight by severity
        severity_weights = {
            "CRITICAL": 25,
            "HIGH": 15,
            "MEDIUM": 8,
            "LOW": 3
        }

        total_deductions = sum(severity_weights.get(f.severity, 0) for f in findings)
        score = max(0, 100 - total_deductions)
        return score

    def determine_risk_level(self, findings: List[SecurityFinding]) -> str:
        """Determine overall risk level"""
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")

        if critical_count > 0:
            return "CRITICAL"
        elif high_count >= 3:
            return "HIGH"
        elif high_count >= 1:
            return "MEDIUM"
        else:
            return "LOW"

    def generate_ai_summary(self, findings: List[SecurityFinding], project_name: str) -> str:
        """Generate AI-powered security assessment summary"""
        if not findings:
            base_summary = f"Security analysis of {project_name} shows no immediate concerns. The configuration follows security best practices."

            # Try to enhance with real AI
            if self.model_manager and self.model_manager.model:
                try:
                    ai_enhancement = self.model_manager.query_security_knowledge(
                        f"Provide additional security recommendations for a clean {project_name} project"
                    )
                    return f"{base_summary}\n\nAI Enhancement: {ai_enhancement}"
                except Exception:
                    pass

            return base_summary

        severity_counts = {}
        categories = set()

        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            categories.add(finding.category)

        # Build intelligent summary
        summary_parts = []

        if "CRITICAL" in severity_counts:
            summary_parts.append(f"URGENT: {severity_counts['CRITICAL']} critical security issues require immediate attention.")

        if "HIGH" in severity_counts:
            summary_parts.append(f"{severity_counts['HIGH']} high-severity issues pose significant security risks.")

        # Identify primary concerns
        primary_concerns = list(categories)[:3]
        if primary_concerns:
            summary_parts.append(f"Primary security concerns: {', '.join(primary_concerns)}.")

        # Add recommendations
        base_recommendation = "Recommend prioritizing credential management and access controls."
        summary_parts.append(base_recommendation)

        base_summary = " ".join(summary_parts)

        # Try to enhance with real AI analysis
        if self.model_manager and self.model_manager.model:
            try:
                findings_context = f"Found {len(findings)} security issues: " + ", ".join(categories)
                ai_enhancement = self.model_manager.query_security_knowledge(
                    f"Based on these security findings: {findings_context}, provide strategic remediation advice"
                )
                return f"{base_summary}\n\nAI Strategic Guidance: {ai_enhancement}"
            except Exception as e:
                print(f"AI enhancement failed: {e}")

        return base_summary

    async def comprehensive_analysis(self, project_path: str, client_name: Optional[str] = None) -> SecurityAssessment:
        """Perform comprehensive security analysis of project"""
        project_path = Path(project_path)
        all_findings = []
        files_analyzed = 0

        # Analyze Terraform files
        for tf_file in project_path.rglob("*.tf"):
            try:
                content = tf_file.read_text()
                findings = await self.analyze_terraform(content, str(tf_file))
                all_findings.extend(findings)
                files_analyzed += 1
            except Exception as e:
                print(f"Error analyzing {tf_file}: {e}")

        # Analyze Kubernetes YAML files
        for yaml_file in project_path.rglob("*.yaml"):
            try:
                content = yaml_file.read_text()
                if "kind:" in content.lower():  # Kubernetes resource
                    findings = await self.analyze_kubernetes_yaml(content, str(yaml_file))
                    all_findings.extend(findings)
                files_analyzed += 1
            except Exception as e:
                print(f"Error analyzing {yaml_file}: {e}")

        # Calculate metrics
        compliance_score = self.calculate_compliance_score(all_findings)
        risk_level = self.determine_risk_level(all_findings)
        ai_summary = self.generate_ai_summary(all_findings, project_path.name)

        # Generate remediation priorities
        remediation_priority = []
        if any(f.severity == "CRITICAL" for f in all_findings):
            remediation_priority.append("1. Address critical vulnerabilities immediately")
        if any(f.category == "Hardcoded Credentials" for f in all_findings):
            remediation_priority.append("2. Implement proper secret management")
        if any(f.category == "Network Security" for f in all_findings):
            remediation_priority.append("3. Review and restrict network access")

        return SecurityAssessment(
            project_name=client_name or project_path.name,
            scan_timestamp=datetime.now(),
            files_analyzed=files_analyzed,
            findings=all_findings,
            compliance_score=compliance_score,
            risk_level=risk_level,
            ai_summary=ai_summary,
            remediation_priority=remediation_priority
        )