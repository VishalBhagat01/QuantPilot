"""
Backend Authentication Module — All auth logic centralized server-side.

Handles:
  - Google OAuth URL generation & callback processing
  - JWT session verification via Supabase
  - Token refresh
  - Sign-out
  - Terms & Conditions acceptance tracking (stored in DB)
"""

import os
import datetime
import logging
from fastapi import Request, HTTPException, Depends
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def get_supabase() -> Client:
    """Create and return a Supabase client. Raises 500 if credentials are missing."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured in backend")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def verify_user(request: Request):
    """
    FastAPI dependency: verify the JWT token from the Authorization header
    using the backend Supabase client. Returns the authenticated user object.
    """
    # Dev-mode bypass when credentials are absent
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"id": "dev_user"}

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# ---------------------------------------------------------------------------
# OAuth Flow Endpoints (called from router in main.py)
# ---------------------------------------------------------------------------

def get_google_oauth_url() -> dict:
    """
    Generate the Supabase-managed Google OAuth redirect URL.
    The frontend calls this endpoint and redirects the browser to the returned URL.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": f"{FRONTEND_URL}/auth/callback",
            },
        })
        return {"url": response.url}
    except Exception as e:
        logger.error(f"[AUTH] Google OAuth URL generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth setup failed: {str(e)}")


def exchange_code_for_session(code: str) -> dict:
    """
    Exchange the OAuth authorization code for a full Supabase session.
    Returns access_token, refresh_token, user info.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.exchange_code_for_session({"auth_code": code})
        session = response.session
        user = response.user
        if not session or not user:
            raise HTTPException(status_code=401, detail="Code exchange returned no session")

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.user_metadata.get("full_name", ""),
                "avatar_url": user.user_metadata.get("avatar_url", ""),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Code exchange failed: {e}")
        raise HTTPException(status_code=401, detail=f"Session exchange failed: {str(e)}")


def refresh_session(refresh_token: str) -> dict:
    """Refresh an expired access_token using the refresh_token."""
    supabase = get_supabase()
    try:
        response = supabase.auth.refresh_session(refresh_token)
        session = response.session
        user = response.user
        if not session:
            raise HTTPException(status_code=401, detail="Refresh returned no session")

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.user_metadata.get("full_name", ""),
                "avatar_url": user.user_metadata.get("avatar_url", ""),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")


def sign_out(access_token: str) -> dict:
    """Revoke a session server-side."""
    supabase = get_supabase()
    try:
        supabase.auth.admin.sign_out(access_token)
    except Exception as e:
        logger.warning(f"[AUTH] Sign-out notice: {e}")
    return {"status": "signed_out"}


def get_current_user_info(request: Request) -> dict:
    """Return the authenticated user's profile from the token."""
    user = verify_user(request)

    if isinstance(user, dict):
        return user

    return {
        "id": user.id,
        "email": user.email,
        "name": getattr(user, "user_metadata", {}).get("full_name", ""),
        "avatar_url": getattr(user, "user_metadata", {}).get("avatar_url", ""),
    }


# ---------------------------------------------------------------------------
# Terms & Conditions Acceptance (persisted in DB)
# ---------------------------------------------------------------------------

def check_terms_accepted(user_id: str, conn) -> bool:
    """Check if a user has accepted the Terms & Conditions."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT accepted_at FROM terms_acceptance WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row is not None
    except Exception as e:
        logger.warning(f"[AUTH] Terms check failed: {e}")
        return False


def accept_terms(user_id: str, conn) -> dict:
    """Record that a user accepted the Terms & Conditions."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO terms_acceptance (user_id, accepted_at)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET accepted_at = EXCLUDED.accepted_at;
                """,
                (user_id, now),
            )
            conn.commit()
        return {"status": "accepted", "accepted_at": now}
    except Exception as e:
        logger.error(f"[AUTH] Terms acceptance write failed: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save acceptance: {str(e)}")
