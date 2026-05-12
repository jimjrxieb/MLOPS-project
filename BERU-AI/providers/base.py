"""
Base LLM Provider Interface for BERU-AI

Lean interface — only what BERU needs for inference.
No agentic engine, no chat handler, no intent router.
BERU is an analyst, not a platform operator.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Base class for BERU LLM providers."""

    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Single-turn generation. Returns response text."""
        ...

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Multi-turn chat. Messages in ChatML format. Returns response text."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is reachable and model is loaded."""
        ...

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata (name, version, parameters)."""
        ...
