#!/usr/bin/env python3
"""
GP-Copilot Path Configuration
============================

Central path management for deployable code.
Uses environment variables with sensible defaults.

Usage:
    from core.paths import GP_ROOT, GP_CHROMA_PATH, GP_LOGS_PATH

Environment Variables (set these for deployment):
    GP_ROOT         - Root of GP-copilot installation
    GP_CHROMA_PATH  - ChromaDB database location
    GP_LOGS_PATH    - Centralized logs location
    GP_DATA_PATH    - GP-DATA directory
    GP_MEMORY_PATH  - Memory persistence location
"""

import os
from pathlib import Path

# Detect GP_ROOT from environment or calculate from this file's location
# This file is at: GP-copilot/GP-MODEL-OPS/JADE-AI/core/paths.py
# GP_ROOT is: GP-copilot/
_default_root = Path(__file__).parent.parent.parent.parent

GP_ROOT = Path(os.getenv('GP_ROOT', _default_root))

# Core paths - all relative to GP_ROOT
GP_CHROMA_PATH = Path(os.getenv(
    'GP_CHROMA_PATH',
    GP_ROOT / 'GP-MODEL-OPS' / '2-rag-ingestion' / '05-ragged-data' / 'chroma'
))

GP_LOGS_PATH = Path(os.getenv(
    'GP_LOGS_PATH',
    GP_ROOT / 'GP-S3' / 'GP-CLOUDWATCH'
))

GP_DATA_PATH = Path(os.getenv(
    'GP_DATA_PATH',
    GP_ROOT / 'GP-DATA'
))

GP_MEMORY_PATH = Path(os.getenv(
    'GP_MEMORY_PATH',
    GP_ROOT / 'GP-S3' / '6-temp' / 'memory'
))

GP_CONSULTING_PATH = Path(os.getenv(
    'GP_CONSULTING_PATH',
    GP_ROOT / 'GP-CONSULTING'
))

GP_PROJECTS_PATH = Path(os.getenv(
    'GP_PROJECTS_PATH',
    GP_ROOT / 'GP-PROJECTS'
))

# Structured data paths
GP_FINDINGS_DB = Path(os.getenv(
    'GP_FINDINGS_DB',
    GP_ROOT / 'GP-S3' / '2-structured-data' / 'findings.db'
))

GP_REPORTS_PATH = Path(os.getenv(
    'GP_REPORTS_PATH',
    GP_ROOT / 'GP-S3' / 'active' / 'reports'
))

# JSA-related paths (these point to logs JADE reads, not training data)
GP_JSA_LOGS_PATH = Path(os.getenv(
    'GP_JSA_LOGS_PATH',
    GP_LOGS_PATH / 'jsa-logs'
))

# JADE chat logs (replaces old GP-DATA/chat-logs)
GP_JADECHAT_LOGS_PATH = Path(os.getenv(
    'GP_JADECHAT_LOGS_PATH',
    GP_ROOT / 'GP-CLOUDWATCH' / 'jadechat-logs'
))


def ensure_paths_exist():
    """Create required directories if they don't exist"""
    for path in [GP_CHROMA_PATH, GP_LOGS_PATH, GP_DATA_PATH,
                 GP_MEMORY_PATH, GP_REPORTS_PATH]:
        path.mkdir(parents=True, exist_ok=True)


def get_deployment_info() -> dict:
    """Get current path configuration for debugging"""
    return {
        'GP_ROOT': str(GP_ROOT),
        'GP_CHROMA_PATH': str(GP_CHROMA_PATH),
        'GP_LOGS_PATH': str(GP_LOGS_PATH),
        'GP_DATA_PATH': str(GP_DATA_PATH),
        'GP_MEMORY_PATH': str(GP_MEMORY_PATH),
        'GP_CONSULTING_PATH': str(GP_CONSULTING_PATH),
        'GP_PROJECTS_PATH': str(GP_PROJECTS_PATH),
        'GP_FINDINGS_DB': str(GP_FINDINGS_DB),
        'GP_REPORTS_PATH': str(GP_REPORTS_PATH),
        'GP_JSA_LOGS_PATH': str(GP_JSA_LOGS_PATH),
        'GP_JADECHAT_LOGS_PATH': str(GP_JADECHAT_LOGS_PATH),
    }


if __name__ == '__main__':
    import json
    print("GP-Copilot Path Configuration:")
    print(json.dumps(get_deployment_info(), indent=2))