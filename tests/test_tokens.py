"""Tests for the token helper utilities."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fitbit_to_kml.tokens import TokenData, load_token_file, write_token_file


def test_load_token_file_normalizes_scope(tmp_path):
    token_payload = {
        "access_token": "abc",
        "refresh_token": "refresh",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "scope": "activity location",
        "token_type": "Bearer",
    }
    path = tmp_path / "tokens.json"
    path.write_text(json.dumps(token_payload), encoding="utf-8")

    token = load_token_file(path)

    assert token.scope == ["activity", "location"]
    assert not token.will_expire_within()


def test_write_token_file_round_trip(tmp_path):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token = TokenData(
        access_token="abc",
        refresh_token="def",
        token_type="Bearer",
        expires_at=expires_at,
        scope=["activity"],
    )
    path = tmp_path / "tokens.json"

    write_token_file(token, path)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["access_token"] == "abc"
    assert saved["refresh_token"] == "def"
    assert "expires_at" in saved
