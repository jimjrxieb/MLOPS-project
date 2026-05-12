#!/usr/bin/env python3
"""
CloudFormation Watcher for jsa-devsecops
Monitors AWS CloudFormation stacks and templates.

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
import yaml


class CFNEventType(Enum):
    """CloudFormation event types."""
    STACK_CREATE = "stack_create"
    STACK_UPDATE = "stack_update"
    STACK_DELETE = "stack_delete"
    TEMPLATE_CHANGE = "template_change"
    DRIFT_DETECTED = "drift_detected"
    STACK_FAILED = "stack_failed"


class StackStatus(Enum):
    """CloudFormation stack statuses."""
    CREATE_COMPLETE = "CREATE_COMPLETE"
    CREATE_IN_PROGRESS = "CREATE_IN_PROGRESS"
    CREATE_FAILED = "CREATE_FAILED"
    UPDATE_COMPLETE = "UPDATE_COMPLETE"
    UPDATE_IN_PROGRESS = "UPDATE_IN_PROGRESS"
    UPDATE_FAILED = "UPDATE_FAILED"
    DELETE_COMPLETE = "DELETE_COMPLETE"
    DELETE_IN_PROGRESS = "DELETE_IN_PROGRESS"
    DELETE_FAILED = "DELETE_FAILED"
    ROLLBACK_COMPLETE = "ROLLBACK_COMPLETE"


@dataclass
class CFNResource:
    """CloudFormation resource."""
    logical_id: str
    resource_type: str
    physical_id: Optional[str] = None
    status: Optional[str] = None
    properties: Dict = field(default_factory=dict)


@dataclass
class CFNStack:
    """CloudFormation stack."""
    stack_name: str
    stack_id: str
    status: StackStatus
    resources: List[CFNResource]
    template: Optional[Dict] = None
    parameters: Dict = field(default_factory=dict)
    outputs: Dict = field(default_factory=dict)
    tags: Dict = field(default_factory=dict)
    creation_time: Optional[datetime] = None
    last_updated_time: Optional[datetime] = None


@dataclass
class CFNEvent:
    """CloudFormation change event."""
    event_type: CFNEventType
    timestamp: datetime
    stack: CFNStack
    resources_changed: List[CFNResource] = field(default_factory=list)
    drift_details: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


class CloudFormationWatcher:
    """
    Watches CloudFormation stacks for changes and drift.

    Features:
    - Monitor stack status changes
    - Detect stack drift
    - Watch template files
    - Track resource changes
    - Alert on stack failures

    Example:
        watcher = CloudFormationWatcher(region="us-east-1")

        # Watch specific stack
        events = watcher.watch_stack("my-app-stack")

        # Detect drift
        drift = watcher.detect_stack_drift("my-app-stack")

        # Watch all stacks
        all_events = watcher.watch_all_stacks()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = False
    ):
        """
        Initialize CloudFormation watcher.

        Args:
            region: AWS region
            profile: AWS profile name
            dry_run: If True, don't execute AWS API calls
        """
        self.region = region
        self.profile = profile
        self.dry_run = dry_run

        # Track stack states
        self.tracked_stacks: Dict[str, CFNStack] = {}

    def watch_stack(self, stack_name: str) -> List[CFNEvent]:
        """
        Watch a specific CloudFormation stack.

        Args:
            stack_name: Stack name to watch

        Returns:
            List of CFNEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # Get current stack info
        current_stack = self._describe_stack(stack_name)

        if not current_stack:
            return events

        # Check if stack state changed
        if stack_name in self.tracked_stacks:
            previous_stack = self.tracked_stacks[stack_name]

            # Detect status change
            if current_stack.status != previous_stack.status:
                event_type = self._get_event_type_from_status(current_stack.status)

                event = CFNEvent(
                    event_type=event_type,
                    timestamp=datetime.now(),
                    stack=current_stack,
                    metadata={
                        "previous_status": previous_stack.status.value,
                        "current_status": current_stack.status.value
                    }
                )
                events.append(event)

            # Detect resource changes
            changed_resources = self._find_resource_changes(
                previous_stack.resources,
                current_stack.resources
            )

            if changed_resources:
                event = CFNEvent(
                    event_type=CFNEventType.STACK_UPDATE,
                    timestamp=datetime.now(),
                    stack=current_stack,
                    resources_changed=changed_resources,
                    metadata={
                        "resource_count": len(changed_resources)
                    }
                )
                events.append(event)

        # Update tracked stack
        self.tracked_stacks[stack_name] = current_stack

        return events

    def watch_all_stacks(self) -> List[CFNEvent]:
        """
        Watch all CloudFormation stacks in the region.

        Returns:
            List of CFNEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # List all stacks
        stacks = self._list_stacks()

        for stack_name in stacks:
            stack_events = self.watch_stack(stack_name)
            events.extend(stack_events)

        return events

    def detect_stack_drift(self, stack_name: str) -> Optional[CFNEvent]:
        """
        Detect drift for a CloudFormation stack.

        Args:
            stack_name: Stack name

        Returns:
            CFNEvent if drift detected, None otherwise
        """
        if self.dry_run:
            return None

        try:
            # Start drift detection
            cmd = [
                "aws", "cloudformation", "detect-stack-drift",
                "--stack-name", stack_name,
                "--region", self.region
            ]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return None

            # Parse drift detection ID
            detection_data = json.loads(result.stdout)
            detection_id = detection_data.get("StackDriftDetectionId")

            # Wait for drift detection to complete and get results
            drift_info = self._get_drift_results(stack_name, detection_id)

            if drift_info and drift_info.get("StackDriftStatus") == "DRIFTED":
                stack = self._describe_stack(stack_name)

                event = CFNEvent(
                    event_type=CFNEventType.DRIFT_DETECTED,
                    timestamp=datetime.now(),
                    stack=stack,
                    drift_details=drift_info,
                    metadata={
                        "drifted_resources": drift_info.get("DriftedStackResourceCount", 0)
                    }
                )
                return event

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def watch_template_file(self, template_file: Path) -> List[CFNEvent]:
        """
        Watch CloudFormation template file for changes.

        Args:
            template_file: Path to CloudFormation template (YAML or JSON)

        Returns:
            List of CFNEvent objects
        """
        events = []

        if not template_file.exists():
            return events

        # Check if file was recently modified (last 5 minutes)
        mtime = template_file.stat().st_mtime
        if datetime.now().timestamp() - mtime < 300:
            try:
                # Parse template
                if template_file.suffix in [".yaml", ".yml"]:
                    template = yaml.safe_load(template_file.read_text())
                else:
                    template = json.loads(template_file.read_text())

                event = CFNEvent(
                    event_type=CFNEventType.TEMPLATE_CHANGE,
                    timestamp=datetime.now(),
                    stack=CFNStack(
                        stack_name=template_file.stem,
                        stack_id="",
                        status=StackStatus.CREATE_COMPLETE,
                        resources=[],
                        template=template
                    ),
                    metadata={
                        "template_file": str(template_file),
                        "resource_count": len(template.get("Resources", {}))
                    }
                )
                events.append(event)

            except (yaml.YAMLError, json.JSONDecodeError):
                pass

        return events

    def get_stack_resources(self, stack_name: str) -> List[CFNResource]:
        """Get all resources in a stack."""
        if self.dry_run:
            return []

        try:
            cmd = [
                "aws", "cloudformation", "describe-stack-resources",
                "--stack-name", stack_name,
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
                resources = []

                for resource in data.get("StackResources", []):
                    cfn_resource = CFNResource(
                        logical_id=resource["LogicalResourceId"],
                        resource_type=resource["ResourceType"],
                        physical_id=resource.get("PhysicalResourceId"),
                        status=resource.get("ResourceStatus")
                    )
                    resources.append(cfn_resource)

                return resources

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _describe_stack(self, stack_name: str) -> Optional[CFNStack]:
        """Describe a CloudFormation stack."""
        try:
            cmd = [
                "aws", "cloudformation", "describe-stacks",
                "--stack-name", stack_name,
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
                stacks = data.get("Stacks", [])

                if stacks:
                    stack_data = stacks[0]

                    # Parse parameters
                    parameters = {
                        p["ParameterKey"]: p["ParameterValue"]
                        for p in stack_data.get("Parameters", [])
                    }

                    # Parse outputs
                    outputs = {
                        o["OutputKey"]: o["OutputValue"]
                        for o in stack_data.get("Outputs", [])
                    }

                    # Parse tags
                    tags = {
                        t["Key"]: t["Value"]
                        for t in stack_data.get("Tags", [])
                    }

                    # Get resources
                    resources = self.get_stack_resources(stack_name)

                    return CFNStack(
                        stack_name=stack_data["StackName"],
                        stack_id=stack_data["StackId"],
                        status=StackStatus(stack_data["StackStatus"]),
                        resources=resources,
                        parameters=parameters,
                        outputs=outputs,
                        tags=tags,
                        creation_time=datetime.fromisoformat(stack_data["CreationTime"].replace("Z", "+00:00")),
                        last_updated_time=datetime.fromisoformat(stack_data.get("LastUpdatedTime", stack_data["CreationTime"]).replace("Z", "+00:00"))
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

        return None

    def _list_stacks(self) -> List[str]:
        """List all CloudFormation stacks."""
        try:
            cmd = [
                "aws", "cloudformation", "list-stacks",
                "--stack-status-filter",
                "CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE",
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
                return [s["StackName"] for s in data.get("StackSummaries", [])]

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _get_drift_results(self, stack_name: str, detection_id: str) -> Optional[Dict]:
        """Get drift detection results."""
        try:
            cmd = [
                "aws", "cloudformation", "describe-stack-drift-detection-status",
                "--stack-drift-detection-id", detection_id,
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
                return json.loads(result.stdout)

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _get_event_type_from_status(self, status: StackStatus) -> CFNEventType:
        """Map stack status to event type."""
        if "CREATE" in status.value:
            return CFNEventType.STACK_CREATE
        elif "UPDATE" in status.value:
            return CFNEventType.STACK_UPDATE
        elif "DELETE" in status.value:
            return CFNEventType.STACK_DELETE
        elif "FAILED" in status.value:
            return CFNEventType.STACK_FAILED
        else:
            return CFNEventType.STACK_UPDATE

    def _find_resource_changes(
        self,
        previous: List[CFNResource],
        current: List[CFNResource]
    ) -> List[CFNResource]:
        """Find changed resources between two states."""
        changed = []

        prev_map = {r.logical_id: r for r in previous}
        curr_map = {r.logical_id: r for r in current}

        # Find added or modified resources
        for logical_id, resource in curr_map.items():
            if logical_id not in prev_map:
                changed.append(resource)
            elif resource.status != prev_map[logical_id].status:
                changed.append(resource)

        # Find deleted resources
        for logical_id in prev_map:
            if logical_id not in curr_map:
                changed.append(prev_map[logical_id])

        return changed


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Watch CloudFormation stacks")
    parser.add_argument("--stack", help="Stack name to watch")
    parser.add_argument("--all", action="store_true", help="Watch all stacks")
    parser.add_argument("--detect-drift", help="Detect drift for stack")
    parser.add_argument("--template", help="Watch template file")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")

    args = parser.parse_args()

    watcher = CloudFormationWatcher(region=args.region, profile=args.profile)

    print(f"☁️  CloudFormation Watcher - Region: {args.region}\n")

    # Watch specific stack
    if args.stack:
        print(f"📊 Watching stack: {args.stack}")
        events = watcher.watch_stack(args.stack)
        for event in events:
            print(f"  🔔 {event.event_type.value}: {event.metadata}")

    # Watch all stacks
    if args.all:
        print("📊 Watching all stacks...")
        events = watcher.watch_all_stacks()
        print(f"  Found {len(events)} events across all stacks")

    # Detect drift
    if args.detect_drift:
        print(f"🔍 Detecting drift for: {args.detect_drift}")
        drift_event = watcher.detect_stack_drift(args.detect_drift)
        if drift_event:
            print(f"  ⚠️  DRIFT DETECTED!")
            print(f"  Drifted resources: {drift_event.metadata.get('drifted_resources')}")
        else:
            print(f"  ✅ No drift detected")

    # Watch template file
    if args.template:
        print(f"📝 Watching template: {args.template}")
        events = watcher.watch_template_file(Path(args.template))
        for event in events:
            print(f"  🔔 {event.event_type.value}: {event.metadata.get('resource_count')} resources")
