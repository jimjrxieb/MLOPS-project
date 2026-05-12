"""
test_model_behavior.py — Smoke tests for model inference quality.

Requires Ollama running with the model loaded.
Run: python3 -m pytest tests/test_model_behavior.py -v

These are NOT comprehensive eval — see 4-eval-clarify/ for that.
These are fast smoke tests that catch obvious regressions.
"""

import json
import os

import pytest
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELS_TO_TEST = ["jade:v1.0"]  # Add "katie:v2.0" when promoted


def ollama_available():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def generate(model, prompt, max_tokens=300):
    """Call Ollama generate and return response text."""
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"num_predict": max_tokens, "temperature": 0.1}},
        timeout=120,
    )
    r.raise_for_status()
    return r.json().get("response", "")


@pytest.fixture(params=MODELS_TO_TEST)
def model(request):
    if not ollama_available():
        pytest.skip("Ollama not running")
    return request.param


class TestNoHallucination:
    """Model must not fabricate commands, CVEs, or CIS numbers."""

    def test_no_fake_kubectl_flags(self, model):
        response = generate(model, "How do I list pods in all namespaces?")
        # Should contain real flags
        assert "kubectl" in response.lower()
        # Should NOT contain made-up flags
        fake_flags = ["--all-pods", "--list-all", "--show-pods"]
        for flag in fake_flags:
            assert flag not in response, f"Hallucinated flag: {flag}"

    def test_no_fake_cve_numbers(self, model):
        response = generate(model, "What is CVE-2024-21626?")
        # Should not invent CVE numbers that look real but aren't
        # (We check for the pattern CVE-YYYY-NNNNN with clearly wrong years)
        assert "CVE-2099" not in response
        assert "CVE-2000-00000" not in response


class TestCoreKnowledge:
    """Model must demonstrate baseline K8s security knowledge."""

    def test_knows_securitycontext(self, model):
        response = generate(model, "A pod is running as root. How do I fix this?")
        response_lower = response.lower()
        assert any(kw in response_lower for kw in [
            "securitycontext", "runasnonroot", "run_as_non_root", "runas"
        ]), "Should mention securityContext or runAsNonRoot"

    def test_knows_networkpolicy(self, model):
        response = generate(model, "How do I restrict pod-to-pod traffic in Kubernetes?")
        response_lower = response.lower()
        assert any(kw in response_lower for kw in [
            "networkpolicy", "network policy", "calico", "cilium"
        ]), "Should mention NetworkPolicy"

    def test_knows_rbac(self, model):
        response = generate(model, "What is RBAC in Kubernetes?")
        response_lower = response.lower()
        assert any(kw in response_lower for kw in [
            "role", "clusterrole", "rolebinding", "rbac"
        ]), "Should mention Role/ClusterRole/RoleBinding"


class TestResponseQuality:
    """Responses must be actionable, not vague."""

    def test_provides_commands_not_just_advice(self, model):
        response = generate(model, "How do I check if a pod has resource limits set?")
        response_lower = response.lower()
        assert any(cmd in response_lower for cmd in [
            "kubectl get", "kubectl describe", "kubectl edit", "-o json", "-o yaml"
        ]), "Should provide actual kubectl commands, not just advice"

    def test_response_not_empty(self, model):
        response = generate(model, "What is a Kubernetes pod?")
        assert len(response.strip()) > 50, f"Response too short: {len(response)} chars"

    def test_response_not_repetitive(self, model):
        response = generate(model, "Explain pod security standards.")
        # Check for excessive repetition (same sentence repeated 3+ times)
        sentences = [s.strip() for s in response.split(".") if len(s.strip()) > 20]
        if len(sentences) >= 3:
            unique = set(sentences)
            repetition_ratio = 1 - (len(unique) / len(sentences))
            assert repetition_ratio < 0.5, (
                f"Response is {repetition_ratio:.0%} repetitive ({len(sentences)} sentences, {len(unique)} unique)"
            )
