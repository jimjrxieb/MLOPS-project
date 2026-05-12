```markdown
# GP-Copilot Slot Management System

**Version**: 1.0.0
**Phase**: 10.2 - Slot Targeting System
**Status**: ✅ Complete

---

## Overview

The Slot Management System provides multi-instance, multi-slot architecture for managing target projects across the GP-Copilot platform.

### Architecture

```
GP-PROJECTS/
├── 01-instance/
│   ├── slot-1/
│   │   ├── ProjectA/          # Target project
│   │   ├── logs/              # Per-agent logs
│   │   ├── workflow/          # State machine
│   │   ├── reports/           # Generated reports
│   │   ├── context/           # Context files
│   │   └── config.json        # Slot configuration
│   ├── slot-2/
│   └── slot-3/
└── 02-instance/
    ├── slot-1/DEFENSE-project/
    ├── slot-2/kubernetes-goat/
    └── slot-3/Portfolio/
```

### Features

- ✅ **Multi-Instance**: Separate instances for different environments/clients
- ✅ **Multi-Slot**: 3 slots per instance for parallel project scanning
- ✅ **Auto-Discovery**: Automatically detects projects in slot directories
- ✅ **Configuration**: Per-slot configs with compliance frameworks, auto-fix settings
- ✅ **Context Management**: Architecture, tech-stack, and compliance context files
- ✅ **Workflow Tracking**: Inbox → Triage → Pending → Resolved state machine

---

## Quick Start

### Basic Usage

```python
from JADE_AI.src.slots import SlotManager, ContextManager

# Initialize manager
manager = SlotManager()

# List all instances
instances = manager.list_instances()
# [Instance(id='01-instance', ...), Instance(id='02-instance', ...)]

# List slots in an instance
slots = manager.list_slots(instance="02-instance")
# [Slot(slot_id='slot-1', ...), Slot(slot_id='slot-2', ...), Slot(slot_id='slot-3', ...)]

# Get specific slot
slot = manager.get_slot(instance="02-instance", slot_id="slot-2")
print(slot.project_name)  # 'kubernetes-goat'
print(slot.project_path)  # Path('/home/.../GP-PROJECTS/02-instance/slot-2/kubernetes-goat')

# Activate slot
manager.activate_slot(instance="02-instance", slot_id="slot-2")

# Get active slot
active = manager.get_active_slot()
```

### Context Management

```python
from JADE_AI.src.slots import SlotManager, ContextManager

# Get slot
manager = SlotManager()
slot = manager.get_slot(instance="02-instance", slot_id="slot-2")

# Initialize context manager
context_mgr = ContextManager(slot)

# Load context
arch = context_mgr.load("architecture")
tech = context_mgr.load("tech-stack")
compliance = context_mgr.load("compliance")

# Save context
context_mgr.save("architecture", "## Architecture\n\n- Microservices\n- Kubernetes")

# Create templates
context_mgr.create_architecture_template()
context_mgr.create_techstack_template()
context_mgr.create_compliance_template(frameworks=["CIS", "NIST"])
```

---

## Models

### Slot

Represents a target project being scanned/fixed.

```python
@dataclass
class Slot:
    instance: str                   # Instance ID (02-instance)
    slot_id: str                    # Slot ID (slot-2)
    project_name: str               # Project name (kubernetes-goat)
    project_path: Path              # Path to project
    status: SlotStatus              # ACTIVE, INACTIVE, SCANNING, FIXING, ERROR
    config: Optional[SlotConfig]    # Slot configuration

    # Auto-generated paths
    base_path: Path                 # GP-PROJECTS/{instance}/{slot_id}/
    logs_path: Path                 # {base_path}/logs/
    workflow_path: Path             # {base_path}/workflow/
    reports_path: Path              # {base_path}/reports/
    context_path: Path              # {base_path}/context/

    # Stats
    last_scan: Optional[datetime]
    findings_count: int
    resolved_count: int
    escalated_count: int
```

### SlotConfig

Per-slot configuration.

```python
@dataclass
class SlotConfig:
    instance: str
    slot_id: str

    # Project
    project_name: Optional[str]
    project_path: Optional[Path]

    # Compliance
    compliance_frameworks: List[ComplianceFramework]  # [CIS, NIST, SOC2, ...]

    # Auto-fix settings
    auto_fix_enabled: bool = True
    confidence_threshold: float = 0.8
    require_approval: bool = False

    # Agents
    enabled_agents: List[str] = ["jsa-ci", "jsa-devsecops", "jsa-monitor"]

    # Notifications
    slack_channel: Optional[str]
    email_recipients: List[str]
```

### Instance

Represents an instance containing multiple slots.

```python
@dataclass
class Instance:
    id: str                     # Instance ID (01-instance, 02-instance)
    name: str                   # Human-readable name
    base_path: Path             # Path to instance directory
    created_at: datetime
    metadata: Dict[str, Any]
```

---

## SlotManager

### List Operations

```python
manager = SlotManager()

# List all instances
instances = manager.list_instances()
for instance in instances:
    print(f"{instance.id}: {len(instance.list_slots())} slots")

# List all slots
all_slots = manager.list_slots()

# List slots in specific instance
instance_slots = manager.list_slots(instance="02-instance")
```

### Get Slot

```python
# Get specific slot
slot = manager.get_slot(instance="02-instance", slot_id="slot-2")

if slot:
    print(f"Project: {slot.project_name}")
    print(f"Path: {slot.project_path}")
    print(f"Status: {slot.status.value}")
    print(f"Findings: {slot.findings_count}")
    print(f"Resolved: {slot.resolved_count}")
```

### Activate/Deactivate

```python
# Activate slot (set as current target)
manager.activate_slot(instance="02-instance", slot_id="slot-2")

# Get active slot
active = manager.get_active_slot()
print(f"Active: {active.instance}/{active.slot_id}")

# Deactivate slot
manager.deactivate_slot(instance="02-instance", slot_id="slot-2")
```

### Path Helpers

```python
# Get logs path
logs_path = manager.get_slot_logs_path(
    instance="02-instance",
    slot_id="slot-2",
    agent="jsa-ci"
)
# Path('.../GP-PROJECTS/02-instance/slot-2/logs/jsa-ci')

# Get workflow path
workflow_path = manager.get_slot_workflow_path(
    instance="02-instance",
    slot_id="slot-2",
    state="pending"
)
# Path('.../GP-PROJECTS/02-instance/slot-2/workflow/pending')

# Get context
context = manager.get_slot_context(instance="02-instance", slot_id="slot-2")
# {
#   "instance": "02-instance",
#   "slot_id": "slot-2",
#   "project_name": "kubernetes-goat",
#   "compliance_frameworks": ["cis", "nist"],
#   ...
# }
```

### Configuration

```python
# Load slot with config
slot = manager.get_slot(instance="02-instance", slot_id="slot-2")

# Modify config
slot.config.auto_fix_enabled = False
slot.config.confidence_threshold = 0.9
slot.config.compliance_frameworks.append(ComplianceFramework.SOC2)

# Save config
manager.save_config(slot)
```

---

## ContextManager

### Load Context

```python
context_mgr = ContextManager(slot)

# Load specific context
arch = context_mgr.load("architecture")
if arch:
    print(arch)  # Markdown content

# Load all context
all_context = context_mgr.load_all()
# {
#   "architecture": "## Architecture\n...",
#   "tech-stack": "## Tech Stack\n...",
#   "compliance": "## Compliance\n..."
# }
```

### Save Context

```python
# Save architecture
context_mgr.save("architecture", """
## Architecture

### Frontend
- React SPA
- Nginx reverse proxy

### Backend
- Python Flask API
- PostgreSQL database

### Infrastructure
- Kubernetes (EKS)
- Terraform
""")

# Update existing context
context_mgr.update("compliance", """
## PCI-DSS

- Requirement 6.2: Ensure all systems are protected from malware
- Requirement 11.2: Run internal and external network vulnerability scans
""")
```

### Templates

```python
# Create architecture template
context_mgr.create_architecture_template()

# Create tech-stack template
context_mgr.create_techstack_template()

# Create compliance template
context_mgr.create_compliance_template(frameworks=["CIS", "NIST", "SOC2"])
```

### Utilities

```python
# Check if context exists
if context_mgr.exists("architecture"):
    print("Architecture context available")

# List existing context files
files = context_mgr.list_files()
# ['architecture', 'tech-stack']

# Delete context
context_mgr.delete("tech-stack")

# Convert to dict (for API responses)
data = context_mgr.to_dict()
# {
#   "slot": "slot-2",
#   "instance": "02-instance",
#   "files": ["architecture", "tech-stack"],
#   "content": {...}
# }
```

---

## Directory Structure

### Slot Directory Layout

```
GP-PROJECTS/{instance}/{slot_id}/
├── {project}/              # Cloned target project
│   ├── src/
│   ├── tests/
│   └── ...
├── logs/                   # Per-agent logs
│   ├── jsa-ci/
│   │   ├── main.log
│   │   ├── scan.log
│   │   └── fix.log
│   ├── jsa-devsecops/
│   │   ├── main.log
│   │   ├── scan.log
│   │   ├── fix.log
│   │   └── verify.log
│   └── jsa-monitor/
│       ├── alerts.log
│       └── escalations.log
├── workflow/               # State machine
│   ├── inbox/              # New findings
│   ├── triage/             # Being analyzed
│   ├── pending/            # Awaiting approval
│   ├── in-progress/        # Being fixed
│   ├── resolved/           # Fixed and verified
│   └── escalated/          # Escalated to human
├── reports/                # Generated reports
│   ├── compliance_cis_20260101.pdf
│   ├── executive_20260101.html
│   └── remediation_20260101.json
├── context/                # Slot context
│   ├── architecture.md
│   ├── tech-stack.md
│   └── compliance.md
├── config.json             # Slot configuration
└── .status                 # Current status (active/inactive)
```

---

## Integration Examples

### With Logging System

```python
from GP_BEDROCK_AGENTS.agents.shared.src.logging import LoggerFactory
from JADE_AI.src.slots import SlotManager

# Get slot
manager = SlotManager()
slot = manager.get_slot(instance="02-instance", slot_id="slot-2")

# Get logger for this slot
logger = LoggerFactory.get_logger(
    agent="jsa-ci",
    instance=slot.instance,
    slot=slot.slot_id,
    log_type="scan"
)

# Logs automatically go to correct slot directory
logger.info("Scan started", extra={"project": slot.project_name})
# Logs to: GP-PROJECTS/02-instance/slot-2/logs/jsa-ci/scan.log
```

### With Workflow State Machine

```python
# Get pending findings
pending_path = manager.get_slot_workflow_path(
    instance="02-instance",
    slot_id="slot-2",
    state="pending"
)

# List pending findings
import json
for finding_file in pending_path.glob("*.json"):
    with open(finding_file) as f:
        finding = json.load(f)
        print(f"Finding {finding['id']}: {finding['severity']}")
```

---

## Files

| File | Purpose | Lines |
|------|---------|-------|
| `models.py` | Data models (Slot, SlotConfig, Instance) | ~280 |
| `manager.py` | SlotManager class | ~350 |
| `context.py` | ContextManager class | ~280 |
| `__init__.py` | Exports | ~40 |
| `README.md` | This file | ~500 |

**Total**: 5 files, ~1,450 lines

---

## Testing

### Manual Test

```bash
cd /home/jimmie/linkops-industries/GP-copilot
python3 -c "
from JADE_AI.src.slots import SlotManager

manager = SlotManager()

# List instances
instances = manager.list_instances()
print(f'Instances: {[i.id for i in instances]}')

# List slots
slots = manager.list_slots(instance='02-instance')
for slot in slots:
    print(f'{slot.slot_id}: {slot.project_name} ({slot.status.value})')

# Get specific slot
slot = manager.get_slot(instance='02-instance', slot_id='slot-2')
if slot:
    print(f'Project: {slot.project_name}')
    print(f'Path: {slot.project_path}')
    print(f'Findings: {slot.findings_count}')
"
```

---

**Status**: ✅ Phase 10.2 Complete
**Next**: Phase 10.3 - JADE Commander Interface
```
