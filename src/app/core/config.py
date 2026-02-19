# src/app/core/config.py
"""
Unified configuration settings for schwab-to-discord.

This is the single source of truth for all configuration.
Use `from app.core import Settings, get_settings` to access.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

from app.core.errors import ConfigError

logger = logging.getLogger(__name__)


def _get_str(key: str, default: str = None, required: bool = False) -> Optional[str]:
    """Get string from environment."""
    value = os.environ.get(key, default)
    if required and not value:
        raise ConfigError(f"Required environment variable {key} is not set")
    return value


def _get_int(key: str, default: int = None) -> Optional[int]:
    """Get integer from environment."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"Environment variable {key} must be an integer, got: {value}")


def _get_bool(key: str, default: bool = False) -> bool:
    """Get boolean from environment."""
    value = os.environ.get(key, "").lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")


@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from environment variables.

    All configuration is loaded from environment variables, which can be set via:
    - .env file (for local development)
    - config/.env.secrets (for sensitive values like API keys)
    - config/schwab-to-discord.env (for base config)
    - Docker environment variables (for production)

    See .env.example for all available options.
    """

    # ==================== Application ====================
    app_name: str
    log_level: str

    # ==================== Schwab API ====================
    schwab_app_key: str
    schwab_app_secret: str
    schwab_callback_url: str
    schwab_timeout: int
    time_delta_days: int
    order_status: str
    poll_interval: int
    tokens_db: str
    call_on_auth: Optional[str]  # Optional callback URL for auth

    # ==================== Discord ====================
    discord_webhook: str
    discord_webhook_2: str  # Secondary webhook (optional)
    discord_role_id: str
    discord_channel_id: Optional[str]
    template: Optional[str]

    # ==================== Database ====================
    db_path: str
    export_path: str

    # ==================== Google Sheets (optional) ====================
    gsheet_credentials_path: Optional[str]
    gsheet_spreadsheet_id: Optional[str]
    gsheet_worksheet_name: str
    gsheet_export_day: str
    gsheet_export_hour: int
    gsheet_export_minute: int

    # ==================== Computed Properties ====================

    @property
    def gsheet_enabled(self) -> bool:
        """Check if Google Sheets export is configured."""
        return bool(self.gsheet_credentials_path and self.gsheet_spreadsheet_id)

    @property
    def callback_url(self) -> str:
        """Alias for schwab_callback_url (backward compatibility)."""
        return self.schwab_callback_url

    @property
    def discord_webhook_secondary(self) -> str:
        """Alias for discord_webhook_2 (backward compatibility)."""
        return self.discord_webhook_2

    @property
    def status(self) -> str:
        """Alias for order_status (backward compatibility with SchwabApi)."""
        return self.order_status

    # ==================== Factory Method ====================

    @classmethod
    def from_environ(cls) -> "Settings":
        """
        Build Settings from environment variables.

        Raises:
            ConfigError: If required values are missing or invalid.
        """
        return cls(
            # Application
            app_name=_get_str("APP_NAME", "Schwab to Discord"),
            log_level=_get_str("LOG_LEVEL", "INFO"),

            # Schwab API
            schwab_app_key=_get_str("SCHWAB_APP_KEY", required=True),
            schwab_app_secret=_get_str("SCHWAB_APP_SECRET", required=True),
            schwab_callback_url=_get_str("CALLBACK_URL", "https://127.0.0.1"),
            schwab_timeout=_get_int("SCHWAB_TIMEOUT", 30),
            time_delta_days=_get_int("TIME_DELTA_DAYS", 7),
            order_status=_get_str("ORDER_STATUS", "FILLED"),
            poll_interval=_get_int("POLL_INTERVAL_SECONDS", 5),
            tokens_db=_get_str("TOKENS_DB", "/data/tokens.db"),
            call_on_auth=_get_str("CALL_ON_AUTH"),

            # Discord
            discord_webhook=_get_str("DISCORD_WEBHOOK", required=True),
            discord_webhook_2=_get_str("DISCORD_WEBHOOK_2", ""),
            discord_role_id=_get_str("DISCORD_ROLE_ID", ""),
            discord_channel_id=_get_str("DISCORD_CHANNEL_ID"),
            template=_get_str("TEMPLATE"),

            # Database
            db_path=_get_str("DB_PATH", "/data/trades.db"),
            export_path=_get_str("EXPORT_PATH", "/data/trades.xlsx"),

            # Google Sheets
            gsheet_credentials_path=_get_str("GOOGLE_SHEETS_CREDENTIALS_PATH"),
            gsheet_spreadsheet_id=_get_str("GOOGLE_SHEETS_SPREADSHEET_ID"),
            gsheet_worksheet_name=_get_str("GOOGLE_SHEETS_WORKSHEET_NAME", "Sheet1"),
            gsheet_export_day=_get_str("GSHEET_EXPORT_DAY", "sat"),
            gsheet_export_hour=_get_int("GSHEET_EXPORT_HOUR", 8),
            gsheet_export_minute=_get_int("GSHEET_EXPORT_MINUTE", 0),
        )

    # ==================== Validation ====================

    def validate(self) -> list[str]:
        """
        Validate settings and return list of errors.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Validate required secrets
        if not self.schwab_app_key or self.schwab_app_key.startswith("your_"):
            errors.append("SCHWAB_APP_KEY is not set or is a placeholder")
        if not self.schwab_app_secret or self.schwab_app_secret.startswith("your_"):
            errors.append("SCHWAB_APP_SECRET is not set or is a placeholder")

        # Validate Discord webhook URL format
        if not self.discord_webhook.startswith("https://discord.com/api/webhooks/"):
            errors.append("DISCORD_WEBHOOK must be a valid Discord webhook URL")

        # Validate numeric ranges
        if self.schwab_timeout < 1:
            errors.append("SCHWAB_TIMEOUT must be at least 1 second")
        if self.poll_interval < 1:
            errors.append("POLL_INTERVAL_SECONDS must be at least 1 second")

        return errors


# ==================== Backward Compatibility ====================
# These aliases allow code using the old models/config.py to work unchanged

Config = Settings  # Alias for backward compatibility
ConfigurationError = ConfigError  # Alias for backward compatibility


def load_config(validate: bool = True) -> Settings:
    """
    Load configuration from environment (backward compatibility wrapper).

    New code should use `from app.core import get_settings` instead.

    Args:
        validate: If True, validates required fields.

    Returns:
        Settings object with all configuration loaded.
    """
    from app.core.runtime import get_settings
    return get_settings()
