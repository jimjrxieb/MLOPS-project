#!/usr/bin/env python3
"""
EC2 Watcher for jsa-devsecops
Monitors EC2 instances for security configuration changes.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class EC2EventType(Enum):
    """Types of EC2 events."""
    INSTANCE_LAUNCHED = "instance_launched"
    INSTANCE_STOPPED = "instance_stopped"
    INSTANCE_TERMINATED = "instance_terminated"
    INSTANCE_RESTARTED = "instance_restarted"
    PUBLIC_IP_ASSIGNED = "public_ip_assigned"
    PUBLIC_IP_REMOVED = "public_ip_removed"
    SECURITY_GROUP_ATTACHED = "security_group_attached"
    SECURITY_GROUP_DETACHED = "security_group_detached"
    IMDSV1_DETECTED = "imdsv1_detected"
    IMDSV2_ENABLED = "imdsv2_enabled"
    USER_DATA_MODIFIED = "user_data_modified"
    IAM_ROLE_ATTACHED = "iam_role_attached"
    IAM_ROLE_DETACHED = "iam_role_detached"
    UNENCRYPTED_VOLUME = "unencrypted_volume"
    PUBLIC_AMI_USED = "public_ami_used"


@dataclass
class EC2Instance:
    """Represents an EC2 instance."""
    instance_id: str
    instance_type: str
    state: str  # pending, running, stopping, stopped, terminated
    availability_zone: str
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    security_groups: List[str] = field(default_factory=list)
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    iam_instance_profile: Optional[str] = None
    metadata_options: Dict = field(default_factory=dict)
    block_device_mappings: List[Dict] = field(default_factory=list)
    launch_time: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class EC2Event:
    """Represents an EC2 security event."""
    event_type: EC2EventType
    timestamp: datetime
    instance_id: str
    details: Dict
    risk_level: str  # Critical, High, Medium, Low
    recommendation: str = ""


class EC2Watcher:
    """
    Monitors EC2 instances for security configuration changes.

    Features:
    - Instance state monitoring (launch, stop, terminate)
    - Public IP assignment detection
    - Security group association tracking
    - IMDSv2 enforcement checking
    - Unencrypted volume detection
    - IAM role attachment monitoring
    - Public AMI usage alerts

    Example:
        watcher = EC2Watcher(region="us-east-1")

        # Watch all instances
        events = watcher.watch_all_instances()

        # Watch specific instance
        events = watcher.watch_instance("i-1234567890abcdef0")

        # Get instances without IMDSv2
        risky_instances = watcher.get_instances_without_imdsv2()

        # Get instances with public IPs
        public_instances = watcher.get_instances_with_public_ips()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        state_file: Path = None
    ):
        """
        Initialize EC2 watcher.

        Args:
            region: AWS region
            profile: AWS profile name
            state_file: Path to store watcher state
        """
        self.region = region
        self.profile = profile
        self.state_file = state_file or Path(f"/tmp/ec2_watcher_state_{region}.json")

        # Track instances
        self.tracked_instances: Dict[str, EC2Instance] = {}

        # Load previous state
        self._load_state()

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "ec2"] + command + ["--region", self.region, "--output", "json"]

        if self.profile:
            cmd.extend(["--profile", self.profile])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)

            return {}

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return {}

    def _get_instance(self, instance_id: str) -> Optional[EC2Instance]:
        """Get EC2 instance details."""
        result = self._run_aws_command([
            "describe-instances",
            "--instance-ids", instance_id
        ])

        if not result or "Reservations" not in result:
            return None

        for reservation in result["Reservations"]:
            for instance_data in reservation.get("Instances", []):
                if instance_data["InstanceId"] == instance_id:
                    return self._parse_instance(instance_data)

        return None

    def _parse_instance(self, instance_data: Dict) -> EC2Instance:
        """Parse EC2 instance data from AWS CLI output."""
        # Parse tags
        tags = {}
        for tag in instance_data.get("Tags", []):
            tags[tag["Key"]] = tag["Value"]

        # Parse security groups
        security_groups = [
            sg["GroupId"]
            for sg in instance_data.get("SecurityGroups", [])
        ]

        # Parse metadata options
        metadata_options = instance_data.get("MetadataOptions", {})

        # Parse IAM instance profile
        iam_profile = None
        if "IamInstanceProfile" in instance_data:
            iam_profile = instance_data["IamInstanceProfile"].get("Arn")

        # Parse launch time
        launch_time = None
        if "LaunchTime" in instance_data:
            launch_time = datetime.fromisoformat(
                instance_data["LaunchTime"].replace("Z", "+00:00")
            )

        return EC2Instance(
            instance_id=instance_data["InstanceId"],
            instance_type=instance_data["InstanceType"],
            state=instance_data["State"]["Name"],
            availability_zone=instance_data["Placement"]["AvailabilityZone"],
            public_ip=instance_data.get("PublicIpAddress"),
            private_ip=instance_data.get("PrivateIpAddress"),
            security_groups=security_groups,
            vpc_id=instance_data.get("VpcId"),
            subnet_id=instance_data.get("SubnetId"),
            iam_instance_profile=iam_profile,
            metadata_options=metadata_options,
            block_device_mappings=instance_data.get("BlockDeviceMappings", []),
            launch_time=launch_time,
            tags=tags
        )

    def watch_instance(self, instance_id: str) -> List[EC2Event]:
        """
        Watch a specific EC2 instance for changes.

        Args:
            instance_id: EC2 instance ID

        Returns:
            List of EC2Event objects
        """
        events = []

        current_instance = self._get_instance(instance_id)
        if not current_instance:
            return events

        # First time seeing this instance
        if instance_id not in self.tracked_instances:
            events.append(EC2Event(
                event_type=EC2EventType.INSTANCE_LAUNCHED,
                timestamp=datetime.now(),
                instance_id=instance_id,
                details={
                    "instance_type": current_instance.instance_type,
                    "vpc_id": current_instance.vpc_id,
                    "state": current_instance.state
                },
                risk_level="Low",
                recommendation="New instance detected - review security configuration"
            ))

            # Check for IMDSv1
            if self._is_imdsv1_enabled(current_instance):
                events.append(EC2Event(
                    event_type=EC2EventType.IMDSV1_DETECTED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "metadata_options": current_instance.metadata_options
                    },
                    risk_level="High",
                    recommendation="Enable IMDSv2 to prevent SSRF attacks: aws ec2 modify-instance-metadata-options --instance-id {} --http-tokens required".format(instance_id)
                ))

            # Check for public IP
            if current_instance.public_ip:
                events.append(EC2Event(
                    event_type=EC2EventType.PUBLIC_IP_ASSIGNED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "public_ip": current_instance.public_ip
                    },
                    risk_level="Medium",
                    recommendation="Instance has public IP - ensure security groups restrict access appropriately"
                ))

            # Check for unencrypted volumes
            unencrypted_volumes = self._check_unencrypted_volumes(current_instance)
            if unencrypted_volumes:
                events.append(EC2Event(
                    event_type=EC2EventType.UNENCRYPTED_VOLUME,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "unencrypted_volumes": unencrypted_volumes
                    },
                    risk_level="High",
                    recommendation="Enable EBS encryption for all volumes (CIS AWS 2.2.1)"
                ))

            # Check for missing IAM role
            if not current_instance.iam_instance_profile:
                events.append(EC2Event(
                    event_type=EC2EventType.IAM_ROLE_DETACHED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={},
                    risk_level="Medium",
                    recommendation="Attach IAM instance profile instead of using access keys"
                ))

        else:
            # Instance exists - check for changes
            previous_instance = self.tracked_instances[instance_id]

            # State change
            if current_instance.state != previous_instance.state:
                if current_instance.state == "stopped":
                    event_type = EC2EventType.INSTANCE_STOPPED
                    risk_level = "Low"
                elif current_instance.state == "terminated":
                    event_type = EC2EventType.INSTANCE_TERMINATED
                    risk_level = "Low"
                elif current_instance.state == "running":
                    event_type = EC2EventType.INSTANCE_RESTARTED
                    risk_level = "Low"
                else:
                    event_type = EC2EventType.INSTANCE_LAUNCHED
                    risk_level = "Low"

                events.append(EC2Event(
                    event_type=event_type,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "previous_state": previous_instance.state,
                        "current_state": current_instance.state
                    },
                    risk_level=risk_level,
                    recommendation=""
                ))

            # Public IP assignment
            if current_instance.public_ip and not previous_instance.public_ip:
                events.append(EC2Event(
                    event_type=EC2EventType.PUBLIC_IP_ASSIGNED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "public_ip": current_instance.public_ip
                    },
                    risk_level="High",
                    recommendation="Public IP assigned - review security groups for 0.0.0.0/0 rules"
                ))

            # Public IP removal
            if previous_instance.public_ip and not current_instance.public_ip:
                events.append(EC2Event(
                    event_type=EC2EventType.PUBLIC_IP_REMOVED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "previous_public_ip": previous_instance.public_ip
                    },
                    risk_level="Low",
                    recommendation=""
                ))

            # Security group changes
            added_sgs = set(current_instance.security_groups) - set(previous_instance.security_groups)
            for sg_id in added_sgs:
                events.append(EC2Event(
                    event_type=EC2EventType.SECURITY_GROUP_ATTACHED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "security_group_id": sg_id
                    },
                    risk_level="Medium",
                    recommendation="Review security group rules for {} - ensure least privilege".format(sg_id)
                ))

            removed_sgs = set(previous_instance.security_groups) - set(current_instance.security_groups)
            for sg_id in removed_sgs:
                events.append(EC2Event(
                    event_type=EC2EventType.SECURITY_GROUP_DETACHED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "security_group_id": sg_id
                    },
                    risk_level="Low",
                    recommendation=""
                ))

            # IAM role changes
            if current_instance.iam_instance_profile != previous_instance.iam_instance_profile:
                if current_instance.iam_instance_profile:
                    events.append(EC2Event(
                        event_type=EC2EventType.IAM_ROLE_ATTACHED,
                        timestamp=datetime.now(),
                        instance_id=instance_id,
                        details={
                            "iam_role": current_instance.iam_instance_profile
                        },
                        risk_level="Medium",
                        recommendation="Review IAM role permissions for least privilege"
                    ))
                else:
                    events.append(EC2Event(
                        event_type=EC2EventType.IAM_ROLE_DETACHED,
                        timestamp=datetime.now(),
                        instance_id=instance_id,
                        details={
                            "previous_iam_role": previous_instance.iam_instance_profile
                        },
                        risk_level="High",
                        recommendation="Instance has no IAM role - using access keys is less secure"
                    ))

            # IMDSv2 changes
            prev_imdsv1 = self._is_imdsv1_enabled(previous_instance)
            curr_imdsv1 = self._is_imdsv1_enabled(current_instance)

            if not prev_imdsv1 and curr_imdsv1:
                events.append(EC2Event(
                    event_type=EC2EventType.IMDSV1_DETECTED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "metadata_options": current_instance.metadata_options
                    },
                    risk_level="High",
                    recommendation="IMDSv1 was re-enabled - this increases SSRF risk"
                ))
            elif prev_imdsv1 and not curr_imdsv1:
                events.append(EC2Event(
                    event_type=EC2EventType.IMDSV2_ENABLED,
                    timestamp=datetime.now(),
                    instance_id=instance_id,
                    details={
                        "metadata_options": current_instance.metadata_options
                    },
                    risk_level="Low",
                    recommendation="IMDSv2 enabled - SSRF risk reduced"
                ))

        # Update tracked state
        self.tracked_instances[instance_id] = current_instance
        self._save_state()

        return events

    def watch_all_instances(self, vpc_id: str = None) -> List[EC2Event]:
        """
        Watch all EC2 instances (optionally filtered by VPC).

        Args:
            vpc_id: Optional VPC ID to filter instances

        Returns:
            List of EC2Event objects
        """
        all_events = []

        # Build describe-instances command
        cmd = ["describe-instances"]
        filters = []

        if vpc_id:
            filters.append(f"Name=vpc-id,Values={vpc_id}")

        # Exclude terminated instances
        filters.append("Name=instance-state-name,Values=pending,running,stopping,stopped")

        if filters:
            cmd.extend(["--filters"] + filters)

        result = self._run_aws_command(cmd)

        if not result or "Reservations" not in result:
            return all_events

        # Watch each instance
        for reservation in result["Reservations"]:
            for instance_data in reservation.get("Instances", []):
                instance_id = instance_data["InstanceId"]
                events = self.watch_instance(instance_id)
                all_events.extend(events)

        return all_events

    def get_instances_without_imdsv2(self) -> List[EC2Instance]:
        """Get instances that don't require IMDSv2."""
        risky_instances = []

        for instance in self.tracked_instances.values():
            if self._is_imdsv1_enabled(instance):
                risky_instances.append(instance)

        return risky_instances

    def get_instances_with_public_ips(self) -> List[EC2Instance]:
        """Get instances with public IP addresses."""
        return [
            instance
            for instance in self.tracked_instances.values()
            if instance.public_ip
        ]

    def get_instances_without_iam_roles(self) -> List[EC2Instance]:
        """Get instances without IAM instance profiles."""
        return [
            instance
            for instance in self.tracked_instances.values()
            if not instance.iam_instance_profile
        ]

    def _is_imdsv1_enabled(self, instance: EC2Instance) -> bool:
        """Check if instance allows IMDSv1."""
        # HttpTokens=optional means IMDSv1 is allowed
        # HttpTokens=required means only IMDSv2 is allowed
        return instance.metadata_options.get("HttpTokens", "optional") == "optional"

    def _check_unencrypted_volumes(self, instance: EC2Instance) -> List[str]:
        """Check for unencrypted EBS volumes."""
        unencrypted_volumes = []

        for bdm in instance.block_device_mappings:
            if "Ebs" in bdm:
                volume_id = bdm["Ebs"].get("VolumeId")
                if volume_id:
                    # Check volume encryption
                    volume_info = self._run_aws_command([
                        "describe-volumes",
                        "--volume-ids", volume_id
                    ])

                    if volume_info and "Volumes" in volume_info:
                        for volume in volume_info["Volumes"]:
                            if not volume.get("Encrypted", False):
                                unencrypted_volumes.append(volume_id)

        return unencrypted_volumes

    def _save_state(self):
        """Save watcher state to file."""
        state = {
            "tracked_instances": {
                instance_id: {
                    "instance_id": inst.instance_id,
                    "instance_type": inst.instance_type,
                    "state": inst.state,
                    "availability_zone": inst.availability_zone,
                    "public_ip": inst.public_ip,
                    "private_ip": inst.private_ip,
                    "security_groups": inst.security_groups,
                    "vpc_id": inst.vpc_id,
                    "subnet_id": inst.subnet_id,
                    "iam_instance_profile": inst.iam_instance_profile,
                    "metadata_options": inst.metadata_options,
                    "block_device_mappings": inst.block_device_mappings,
                    "launch_time": inst.launch_time.isoformat() if inst.launch_time else None,
                    "tags": inst.tags
                }
                for instance_id, inst in self.tracked_instances.items()
            }
        }

        try:
            self.state_file.write_text(json.dumps(state, indent=2))
        except (IOError, OSError):
            pass

    def _load_state(self):
        """Load watcher state from file."""
        if not self.state_file.exists():
            return

        try:
            state = json.loads(self.state_file.read_text())

            for instance_id, inst_data in state.get("tracked_instances", {}).items():
                launch_time = None
                if inst_data.get("launch_time"):
                    launch_time = datetime.fromisoformat(inst_data["launch_time"])

                self.tracked_instances[instance_id] = EC2Instance(
                    instance_id=inst_data["instance_id"],
                    instance_type=inst_data["instance_type"],
                    state=inst_data["state"],
                    availability_zone=inst_data["availability_zone"],
                    public_ip=inst_data.get("public_ip"),
                    private_ip=inst_data.get("private_ip"),
                    security_groups=inst_data.get("security_groups", []),
                    vpc_id=inst_data.get("vpc_id"),
                    subnet_id=inst_data.get("subnet_id"),
                    iam_instance_profile=inst_data.get("iam_instance_profile"),
                    metadata_options=inst_data.get("metadata_options", {}),
                    block_device_mappings=inst_data.get("block_device_mappings", []),
                    launch_time=launch_time,
                    tags=inst_data.get("tags", {})
                )

        except (json.JSONDecodeError, IOError, OSError):
            pass


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor EC2 instances for security changes")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--instance-id", help="Watch specific instance")
    parser.add_argument("--vpc-id", help="Watch all instances in VPC")
    parser.add_argument("--check-imdsv2", action="store_true", help="List instances without IMDSv2")
    parser.add_argument("--check-public-ips", action="store_true", help="List instances with public IPs")
    parser.add_argument("--check-iam-roles", action="store_true", help="List instances without IAM roles")
    parser.add_argument("--watch-all", action="store_true", help="Watch all instances")

    args = parser.parse_args()

    watcher = EC2Watcher(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 EC2 Security Watcher\n")
    print(f"Region: {args.region}\n")

    # Check modes
    if args.check_imdsv2:
        instances = watcher.get_instances_without_imdsv2()
        print(f"⚠️  Instances without IMDSv2 ({len(instances)}):\n")
        for instance in instances:
            print(f"  • {instance.instance_id} ({instance.instance_type})")
            print(f"    State: {instance.state}")
            print(f"    Metadata Options: {instance.metadata_options}")
            print()

    elif args.check_public_ips:
        instances = watcher.get_instances_with_public_ips()
        print(f"🌐 Instances with Public IPs ({len(instances)}):\n")
        for instance in instances:
            print(f"  • {instance.instance_id} ({instance.instance_type})")
            print(f"    Public IP: {instance.public_ip}")
            print(f"    Security Groups: {', '.join(instance.security_groups)}")
            print()

    elif args.check_iam_roles:
        instances = watcher.get_instances_without_iam_roles()
        print(f"🔐 Instances without IAM Roles ({len(instances)}):\n")
        for instance in instances:
            print(f"  • {instance.instance_id} ({instance.instance_type})")
            print(f"    State: {instance.state}")
            print()

    # Watch modes
    elif args.instance_id:
        print(f"👁️  Watching instance: {args.instance_id}\n")
        events = watcher.watch_instance(args.instance_id)

        if not events:
            print("✅ No security events detected\n")
        else:
            print(f"📊 Security Events ({len(events)}):\n")
            for event in events:
                risk_icon = {
                    "Critical": "🔴",
                    "High": "🟠",
                    "Medium": "🟡",
                    "Low": "🟢"
                }[event.risk_level]

                print(f"{risk_icon} {event.event_type.value.upper()}")
                print(f"   Risk: {event.risk_level}")
                print(f"   Details: {event.details}")
                if event.recommendation:
                    print(f"   💡 {event.recommendation}")
                print()

    elif args.watch_all or args.vpc_id:
        if args.vpc_id:
            print(f"👁️  Watching all instances in VPC: {args.vpc_id}\n")
        else:
            print(f"👁️  Watching all instances\n")

        events = watcher.watch_all_instances(vpc_id=args.vpc_id)

        if not events:
            print("✅ No security events detected\n")
        else:
            print(f"📊 Security Events ({len(events)}):\n")

            # Group by instance
            events_by_instance = {}
            for event in events:
                if event.instance_id not in events_by_instance:
                    events_by_instance[event.instance_id] = []
                events_by_instance[event.instance_id].append(event)

            for instance_id, instance_events in events_by_instance.items():
                print(f"Instance: {instance_id} ({len(instance_events)} events)")

                for event in instance_events:
                    risk_icon = {
                        "Critical": "🔴",
                        "High": "🟠",
                        "Medium": "🟡",
                        "Low": "🟢"
                    }[event.risk_level]

                    print(f"  {risk_icon} {event.event_type.value}")
                    if event.recommendation:
                        print(f"     💡 {event.recommendation}")

                print()

    else:
        parser.print_help()
