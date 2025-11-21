"""Helpers for reading and writing Fitbit token files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

UTC = timezone.utc


@dataclass
class TokenData:
    """In-memory representation of Fitbit OAuth tokens."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: Optional[List[str]] = None
    token_type: Optional[str] = None
    raw: Dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TokenData":
        """Create a TokenData from the JSON payload stored on disk."""
        expires_at_str = payload.get("expires_at")
        expires_at = _parse_timestamp(expires_at_str) if expires_at_str else None
        scope_value = payload.get("scope")
        if isinstance(scope_value, str):
            scope = [scope.strip() for scope in scope_value.split() if scope.strip()]
        elif isinstance(scope_value, Iterable):
            scope = [str(item) for item in scope_value]
        else:
            scope = None

        return cls(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            scope=scope,
            token_type=payload.get("token_type"),
            raw=payload,
        )

    def as_serializable_dict(self) -> Dict[str, Any]:
        """Return a JSON serializable representation of the token."""
        data: Dict[str, Any] = {
            "access_token": self.access_token,
            "token_type": self.token_type,
        }
        if self.refresh_token:
            data["refresh_token"] = self.refresh_token
        if self.expires_at:
            data["expires_at"] = self.expires_at.astimezone(UTC).isoformat()
        if self.scope:
            data["scope"] = " ".join(self.scope)
        if self.raw:
            for key, value in self.raw.items():
                if key not in data:
                    data[key] = value
        return data

    def will_expire_within(self, delta: timedelta = timedelta(minutes=1)) -> bool:
        """Return True when the token is expired or expiring soon."""
        if not self.expires_at:
            return False
        return self.expires_at <= datetime.now(tz=UTC) + delta


def _parse_timestamp(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def load_token_file(path: str | Path) -> TokenData:
    """Load token JSON from disk."""
    token_path = Path(path).expanduser()
    with token_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return TokenData.from_dict(payload)


def write_token_file(token: TokenData, path: str | Path) -> None:
    """Persist token JSON to disk."""
    token_path = Path(path).expanduser()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with token_path.open("w", encoding="utf-8") as handle:
        json.dump(token.as_serializable_dict(), handle, indent=2)
        handle.write("\n")
