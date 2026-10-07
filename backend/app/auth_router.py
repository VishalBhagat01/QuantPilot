"""
Authentication API Router — Distributed endpoint layer for auth operations.

All core logic lives in backend/app/auth.py. This router exposes
clean REST endpoints consumed by the frontend thin-client.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from backend.app.auth import (
    verify_user,
    get_google_oauth_url,
    exchange_code_for_session,
    refresh_session,
    sign_out,
    get_current_user_info,
    check_terms_accepted,
    accept_terms,
)
from backend.db.db import get_db, release_db, check_db_availability

router = APIRouter(prefix="/auth", tags=["Authentication"])


class CodeExchangeRequest(BaseModel):
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class SignOutRequest(BaseModel):
    access_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Public Endpoints (no token needed)
# ---------------------------------------------------------------------------

@router.get("/google/url")
def google_oauth_url():
    """
    [PUBLIC] Generate the Google OAuth redirect URL.
    Frontend calls this, gets a URL, and redirects the browser window.
    """
    return get_google_oauth_url()


@router.post("/callback")
def oauth_callback(req: CodeExchangeRequest):
    """
    [PUBLIC] Exchange the authorization code from Google OAuth for a session.
    Returns access_token, refresh_token, and basic user info.
    """
    return exchange_code_for_session(req.code)


@router.post("/refresh")
def token_refresh(req: RefreshRequest):
    """
    [PUBLIC] Refresh an expired access_token using the refresh_token.
    """
    return refresh_session(req.refresh_token)


# ---------------------------------------------------------------------------
# Protected Endpoints (Bearer token required)
# ---------------------------------------------------------------------------

@router.get("/me")
def get_me(request: Request, user=Depends(verify_user)):
    """
    [PROTECTED] Return the currently authenticated user's profile.
    """
    return get_current_user_info(request)


@router.post("/signout")
def logout(req: SignOutRequest, user=Depends(verify_user)):
    """
    [PROTECTED] Revoke the current session server-side.
    """
    user_id = user.id if hasattr(user, "id") else user.get("id")
    token = req.access_token or ""
    return sign_out(token)


@router.get("/terms/status")
def terms_status(user=Depends(verify_user)):
    """
    [PROTECTED] Check if the current user has accepted Terms & Conditions.
    """
    user_id = user.id if hasattr(user, "id") else user.get("id")

    if not check_db_availability():
        # If DB is unavailable, assume accepted for dev convenience
        return {"accepted": True}

    conn = get_db()
    try:
        accepted = check_terms_accepted(user_id, conn)
        return {"accepted": accepted}
    finally:
        release_db(conn)


@router.post("/terms/accept")
def accept_terms_endpoint(user=Depends(verify_user)):
    """
    [PROTECTED] Record that the user accepted Terms & Conditions.
    """
    user_id = user.id if hasattr(user, "id") else user.get("id")

    if not check_db_availability():
        return {"status": "accepted", "accepted_at": "dev_mode"}

    conn = get_db()
    try:
        return accept_terms(user_id, conn)
    finally:
        release_db(conn)


# ---------------------------------------------------------------------------
# Terms & Conditions Content
# ---------------------------------------------------------------------------

@router.get("/terms/content")
def get_terms_content():
    """
    [PUBLIC] Return the Terms & Conditions document.
    Content is served from the backend so it can be updated server-side
    without redeploying the frontend.
    """
    return {
        "title": "Terms & Conditions",
        "version": "1.0",
        "last_updated": "2026-10-07",
        "sections": [
            {
                "heading": "1. Acceptance of Terms",
                "body": (
                    "By accessing and using QuantPilot (the \"Service\"), you acknowledge that you have read, "
                    "understood, and agree to be bound by these Terms & Conditions. If you do not agree, "
                    "you must not access or use the Service."
                ),
            },
            {
                "heading": "2. Description of Service",
                "body": (
                    "QuantPilot is an AI-powered financial intelligence and research platform. "
                    "The Service provides real-time market data retrieval, technical analysis, "
                    "chart pattern detection, and simulated paper trading capabilities. "
                    "QuantPilot is designed for informational and educational purposes only."
                ),
            },
            {
                "heading": "3. No Financial Advice",
                "body": (
                    "The information provided by QuantPilot does NOT constitute financial, investment, "
                    "trading, or tax advice. All analysis, signals, predictions, and recommendations "
                    "generated by the AI agent are for research and educational purposes only. "
                    "You should consult a qualified financial advisor before making any investment decisions. "
                    "Past performance does not guarantee future results."
                ),
            },
            {
                "heading": "4. Paper Trading & Simulated Execution",
                "body": (
                    "QuantPilot integrates with Alpaca Markets for paper (simulated) trading. "
                    "All trades executed through the platform are simulated unless explicitly "
                    "configured otherwise. You acknowledge that simulated trading results may "
                    "differ significantly from real-market performance. The Service is not "
                    "responsible for any financial losses incurred from live trading."
                ),
            },
            {
                "heading": "5. User Accounts & Authentication",
                "body": (
                    "You are responsible for maintaining the security of your account credentials. "
                    "You must not share your login information with third parties. "
                    "You are solely responsible for all activity that occurs under your account. "
                    "We reserve the right to suspend or terminate accounts that violate these terms."
                ),
            },
            {
                "heading": "6. Data & Privacy",
                "body": (
                    "We collect and store your queries, analysis history, and trading simulations "
                    "to provide and improve the Service. Your data is stored securely in our "
                    "database infrastructure. We do not sell your personal data to third parties. "
                    "Market data is sourced from third-party providers (Yahoo Finance, Finnhub, Alpha Vantage) "
                    "and is subject to their respective terms of service."
                ),
            },
            {
                "heading": "7. AI-Generated Content Disclaimer",
                "body": (
                    "QuantPilot uses large language models (LLMs) and computer vision models "
                    "to generate analysis and insights. AI-generated content may contain errors, "
                    "hallucinations, or inaccuracies. You should independently verify any "
                    "critical information before acting on it. The Service makes no warranties "
                    "regarding the accuracy, completeness, or reliability of AI-generated content."
                ),
            },
            {
                "heading": "8. Limitation of Liability",
                "body": (
                    "To the maximum extent permitted by law, QuantPilot, its creators, and affiliates "
                    "shall not be liable for any indirect, incidental, special, consequential, or punitive "
                    "damages, including but not limited to loss of profits, data, or goodwill, "
                    "arising from your use of the Service. The total liability shall not exceed "
                    "the amount paid by you for the Service in the 12 months prior to the claim."
                ),
            },
            {
                "heading": "9. Acceptable Use",
                "body": (
                    "You agree not to: (a) use the Service for any unlawful purpose; "
                    "(b) attempt to gain unauthorized access to any part of the Service; "
                    "(c) use automated scripts to overload or abuse the API; "
                    "(d) reverse engineer or decompile any component of the Service; "
                    "(e) use the Service to manipulate markets or engage in fraudulent trading."
                ),
            },
            {
                "heading": "10. Modifications to Terms",
                "body": (
                    "We reserve the right to modify these Terms at any time. Material changes "
                    "will be communicated through the Service interface. Continued use after "
                    "changes constitutes acceptance of the updated Terms."
                ),
            },
            {
                "heading": "11. Governing Law",
                "body": (
                    "These Terms shall be governed by and construed in accordance with the laws "
                    "of India. Any disputes arising from these Terms shall be subject to the "
                    "exclusive jurisdiction of the courts in India."
                ),
            },
        ],
    }
