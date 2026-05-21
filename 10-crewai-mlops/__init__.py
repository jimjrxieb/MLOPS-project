"""
CrewAI MLOps workflows for GP-Copilot.

This package turns security, governance, and RAG ingestion playbooks into
repeatable CrewAI workflows. Deterministic collectors gather evidence first;
LLM agents are reserved for judgment, review, classification, and reporting.
"""
import os

os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai-storage")

__all__ = ["synthetic_pipeline", "beru", "rag_ingestion"]
