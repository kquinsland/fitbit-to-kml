"""Tests for fitbit_to_kml.get_auth OAuth2 flow."""

import os
from unittest.mock import patch

import pytest

from fitbit_to_kml import get_auth


def test_get_env_or_exit_success():
    """Test get_env_or_exit returns value when env var is set."""
    with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        result = get_auth.get_env_or_exit("TEST_VAR")
        assert result == "test_value"


def test_get_env_or_exit_missing():
    """Test get_env_or_exit exits when env var is not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            get_auth.get_env_or_exit("MISSING_VAR")
        assert exc_info.value.code == 1


def test_create_fitbit_client():
    """Test FitBit client creation with correct configuration."""
    client = get_auth.create_fitbit_client(
        client_id="test_client_id",
        client_secret="test_secret",
        redirect_uri="http://localhost:8080/callback",
    )

    assert client.client_id == "test_client_id"
    assert client.authorization_endpoint == get_auth.FITBIT_AUTHORIZATION_ENDPOINT
    assert client.token_endpoint == get_auth.FITBIT_TOKEN_ENDPOINT
    assert client.redirect_uri == "http://localhost:8080/callback"


def test_required_scopes():
    """Test that required scopes are correctly defined."""
    assert "activity" in get_auth.REQUIRED_SCOPES
    assert "location" in get_auth.REQUIRED_SCOPES
    assert len(get_auth.REQUIRED_SCOPES) == 3


def test_fitbit_endpoints():
    """Test that FitBit endpoints are correctly defined."""
    assert (
        get_auth.FITBIT_AUTHORIZATION_ENDPOINT
        == "https://www.fitbit.com/oauth2/authorize"
    )
    assert get_auth.FITBIT_TOKEN_ENDPOINT == "https://api.fitbit.com/oauth2/token"
    assert get_auth.FITBIT_REVOCATION_ENDPOINT == "https://api.fitbit.com/oauth2/revoke"
