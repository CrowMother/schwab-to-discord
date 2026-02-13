# src/app/core/errors.py
"""Custom exceptions for the application."""

from __future__ import annotations


class ConfigError(RuntimeError):
    """Configuration validation or loading failed."""
    pass


class SchwabError(Exception):
    """Schwab API operation failed."""
    pass


class SchwabConnectionError(SchwabError):
    """Cannot connect to Schwab API."""
    pass


class SchwabAuthError(SchwabError):
    """Schwab authentication failed."""
    pass


class DiscordError(Exception):
    """Discord operation failed."""
    pass


class DiscordSendError(DiscordError):
    """Failed to send Discord message."""
    pass


class DatabaseError(Exception):
    """Database operation failed."""
    pass
