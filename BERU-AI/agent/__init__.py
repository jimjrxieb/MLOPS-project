"""BERU agent — LangGraph orchestrator that wires the fine-tuned brain to playbooks.

The package directory (BERU-AI) contains a hyphen and cannot be a Python module name,
so we add it to sys.path on import. This lets nodes.py import sibling packages
(providers/, core/, tools/) as top-level names.
"""
import sys as _sys
from pathlib import Path as _Path

_BERU_AI_ROOT = _Path(__file__).resolve().parent.parent
if str(_BERU_AI_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_BERU_AI_ROOT))

from .graph import build_graph, run_audit, run_ssp_grading, run_ciso_briefing  # noqa: E402
from .state import BERUState  # noqa: E402

__all__ = ["build_graph", "run_audit", "run_ssp_grading", "run_ciso_briefing", "BERUState"]
