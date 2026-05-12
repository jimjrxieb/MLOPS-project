"""
LLM Providers for JADE

Plug-and-play LLM provider system supporting:
- Ollama (jade:v1.0 fine-tuned model) - Default
- OpenAI (GPT-4, GPT-4 Turbo)
- Anthropic (Claude Haiku, cloud fallback)
- Google Gemini (Gemini Pro, Gemini 1.5 Pro)

Usage:
    >>> from providers import OllamaProvider, get_llm_provider
    >>> # Use specific provider
    >>> provider = OllamaProvider(model_name="jade:v1.0")
    >>> response = provider.generate("How do I drain a node?")

    >>> # Use factory (reads jade_config.yaml)
    >>> from core.llm_provider import get_llm_provider
    >>> provider = get_llm_provider()  # Uses config defaults
    >>> response = provider.generate("Summarize JSA activity")

Environment Variables for Plug-and-Play:
    JADE_PROVIDER=ollama|anthropic|openai|gemini
    JADE_MODEL=jade:v1.0|claude-haiku|gpt-4|gemini-pro
"""

from .base import BaseLLMProvider
from .ollama import OllamaProvider, get_ollama_provider
from .openai import OpenAIProvider, get_openai_provider
from .anthropic import AnthropicProvider, get_anthropic_provider
from .gemini import GeminiProvider, get_gemini_provider

__all__ = [
    # Base interface
    'BaseLLMProvider',

    # Providers
    'OllamaProvider',
    'OpenAIProvider',
    'AnthropicProvider',
    'GeminiProvider',

    # Convenience functions
    'get_ollama_provider',
    'get_openai_provider',
    'get_anthropic_provider',
    'get_gemini_provider',
]
