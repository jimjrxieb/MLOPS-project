"""Pipeline stages"""
from pathlib import Path
import sys

# Import stages with relative imports
try:
    from . import discover
    from . import preprocess
    from . import route
    from . import cleanup
except ImportError:
    # Fallback to direct imports
    sys.path.insert(0, str(Path(__file__).parent))
    import importlib.util

    def load_stage(name, filename):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    discover = load_stage('discover', 'discover.py')
    preprocess = load_stage('preprocess', 'preprocess.py')
    route = load_stage('route', 'route.py')
    cleanup = load_stage('cleanup', 'cleanup.py')
