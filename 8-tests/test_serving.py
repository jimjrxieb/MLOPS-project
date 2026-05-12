"""
test_serving.py — Validates model serving infrastructure.

Run: python3 -m pytest tests/test_serving.py -v
"""

import os
import time

import pytest
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
GP_API_URL = os.environ.get("GP_API_URL", "http://localhost:8000")


def ollama_available():
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).status_code == 200
    except Exception:
        return False


def gp_api_available():
    try:
        return requests.get(f"{GP_API_URL}/api/jade/health", timeout=5).status_code == 200
    except Exception:
        return False


class TestOllamaHealth:
    """Ollama serving infrastructure tests."""

    @pytest.fixture(autouse=True)
    def skip_if_unavailable(self):
        if not ollama_available():
            pytest.skip("Ollama not running")

    def test_ollama_responds(self):
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        assert r.status_code == 200

    def test_model_loaded(self):
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        assert len(models) > 0, "No models loaded in Ollama"

    def test_inference_latency_under_30s(self):
        """3B model should respond in under 30 seconds."""
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if not models:
            pytest.skip("No models loaded")

        start = time.perf_counter()
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": models[0], "prompt": "What is a pod?",
                  "stream": False, "options": {"num_predict": 50}},
            timeout=30,
        )
        elapsed = time.perf_counter() - start
        assert r.status_code == 200
        assert elapsed < 30, f"Inference took {elapsed:.1f}s (threshold: 30s)"


class TestGPAPIHealth:
    """GP-API JADE endpoint tests."""

    @pytest.fixture(autouse=True)
    def skip_if_unavailable(self):
        if not gp_api_available():
            pytest.skip("GP-API not running")

    def test_jade_health_endpoint(self):
        r = requests.get(f"{GP_API_URL}/api/jade/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")

    def test_jade_status_endpoint(self):
        r = requests.get(f"{GP_API_URL}/api/jade/status", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "jade_available" in data
        assert "rag_available" in data

    def test_jade_tracking_endpoint(self):
        r = requests.get(f"{GP_API_URL}/api/jade/tracking", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "tracking_enabled" in data

    def test_jade_ask_returns_response(self):
        r = requests.post(
            f"{GP_API_URL}/api/jade/ask",
            json={"question": "What is a Kubernetes namespace?", "max_tokens": 100},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["answer"]) > 0
        assert data["response_time_ms"] > 0
