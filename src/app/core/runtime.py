# src/app/core/runtime.py
"""Runtime settings management with lazy loading."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from dotenv import load_dotenv

from app.core.config import Settings
from app.core.errors import ConfigError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Module-level singleton
_settings: Optional[Settings] = None


def _find_project_root() -> Path:
    """Find the project root directory."""
    # Start from this file's location and walk up
    current = Path(__file__).resolve()

    # Walk up looking for markers
    for parent in [current] + list(current.parents):
        if (parent / "docker-compose.yml").exists():
            return parent
        if (parent / "pyproject.toml").exists():
            return parent

    # Fallback to current working directory
    return Path.cwd()


def load_settings() -> Settings:
    """
    Load settings from environment files and process environment.

    Load order (later values override earlier):
    1. config/.env.secrets (secrets - gitignored)
    2. config/schwab-to-discord.env (base config - committed)
    3. Process environment (Docker/CI overrides)

    Returns:
        Settings: Loaded and validated settings.

    Raises:
        ConfigError: If required settings are missing or invalid.
    """
    project_root = _find_project_root()
    config_dir = project_root / "config"

    # Load in order (later overrides earlier)
    env_files = [
        config_dir / "schwab-to-discord.env",  # Base config
        config_dir / ".env.secrets",            # Secrets (overrides base)
        project_root / ".env",                  # Legacy support
    ]

    loaded_files = []
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            loaded_files.append(str(env_file))

    if loaded_files:
        logger.debug(f"Loaded environment files: {loaded_files}")

    # Build settings from environment
    try:
        settings = Settings.from_environ()
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Failed to load settings: {e}") from e

    # Validate settings
    errors = settings.validate()
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ConfigError(error_msg)

    return settings


def get_settings() -> Settings:
    """
    Get the application settings singleton.

    Settings are loaded lazily on first access and cached.

    Returns:
        Settings: The application settings.

    Raises:
        ConfigError: If settings cannot be loaded or are invalid.
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton (primarily for testing)."""
    global _settings
    _settings = None


class _SettingsProxy:
    """
    Lazy proxy for settings access.

    Allows importing `settings` at module level without
    triggering immediate loading.

    Usage:
        from app.core import settings
        print(settings.app_name)  # Loads on first attribute access
    """

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        if _settings is None:
            return "<Settings: not loaded>"
        return repr(_settings)


# Lazy settings proxy for convenient imports
settings = _SettingsProxy()
