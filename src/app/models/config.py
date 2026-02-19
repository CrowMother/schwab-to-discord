# src/app/models/config.py
"""
Configuration re-exports for backward compatibility.

DEPRECATED: New code should use `from app.core import Settings, get_settings`.

This module re-exports configuration classes from app.core.config to maintain
backward compatibility with existing code that imports from app.models.config.
"""

from __future__ import annotations

# Re-export everything from core.config for backward compatibility
from app.core.config import (
    Settings,
    Settings as Config,  # Alias
    ConfigError as ConfigurationError,  # Alias
    load_config,
)

# Re-export get_settings for convenience
from app.core.runtime import get_settings

__all__ = [
    "Settings",
    "Config",
    "ConfigurationError",
    "load_config",
    "get_settings",
]


# Backward compatibility helper - deprecated
def load_single_value(key: str, alt=None):
    """
    DEPRECATED: Use get_settings() and access settings attributes instead.

    Example:
        # Old way (deprecated)
        webhook = load_single_value("DISCORD_WEBHOOK")

        # New way
        from app.core import get_settings
        settings = get_settings()
        webhook = settings.discord_webhook
    """
    import os
    val = os.getenv(key)
    return val if val is not None and val != "" else alt
