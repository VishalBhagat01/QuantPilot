"""
Backend Authentication Module.

Centralizes authentication and authorization-related operations:
- Google OAuth URL generation and callback code exchange
- Supabase JWT verification
- Access-token refresh and sign-out
- User profile serialization
- Terms & Conditions acceptance persistence

Business logic, public function names, return payloads, and database
operations are kept compatible with the existing implementation.
"""

import datetime
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

def get_supabase() -> Client:
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=500,
            detail="Supabase credentials not configured in backend",
        )

    return create_client(SUPABASE_URL, SUPABASE_KEY)

def _get_user_metadata(user: Any) -> dict[str, Any]:
    """Safely retrieve user metadata from an authentication response."""
    metadata = (
        user.get("user_metadata", {})
        if isinstance(user, dict)
        else getattr(user, "user_metadata", {})
    )

    return metadata if isinstance(metadata, dict) else {}


def _serialize_user(user: Any) -> dict[str, Any]:
    """Convert a Supabase user object into the public profile payload."""
    if isinstance(user, dict):
        user_id = user.get("id")
        email = user.get("email")
    else:
        user_id = user.id 
        email = user.email

    metadata = _get_user_metadata(user)

    return {
        "id": user_id,
        "email": email,
        "name": metadata.get("full_name", ""),
        "avatar_url": metadata.get("avatar_url", ""),
    }


def _serialize_session(session: Any, user: Any) -> dict[str, Any]:
    """Build the standard authentication session response."""
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
        "user": _serialize_user(user),
    }


def verify_user(request: Request) -> Any:
    """
    FastAPI dependency that validates the Bearer token through Supabase.

    Returns the authenticated Supabase user object.

    Note:
        The existing development bypass is preserved for compatibility.
        It must not be enabled in production.
    """
    # Preserve the existing development-mode behavior.
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"id": "dev_user"}

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

        return user_response.user

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            "[AUTH] User verification failed",
            exc_info=True,
        )
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(exc)}",
        ) from exc

# Google OAuth

def get_google_oauth_url() -> dict[str, Any]:
    """
    Generate the Supabase-managed Google OAuth URL.

    The frontend redirects the browser to the returned URL.
    """
    supabase = get_supabase()

    try:
        response = supabase.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {
                    "redirect_to": f"{FRONTEND_URL}/auth/callback",
                },
            }
        )

        return {"url": response.url}

    except Exception as exc:
        logger.error(
            "[AUTH] Google OAuth URL generation failed",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"OAuth setup failed: {str(exc)}",
        ) from exc


def exchange_code_for_session(code: str) -> dict[str, Any]:
    """
    Exchange an OAuth authorization code for a Supabase session.

    Returns access_token, refresh_token, expiry, and user information.
    """
    supabase = get_supabase()

    try:
        response = supabase.auth.exchange_code_for_session(
            {"auth_code": code}
        )

        session = response.session
        user = response.user

        if not session or not user:
            raise HTTPException(
                status_code=401,
                detail="Code exchange returned no session",
            )

        return _serialize_session(session, user)

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            "[AUTH] OAuth code exchange failed",
            exc_info=True,
        )
        raise HTTPException(
            status_code=401,
            detail=f"Session exchange failed: {str(exc)}",
        ) from exc


def refresh_session(refresh_token: str) -> dict[str, Any]:
    """Refresh the Supabase session using a refresh token."""
    supabase = get_supabase()

    try:
        response = supabase.auth.refresh_session(refresh_token)

        session = response.session
        user = response.user

        if not session:
            raise HTTPException(
                status_code=401,
                detail="Refresh returned no session",
            )

        return _serialize_session(session, user)

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            "[AUTH] Session refresh failed",
            exc_info=True,
        )
        raise HTTPException(
            status_code=401,
            detail=f"Token refresh failed: {str(exc)}",
        ) from exc


def sign_out(access_token: str) -> dict[str, str]:
    """
    Attempt to revoke the Supabase session.

    Preserves the existing behavior of returning signed_out even when
    the server-side revocation attempt raises an exception.
    """
    supabase = get_supabase()

    try:
        supabase.auth.admin.sign_out(access_token)

    except Exception:
        logger.warning(
            "[AUTH] Server-side sign-out failed",
            exc_info=True,
        )

    return {"status": "signed_out"}

def get_current_user_info(request: Request) -> dict[str, Any]:
    """Return the authenticated user's public profile."""
    user = verify_user(request)

    # Preserve the development bypass response: {"id": "dev_user"}.
    if isinstance(user, dict) and "user_metadata" not in user:
        return user

    return _serialize_user(user)

def check_terms_accepted(user_id: str, conn: Any) -> bool:
    """Check whether a user has an acceptance record."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT accepted_at
                FROM terms_acceptance
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()

        return row is not None

    except Exception:
        logger.warning(
            "[AUTH] Terms acceptance check failed",
            exc_info=True,
        )
        return False


def accept_terms(user_id: str, conn: Any) -> dict[str, str]:
    """Persist the user's Terms & Conditions acceptance."""
    accepted_at = datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO terms_acceptance (user_id, accepted_at)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET accepted_at = EXCLUDED.accepted_at;
                """,
                (user_id, accepted_at),
            )

        conn.commit()

        return {
            "status": "accepted",
            "accepted_at": accepted_at,
        }

    except Exception as exc:
        logger.error(
            "[AUTH] Terms acceptance persistence failed",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Could not save acceptance: {str(exc)}",
        ) from exc
