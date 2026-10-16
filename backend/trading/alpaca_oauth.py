"""Per-user Alpaca OAuth connections for paper trading."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import settings
from backend.db.db import db_session

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    key = settings.alpaca_token_encryption_key
    if not key:
        raise RuntimeError("ALPACA_TOKEN_ENCRYPTION_KEY is not configured.")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("ALPACA_TOKEN_ENCRYPTION_KEY is invalid.") from exc


def create_authorization(user_id: str) -> str:
    if not settings.alpaca_client_id or not settings.alpaca_redirect_uri:
        raise RuntimeError("Alpaca OAuth configuration is incomplete.")
    state = secrets.token_urlsafe(32)
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alpaca_oauth_states (state, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (state, user_id, datetime.now(timezone.utc) + timedelta(minutes=10)),
            )
        conn.commit()
    params = {
        "response_type": "code",
        "client_id": settings.alpaca_client_id,
        "redirect_uri": settings.alpaca_redirect_uri,
        "scope": settings.alpaca_oauth_scopes,
        "state": state,
        "env": "paper",
    }
    return f"https://app.alpaca.markets/oauth/authorize?{urlencode(params)}"


def _consume_state(state: str) -> str:
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM alpaca_oauth_states
                WHERE state = %s AND expires_at > CURRENT_TIMESTAMP
                RETURNING user_id
                """,
                (state,),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise ValueError("OAuth state is invalid or expired.")
    return row["user_id"]


def exchange_code(code: str, state: str) -> dict[str, Any]:
    user_id = _consume_state(state)
    if not settings.alpaca_client_id or not settings.alpaca_client_secret:
        raise RuntimeError(
            "Alpaca OAuth credentials are missing. Configure ALPACA_CLIENT_ID "
            "and ALPACA_CLIENT_SECRET with OAuth application credentials."
        )
    response = requests.post(
        "https://api.alpaca.markets/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.alpaca_client_id,
            "client_secret": settings.alpaca_client_secret,
            "redirect_uri": settings.alpaca_redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=settings.http_timeout,
    )
    if not response.ok:
        try:
            provider_error = response.json().get("error", "unknown_error")
        except ValueError:
            provider_error = "invalid_provider_response"
        logger.warning(
            "[ALPACA] OAuth token exchange failed: status=%s error=%s",
            response.status_code,
            provider_error,
        )
        if response.status_code in (400, 401):
            raise ValueError(
                "Alpaca rejected the OAuth client. Use the OAuth application's "
                "Client ID and Client Secret, not paper API keys."
            )
        raise ValueError("Alpaca authorization could not be completed.")
    payload = response.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not access_token:
        raise ValueError("Alpaca authorization returned no access token.")

    encrypted_access = _fernet().encrypt(access_token.encode()).decode()
    encrypted_refresh = _fernet().encrypt(refresh_token.encode()).decode() if refresh_token else None
    expires_at = None
    if payload.get("expires_in"):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload["expires_in"]))

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alpaca_connections
                    (user_id, access_token, refresh_token, expires_at, environment, updated_at)
                VALUES (%s, %s, %s, %s, 'paper', CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    environment = 'paper',
                    revoked_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, encrypted_access, encrypted_refresh, expires_at),
            )
        conn.commit()
    return {"user_id": user_id, "environment": "paper", "connected": True}


def get_connection(user_id: str) -> dict[str, Any] | None:
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT environment, expires_at, revoked_at, created_at, updated_at
                FROM alpaca_connections
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
    if not row or row["revoked_at"] is not None:
        return None
    return {
        "connected": True,
        "environment": row["environment"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def disconnect(user_id: str) -> None:
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alpaca_connections
                SET revoked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (user_id,),
            )
        conn.commit()


def access_token(user_id: str) -> str:
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT access_token, environment, revoked_at
                FROM alpaca_connections
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
    if not row or row["revoked_at"] is not None or row["environment"] != "paper":
        raise RuntimeError("Connect an Alpaca paper account before using trading features.")
    try:
        return _fernet().decrypt(row["access_token"].encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise RuntimeError("Stored Alpaca connection cannot be decrypted.") from exc


def request(user_id: str, method: str, path: str, **kwargs: Any) -> Any:
    token = access_token(user_id)
    response = requests.request(
        method,
        f"https://paper-api.alpaca.markets{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=settings.http_timeout,
        **kwargs,
    )
    if response.status_code in (401, 403):
        raise RuntimeError("Alpaca authorization expired or was revoked. Reconnect your account.")
    if not response.ok:
        raise RuntimeError("Alpaca request failed.")
    return response.json() if response.content else {}
