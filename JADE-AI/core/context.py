"""
Context Manager for GP-Copilot Platform

Manages slot-specific context files (architecture.md, tech-stack.md, compliance.md).
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from .models import Slot


class ContextManager:
    """
    Manages slot-specific context.

    Context provides additional information about the target project:
    - architecture.md: System architecture, components, dependencies
    - tech-stack.md: Technologies used (languages, frameworks, tools)
    - compliance.md: Compliance requirements and mappings

    Usage:
        context_mgr = ContextManager(slot)

        # Load all context
        context = context_mgr.load_all()

        # Load specific context
        arch = context_mgr.load("architecture")

        # Save context
        context_mgr.save("tech-stack", "## Tech Stack\n\n- Python 3.11\n- Flask\n- PostgreSQL")

        # Update context
        context_mgr.update("compliance", additional_content)
    """

    # Standard context file names
    CONTEXT_FILES = {
        "architecture": "architecture.md",
        "tech-stack": "tech-stack.md",
        "compliance": "compliance.md",
    }

    def __init__(self, slot: Slot):
        """
        Initialize ContextManager for a slot.

        Args:
            slot: Slot object
        """
        self.slot = slot
        self.context_path = slot.context_path

        # Ensure context directory exists
        self.context_path.mkdir(parents=True, exist_ok=True)

    def load(self, context_type: str) -> Optional[str]:
        """
        Load specific context file.

        Args:
            context_type: Type of context (architecture, tech-stack, compliance)

        Returns:
            Context content as string, or None if not found

        Example:
            >>> context_mgr = ContextManager(slot)
            >>> arch = context_mgr.load("architecture")
            >>> print(arch)
            ## Architecture
            ...
        """
        filename = self.CONTEXT_FILES.get(context_type)

        if not filename:
            return None

        filepath = self.context_path / filename

        if not filepath.exists():
            return None

        try:
            return filepath.read_text(encoding="utf-8")
        except Exception:
            return None

    def save(self, context_type: str, content: str) -> bool:
        """
        Save context file.

        Args:
            context_type: Type of context
            content: Markdown content to save

        Returns:
            True if saved successfully

        Example:
            >>> context_mgr.save("tech-stack", "## Tech Stack\n\n- Python\n- Flask")
            True
        """
        filename = self.CONTEXT_FILES.get(context_type)

        if not filename:
            return False

        filepath = self.context_path / filename

        try:
            filepath.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def update(self, context_type: str, additional_content: str) -> bool:
        """
        Append to existing context file.

        Args:
            context_type: Type of context
            additional_content: Content to append

        Returns:
            True if updated successfully

        Example:
            >>> context_mgr.update("compliance", "\n\n## PCI-DSS\n\n- Requirement 6.2: ...")
            True
        """
        existing = self.load(context_type) or ""
        new_content = existing + "\n\n" + additional_content
        return self.save(context_type, new_content)

    def load_all(self) -> Dict[str, str]:
        """
        Load all context files.

        Returns:
            Dictionary of {context_type: content}

        Example:
            >>> context = context_mgr.load_all()
            >>> context
            {
                "architecture": "## Architecture\n...",
                "tech-stack": "## Tech Stack\n...",
                "compliance": "## Compliance\n..."
            }
        """
        context = {}

        for context_type in self.CONTEXT_FILES.keys():
            content = self.load(context_type)
            if content:
                context[context_type] = content

        return context

    def exists(self, context_type: str) -> bool:
        """
        Check if context file exists.

        Args:
            context_type: Type of context

        Returns:
            True if file exists
        """
        filename = self.CONTEXT_FILES.get(context_type)

        if not filename:
            return False

        filepath = self.context_path / filename

        return filepath.exists()

    def delete(self, context_type: str) -> bool:
        """
        Delete context file.

        Args:
            context_type: Type of context

        Returns:
            True if deleted successfully
        """
        filename = self.CONTEXT_FILES.get(context_type)

        if not filename:
            return False

        filepath = self.context_path / filename

        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            return True
        except Exception:
            return False

    def list_files(self) -> List[str]:
        """
        List all context files that exist.

        Returns:
            List of context types

        Example:
            >>> context_mgr.list_files()
            ['architecture', 'tech-stack']
        """
        existing = []

        for context_type in self.CONTEXT_FILES.keys():
            if self.exists(context_type):
                existing.append(context_type)

        return existing

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for API responses.

        Returns:
            Dictionary with context metadata and content

        Example:
            >>> context_mgr.to_dict()
            {
                "slot": "slot-2",
                "instance": "02-instance",
                "files": ["architecture", "tech-stack"],
                "content": {
                    "architecture": "...",
                    "tech-stack": "..."
                }
            }
        """
        return {
            "slot": self.slot.slot_id,
            "instance": self.slot.instance,
            "files": self.list_files(),
            "content": self.load_all(),
        }

    # Helper methods for creating standard context files

    def create_architecture_template(self) -> bool:
        """
        Create architecture.md template.

        Returns:
            True if created successfully
        """
        template = f"""# {self.slot.project_name} - Architecture

## Overview

[Brief description of the system architecture]

## Components

### Frontend
- [Component 1]
- [Component 2]

### Backend
- [Component 1]
- [Component 2]

### Data Layer
- [Database 1]
- [Database 2]

## Dependencies

### External Services
- [Service 1]
- [Service 2]

### Third-Party Libraries
- [Library 1]
- [Library 2]

## Deployment

- **Environment**: [Production/Staging/Development]
- **Platform**: [Kubernetes/EC2/Lambda]
- **CI/CD**: [GitHub Actions/GitLab CI/Jenkins]

## Security Considerations

- [Security note 1]
- [Security note 2]
"""
        return self.save("architecture", template)

    def create_techstack_template(self) -> bool:
        """
        Create tech-stack.md template.

        Returns:
            True if created successfully
        """
        template = f"""# {self.slot.project_name} - Tech Stack

## Languages

- [Language 1] (version)
- [Language 2] (version)

## Frameworks

- [Framework 1] (version)
- [Framework 2] (version)

## Build Tools

- [Tool 1]
- [Tool 2]

## Testing

- [Testing framework 1]
- [Testing framework 2]

## Infrastructure

- **Container Runtime**: [Docker/containerd]
- **Orchestration**: [Kubernetes/ECS/Docker Swarm]
- **IaC**: [Terraform/CloudFormation/Pulumi]

## Monitoring & Observability

- **Metrics**: [Prometheus/CloudWatch]
- **Logging**: [ELK/Loki/CloudWatch Logs]
- **Tracing**: [Jaeger/X-Ray]
"""
        return self.save("tech-stack", template)

    def create_compliance_template(self, frameworks: List[str]) -> bool:
        """
        Create compliance.md template.

        Args:
            frameworks: List of compliance frameworks (CIS, NIST, SOC2, etc.)

        Returns:
            True if created successfully
        """
        framework_sections = []

        for framework in frameworks:
            framework_sections.append(f"""## {framework.upper()}

### Requirements

- [Requirement 1]
- [Requirement 2]

### Implementation Status

- ✅ [Control 1]: Implemented
- ⏳ [Control 2]: In Progress
- ❌ [Control 3]: Not Implemented

### Evidence

- [Evidence location 1]
- [Evidence location 2]
""")

        template = f"""# {self.slot.project_name} - Compliance

## Overview

This document tracks compliance requirements and their implementation status.

## Frameworks

{', '.join([f.upper() for f in frameworks])}

{"".join(framework_sections)}

## Audit History

| Date | Auditor | Framework | Result |
|------|---------|-----------|--------|
| YYYY-MM-DD | [Auditor] | [Framework] | [Pass/Fail] |
"""
        return self.save("compliance", template)
