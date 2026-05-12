"""
Google Gemini LLM Provider

Cloud-based LLM provider using Google's Generative AI API.
Supports Gemini Pro and Gemini Pro Vision models.

Requirements:
    pip install google-generativeai

Usage:
    export GOOGLE_API_KEY=...
    provider = GeminiProvider(model_name="gemini-pro")
"""

import os
from typing import Optional, Dict, Any, List, Iterator
from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini API provider for JADE.

    Supports:
    - Gemini Pro (gemini-pro)
    - Gemini Pro Vision (gemini-pro-vision)
    - Gemini 1.5 Pro (gemini-1.5-pro)

    Example:
        >>> from providers import GeminiProvider
        >>> provider = GeminiProvider(
        ...     model_name="gemini-pro",
        ...     config={"api_key": "..."}
        ... )
        >>> response = provider.generate("How do I drain a Kubernetes node?")
    """

    def __init__(
        self,
        model_name: str = "gemini-pro",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Gemini provider.

        Args:
            model_name: Gemini model (e.g., "gemini-pro", "gemini-1.5-pro")
            config: Configuration with optional keys:
                - api_key: Google API key (or use GOOGLE_API_KEY env var)
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(model_name, config)

        # Get API key from config or environment
        self.api_key = self.config.get('api_key') or os.getenv('GOOGLE_API_KEY')
        self.timeout = self.config.get('timeout', 120)

        self.model = None
        self.available = False

        # Try to import and initialize Gemini client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gemini client"""
        try:
            import google.generativeai as genai

            if not self.api_key:
                print("❌ Google API key not found")
                print("   Set GOOGLE_API_KEY environment variable or pass api_key in config")
                return

            # Configure the API
            genai.configure(api_key=self.api_key)

            # Initialize model
            self.model = genai.GenerativeModel(self.model_name)
            self.available = True
            print(f"✅ Gemini connected: {self.model_name}")

        except ImportError:
            print("❌ google-generativeai not installed")
            print("   Install: pip install google-generativeai")
        except Exception as e:
            print(f"❌ Gemini initialization failed: {e}")

    def is_available(self) -> bool:
        """Check if Gemini is available"""
        return self.available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate response using Gemini.

        Args:
            prompt: User prompt
            system_prompt: System instructions (prepended to prompt)
            max_tokens: Maximum response tokens
            temperature: Creativity (0.0-1.0)

        Returns:
            Generated text response
        """
        if not self.available:
            return "Error: Gemini not available"

        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate response
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )

            return response.text

        except Exception as e:
            return f"Error generating response: {e}"

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream response using Gemini.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            max_tokens: Maximum response tokens
            temperature: Creativity (0.0-1.0)

        Yields:
            Response chunks
        """
        if not self.available:
            yield "Error: Gemini not available"
            return

        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate streaming response
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"Error: {e}"

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "gemini",
            "model": self.model_name,
            "available": self.available,
            "api_key_set": bool(self.api_key),
        }


def get_gemini_provider(
    model_name: str = "gemini-pro",
    config: Optional[Dict[str, Any]] = None
) -> GeminiProvider:
    """
    Factory function to create Gemini provider.

    Args:
        model_name: Model to use
        config: Optional configuration

    Returns:
        GeminiProvider instance
    """
    return GeminiProvider(model_name=model_name, config=config)
