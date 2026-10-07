/**
 * authApi.js — Thin API client for all authentication operations.
 * 
 * All core auth logic lives on the backend. The frontend only:
 *   1. Calls backend endpoints
 *   2. Stores tokens in localStorage
 *   3. Sets axios Authorization header
 * 
 * No Supabase SDK is used for authentication.
 */

import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOKEN_KEY = "quantpilot_access_token";
const REFRESH_KEY = "quantpilot_refresh_token";
const USER_KEY = "quantpilot_user";

// ---------------------------------------------------------------------------
// Token Persistence
// ---------------------------------------------------------------------------

export function getStoredTokens() {
  return {
    accessToken: localStorage.getItem(TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_KEY),
  };
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storeSession(data) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  delete axios.defaults.headers.common["Authorization"];
}

// ---------------------------------------------------------------------------
// Auth API Calls (all hit the backend)
// ---------------------------------------------------------------------------

/** Get the Google OAuth redirect URL from the backend */
export async function getGoogleOAuthUrl() {
  const res = await axios.get(`${API_BASE}/auth/google/url`);
  return res.data.url;
}

/** Exchange the OAuth code for a session (called after redirect) */
export async function exchangeCodeForSession(code) {
  const res = await axios.post(`${API_BASE}/auth/callback`, { code });
  storeSession(res.data);
  return res.data;
}

/** Refresh the access token using the stored refresh token */
export async function refreshAccessToken() {
  const { refreshToken } = getStoredTokens();
  if (!refreshToken) throw new Error("No refresh token available");

  const res = await axios.post(`${API_BASE}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  storeSession(res.data);
  return res.data;
}

/** Get current user info from backend (validates token server-side) */
export async function getCurrentUser() {
  const { accessToken } = getStoredTokens();
  if (!accessToken) return null;

  axios.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;

  try {
    const res = await axios.get(`${API_BASE}/auth/me`);
    return res.data;
  } catch (err) {
    // If 401, try refreshing
    if (err.response?.status === 401) {
      try {
        await refreshAccessToken();
        const res = await axios.get(`${API_BASE}/auth/me`);
        return res.data;
      } catch {
        clearSession();
        return null;
      }
    }
    clearSession();
    return null;
  }
}

/** Sign out through the backend */
export async function signOut() {
  const { accessToken } = getStoredTokens();
  try {
    await axios.post(
      `${API_BASE}/auth/signout`,
      { access_token: accessToken },
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
  } catch {
    // Sign out locally even if backend call fails
  }
  clearSession();
}

// ---------------------------------------------------------------------------
// Terms & Conditions API
// ---------------------------------------------------------------------------

/** Check if the current user has accepted T&C */
export async function checkTermsAccepted() {
  try {
    const res = await axios.get(`${API_BASE}/auth/terms/status`);
    return res.data.accepted;
  } catch {
    return false;
  }
}

/** Accept T&C for the current user */
export async function acceptTerms() {
  const res = await axios.post(`${API_BASE}/auth/terms/accept`);
  return res.data;
}

/** Fetch the T&C content from backend */
export async function getTermsContent() {
  const res = await axios.get(`${API_BASE}/auth/terms/content`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Initialize Session on App Load
// ---------------------------------------------------------------------------

export async function initializeAuth() {
  const { accessToken } = getStoredTokens();
  if (!accessToken) return { user: null, termsAccepted: false };

  const user = await getCurrentUser();
  if (!user) return { user: null, termsAccepted: false };

  const termsAccepted = await checkTermsAccepted();
  return { user, termsAccepted };
}
