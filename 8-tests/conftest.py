"""
pytest conftest — shared fixtures and sys.path setup for GP-MODEL-OPS tests.

Makes '10-crewai-mlops' (hyphenated on disk) importable as 'crewai_mlops'
so tests can do: from crewai_mlops.rag_ingestion.collectors import ...
"""
import importlib
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_CREWAI_DIR = _ROOT / "10-crewai-mlops"


def _register_crewai_mlops():
    """Register 10-crewai-mlops directory as importable 'crewai_mlops' package."""
    if "crewai_mlops" in sys.modules:
        return

    spec = importlib.util.spec_from_file_location(
        "crewai_mlops",
        _CREWAI_DIR / "__init__.py",
        submodule_search_locations=[str(_CREWAI_DIR)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["crewai_mlops"] = module
    spec.loader.exec_module(module)

    # Also ensure the 10-crewai-mlops dir is on sys.path so sub-packages resolve
    crewai_dir_str = str(_CREWAI_DIR)
    if crewai_dir_str not in sys.path:
        sys.path.insert(0, crewai_dir_str)


_register_crewai_mlops()
