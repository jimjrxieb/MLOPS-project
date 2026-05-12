"""
Slot Models for GP-Copilot Platform

Data models for instances, slots, and configurations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class SlotStatus(str, Enum):
    """Slot status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SCANNING = "scanning"
    FIXING = "fixing"
    ERROR = "error"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    CIS = "cis"
    NIST = "nist"
    SOC2 = "soc2"
    PCI_DSS = "pci-dss"
    HIPAA = "hipaa"
    FEDRAMP = "fedramp"
    ISO27001 = "iso27001"


@dataclass
class Instance:
    """
    An instance contains multiple slots (projects).

    Example:
        Instance(
            id="02-instance",
            name="Production Instance",
            base_path=Path("/home/.../GP-PROJECTS/02-instance")
        )
    """

    id: str                                 # Instance ID (01-instance, 02-instance)
    name: str                               # Human-readable name
    base_path: Path                         # Path to instance directory
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure base_path is a Path object."""
        if isinstance(self.base_path, str):
            self.base_path = Path(self.base_path)

    def get_slot_path(self, slot_id: str) -> Path:
        """Get path to specific slot."""
        return self.base_path / slot_id

    def list_slots(self) -> List[str]:
        """List all slots in this instance."""
        if not self.base_path.exists():
            return []

        slots = []
        for item in self.base_path.iterdir():
            if item.is_dir() and item.name.startswith("slot-"):
                slots.append(item.name)

        return sorted(slots)


@dataclass
class SlotConfig:
    """
    Configuration for a specific slot.

    Example:
        SlotConfig(
            instance="02-instance",
            slot_id="slot-2",
            project_name="kubernetes-goat",
            compliance_frameworks=[ComplianceFramework.CIS, ComplianceFramework.NIST],
            auto_fix_enabled=True,
            confidence_threshold=0.8
        )
    """

    # Identity
    instance: str                           # Instance ID
    slot_id: str                            # Slot ID (slot-1, slot-2, slot-3)

    # Project
    project_name: Optional[str] = None      # Human-readable project name
    project_path: Optional[Path] = None     # Path to cloned project (auto-detected)

    # Compliance
    compliance_frameworks: List[ComplianceFramework] = field(default_factory=list)

    # Auto-fix settings
    auto_fix_enabled: bool = True
    confidence_threshold: float = 0.8       # Minimum confidence for auto-fix
    require_approval: bool = False          # Require human approval for C-rank

    # Agents
    enabled_agents: List[str] = field(default_factory=lambda: ["jsa-ci", "jsa-devsecops", "jsa-monitor"])

    # Notifications
    slack_channel: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Auto-detect project path if not provided."""
        if self.project_path is None:
            # Auto-detect: GP-PROJECTS/{instance}/{slot_id}/project/
            base_path = Path("/home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS")
            slot_path = base_path / self.instance / self.slot_id

            # Look for project directory (first non-hidden directory that's not logs, workflow, etc.)
            if slot_path.exists():
                for item in slot_path.iterdir():
                    if (item.is_dir() and
                        not item.name.startswith(".") and
                        item.name not in {"logs", "workflow", "reports", "context"}):
                        self.project_path = item
                        if self.project_name is None:
                            self.project_name = item.name
                        break

        if isinstance(self.project_path, str):
            self.project_path = Path(self.project_path)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "instance": self.instance,
            "slot_id": self.slot_id,
            "project_name": self.project_name,
            "project_path": str(self.project_path) if self.project_path else None,
            "compliance_frameworks": [f.value for f in self.compliance_frameworks],
            "auto_fix_enabled": self.auto_fix_enabled,
            "confidence_threshold": self.confidence_threshold,
            "require_approval": self.require_approval,
            "enabled_agents": self.enabled_agents,
            "slack_channel": self.slack_channel,
            "email_recipients": self.email_recipients,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlotConfig":
        """Create from dictionary."""
        return cls(
            instance=data["instance"],
            slot_id=data["slot_id"],
            project_name=data.get("project_name"),
            project_path=Path(data["project_path"]) if data.get("project_path") else None,
            compliance_frameworks=[ComplianceFramework(f) for f in data.get("compliance_frameworks", [])],
            auto_fix_enabled=data.get("auto_fix_enabled", True),
            confidence_threshold=data.get("confidence_threshold", 0.8),
            require_approval=data.get("require_approval", False),
            enabled_agents=data.get("enabled_agents", ["jsa-ci", "jsa-devsecops", "jsa-monitor"]),
            slack_channel=data.get("slack_channel"),
            email_recipients=data.get("email_recipients", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Slot:
    """
    A slot represents a target project being scanned/fixed by JSA agents.

    Example:
        Slot(
            instance="02-instance",
            slot_id="slot-2",
            project_name="kubernetes-goat",
            status=SlotStatus.ACTIVE,
            config=SlotConfig(...)
        )
    """

    # Identity
    instance: str                           # Instance ID
    slot_id: str                            # Slot ID

    # Project
    project_name: str                       # Project name
    project_path: Path                      # Path to project

    # Status
    status: SlotStatus = SlotStatus.INACTIVE

    # Configuration
    config: Optional[SlotConfig] = None

    # Paths (auto-generated)
    base_path: Path = None                  # GP-PROJECTS/{instance}/{slot_id}/
    logs_path: Path = None                  # {base_path}/logs/
    workflow_path: Path = None              # {base_path}/workflow/
    reports_path: Path = None               # {base_path}/reports/
    context_path: Path = None               # {base_path}/context/

    # Stats
    last_scan: Optional[datetime] = None
    findings_count: int = 0
    resolved_count: int = 0
    escalated_count: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Auto-generate paths and create directories."""
        base = Path("/home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS")

        # Set base path
        if self.base_path is None:
            self.base_path = base / self.instance / self.slot_id

        # Set subdirectory paths
        if self.logs_path is None:
            self.logs_path = self.base_path / "logs"
        if self.workflow_path is None:
            self.workflow_path = self.base_path / "workflow"
        if self.reports_path is None:
            self.reports_path = self.base_path / "reports"
        if self.context_path is None:
            self.context_path = self.base_path / "context"

        # Convert string paths to Path objects
        if isinstance(self.project_path, str):
            self.project_path = Path(self.project_path)
        if isinstance(self.base_path, str):
            self.base_path = Path(self.base_path)

    def ensure_directories(self):
        """Create slot directory structure if it doesn't exist."""
        # Create main directories
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.reports_path.mkdir(parents=True, exist_ok=True)
        self.context_path.mkdir(parents=True, exist_ok=True)

        # Create workflow state directories
        workflow_states = ["inbox", "triage", "pending", "in-progress", "resolved", "escalated"]
        for state in workflow_states:
            (self.workflow_path / state).mkdir(parents=True, exist_ok=True)

    def get_workflow_state_path(self, state: str) -> Path:
        """Get path for specific workflow state."""
        return self.workflow_path / state

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "instance": self.instance,
            "slot_id": self.slot_id,
            "project_name": self.project_name,
            "project_path": str(self.project_path),
            "status": self.status.value,
            "base_path": str(self.base_path),
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "findings_count": self.findings_count,
            "resolved_count": self.resolved_count,
            "escalated_count": self.escalated_count,
            "config": self.config.to_dict() if self.config else None,
            "metadata": self.metadata,
        }
