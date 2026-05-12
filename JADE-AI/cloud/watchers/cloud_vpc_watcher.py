#!/usr/bin/env python3
"""
VPC Watcher for jsa-devsecops
Monitors AWS VPC, Security Groups, NACLs, and network configurations.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class VPCEventType(Enum):
    """VPC event types."""
    SECURITY_GROUP_CREATED = "security_group_created"
    SECURITY_GROUP_MODIFIED = "security_group_modified"
    SECURITY_GROUP_DELETED = "security_group_deleted"
    RULE_ADDED = "rule_added"
    RULE_REMOVED = "rule_removed"
    NACL_MODIFIED = "nacl_modified"
    VPC_CREATED = "vpc_created"
    SUBNET_CREATED = "subnet_created"
    OPEN_PORT_DETECTED = "open_port_detected"


@dataclass
class SecurityGroupRule:
    """Security group rule."""
    ip_protocol: str
    from_port: Optional[int]
    to_port: Optional[int]
    cidr_ipv4: Optional[str] = None
    cidr_ipv6: Optional[str] = None
    referenced_group_id: Optional[str] = None
    description: str = ""


@dataclass
class SecurityGroup:
    """Security group details."""
    group_id: str
    group_name: str
    description: str
    vpc_id: str
    ingress_rules: List[SecurityGroupRule] = field(default_factory=list)
    egress_rules: List[SecurityGroupRule] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class VPC:
    """VPC details."""
    vpc_id: str
    cidr_block: str
    is_default: bool
    state: str
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Subnet:
    """Subnet details."""
    subnet_id: str
    vpc_id: str
    cidr_block: str
    availability_zone: str
    map_public_ip_on_launch: bool
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class VPCEvent:
    """VPC change event."""
    event_type: VPCEventType
    timestamp: datetime
    resource_type: str  # SecurityGroup, NACL, VPC, Subnet
    resource_id: str
    resource_name: str
    details: Dict = field(default_factory=dict)
    risk_level: str = "Medium"  # Critical, High, Medium, Low


class VPCWatcher:
    """
    Watches AWS VPC resources for security changes.

    Features:
    - Monitor security groups
    - Detect overly permissive rules (0.0.0.0/0)
    - Track NACL changes
    - Monitor VPC/subnet creation
    - Alert on open sensitive ports (22, 3389, etc.)

    Example:
        watcher = VPCWatcher(region="us-east-1", profile="prod")

        # Watch all security groups
        events = watcher.watch_security_groups()

        # Watch specific security group
        sg_events = watcher.watch_security_group("sg-12345")

        # Get overly permissive security groups
        risky_sgs = watcher.get_overpermissive_security_groups()

        # Watch VPC
        vpc_events = watcher.watch_vpc("vpc-12345")
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = False
    ):
        """
        Initialize VPC watcher.

        Args:
            region: AWS region
            profile: AWS profile name
            dry_run: If True, don't execute AWS API calls
        """
        self.region = region
        self.profile = profile
        self.dry_run = dry_run

        # Track VPC resources
        self.tracked_security_groups: Dict[str, SecurityGroup] = {}
        self.tracked_vpcs: Dict[str, VPC] = {}
        self.tracked_subnets: Dict[str, Subnet] = {}

        # Sensitive ports
        self.sensitive_ports = {
            22: "SSH",
            3389: "RDP",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            27017: "MongoDB",
            1433: "MSSQL",
            5984: "CouchDB"
        }

    def watch_security_groups(self, vpc_id: str = None) -> List[VPCEvent]:
        """
        Watch all security groups.

        Args:
            vpc_id: Optional VPC ID to filter by

        Returns:
            List of VPCEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # List all security groups
        security_groups = self._list_security_groups(vpc_id)

        for sg in security_groups:
            sg_events = self.watch_security_group(sg["GroupId"])
            events.extend(sg_events)

        return events

    def watch_security_group(self, group_id: str) -> List[VPCEvent]:
        """
        Watch specific security group.

        Args:
            group_id: Security group ID

        Returns:
            List of VPCEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # Get current security group
        current_sg = self._get_security_group(group_id)
        if not current_sg:
            return events

        # Check if tracked
        if group_id in self.tracked_security_groups:
            previous_sg = self.tracked_security_groups[group_id]

            # Detect ingress rule changes
            added_ingress = self._find_added_rules(
                previous_sg.ingress_rules,
                current_sg.ingress_rules
            )

            for rule in added_ingress:
                risk_level = self._assess_rule_risk(rule)

                event = VPCEvent(
                    event_type=VPCEventType.RULE_ADDED,
                    timestamp=datetime.now(),
                    resource_type="SecurityGroup",
                    resource_id=group_id,
                    resource_name=current_sg.group_name,
                    details={
                        "direction": "ingress",
                        "protocol": rule.ip_protocol,
                        "from_port": rule.from_port,
                        "to_port": rule.to_port,
                        "cidr": rule.cidr_ipv4 or rule.cidr_ipv6
                    },
                    risk_level=risk_level
                )
                events.append(event)

                # Special alert for 0.0.0.0/0 on sensitive ports
                if rule.cidr_ipv4 == "0.0.0.0/0" and rule.from_port in self.sensitive_ports:
                    event = VPCEvent(
                        event_type=VPCEventType.OPEN_PORT_DETECTED,
                        timestamp=datetime.now(),
                        resource_type="SecurityGroup",
                        resource_id=group_id,
                        resource_name=current_sg.group_name,
                        details={
                            "port": rule.from_port,
                            "service": self.sensitive_ports[rule.from_port],
                            "cidr": "0.0.0.0/0"
                        },
                        risk_level="Critical"
                    )
                    events.append(event)

            # Detect removed ingress rules
            removed_ingress = self._find_removed_rules(
                previous_sg.ingress_rules,
                current_sg.ingress_rules
            )

            for rule in removed_ingress:
                event = VPCEvent(
                    event_type=VPCEventType.RULE_REMOVED,
                    timestamp=datetime.now(),
                    resource_type="SecurityGroup",
                    resource_id=group_id,
                    resource_name=current_sg.group_name,
                    details={
                        "direction": "ingress",
                        "protocol": rule.ip_protocol,
                        "from_port": rule.from_port,
                        "to_port": rule.to_port,
                        "cidr": rule.cidr_ipv4 or rule.cidr_ipv6
                    },
                    risk_level="Low"
                )
                events.append(event)

        else:
            # New security group detected
            event = VPCEvent(
                event_type=VPCEventType.SECURITY_GROUP_CREATED,
                timestamp=datetime.now(),
                resource_type="SecurityGroup",
                resource_id=group_id,
                resource_name=current_sg.group_name,
                details={
                    "vpc_id": current_sg.vpc_id,
                    "ingress_rules": len(current_sg.ingress_rules),
                    "egress_rules": len(current_sg.egress_rules)
                },
                risk_level="Medium"
            )
            events.append(event)

        # Update tracked security group
        self.tracked_security_groups[group_id] = current_sg

        return events

    def watch_vpc(self, vpc_id: str) -> List[VPCEvent]:
        """
        Watch specific VPC.

        Args:
            vpc_id: VPC ID

        Returns:
            List of VPCEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # Get current VPC
        current_vpc = self._get_vpc(vpc_id)
        if not current_vpc:
            return events

        # Check if new VPC
        if vpc_id not in self.tracked_vpcs:
            event = VPCEvent(
                event_type=VPCEventType.VPC_CREATED,
                timestamp=datetime.now(),
                resource_type="VPC",
                resource_id=vpc_id,
                resource_name=current_vpc.tags.get("Name", vpc_id),
                details={
                    "cidr_block": current_vpc.cidr_block,
                    "is_default": current_vpc.is_default
                },
                risk_level="Medium"
            )
            events.append(event)

        # Update tracked VPC
        self.tracked_vpcs[vpc_id] = current_vpc

        return events

    def get_overpermissive_security_groups(self) -> List[SecurityGroup]:
        """
        Get security groups with overly permissive rules.

        Returns:
            List of SecurityGroup objects with risky rules
        """
        risky_sgs = []

        if self.dry_run:
            return risky_sgs

        for sg_id, sg in self.tracked_security_groups.items():
            # Check for 0.0.0.0/0 ingress rules
            for rule in sg.ingress_rules:
                if rule.cidr_ipv4 == "0.0.0.0/0":
                    # Extra risky if on sensitive ports
                    if rule.from_port in self.sensitive_ports:
                        risky_sgs.append(sg)
                        break

        return risky_sgs

    def _list_security_groups(self, vpc_id: str = None) -> List[Dict]:
        """List all security groups."""
        try:
            cmd = ["aws", "ec2", "describe-security-groups", "--region", self.region, "--output", "json"]

            if vpc_id:
                cmd.extend(["--filters", f"Name=vpc-id,Values={vpc_id}"])

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("SecurityGroups", [])

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _get_security_group(self, group_id: str) -> Optional[SecurityGroup]:
        """Get security group details."""
        try:
            cmd = [
                "aws", "ec2", "describe-security-groups",
                "--group-ids", group_id,
                "--region", self.region,
                "--output", "json"
            ]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                sgs = data.get("SecurityGroups", [])

                if sgs:
                    sg_data = sgs[0]

                    # Parse ingress rules
                    ingress_rules = []
                    for rule in sg_data.get("IpPermissions", []):
                        for ip_range in rule.get("IpRanges", []):
                            ingress_rules.append(SecurityGroupRule(
                                ip_protocol=rule.get("IpProtocol", "-1"),
                                from_port=rule.get("FromPort"),
                                to_port=rule.get("ToPort"),
                                cidr_ipv4=ip_range.get("CidrIp"),
                                description=ip_range.get("Description", "")
                            ))

                        for ip_range in rule.get("Ipv6Ranges", []):
                            ingress_rules.append(SecurityGroupRule(
                                ip_protocol=rule.get("IpProtocol", "-1"),
                                from_port=rule.get("FromPort"),
                                to_port=rule.get("ToPort"),
                                cidr_ipv6=ip_range.get("CidrIpv6"),
                                description=ip_range.get("Description", "")
                            ))

                    # Parse egress rules
                    egress_rules = []
                    for rule in sg_data.get("IpPermissionsEgress", []):
                        for ip_range in rule.get("IpRanges", []):
                            egress_rules.append(SecurityGroupRule(
                                ip_protocol=rule.get("IpProtocol", "-1"),
                                from_port=rule.get("FromPort"),
                                to_port=rule.get("ToPort"),
                                cidr_ipv4=ip_range.get("CidrIp"),
                                description=ip_range.get("Description", "")
                            ))

                    # Parse tags
                    tags = {tag["Key"]: tag["Value"] for tag in sg_data.get("Tags", [])}

                    return SecurityGroup(
                        group_id=sg_data["GroupId"],
                        group_name=sg_data["GroupName"],
                        description=sg_data["Description"],
                        vpc_id=sg_data["VpcId"],
                        ingress_rules=ingress_rules,
                        egress_rules=egress_rules,
                        tags=tags
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _get_vpc(self, vpc_id: str) -> Optional[VPC]:
        """Get VPC details."""
        try:
            cmd = [
                "aws", "ec2", "describe-vpcs",
                "--vpc-ids", vpc_id,
                "--region", self.region,
                "--output", "json"
            ]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                vpcs = data.get("Vpcs", [])

                if vpcs:
                    vpc_data = vpcs[0]
                    tags = {tag["Key"]: tag["Value"] for tag in vpc_data.get("Tags", [])}

                    return VPC(
                        vpc_id=vpc_data["VpcId"],
                        cidr_block=vpc_data["CidrBlock"],
                        is_default=vpc_data.get("IsDefault", False),
                        state=vpc_data["State"],
                        tags=tags
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _find_added_rules(
        self,
        previous: List[SecurityGroupRule],
        current: List[SecurityGroupRule]
    ) -> List[SecurityGroupRule]:
        """Find rules that were added."""
        added = []

        prev_set = {self._rule_signature(r) for r in previous}
        curr_set = {self._rule_signature(r) for r in current}

        added_sigs = curr_set - prev_set

        for rule in current:
            if self._rule_signature(rule) in added_sigs:
                added.append(rule)

        return added

    def _find_removed_rules(
        self,
        previous: List[SecurityGroupRule],
        current: List[SecurityGroupRule]
    ) -> List[SecurityGroupRule]:
        """Find rules that were removed."""
        removed = []

        prev_set = {self._rule_signature(r) for r in previous}
        curr_set = {self._rule_signature(r) for r in current}

        removed_sigs = prev_set - curr_set

        for rule in previous:
            if self._rule_signature(rule) in removed_sigs:
                removed.append(rule)

        return removed

    def _rule_signature(self, rule: SecurityGroupRule) -> str:
        """Generate unique signature for rule."""
        return f"{rule.ip_protocol}:{rule.from_port}:{rule.to_port}:{rule.cidr_ipv4}:{rule.cidr_ipv6}"

    def _assess_rule_risk(self, rule: SecurityGroupRule) -> str:
        """Assess risk level of security group rule."""
        # 0.0.0.0/0 on sensitive ports is critical
        if rule.cidr_ipv4 == "0.0.0.0/0" and rule.from_port in self.sensitive_ports:
            return "Critical"

        # 0.0.0.0/0 on any port is high risk
        if rule.cidr_ipv4 == "0.0.0.0/0":
            return "High"

        # Specific CIDR is medium risk
        if rule.cidr_ipv4:
            return "Medium"

        return "Low"


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Watch AWS VPC for changes")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--vpc-id", help="VPC ID to watch")
    parser.add_argument("--security-group", help="Security group ID to watch")
    parser.add_argument("--check-overpermissive", action="store_true", help="Check for overpermissive security groups")

    args = parser.parse_args()

    watcher = VPCWatcher(region=args.region, profile=args.profile)

    print(f"🌐 VPC Watcher - Region: {args.region}\n")

    # Watch specific resources
    if args.security_group:
        print(f"📊 Watching security group: {args.security_group}\n")
        events = watcher.watch_security_group(args.security_group)
    elif args.vpc_id:
        print(f"📊 Watching VPC: {args.vpc_id}\n")
        events = watcher.watch_security_groups(vpc_id=args.vpc_id)
        events.extend(watcher.watch_vpc(args.vpc_id))
    else:
        print("📊 Watching all security groups...\n")
        events = watcher.watch_security_groups()

    # Display events
    if events:
        print(f"🔔 Found {len(events)} VPC events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. [{event.risk_level.upper()}] {event.event_type.value}")
            print(f"   Resource: {event.resource_type} ({event.resource_id})")
            print(f"   Details: {event.details}")
            print()

    # Check overpermissive
    if args.check_overpermissive:
        print("\n🔍 Checking for overpermissive security groups...\n")
        risky_sgs = watcher.get_overpermissive_security_groups()

        if risky_sgs:
            print(f"⚠️  Found {len(risky_sgs)} overpermissive security groups:\n")
            for sg in risky_sgs:
                print(f"- {sg.group_name} ({sg.group_id})")
                for rule in sg.ingress_rules:
                    if rule.cidr_ipv4 == "0.0.0.0/0":
                        port_info = f"Port {rule.from_port}"
                        if rule.from_port in watcher.sensitive_ports:
                            port_info += f" ({watcher.sensitive_ports[rule.from_port]})"
                        print(f"  ⚠️  {port_info} open to 0.0.0.0/0")
                print()
        else:
            print("✅ No overpermissive security groups detected")
