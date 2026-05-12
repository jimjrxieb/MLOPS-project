"""
Ollama LLM Provider for BERU-AI

HTTP-based inference against an Ollama server.
Default model: beru:v1.4 (LLaMA 3.2-3B fine-tuned, exp-010 champion) — override
with the BERU_MODEL env var or the model_name arg.
Default base URL: localhost:11434 — override with the OLLAMA_HOST env var (so the
same code runs on a laptop and inside docker-compose where ollama is a service).
Falls back to llama3.2:3b base if the fine-tune isn't loaded — see D-009.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import BaseLLMProvider

# Load system prompt from config
_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_system_prompt() -> str:
    prompt_path = _CONFIG_DIR / "system_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text().strip()
    return "You are Beru, a CySA+ certified security analyst."


class OllamaProvider(BaseLLMProvider):
    """
    Ollama-based LLM provider for BERU-AI.

    Uses HTTP API at localhost:11434. Supports model fallback
    and graceful degradation.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        # model precedence: explicit arg > BERU_MODEL env > current champion default.
        resolved_model = model_name or os.environ.get("BERU_MODEL") or "beru:v1.4"
        super().__init__(resolved_model, config)
        # base_url precedence: config arg > OLLAMA_HOST env > localhost default.
        self.base_url = (
            self.config.get("base_url")
            or os.environ.get("OLLAMA_HOST")
            or "http://localhost:11434"
        ).rstrip("/")
        self.fallback_model = self.config.get("fallback_model", "llama3.2:3b")
        self.timeout = self.config.get("timeout", 120)
        self.system_prompt = _load_system_prompt()
        self.available = False
        self.using_fallback = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if Ollama is running and model is loaded."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if self.model_name in models:
                    self.available = True
                elif self.fallback_model and self.fallback_model in models:
                    self.available = True
                    self.using_fallback = True
        except requests.ConnectionError:
            self.available = False

    def _active_model(self) -> str:
        return self.fallback_model if self.using_fallback else self.model_name

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Single-turn generation via /api/generate."""
        payload = {
            "model": self._active_model(),
            "prompt": prompt,
            "system": system_prompt or self.system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Multi-turn chat via /api/chat."""
        # Prepend system prompt if not already present
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        payload = {
            "model": self._active_model(),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    def is_available(self) -> bool:
        self._check_availability()
        return self.available

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model": self._active_model(),
            "primary_model": self.model_name,
            "using_fallback": self.using_fallback,
            "base_url": self.base_url,
            "available": self.available,
        }
