"""
MLOps instrumentation for JADE inference pipeline.

Tracks model performance, latency, and usage via MLflow.
Degrades gracefully — if MLflow is unavailable, inference still works.
"""

from .inference_tracker import InferenceTracker, get_tracker
