# tests/models/test_config.py
"""Tests for configuration management."""

import pytest
import os
from unittest.mock import patch, MagicMock

from app.models.config import Config, load_config, ConfigurationError


@pytest.fixture
def minimal_env():
    """Provide minimal required environment variables."""
    return {
        "SCHWAB_APP_KEY": "test_key",
        "SCHWAB_APP_SECRET": "test_secret",
        "CALLBACK_URL": "https://localhost",
        "DISCORD_WEBHOOK": "https://discord.com/api/webhooks/123/abc",
    }


@pytest.fixture
def full_env(minimal_env):
    """Provide full environment variables."""
    return {
        **minimal_env,
        "APP_NAME": "Test App",
        "DISCORD_WEBHOOK_2": "https://discord.com/api/webhooks/456/def",
        "DISCORD_ROLE_ID": "123456789",
        "DB_PATH": "/custom/path/trades.db",
        "TIME_DELTA_DAYS": "5",
        "SCHWAB_TIMEOUT": "15",
    }


@pytest.fixture
def mock_load_dotenv():
    """Mock load_dotenv to prevent reading actual .env files."""
    with patch("app.models.config.load_dotenv"):
        yield


def test_config_validation_passes_with_required_fields(minimal_env, mock_load_dotenv):
    """Test config validation passes with all required fields."""
    with patch.dict(os.environ, minimal_env, clear=True):
        config = load_config(validate=True)

        assert config.schwab_app_key == "test_key"
        assert config.schwab_app_secret == "test_secret"
        assert config.discord_webhook == "https://discord.com/api/webhooks/123/abc"


def test_config_validation_fails_missing_schwab_key(mock_load_dotenv):
    """Test config validation fails without SCHWAB_APP_KEY."""
    env = {
        "SCHWAB_APP_SECRET": "secret",
        "CALLBACK_URL": "https://localhost",
        "DISCORD_WEBHOOK": "https://discord.com/api/webhooks/123/abc",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="SCHWAB_APP_KEY is required"):
            load_config(validate=True)


def test_config_validation_fails_missing_discord_webhook(mock_load_dotenv):
    """Test config validation fails without DISCORD_WEBHOOK."""
    env = {
        "SCHWAB_APP_KEY": "key",
        "SCHWAB_APP_SECRET": "secret",
        "CALLBACK_URL": "https://localhost",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="DISCORD_WEBHOOK is required"):
            load_config(validate=True)


def test_config_validation_fails_invalid_webhook_url(mock_load_dotenv):
    """Test config validation fails with invalid webhook URL."""
    env = {
        "SCHWAB_APP_KEY": "key",
        "SCHWAB_APP_SECRET": "secret",
        "CALLBACK_URL": "https://localhost",
        "DISCORD_WEBHOOK": "not-a-url",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="DISCORD_WEBHOOK must be a valid URL"):
            load_config(validate=True)


def test_config_loads_defaults(minimal_env, mock_load_dotenv):
    """Test config uses defaults for optional fields."""
    with patch.dict(os.environ, minimal_env, clear=True):
        config = load_config(validate=True)

        assert config.app_name == "Schwab to Discord"
        assert config.db_path == "/data/trades.db"
        assert config.schwab_timeout == 10
        assert config.time_delta_days == 7


def test_config_loads_custom_values(full_env, mock_load_dotenv):
    """Test config loads custom values from env."""
    with patch.dict(os.environ, full_env, clear=True):
        config = load_config(validate=True)

        assert config.app_name == "Test App"
        assert config.db_path == "/custom/path/trades.db"
        assert config.schwab_timeout == 15
        assert config.time_delta_days == 5
        assert config.discord_webhook_secondary == "https://discord.com/api/webhooks/456/def"
        assert config.discord_role_id == "123456789"


def test_config_skip_validation(mock_load_dotenv):
    """Test config can skip validation."""
    env = {}  # No required fields
    with patch.dict(os.environ, env, clear=True):
        # Should not raise
        config = load_config(validate=False)
        assert config.schwab_app_key == ""
