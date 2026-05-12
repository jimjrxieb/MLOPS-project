"""
OpenAI LLM Provider

Cloud-based LLM provider using OpenAI API.
Supports GPT-4, GPT-4 Turbo, and GPT-3.5 models.

Requirements:
    pip install openai

Usage:
    export OPENAI_API_KEY=sk-...
    provider = OpenAIProvider(model_name="gpt-4-turbo-preview")
"""

import os
from typing import Optional, Dict, Any, List, Iterator
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider for JADE.

    Supports:
    - GPT-4 Turbo (gpt-4-turbo-preview)
    - GPT-4 (gpt-4)
    - GPT-3.5 Turbo (gpt-3.5-turbo)

    Example:
        >>> from providers import OpenAIProvider
        >>> provider = OpenAIProvider(
        ...     model_name="gpt-4-turbo-preview",
        ...     config={"api_key": "sk-..."}
        ... )
        >>> response = provider.generate("How do I drain a Kubernetes node?")
    """

    def __init__(
        self,
        model_name: str = "gpt-4-turbo-preview",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize OpenAI provider.

        Args:
            model_name: OpenAI model (e.g., "gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo")
            config: Configuration with optional keys:
                - api_key: OpenAI API key (or use OPENAI_API_KEY env var)
                - api_base: Custom API base URL
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(model_name, config)

        # Get API key from config or environment
        self.api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        self.api_base = self.config.get('api_base')
        self.timeout = self.config.get('timeout', 120)

        self.client = None
        self.available = False

        # Try to import and initialize OpenAI client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI

            if not self.api_key:
                print("❌ OpenAI API key not found")
                print("   Set OPENAI_API_KEY environment variable or pass api_key in config")
                return

            # Initialize client
            client_kwargs = {"api_key": self.api_key}
            if self.api_base:
                client_kwargs["base_url"] = self.api_base

            self.client = OpenAI(**client_kwargs)
            self.available = True
            print(f"✅ OpenAI connected: {self.model_name}")

        except ImportError:
            print("❌ OpenAI library not installed")
            print("   Install: pip install openai")
        except Exception as e:
            print(f"❌ OpenAI initialization failed: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: User prompt or question
            system_prompt: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: 0.0 (factual) to 1.0 (creative)
            **kwargs: Additional OpenAI parameters

        Returns:
            Generated text response
        """
        if not self.available or not self.client:
            return "❌ OpenAI not available. Check API key and installation."

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Make API call
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout,
                **kwargs
            )

            # Extract response
            return response.choices[0].message.content

        except Exception as e:
            return f"❌ OpenAI request failed: {e}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Multi-turn chat using OpenAI API.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Maximum tokens to generate
            temperature: Creativity level
            **kwargs: Additional OpenAI parameters

        Returns:
            Assistant's response
        """
        if not self.available or not self.client:
            return "❌ OpenAI not available"

        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout,
                **kwargs
            )

            # Extract response
            return response.choices[0].message.content

        except Exception as e:
            return f"❌ OpenAI chat failed: {e}"

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[Iterator[str]]:
        """
        Stream text generation using OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: Optional system message
            max_tokens: Maximum tokens
            temperature: Creativity level
            **kwargs: Additional OpenAI parameters

        Returns:
            Iterator yielding text chunks
        """
        if not self.available or not self.client:
            return None

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Make streaming API call
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=self.timeout,
                **kwargs
            )

            # Yield chunks
            def generate_chunks():
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            return generate_chunks()

        except Exception as e:
            print(f"❌ OpenAI streaming failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if OpenAI is ready"""
        return self.available and self.client is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "openai",
            "model": self.model_name,
            "available": self.available,
            "api_base": self.api_base or "https://api.openai.com/v1",
            "backend": "OpenAI Cloud",
            "streaming_supported": True,
        }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================
def get_openai_provider(
    model_name: str = "gpt-4-turbo-preview",
    api_key: Optional[str] = None
) -> OpenAIProvider:
    """
    Get OpenAI provider instance.

    Args:
        model_name: OpenAI model (default: gpt-4-turbo-preview)
        api_key: OpenAI API key (or use OPENAI_API_KEY env var)

    Returns:
        OpenAIProvider instance

    Example:
        >>> provider = get_openai_provider(
        ...     model_name="gpt-4",
        ...     api_key="sk-..."
        ... )
    """
    config = {}
    if api_key:
        config['api_key'] = api_key

    return OpenAIProvider(model_name=model_name, config=config)
