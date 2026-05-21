"""
config_loader.py — LLM-agnostic configuration for all BERU crews.

Priority order for LLM config:
  1. llm-config.yaml (in same dir as this file)
  2. Environment variables (CREWAI_LLM, OLLAMA_BASE_URL, *_API_KEY)
  3. Defaults (ollama/llama3.2)

API key handling:
  - ollama: never needed
  - cloud providers: reads from api_key field, then env var, then prompts interactively
"""

import os
import sys
import getpass
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent / "llm-config.yaml"
_LOADED_CONFIG = None


def _load_config() -> dict:
    global _LOADED_CONFIG
    if _LOADED_CONFIG is not None:
        return _LOADED_CONFIG
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            _LOADED_CONFIG = yaml.safe_load(f) or {}
    else:
        _LOADED_CONFIG = {}
    return _LOADED_CONFIG


def _get_api_key(provider: str, key_from_config: str) -> str:
    """Return API key: config file -> env var -> interactive prompt."""
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
    }
    if key_from_config:
        return key_from_config
    env_var = env_map.get(provider)
    if env_var and os.getenv(env_var):
        return os.getenv(env_var)
    # Interactive prompt -- only fires when running a crew, not on import
    print(f"\n[beru config] No API key found for provider '{provider}'.")
    print(f"  Set it in llm-config.yaml, or export {env_var}.")
    try:
        key = getpass.getpass(f"  Enter {provider} API key (or Ctrl+C to cancel): ").strip()
        if not key:
            print("  No key provided. Crew will likely fail at LLM calls.")
        return key
    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.")
        sys.exit(1)


def make_llm():
    """Build and return a crewai LLM object from llm-config.yaml or env vars."""
    from crewai import LLM

    cfg = _load_config()
    llm_cfg = cfg.get("llm", {})

    provider = llm_cfg.get("provider") or os.getenv("CREWAI_PROVIDER", "ollama")
    model = llm_cfg.get("model") or os.getenv("CREWAI_LLM", "llama3.2")
    base_url = llm_cfg.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    raw_key = llm_cfg.get("api_key", "")
    azure_endpoint = llm_cfg.get("azure_endpoint", "")

    if provider == "ollama":
        # crewai expects "ollama/model-name" format
        full_model = f"ollama/{model}" if not model.startswith("ollama/") else model
        return LLM(model=full_model, base_url=base_url)

    elif provider == "openai":
        api_key = _get_api_key("openai", raw_key)
        return LLM(model=model, api_key=api_key)

    elif provider == "anthropic":
        api_key = _get_api_key("anthropic", raw_key)
        return LLM(model=model, api_key=api_key)

    elif provider == "gemini":
        api_key = _get_api_key("gemini", raw_key)
        full_model = model if model.startswith("gemini/") else f"gemini/{model}"
        return LLM(model=full_model, api_key=api_key)

    elif provider == "azure":
        api_key = _get_api_key("azure", raw_key)
        return LLM(
            model=model,
            api_key=api_key,
            base_url=azure_endpoint or base_url,
        )

    else:
        print(f"[beru config] Unknown provider '{provider}', falling back to ollama/llama3.2")
        return LLM(model="ollama/llama3.2", base_url="http://localhost:11434")


def get_engagement_config() -> dict:
    """Return engagement-level config (system name, cluster, region, etc.)."""
    cfg = _load_config()
    eng = cfg.get("engagement", {})
    # Auto-detect cluster from kubectl context if not set
    cluster = eng.get("cluster", "")
    if not cluster:
        try:
            import subprocess
            result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True, text=True, timeout=5,
            )
            cluster = result.stdout.strip() if result.returncode == 0 else "unknown-cluster"
        except Exception:
            cluster = "unknown-cluster"
    return {
        "system_name": eng.get("system_name", "Target System"),
        "cluster": cluster,
        "aws_region": eng.get("aws_region", "us-east-1"),
        "analyst": eng.get("analyst", "beru:v1.6"),
        "output_dir": eng.get("output_dir", ""),
    }
