# ============================================================
# DevAgent — Configuration Package
# ============================================================
# This package contains all configuration-related modules:
#
#   settings.py  — Pydantic Settings (env var validation)
#   constants.py — Enums, defaults, system-wide constants
#
# Usage:
#   from src.config.settings import get_settings
#   from src.config.constants import AgentType, TaskStatus
# ============================================================

from src.config.constants import AgentType, TaskStatus
from src.config.settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
    "AgentType",
    "TaskStatus",
]
