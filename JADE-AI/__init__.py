"""
GP-AI: Intelligent Security Analysis Engine
Central AI system for GP-Copilot with Jade integration
"""

# Import main components for backward compatibility
from .engines.ai_security_engine import AISecurityEngine, ai_security_engine
from .engines.rag_engine import RAGEngine, rag_engine
from .engines.security_reasoning import SecurityReasoningEngine
from .integrations.scan_results_integrator import ScanResultsIntegrator, scan_integrator
from .models.model_manager import ModelManager, model_manager
from .models.gpu_config import gpu_config

# Version info
__version__ = "2.0.0"
__author__ = "GuidePoint Security"

# Export main classes
__all__ = [
    'AISecurityEngine',
    'RAGEngine',
    'SecurityReasoningEngine',
    'ScanResultsIntegrator',
    'ModelManager',
    'ai_security_engine',
    'rag_engine',
    'scan_integrator',
    'model_manager',
    'gpu_config'
]