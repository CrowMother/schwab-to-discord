# src/app/models/config.py
"""Configuration management with validation and secrets separation."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.constants import Defaults

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required values."""
    pass


@dataclass(frozen=True)
class Config:
    """Application configuration with validation."""
    # App settings
    app_name: str

    # Schwab API (secrets)
    schwab_app_key: str
    schwab_app_secret: str
    callback_url: str
    tokens_db: str
    schwab_timeout: int
    call_on_auth: Optional[str]
    time_delta_days: int
    status: Optional[str]

    # Discord (secrets)
    discord_webhook: str
    discord_webhook_secondary: Optional[str]
    discord_channel: Optional[str]
    discord_role_id: Optional[str]

    # Database
    db_path: str

    # Google Sheets (secrets)
    google_sheets_credentials_path: Optional[str]
    google_sheets_spreadsheet_id: Optional[str]
    google_sheets_worksheet_name: Optional[str]

    # Export settings
    export_path: str

    # Scheduler settings
    gsheet_export_day: str
    gsheet_export_hour: int
    gsheet_export_minute: int

    def validate(self) -> None:
        """Validate that all required configuration is present."""
        errors = []

        # Required Schwab settings
        if not self.schwab_app_key:
            errors.append("SCHWAB_APP_KEY is required")
        if not self.schwab_app_secret:
            errors.append("SCHWAB_APP_SECRET is required")
        if not self.callback_url:
            errors.append("CALLBACK_URL is required")

        # Required Discord settings (at least primary webhook)
        if not self.discord_webhook:
            errors.append("DISCORD_WEBHOOK is required")

        # Validate URLs
        if self.discord_webhook and not self.discord_webhook.startswith("http"):
            errors.append("DISCORD_WEBHOOK must be a valid URL")
        if self.discord_webhook_secondary and not self.discord_webhook_secondary.startswith("http"):
            errors.append("DISCORD_WEBHOOK_2 must be a valid URL")

        if errors:
            raise ConfigurationError("Configuration errors:\n  - " + "\n  - ".join(errors))


def _opt_str(key: str, alt: Optional[str] = None) -> Optional[str]:
    """Get optional string from environment."""
    val = os.getenv(key)
    return val if val is not None and val != "" else alt


def _opt_int(key: str, alt: Optional[int] = None) -> Optional[int]:
    """Get optional integer from environment."""
    val = os.getenv(key)
    if val is not None and val != "":
        try:
            return int(val)
        except ValueError:
            logger.warning(f"Invalid integer value for {key}: {val}, using default: {alt}")
            return alt
    return alt


def _opt_bool(key: str, alt: Optional[bool] = None) -> Optional[bool]:
    """Get optional boolean from environment."""
    val = os.getenv(key)
    if val is not None and val != "":
        return val.lower() in ("1", "true", "yes", "on")
    return alt


def _opt_float(key: str, alt: Optional[float] = None) -> Optional[float]:
    """Get optional float from environment."""
    val = os.getenv(key)
    if val is not None and val != "":
        try:
            return float(val)
        except ValueError:
            logger.warning(f"Invalid float value for {key}: {val}, using default: {alt}")
            return alt
    return alt


def _load_env_files() -> None:
    """Load environment files in order: .env then .env.secrets (secrets override)."""
    # Find project root (where .env files should be)
    # Try current directory first, then look for src/app parent
    possible_roots = [
        Path.cwd(),
        Path(__file__).parent.parent.parent.parent,  # Up from src/app/models
    ]

    for root in possible_roots:
        env_file = root / ".env"
        secrets_file = root / ".env.secrets"

        if env_file.exists():
            load_dotenv(env_file)
            logger.debug(f"Loaded environment from {env_file}")

        if secrets_file.exists():
            load_dotenv(secrets_file, override=True)
            logger.debug(f"Loaded secrets from {secrets_file}")
            return
        elif env_file.exists():
            # .env exists but .env.secrets doesn't - warn in production
            logger.debug(f"No .env.secrets found at {secrets_file}, using .env only")
            return

    # Fallback: just load whatever dotenv can find
    load_dotenv()


def load_config(validate: bool = True) -> Config:
    """
    Load configuration from environment files.

    Args:
        validate: If True, validates required fields and raises ConfigurationError if invalid.

    Returns:
        Config object with all settings loaded.
    """
    _load_env_files()

    config = Config(
        # App settings
        app_name=_opt_str("APP_NAME", "Schwab to Discord"),

        # Schwab API
        schwab_app_key=_opt_str("SCHWAB_APP_KEY", ""),
        schwab_app_secret=_opt_str("SCHWAB_APP_SECRET", ""),
        callback_url=_opt_str("CALLBACK_URL", ""),
        tokens_db=_opt_str("TOKENS_DB", Defaults.TOKENS_DB),
        schwab_timeout=_opt_int("SCHWAB_TIMEOUT", Defaults.SCHWAB_TIMEOUT),
        call_on_auth=_opt_str("CALL_ON_AUTH"),
        time_delta_days=_opt_int("TIME_DELTA_DAYS", Defaults.TIME_DELTA_DAYS),
        status=_opt_str("ORDER_STATUS"),

        # Discord
        discord_webhook=_opt_str("DISCORD_WEBHOOK", ""),
        discord_webhook_secondary=_opt_str("DISCORD_WEBHOOK_2"),
        discord_channel=_opt_str("DISCORD_CHANNEL_ID"),
        discord_role_id=_opt_str("DISCORD_ROLE_ID"),

        # Database
        db_path=_opt_str("DB_PATH", Defaults.DB_PATH),

        # Google Sheets
        google_sheets_credentials_path=_opt_str("GOOGLE_SHEETS_CREDENTIALS_PATH"),
        google_sheets_spreadsheet_id=_opt_str("GOOGLE_SHEETS_SPREADSHEET_ID"),
        google_sheets_worksheet_name=_opt_str("GOOGLE_SHEETS_WORKSHEET_NAME", "Sheet1"),

        # Export
        export_path=_opt_str("EXPORT_PATH", Defaults.EXPORT_PATH),

        # Scheduler
        gsheet_export_day=_opt_str("GSHEET_EXPORT_DAY", Defaults.GSHEET_EXPORT_DAY),
        gsheet_export_hour=_opt_int("GSHEET_EXPORT_HOUR", Defaults.GSHEET_EXPORT_HOUR),
        gsheet_export_minute=_opt_int("GSHEET_EXPORT_MINUTE", Defaults.GSHEET_EXPORT_MINUTE),
    )

    if validate:
        config.validate()

    return config


# Backward compatibility - deprecated, use config.discord_webhook_secondary instead
def load_single_value(key: str, alt=None):
    """
    DEPRECATED: Use load_config() and access config attributes instead.
    Kept for backward compatibility during migration.
    """
    val = os.getenv(key)
    return val if val is not None and val != "" else alt
