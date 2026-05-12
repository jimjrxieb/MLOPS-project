"""
JADE-AI Core Module
Central brain of JADE - LLM, RAG, memory, and agentic engine

Components:
- agentic_engine: Claude Code style tool use and reasoning
- llm_provider: LLM provider factory (Anthropic, Ollama, OpenAI, Gemini)
- rag_engine/raggraph_engine: Vector search and retrieval
- memory_manager: Conversation state persistence
- context: Slot and project context
- manager: Slot management
- models: Data models
- paths: Centralized path configuration
- jade_logger: Evidence logging
- secrets_manager: Secrets handling
- log_brain: Central log-agnostic intelligence (Tony Stark's sensor fusion)
"""

from .models import (
    Slot,
    SlotConfig,
    SlotStatus,
    Instance,
    ComplianceFramework,
)
from .manager import SlotManager
from .context import ContextManager
from .paths import (
    GP_ROOT,
    GP_CHROMA_PATH,
    GP_LOGS_PATH,
    GP_DATA_PATH,
    GP_MEMORY_PATH,
    GP_CONSULTING_PATH,
    GP_PROJECTS_PATH,
)
from .log_brain import (
    LogBrain,
    get_log_brain,
    NormalizedEvent,
    EventSeverity,
    EventCategory,
    SourceType,
    # Normalizers for custom usage
    TrivyNormalizer,
    CheckovNormalizer,
    SemgrepNormalizer,
    BanditNormalizer,
    GitleaksNormalizer,
    GrypeNormalizer,
    KubernetesPodLogNormalizer,
    GitHubActionsNormalizer,
    AWSGuardDutyNormalizer,
    AWSCloudWatchNormalizer,
    JSAAgentNormalizer,
)

__all__ = [
    # Models
    "Slot",
    "SlotConfig",
    "SlotStatus",
    "Instance",
    "ComplianceFramework",

    # Managers
    "SlotManager",
    "ContextManager",

    # Paths
    "GP_ROOT",
    "GP_CHROMA_PATH",
    "GP_LOGS_PATH",
    "GP_DATA_PATH",
    "GP_MEMORY_PATH",
    "GP_CONSULTING_PATH",
    "GP_PROJECTS_PATH",

    # LogBrain - Central Log-Agnostic Intelligence
    "LogBrain",
    "get_log_brain",
    "NormalizedEvent",
    "EventSeverity",
    "EventCategory",
    "SourceType",

    # Normalizers
    "TrivyNormalizer",
    "CheckovNormalizer",
    "SemgrepNormalizer",
    "BanditNormalizer",
    "GitleaksNormalizer",
    "GrypeNormalizer",
    "KubernetesPodLogNormalizer",
    "GitHubActionsNormalizer",
    "AWSGuardDutyNormalizer",
    "AWSCloudWatchNormalizer",
    "JSAAgentNormalizer",
]

__version__ = "2.0.0"
