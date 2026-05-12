"""
JADE Version Configuration - Single Source of Truth
====================================================
Import this module to get the current JADE model version.

Usage:
    from JADE-AI.config.version import JADE_MODEL, JADE_FALLBACK
    # or if not in Python path:
    from version import JADE_MODEL

Change versions in jade_config.yaml under the 'version' section.
This file reads from there and exports constants.
"""

import os
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Default values (fallback if config can't be read)
_DEFAULT_MODEL = "jade:v1.0"
_DEFAULT_FALLBACK = "jade:v0.9"  # Ollama fallback if v1.0 unavailable

def _load_from_config() -> tuple[str, str]:
    """Load version from jade_config.yaml"""
    if yaml is None:
        return _DEFAULT_MODEL, _DEFAULT_FALLBACK

    config_path = Path(__file__).parent / "jade_config.yaml"
    if not config_path.exists():
        return _DEFAULT_MODEL, _DEFAULT_FALLBACK

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        version_config = config.get("version", {})
        model = version_config.get("jade_model", _DEFAULT_MODEL)
        fallback = version_config.get("jade_fallback", _DEFAULT_FALLBACK)
        return model, fallback
    except Exception:
        return _DEFAULT_MODEL, _DEFAULT_FALLBACK

# Export constants
JADE_MODEL, JADE_FALLBACK = _load_from_config()

# Also support environment variable override
JADE_MODEL = os.environ.get("JADE_MODEL", JADE_MODEL)

# For convenience - extract version from model string
# Handles both "jade:v1.0" (Ollama) and "claude-haiku-4-5-20251001" (Anthropic) formats
VERSION = JADE_MODEL.split(":")[-1] if ":" in JADE_MODEL else JADE_MODEL

__all__ = ["JADE_MODEL", "JADE_FALLBACK", "VERSION"]

if __name__ == "__main__":
    print(f"JADE Model: {JADE_MODEL}")
    print(f"Fallback:   {JADE_FALLBACK}")
    print(f"Version:    {VERSION}")
