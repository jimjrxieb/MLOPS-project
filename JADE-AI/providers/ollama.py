"""
Ollama LLM Provider

Fast, GPU-accelerated inference using local Ollama server.
Default provider for JADE using jade:v1.0 fine-tuned model.

Performance:
- Model load: Instant (Ollama keeps model in memory)
- Inference: <1s (vs 5-10s with PyTorch)
- GPU: Full RTX 5080 acceleration
- Memory: Managed by Ollama
"""

import requests
import json
import time
from typing import Optional, Dict, Any, List, Iterator
from .base import BaseLLMProvider

# MLOps tracking (graceful degradation — inference works without it)
try:
    from ..mlops import get_tracker
    _tracker = get_tracker()
except Exception:
    _tracker = None

# LangChain integration (consistency with JSA)
try:
    from langchain_ollama import OllamaLLM
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class OllamaProvider(BaseLLMProvider):
    """
    Ollama-based LLM provider using HTTP API.

    Features:
    - GPU acceleration (RTX 5080)
    - Instant model loading (background service)
    - Streaming support
    - Model fallback support
    - jade:v1.0 fine-tuned security model

    Example:
        >>> from providers import OllamaProvider
        >>> provider = OllamaProvider(
        ...     model_name="jade:v1.0",
        ...     config={"fallback_model": "jade:v0.8"}
        ... )
        >>> response = provider.generate("How do I drain a Kubernetes node?")
    """

    def __init__(
        self,
        model_name: str = "jade:v1.0",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Ollama provider.

        Args:
            model_name: Primary model to use (e.g., "jade:v1.0", "jade:v0.8")
            config: Configuration with optional keys:
                - base_url: Ollama API endpoint (default: http://localhost:11434)
                - fallback_model: Fallback model if primary fails
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(model_name, config)

        # Load config
        self.base_url = self.config.get('base_url', 'http://localhost:11434').rstrip('/')
        self.fallback_model = self.config.get('fallback_model')
        self.timeout = self.config.get('timeout', 120)

        self.available = False
        self.using_fallback = False
        self._langchain_llm = None  # LangChain OllamaLLM instance

        # Test connectivity and model availability
        self._check_availability()

        # Initialize LangChain LLM if available (consistency with JSA)
        if LANGCHAIN_AVAILABLE and self.available:
            try:
                self._langchain_llm = OllamaLLM(
                    model=self.model_name,
                    base_url=self.base_url,
                    temperature=0.7
                )
            except Exception as e:
                print(f"⚠️  LangChain init failed, using HTTP fallback: {e}")
                self._langchain_llm = None

    def _check_availability(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()

            # Check if model exists
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]

            # Check primary model
            if self.model_name in model_names:
                self.available = True
                self.using_fallback = False
                print(f"✅ Ollama connected: {self.model_name}")
                return True

            # Check fallback model if primary not found
            if self.fallback_model and self.fallback_model in model_names:
                print(f"⚠️  Primary model {self.model_name} not found")
                print(f"✅ Using fallback: {self.fallback_model}")
                self.model_name = self.fallback_model
                self.available = True
                self.using_fallback = True
                return True

            # Neither primary nor fallback available
            print(f"❌ Model {self.model_name} not found in Ollama")
            if self.fallback_model:
                print(f"❌ Fallback {self.fallback_model} also not found")
            print(f"   Available models: {', '.join(model_names)}")
            print(f"   Run: ollama pull {self.model_name}")
            return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Ollama not available: {e}")
            print("   Start Ollama: ollama serve")
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text from prompt using Ollama.

        Args:
            prompt: User prompt or question
            system_prompt: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: 0.0 (factual) to 1.0 (creative)
            **kwargs: Additional Ollama options

        Returns:
            Generated text response
        """
        if not self.available:
            return "❌ Ollama not available. Run: ollama serve"

        start_time = time.perf_counter()
        response_text = ""
        success = True
        error_msg = ""

        # Use LangChain if available (consistency with JSA)
        if self._langchain_llm:
            try:
                # Combine system prompt and user prompt for LangChain
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response_text = self._langchain_llm.invoke(full_prompt)
                self._log_inference("generate", prompt, response_text, start_time,
                                    temperature=temperature, max_tokens=max_tokens)
                return response_text
            except Exception as e:
                # Fall back to HTTP on LangChain error
                print(f"⚠️  LangChain invoke failed, using HTTP: {e}")

        # HTTP fallback (if LangChain fails or not available)
        try:
            # Build request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt

            # Add any additional options
            if kwargs:
                payload["options"].update(kwargs)

            # Make request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            result = response.json()
            response_text = result.get('response', '')
            self._log_inference("generate", prompt, response_text, start_time,
                                temperature=temperature, max_tokens=max_tokens)
            return response_text

        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {self.timeout}s"
            self._log_inference("generate", prompt, "", start_time,
                                success=False, error=error_msg)
            return f"❌ {error_msg}"
        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama request failed: {e}"
            self._log_inference("generate", prompt, "", start_time,
                                success=False, error=error_msg)
            return f"❌ {error_msg}"
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Ollama response: {e}"
            self._log_inference("generate", prompt, "", start_time,
                                success=False, error=error_msg)
            return f"❌ {error_msg}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Multi-turn chat with conversation history.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Maximum tokens to generate
            temperature: Creativity level
            **kwargs: Additional Ollama options

        Returns:
            Assistant's response
        """
        if not self.available:
            return "❌ Ollama not available"

        start_time = time.perf_counter()
        # Estimate prompt size from all messages
        prompt_text = " ".join(m.get("content", "") for m in messages)

        try:
            # Build request payload using Ollama's chat endpoint
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }

            # Add any additional options
            if kwargs:
                payload["options"].update(kwargs)

            # Make request to chat endpoint
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            result = response.json()
            response_text = ""
            if 'message' in result and 'content' in result['message']:
                response_text = result['message']['content']

            self._log_inference("chat", prompt_text, response_text, start_time,
                                temperature=temperature, max_tokens=max_tokens)
            return response_text

        except requests.exceptions.Timeout:
            error_msg = f"Chat timed out after {self.timeout}s"
            self._log_inference("chat", prompt_text, "", start_time,
                                success=False, error=error_msg)
            return f"❌ {error_msg}"
        except requests.exceptions.RequestException as e:
            error_msg = f"Chat request failed: {e}"
            self._log_inference("chat", prompt_text, "", start_time,
                                success=False, error=error_msg)
            return f"❌ {error_msg}"
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse chat response: {e}"
            self._log_inference("chat", prompt_text, "", start_time,
                                success=False, error=error_msg)
            return f"❌ {error_msg}"

    def _log_inference(
        self,
        method: str,
        prompt: str,
        response: str,
        start_time: float,
        success: bool = True,
        error: str = "",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """Log inference metrics to MLflow tracker."""
        if _tracker is None:
            return
        try:
            from ..mlops.inference_tracker import InferenceMetrics
            _tracker.log_inference(InferenceMetrics(
                model=self.model_name,
                provider="ollama",
                method=method,
                prompt_chars=len(prompt),
                response_chars=len(response),
                latency_ms=(time.perf_counter() - start_time) * 1000,
                llm_latency_ms=(time.perf_counter() - start_time) * 1000,
                success=success,
                error=error,
                temperature=temperature,
                max_tokens=max_tokens,
                using_fallback=self.using_fallback,
            ))
        except Exception:
            pass  # Never break inference for tracking

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[Iterator[str]]:
        """
        Stream text generation with Ollama.

        Args:
            prompt: User prompt
            system_prompt: Optional system message
            max_tokens: Maximum tokens
            temperature: Creativity level
            **kwargs: Additional Ollama options

        Returns:
            Iterator yielding text chunks

        Example:
            >>> stream = provider.stream("Explain Kubernetes pods")
            >>> for chunk in stream:
            ...     print(chunk, end='', flush=True)
        """
        if not self.available:
            return None

        try:
            # Build request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt

            # Add any additional options
            if kwargs:
                payload["options"].update(kwargs)

            # Make streaming request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()

            # Yield chunks
            def generate_chunks():
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            yield chunk['response']

            return generate_chunks()

        except Exception as e:
            print(f"❌ Streaming failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Ollama is ready"""
        return self.available

    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information"""
        return {
            "provider": "ollama",
            "model": self.model_name,
            "available": self.available,
            "using_fallback": self.using_fallback,
            "fallback_model": self.fallback_model,
            "base_url": self.base_url,
            "backend": "Ollama",
            "gpu_accelerated": True,
            "inference_speed": "<1s (typical)",
            "model_load_time": "Instant (background service)",
        }

    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different Ollama model.

        Args:
            model_name: Model to switch to (e.g., "llama3.1:70b-instruct")

        Returns:
            True if switch successful
        """
        old_model = self.model_name
        self.model_name = model_name

        if self._check_availability():
            print(f"✅ Switched from {old_model} to {model_name}")
            return True
        else:
            # Revert if new model not available
            self.model_name = old_model
            print(f"⚠️  Reverted to {old_model}")
            return False


# ============================================================
# CONVENIENCE FUNCTION FOR BACKWARD COMPATIBILITY
# ============================================================
def get_ollama_provider(
    model_name: str = "jade:v1.0",
    fallback_model: Optional[str] = "jade:v0.8",
    base_url: str = "http://localhost:11434"
) -> OllamaProvider:
    """
    Get Ollama provider instance.

    Args:
        model_name: Primary model to use (default: jade:v1.0)
        fallback_model: Fallback model if primary unavailable (default: jade:v0.8)
        base_url: Ollama API endpoint

    Returns:
        OllamaProvider instance

    Example:
        >>> provider = get_ollama_provider(
        ...     model_name="jade:v1.0",
        ...     fallback_model="jade:v0.8"
        ... )
    """
    config = {
        'base_url': base_url,
        'fallback_model': fallback_model
    }
    return OllamaProvider(model_name=model_name, config=config)
