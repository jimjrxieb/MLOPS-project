"""
Anthropic LLM Provider

Cloud-based LLM provider using Anthropic Claude API.
Supports Claude Opus, Sonnet, and Haiku models.

Requirements:
    pip install anthropic

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    provider = AnthropicProvider(model_name="claude-sonnet-4-5")
"""

import os
from typing import Optional, Dict, Any, List, Iterator
from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude API provider for JADE.

    Supports:
    - Claude Opus 4.5 (claude-opus-4-5)
    - Claude Sonnet 4.5 (claude-sonnet-4-5)
    - Claude Haiku 3.5 (claude-3-5-haiku-20241022)

    Example:
        >>> from providers import AnthropicProvider
        >>> provider = AnthropicProvider(
        ...     model_name="claude-sonnet-4-5",
        ...     config={"api_key": "sk-ant-..."}
        ... )
        >>> response = provider.generate("How do I drain a Kubernetes node?")
    """

    def __init__(
        self,
        model_name: str = "claude-haiku-4-5-20251001",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Anthropic provider (cloud fallback).

        Args:
            model_name: Claude model (e.g., "claude-haiku-4-5-20251001", "claude-sonnet-4-5")
            config: Configuration with optional keys:
                - api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
                - api_base: Custom API base URL
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(model_name, config)

        # Get API key from config or environment
        self.api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        self.api_base = self.config.get('api_base')
        self.timeout = self.config.get('timeout', 120)

        self.client = None
        self.available = False

        # Try to import and initialize Anthropic client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic

            if not self.api_key:
                print("❌ Anthropic API key not found")
                print("   Set ANTHROPIC_API_KEY environment variable or pass api_key in config")
                return

            # Initialize client
            client_kwargs = {"api_key": self.api_key}
            if self.api_base:
                client_kwargs["base_url"] = self.api_base

            self.client = Anthropic(**client_kwargs)
            self.available = True
            print(f"✅ Anthropic connected: {self.model_name}")

        except ImportError:
            print("❌ Anthropic library not installed")
            print("   Install: pip install anthropic")
        except Exception as e:
            print(f"❌ Anthropic initialization failed: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text using Anthropic Claude API.

        Args:
            prompt: User prompt or question
            system_prompt: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: 0.0 (factual) to 1.0 (creative)
            **kwargs: Additional Anthropic parameters

        Returns:
            Generated text response
        """
        if not self.available or not self.client:
            return "❌ Anthropic not available. Check API key and installation."

        try:
            # Build request kwargs
            request_kwargs = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }

            # Add system prompt if provided
            if system_prompt:
                request_kwargs["system"] = system_prompt

            # Add any additional parameters
            request_kwargs.update(kwargs)

            # Make API call
            response = self.client.messages.create(**request_kwargs)

            # Extract response
            return response.content[0].text

        except Exception as e:
            return f"❌ Anthropic request failed: {e}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Multi-turn chat using Anthropic Claude API.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Maximum tokens to generate
            temperature: Creativity level
            **kwargs: Additional Anthropic parameters

        Returns:
            Assistant's response
        """
        if not self.available or not self.client:
            return "❌ Anthropic not available"

        try:
            # Separate system message from conversation
            system_message = None
            conversation_messages = []

            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    conversation_messages.append(msg)

            # Build request kwargs
            request_kwargs = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": conversation_messages
            }

            # Add system prompt if found
            if system_message:
                request_kwargs["system"] = system_message

            # Add any additional parameters
            request_kwargs.update(kwargs)

            # Make API call
            response = self.client.messages.create(**request_kwargs)

            # Extract response
            return response.content[0].text

        except Exception as e:
            return f"❌ Anthropic chat failed: {e}"

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[Iterator[str]]:
        """
        Stream text generation using Anthropic Claude API.

        Args:
            prompt: User prompt
            system_prompt: Optional system message
            max_tokens: Maximum tokens
            temperature: Creativity level
            **kwargs: Additional Anthropic parameters

        Returns:
            Iterator yielding text chunks
        """
        if not self.available or not self.client:
            return None

        try:
            # Build request kwargs
            request_kwargs = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }

            # Add system prompt if provided
            if system_prompt:
                request_kwargs["system"] = system_prompt

            # Add any additional parameters
            request_kwargs.update(kwargs)

            # Make streaming API call
            stream = self.client.messages.stream(**request_kwargs)

            # Yield chunks
            def generate_chunks():
                with stream as s:
                    for text in s.text_stream:
                        yield text

            return generate_chunks()

        except Exception as e:
            print(f"❌ Anthropic streaming failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Anthropic is ready"""
        return self.available and self.client is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information"""
        return {
            "provider": "anthropic",
            "model": self.model_name,
            "available": self.available,
            "api_base": self.api_base or "https://api.anthropic.com",
            "backend": "Anthropic Cloud",
            "streaming_supported": True,
        }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================
def get_anthropic_provider(
    model_name: str = "claude-haiku-4-5-20251001",
    api_key: Optional[str] = None
) -> AnthropicProvider:
    """
    Get Anthropic provider instance.

    Args:
        model_name: Claude model (default: claude-haiku-4-5-20251001)
        api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)

    Returns:
        AnthropicProvider instance

    Example:
        >>> provider = get_anthropic_provider(
        ...     model_name="claude-opus-4-5",
        ...     api_key="sk-ant-..."
        ... )
    """
    config = {}
    if api_key:
        config['api_key'] = api_key

    return AnthropicProvider(model_name=model_name, config=config)
