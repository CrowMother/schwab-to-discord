import pytest
from unittest.mock import MagicMock, patch

# import your class from where you placed it
from app.api.schwab import SchwabApi


def test_get_orders_success_calls_client_and_returns_json():
    # Arrange
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = [{"orderId": 123}]

    fake_client = MagicMock()
    fake_client.account_orders_all.return_value = fake_response

    # Patch schwabdev.Client inside the module under test
    with patch("app.services.schwab_api.schwabdev.Client", return_value=fake_client) as mock_ctor:
        api = SchwabApi("KEY", "SECRET")

        # Act
        result = api.get_orders("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", status="FILLED")

        # Assert
        mock_ctor.assert_called_once_with("KEY", "SECRET")

        fake_client.account_orders_all.assert_called_once_with(
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00Z",
            None,
            "FILLED",
        )
        fake_response.raise_for_status.assert_called_once()
        fake_response.json.assert_called_once()
        assert result == [{"orderId": 123}]


def test_get_orders_http_error_raises():
    # Arrange
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = RuntimeError("HTTP 401")  # could be requests.HTTPError too

    fake_client = MagicMock()
    fake_client.account_orders_all.return_value = fake_response

    with patch("app.services.schwab_api.schwabdev.Client", return_value=fake_client):
        api = SchwabApi("KEY", "SECRET")

        # Act / Assert
        with pytest.raises(RuntimeError, match="HTTP 401"):
            api.get_orders("start", "end", status=None)

        fake_response.raise_for_status.assert_called_once()


def test_get_orders_passes_none_status():
    # Arrange
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = []

    fake_client = MagicMock()
    fake_client.account_orders_all.return_value = fake_response

    with patch("app.services.schwab_api.schwabdev.Client", return_value=fake_client):
        api = SchwabApi("KEY", "SECRET")

        # Act
        api.get_orders("start", "end", status=None)

        # Assert: status is None in final arg
        fake_client.account_orders_all.assert_called_once_with("start", "end", None, None)
