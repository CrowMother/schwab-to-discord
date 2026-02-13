# tests/api/test_schwab_api.py
"""Tests for Schwab API client."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from app.api.schwab import SchwabApi, SchwabApiError


@dataclass
class MockConfig:
    """Mock config for testing."""
    schwab_app_key: str = "test_key"
    schwab_app_secret: str = "test_secret"
    callback_url: str = "https://localhost"
    tokens_db: str = "/tmp/tokens.db"
    schwab_timeout: int = 10
    call_on_auth: str = None
    time_delta_days: int = 7
    status: str = "FILLED"


@pytest.fixture
def mock_config():
    """Provide mock config for tests."""
    return MockConfig()


@pytest.fixture
def mock_schwabdev_client():
    """Provide mock schwabdev client."""
    with patch("app.api.schwab.schwabdev.Client") as mock_client:
        yield mock_client


def test_schwab_api_init(mock_config, mock_schwabdev_client):
    """Test SchwabApi initialization creates client with correct params."""
    api = SchwabApi(mock_config)

    mock_schwabdev_client.assert_called_once_with(
        app_key="test_key",
        app_secret="test_secret",
        callback_url="https://localhost",
        tokens_db="/tmp/tokens.db",
        timeout=10,
        call_on_auth=None
    )


def test_get_orders_success(mock_config, mock_schwabdev_client):
    """Test get_orders returns order list on success."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [{"orderId": 123}, {"orderId": 456}]

    mock_client_instance = MagicMock()
    mock_client_instance.account_orders_all.return_value = mock_response
    mock_schwabdev_client.return_value = mock_client_instance

    # Test
    api = SchwabApi(mock_config)
    result = api.get_orders(mock_config)

    # Verify
    assert result == [{"orderId": 123}, {"orderId": 456}]
    mock_response.raise_for_status.assert_called_once()
    mock_response.json.assert_called_once()


def test_get_orders_retries_on_connection_error(mock_config, mock_schwabdev_client):
    """Test get_orders retries on connection errors."""
    from requests.exceptions import ConnectionError

    # Setup mock that fails twice then succeeds
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [{"orderId": 123}]

    mock_client_instance = MagicMock()
    mock_client_instance.account_orders_all.side_effect = [
        ConnectionError("Network error"),
        ConnectionError("Network error"),
        mock_response
    ]
    mock_schwabdev_client.return_value = mock_client_instance

    # Test with patched sleep to speed up
    with patch("app.api.schwab.time.sleep"):
        api = SchwabApi(mock_config)
        result = api.get_orders(mock_config)

    # Verify retried and eventually succeeded
    assert result == [{"orderId": 123}]
    assert mock_client_instance.account_orders_all.call_count == 3


def test_get_orders_raises_after_max_retries(mock_config, mock_schwabdev_client):
    """Test get_orders raises SchwabApiError after max retries."""
    from requests.exceptions import ConnectionError

    # Setup mock that always fails
    mock_client_instance = MagicMock()
    mock_client_instance.account_orders_all.side_effect = ConnectionError("Network error")
    mock_schwabdev_client.return_value = mock_client_instance

    # Test with patched sleep
    with patch("app.api.schwab.time.sleep"):
        api = SchwabApi(mock_config)

        with pytest.raises(SchwabApiError, match="API call failed after"):
            api.get_orders(mock_config)


def test_get_account_details_success(mock_config, mock_schwabdev_client):
    """Test get_account_details returns account data on success."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [{"securitiesAccount": {"positions": []}}]

    mock_client_instance = MagicMock()
    mock_client_instance.account_details_all.return_value = mock_response
    mock_schwabdev_client.return_value = mock_client_instance

    api = SchwabApi(mock_config)
    result = api.get_account_details(fields="positions")

    assert result == [{"securitiesAccount": {"positions": []}}]
    mock_client_instance.account_details_all.assert_called_once_with(fields="positions")
