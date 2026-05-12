#!/usr/bin/env python3
"""
CloudFormation Analyzer for jsa-devsecops
Analyzes AWS CloudFormation templates for security issues and compliance violations.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import yaml


class FindingType(Enum):
    """Types of security findings."""
    SECURITY_GROUP_OPEN = "security_group_open"
    ENCRYPTION_DISABLED = "encryption_disabled"
    PUBLIC_ACCESS = "public_access"
    HARDCODED_SECRET = "hardcoded_secret"
    MISSING_LOGGING = "missing_logging"
    IAM_OVERPRIVILEGED = "iam_overprivileged"
    INSECURE_PROTOCOL = "insecure_protocol"
    MISSING_BACKUP = "missing_backup"
    MISCONFIGURATION = "misconfiguration"


class FindingSeverity(Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class CFNFinding:
    """CloudFormation security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    resource_type: str
    resource_name: str
    logical_id: str
    description: str
    recommendation: str
    template_file: Optional[Path] = None
    line_number: Optional[int] = None
    compliance_frameworks: List[str] = field(default_factory=list)
    cve_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """CloudFormation analysis result."""
    timestamp: datetime
    template_dir: Path
    findings: List[CFNFinding]
    total_resources: int
    scanned_templates: List[Path]
    summary: Dict  # Severity breakdown


class CloudFormationAnalyzer:
    """
    Analyzes CloudFormation templates for security issues.

    Features:
    - Built-in security checks (encryption, IAM, public access)
    - Integration with checkov
    - Compliance framework mapping (CIS, PCI-DSS, SOC2)
    - JSON/YAML template support

    Example:
        analyzer = CloudFormationAnalyzer(template_dir="/infra/cloudformation")

        # Run analysis
        result = analyzer.analyze()

        # Check specific compliance framework
        pci_findings = analyzer.check_compliance("PCI-DSS")

        # Get high severity findings only
        critical = analyzer.get_findings_by_severity(FindingSeverity.HIGH)
    """

    def __init__(
        self,
        template_dir: Path = None,
        template_file: Path = None,
        dry_run: bool = False
    ):
        """
        Initialize CloudFormation analyzer.

        Args:
            template_dir: Directory containing CloudFormation templates
            template_file: Single template file to analyze
            dry_run: If True, don't execute external tools
        """
        self.template_dir = template_dir or Path.cwd()
        self.template_file = template_file
        self.dry_run = dry_run

        self.findings: List[CFNFinding] = []

    def analyze(self) -> AnalysisResult:
        """
        Run comprehensive CloudFormation analysis.

        Returns:
            AnalysisResult with all findings
        """
        self.findings = []

        # Find all CloudFormation templates
        if self.template_file:
            templates = [self.template_file]
        else:
            templates = list(self.template_dir.glob("**/*.yaml")) + \
                       list(self.template_dir.glob("**/*.yml")) + \
                       list(self.template_dir.glob("**/*.json"))

        # Filter for CloudFormation templates
        cfn_templates = []
        for template in templates:
            if self._is_cloudformation_template(template):
                cfn_templates.append(template)

        total_resources = 0

        # Run built-in checks
        for template in cfn_templates:
            template_data = self._parse_template(template)
            if not template_data:
                continue

            resources = template_data.get("Resources", {})
            total_resources += len(resources)

            self.findings.extend(self._check_security_groups(template, template_data))
            self.findings.extend(self._check_encryption(template, template_data))
            self.findings.extend(self._check_public_access(template, template_data))
            self.findings.extend(self._check_secrets(template, template_data))
            self.findings.extend(self._check_logging(template, template_data))
            self.findings.extend(self._check_iam_policies(template, template_data))
            self.findings.extend(self._check_insecure_protocols(template, template_data))

        # Run external scanners
        if not self.dry_run:
            self.findings.extend(self._run_checkov())

        # Generate summary
        summary = self._generate_summary()

        return AnalysisResult(
            timestamp=datetime.now(),
            template_dir=self.template_dir,
            findings=self.findings,
            total_resources=total_resources,
            scanned_templates=cfn_templates,
            summary=summary
        )

    def check_compliance(self, framework: str) -> List[CFNFinding]:
        """
        Check compliance for specific framework.

        Args:
            framework: Compliance framework (CIS, PCI-DSS, SOC2)

        Returns:
            List of findings relevant to framework
        """
        return [
            f for f in self.findings
            if any(framework.upper() in cf.upper() for cf in f.compliance_frameworks)
        ]

    def get_findings_by_severity(self, severity: FindingSeverity) -> List[CFNFinding]:
        """Get findings by severity level."""
        return [f for f in self.findings if f.severity == severity]

    def _is_cloudformation_template(self, file_path: Path) -> bool:
        """Check if file is a CloudFormation template."""
        try:
            data = self._parse_template(file_path)
            if not data:
                return False

            # CloudFormation templates have AWSTemplateFormatVersion or Resources
            return "AWSTemplateFormatVersion" in data or "Resources" in data
        except Exception:
            return False

    def _parse_template(self, template_path: Path) -> Optional[Dict]:
        """Parse CloudFormation template (JSON or YAML)."""
        try:
            content = template_path.read_text()

            if template_path.suffix == ".json":
                return json.loads(content)
            else:
                return yaml.safe_load(content)
        except Exception:
            return None

    def _check_security_groups(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for overly permissive security groups."""
        findings = []
        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::EC2::SecurityGroup":
                continue

            properties = resource.get("Properties", {})
            ingress_rules = properties.get("SecurityGroupIngress", [])

            for rule in ingress_rules:
                cidr = rule.get("CidrIp", "")
                if cidr == "0.0.0.0/0":
                    from_port = rule.get("FromPort", "any")
                    to_port = rule.get("ToPort", "any")

                    finding = CFNFinding(
                        finding_type=FindingType.SECURITY_GROUP_OPEN,
                        severity=FindingSeverity.HIGH,
                        resource_type="AWS::EC2::SecurityGroup",
                        resource_name=properties.get("GroupName", logical_id),
                        logical_id=logical_id,
                        description=f"Security group allows ingress from 0.0.0.0/0 on ports {from_port}-{to_port}",
                        recommendation="Restrict ingress to specific IP ranges or security groups",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 4.1", "PCI-DSS 1.2.1"]
                    )
                    findings.append(finding)

        return findings

    def _check_encryption(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for unencrypted storage resources."""
        findings = []
        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            resource_type = resource.get("Type")
            properties = resource.get("Properties", {})

            # Check S3 bucket encryption
            if resource_type == "AWS::S3::Bucket":
                encryption_config = properties.get("BucketEncryption")
                if not encryption_config:
                    finding = CFNFinding(
                        finding_type=FindingType.ENCRYPTION_DISABLED,
                        severity=FindingSeverity.HIGH,
                        resource_type=resource_type,
                        resource_name=properties.get("BucketName", logical_id),
                        logical_id=logical_id,
                        description="S3 bucket does not have encryption enabled",
                        recommendation="Add BucketEncryption with ServerSideEncryptionConfiguration",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 2.1.1", "PCI-DSS 3.4", "SOC2 CC6.6"]
                    )
                    findings.append(finding)

            # Check RDS encryption
            elif resource_type == "AWS::RDS::DBInstance":
                storage_encrypted = properties.get("StorageEncrypted", False)
                if not storage_encrypted:
                    finding = CFNFinding(
                        finding_type=FindingType.ENCRYPTION_DISABLED,
                        severity=FindingSeverity.HIGH,
                        resource_type=resource_type,
                        resource_name=properties.get("DBInstanceIdentifier", logical_id),
                        logical_id=logical_id,
                        description="RDS instance does not have storage encryption enabled",
                        recommendation="Set StorageEncrypted: true",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 2.3.1", "PCI-DSS 3.4"]
                    )
                    findings.append(finding)

            # Check EBS volume encryption
            elif resource_type == "AWS::EC2::Volume":
                encrypted = properties.get("Encrypted", False)
                if not encrypted:
                    finding = CFNFinding(
                        finding_type=FindingType.ENCRYPTION_DISABLED,
                        severity=FindingSeverity.MEDIUM,
                        resource_type=resource_type,
                        resource_name=logical_id,
                        logical_id=logical_id,
                        description="EBS volume does not have encryption enabled",
                        recommendation="Set Encrypted: true",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 2.2.1"]
                    )
                    findings.append(finding)

        return findings

    def _check_public_access(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for publicly accessible resources."""
        findings = []
        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            resource_type = resource.get("Type")
            properties = resource.get("Properties", {})

            # Check RDS public accessibility
            if resource_type == "AWS::RDS::DBInstance":
                publicly_accessible = properties.get("PubliclyAccessible", False)
                if publicly_accessible:
                    finding = CFNFinding(
                        finding_type=FindingType.PUBLIC_ACCESS,
                        severity=FindingSeverity.CRITICAL,
                        resource_type=resource_type,
                        resource_name=properties.get("DBInstanceIdentifier", logical_id),
                        logical_id=logical_id,
                        description="RDS instance is publicly accessible",
                        recommendation="Set PubliclyAccessible: false",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 2.3.3", "PCI-DSS 1.2.1"]
                    )
                    findings.append(finding)

            # Check S3 bucket public access
            elif resource_type == "AWS::S3::Bucket":
                public_access_config = properties.get("PublicAccessBlockConfiguration")
                if not public_access_config:
                    finding = CFNFinding(
                        finding_type=FindingType.PUBLIC_ACCESS,
                        severity=FindingSeverity.HIGH,
                        resource_type=resource_type,
                        resource_name=properties.get("BucketName", logical_id),
                        logical_id=logical_id,
                        description="S3 bucket does not have public access block configured",
                        recommendation="Add PublicAccessBlockConfiguration with BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy, RestrictPublicBuckets all set to true",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 2.1.5"]
                    )
                    findings.append(finding)

        return findings

    def _check_secrets(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for hardcoded secrets."""
        findings = []

        # Convert template to JSON string for pattern matching
        template_str = json.dumps(template_data)

        # Patterns for secrets
        secret_patterns = [
            (r'["\']?(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', "Password"),
            (r'["\']?(?:api_key|apikey|api-key)["\']?\s*[:=]\s*["\']([^"\']{16,})["\']', "API Key"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
            (r'["\']?(?:secret_key|secret-key)["\']?\s*[:=]\s*["\']([^"\']{20,})["\']', "Secret Key"),
        ]

        for pattern, secret_type in secret_patterns:
            matches = re.finditer(pattern, template_str, re.IGNORECASE)
            for match in matches:
                # Skip if it's a reference or parameter
                context = template_str[max(0, match.start()-50):match.end()+50]
                if "Ref" in context or "!Ref" in context or "Fn::GetAtt" in context:
                    continue

                finding = CFNFinding(
                    finding_type=FindingType.HARDCODED_SECRET,
                    severity=FindingSeverity.CRITICAL,
                    resource_type="Unknown",
                    resource_name="Unknown",
                    logical_id="Unknown",
                    description=f"Hardcoded {secret_type} detected in template",
                    recommendation=f"Use AWS Secrets Manager or Parameter Store instead of hardcoding {secret_type}",
                    template_file=template_path,
                    compliance_frameworks=["PCI-DSS 8.2.1", "SOC2 CC6.1"],
                    metadata={"secret_type": secret_type}
                )
                findings.append(finding)

        return findings

    def _check_logging(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for missing logging configurations."""
        findings = []
        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            resource_type = resource.get("Type")
            properties = resource.get("Properties", {})

            # Check S3 bucket logging
            if resource_type == "AWS::S3::Bucket":
                logging_config = properties.get("LoggingConfiguration")
                if not logging_config:
                    finding = CFNFinding(
                        finding_type=FindingType.MISSING_LOGGING,
                        severity=FindingSeverity.MEDIUM,
                        resource_type=resource_type,
                        resource_name=properties.get("BucketName", logical_id),
                        logical_id=logical_id,
                        description="S3 bucket does not have access logging enabled",
                        recommendation="Add LoggingConfiguration to enable access logs",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 2.1.3", "PCI-DSS 10.2.1", "SOC2 CC7.2"]
                    )
                    findings.append(finding)

            # Check CloudTrail logging
            elif resource_type == "AWS::CloudTrail::Trail":
                is_logging = properties.get("IsLogging", True)
                if not is_logging:
                    finding = CFNFinding(
                        finding_type=FindingType.MISSING_LOGGING,
                        severity=FindingSeverity.HIGH,
                        resource_type=resource_type,
                        resource_name=properties.get("TrailName", logical_id),
                        logical_id=logical_id,
                        description="CloudTrail trail has logging disabled",
                        recommendation="Set IsLogging: true",
                        template_file=template_path,
                        compliance_frameworks=["CIS AWS 3.1", "PCI-DSS 10.2"]
                    )
                    findings.append(finding)

        return findings

    def _check_iam_policies(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for overprivileged IAM policies."""
        findings = []
        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            resource_type = resource.get("Type")
            properties = resource.get("Properties", {})

            if resource_type not in ["AWS::IAM::Policy", "AWS::IAM::Role", "AWS::IAM::ManagedPolicy"]:
                continue

            # Get policy document
            policy_doc = properties.get("PolicyDocument")
            if not policy_doc:
                # Check inline policies in Role
                if resource_type == "AWS::IAM::Role":
                    policies = properties.get("Policies", [])
                    for policy in policies:
                        policy_doc = policy.get("PolicyDocument")
                        if policy_doc:
                            self._check_policy_document(
                                findings,
                                policy_doc,
                                logical_id,
                                resource_type,
                                template_path
                            )
                continue

            self._check_policy_document(
                findings,
                policy_doc,
                logical_id,
                resource_type,
                template_path
            )

        return findings

    def _check_policy_document(
        self,
        findings: List[CFNFinding],
        policy_doc: Dict,
        logical_id: str,
        resource_type: str,
        template_path: Path
    ):
        """Check IAM policy document for overprivileged actions."""
        statements = policy_doc.get("Statement", [])

        for statement in statements:
            if statement.get("Effect") != "Allow":
                continue

            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            resources = statement.get("Resource", [])
            if isinstance(resources, str):
                resources = [resources]

            # Check for wildcard actions
            if "*" in actions:
                finding = CFNFinding(
                    finding_type=FindingType.IAM_OVERPRIVILEGED,
                    severity=FindingSeverity.HIGH,
                    resource_type=resource_type,
                    resource_name=logical_id,
                    logical_id=logical_id,
                    description="IAM policy allows all actions (*)",
                    recommendation="Use specific actions instead of wildcard",
                    template_file=template_path,
                    compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2", "SOC2 CC6.1"]
                )
                findings.append(finding)

            # Check for wildcard resources with sensitive actions
            if "*" in resources:
                sensitive_patterns = ["Delete", "Put", "Create", "Modify", "Update"]
                for action in actions:
                    if any(pattern in action for pattern in sensitive_patterns):
                        finding = CFNFinding(
                            finding_type=FindingType.IAM_OVERPRIVILEGED,
                            severity=FindingSeverity.MEDIUM,
                            resource_type=resource_type,
                            resource_name=logical_id,
                            logical_id=logical_id,
                            description=f"IAM policy allows {action} on all resources (*)",
                            recommendation="Restrict Resource to specific ARNs",
                            template_file=template_path,
                            compliance_frameworks=["CIS AWS 1.16", "SOC2 CC6.1"]
                        )
                        findings.append(finding)

    def _check_insecure_protocols(
        self,
        template_path: Path,
        template_data: Dict
    ) -> List[CFNFinding]:
        """Check for insecure protocols (HTTP, SSLv3, TLS 1.0/1.1)."""
        findings = []
        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            resource_type = resource.get("Type")
            properties = resource.get("Properties", {})

            # Check ALB listener protocols
            if resource_type == "AWS::ElasticLoadBalancingV2::Listener":
                protocol = properties.get("Protocol", "")
                if protocol == "HTTP":
                    finding = CFNFinding(
                        finding_type=FindingType.INSECURE_PROTOCOL,
                        severity=FindingSeverity.HIGH,
                        resource_type=resource_type,
                        resource_name=logical_id,
                        logical_id=logical_id,
                        description="Load balancer listener uses insecure HTTP protocol",
                        recommendation="Use HTTPS protocol with valid SSL certificate",
                        template_file=template_path,
                        compliance_frameworks=["PCI-DSS 4.1", "SOC2 CC6.6"]
                    )
                    findings.append(finding)

                # Check SSL policy
                ssl_policy = properties.get("SslPolicy", "")
                if ssl_policy and "TLSv1" in ssl_policy and "TLSv1-2" not in ssl_policy:
                    finding = CFNFinding(
                        finding_type=FindingType.INSECURE_PROTOCOL,
                        severity=FindingSeverity.MEDIUM,
                        resource_type=resource_type,
                        resource_name=logical_id,
                        logical_id=logical_id,
                        description="Load balancer uses outdated TLS 1.0 or 1.1",
                        recommendation="Use TLS 1.2 or higher (ELBSecurityPolicy-TLS-1-2-2017-01)",
                        template_file=template_path,
                        compliance_frameworks=["PCI-DSS 4.1"]
                    )
                    findings.append(finding)

        return findings

    def _run_checkov(self) -> List[CFNFinding]:
        """Run checkov CloudFormation scanner."""
        findings = []

        try:
            # Determine scan path
            scan_path = str(self.template_file) if self.template_file else str(self.template_dir)

            cmd = [
                "checkov",
                "--framework", "cloudformation",
                "--directory" if not self.template_file else "--file", scan_path,
                "--output", "json",
                "--quiet"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.stdout:
                data = json.loads(result.stdout)

                # Parse checkov results
                for check_result in data.get("results", {}).get("failed_checks", []):
                    severity_map = {
                        "CRITICAL": FindingSeverity.CRITICAL,
                        "HIGH": FindingSeverity.HIGH,
                        "MEDIUM": FindingSeverity.MEDIUM,
                        "LOW": FindingSeverity.LOW,
                    }

                    finding = CFNFinding(
                        finding_type=FindingType.MISCONFIGURATION,
                        severity=severity_map.get(check_result.get("severity", "MEDIUM"), FindingSeverity.MEDIUM),
                        resource_type=check_result.get("resource", "Unknown"),
                        resource_name=check_result.get("resource", "Unknown"),
                        logical_id=check_result.get("resource", "Unknown"),
                        description=check_result.get("check_name", "Unknown"),
                        recommendation=check_result.get("guideline", "Review Checkov documentation"),
                        template_file=Path(check_result.get("file_path", "Unknown")),
                        line_number=check_result.get("file_line_range", [0])[0],
                        compliance_frameworks=check_result.get("bc_check_id", "").split("_"),
                        metadata={
                            "check_id": check_result.get("check_id"),
                            "scanner": "checkov"
                        }
                    )
                    findings.append(finding)

        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # Checkov not installed
            pass
        except json.JSONDecodeError:
            pass

        return findings

    def _generate_summary(self) -> Dict:
        """Generate findings summary."""
        summary = {
            "total": len(self.findings),
            "critical": len([f for f in self.findings if f.severity == FindingSeverity.CRITICAL]),
            "high": len([f for f in self.findings if f.severity == FindingSeverity.HIGH]),
            "medium": len([f for f in self.findings if f.severity == FindingSeverity.MEDIUM]),
            "low": len([f for f in self.findings if f.severity == FindingSeverity.LOW]),
            "info": len([f for f in self.findings if f.severity == FindingSeverity.INFO]),
        }

        # Breakdown by finding type
        summary["by_type"] = {}
        for finding in self.findings:
            finding_type = finding.finding_type.value
            summary["by_type"][finding_type] = summary["by_type"].get(finding_type, 0) + 1

        return summary


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze CloudFormation templates")
    parser.add_argument("--template-dir", help="Directory containing CloudFormation templates")
    parser.add_argument("--template", help="Single template file to analyze")
    parser.add_argument("--compliance", choices=["CIS", "PCI-DSS", "SOC2"], help="Check specific compliance framework")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by minimum severity")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    template_dir = Path(args.template_dir) if args.template_dir else None
    template_file = Path(args.template) if args.template else None

    analyzer = CloudFormationAnalyzer(
        template_dir=template_dir,
        template_file=template_file
    )

    print(f"☁️  CloudFormation Analyzer\n")

    # Run analysis
    result = analyzer.analyze()

    # Filter by compliance if specified
    findings = result.findings
    if args.compliance:
        findings = analyzer.check_compliance(args.compliance)
        print(f"📋 Compliance Framework: {args.compliance}\n")

    # Filter by severity if specified
    if args.severity:
        severity_map = {
            "critical": FindingSeverity.CRITICAL,
            "high": FindingSeverity.HIGH,
            "medium": FindingSeverity.MEDIUM,
            "low": FindingSeverity.LOW,
            "info": FindingSeverity.INFO
        }
        min_severity = severity_map[args.severity]
        severity_order = [FindingSeverity.CRITICAL, FindingSeverity.HIGH, FindingSeverity.MEDIUM, FindingSeverity.LOW, FindingSeverity.INFO]
        min_index = severity_order.index(min_severity)
        findings = [f for f in findings if severity_order.index(f.severity) <= min_index]

    # Output results
    if args.output == "json":
        output = {
            "timestamp": result.timestamp.isoformat(),
            "summary": result.summary,
            "findings": [
                {
                    "type": f.finding_type.value,
                    "severity": f.severity.value,
                    "resource_type": f.resource_type,
                    "logical_id": f.logical_id,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "template": str(f.template_file) if f.template_file else None,
                    "compliance": f.compliance_frameworks
                }
                for f in findings
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"📊 Analysis Summary:")
        print(f"  Total templates scanned: {len(result.scanned_templates)}")
        print(f"  Total resources: {result.total_resources}")
        print(f"  Total findings: {result.summary['total']}")
        print(f"  Critical: {result.summary['critical']}")
        print(f"  High: {result.summary['high']}")
        print(f"  Medium: {result.summary['medium']}")
        print(f"  Low: {result.summary['low']}\n")

        if findings:
            print(f"🔍 Findings ({len(findings)}):\n")
            for i, finding in enumerate(findings, 1):
                print(f"{i}. [{finding.severity.value.upper()}] {finding.description}")
                print(f"   Resource: {finding.resource_type} ({finding.logical_id})")
                print(f"   Recommendation: {finding.recommendation}")
                if finding.template_file:
                    print(f"   File: {finding.template_file}")
                if finding.compliance_frameworks:
                    print(f"   Compliance: {', '.join(finding.compliance_frameworks)}")
                print()
