/**
 * authApi.js — Auth client with backend-first architecture.
 * 
 * Architecture:
 *   - OAuth redirect flow uses Supabase client-side (PKCE requires browser-side code_verifier)
 *   - After session is obtained, tokens are stored locally and sent to backend
 *   - ALL subsequent auth operations (verify, refresh, signout, T&C) go through backend
 *   - Session validation is always server-side via GET /auth/me
 */

import axios from "axios";
import { supabase } from "./supabaseClient";

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

export function storeSession({ access_token, refresh_token, user }) {
  if (access_token) localStorage.setItem(TOKEN_KEY, access_token);
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  if (access_token) {
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
  }
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  delete axios.defaults.headers.common["Authorization"];
  
  // Clear Supabase's default local storage key to prevent ghost sessions
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
      localStorage.removeItem(key);
    }
  }
}

// ---------------------------------------------------------------------------
// OAuth Flow (Supabase client-side — required for PKCE)
// ---------------------------------------------------------------------------

/**
 * Start the Google OAuth flow via Supabase client-side SDK.
 * This is the one operation that MUST happen client-side because
 * Supabase PKCE stores the code_verifier in the browser.
 */
export async function startGoogleOAuth() {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
  });
  if (error) throw error;
}

/**
 * Listen for auth state changes from Supabase (e.g. after OAuth redirect).
 * When a session is detected, capture tokens and store them.
 * Returns an unsubscribe function.
 */
export function onAuthStateChange(callback) {
  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange((_event, session) => {
    if (session) {
      const userData = {
        id: session.user.id,
        email: session.user.email,
        name: session.user.user_metadata?.full_name || "",
        avatar_url: session.user.user_metadata?.avatar_url || "",
      };
      storeSession({
        access_token: session.access_token,
        refresh_token: session.refresh_token,
        user: userData,
      });
      callback(userData, session);
    } else {
      clearSession();
      callback(null, null);
    }
  });

  return () => subscription.unsubscribe();
}

/**
 * Check for an existing Supabase session on app load.
 * If found, capture the tokens and return the user.
 */
export async function getExistingSession() {
  const { data: { session } } = await supabase.auth.getSession();
  if (session) {
    const userData = {
      id: session.user.id,
      email: session.user.email,
      name: session.user.user_metadata?.full_name || "",
      avatar_url: session.user.user_metadata?.avatar_url || "",
    };
    storeSession({
      access_token: session.access_token,
      refresh_token: session.refresh_token,
      user: userData,
    });
    return { user: userData, session };
  }
  return { user: null, session: null };
}

// ---------------------------------------------------------------------------
// Backend-driven Auth Operations
// ---------------------------------------------------------------------------

/** Validate the current token server-side via GET /auth/me */
export async function validateSession() {
  const { accessToken } = getStoredTokens();
  if (!accessToken) return null;

  axios.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;

  try {
    const res = await axios.get(`${API_BASE}/auth/me`);
    return res.data;
  } catch (err) {
    if (err.response?.status === 401) {
      // Try refreshing via Supabase
      try {
        const { data: { session } } = await supabase.auth.refreshSession();
        if (session) {
          storeSession({
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            user: getStoredUser(),
          });
          const res = await axios.get(`${API_BASE}/auth/me`);
          return res.data;
        }
      } catch {
        // Refresh failed
      }
      clearSession();
      return null;
    }
    return null;
  }
}

/** Sign out — revoke on backend AND clear Supabase session */
export async function signOut() {
  const { accessToken } = getStoredTokens();
  if (accessToken) {
    try {
      await axios.post(
        `${API_BASE}/auth/signout`,
        { access_token: accessToken },
        { headers: { Authorization: `Bearer ${accessToken}` } }
      );
    } catch {
      // Backend signout failed, ignore
    }
  }
  
  try {
    await supabase.auth.signOut();
  } catch (err) {
    console.warn("Supabase signout threw an error, clearing locally anyway:", err);
  } finally {
    clearSession();
    // Also clear Supabase's default local storage key to prevent ghost sessions
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
        localStorage.removeItem(key);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Terms & Conditions API (all backend)
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
// Initialize Auth on App Load
// ---------------------------------------------------------------------------

export async function initializeAuth() {
  // 1. Check for existing Supabase session (handles OAuth callback automatically)
  const { user } = await getExistingSession();
  if (!user) return { user: null, termsAccepted: false };

  // 2. Validate the token server-side
  const validatedUser = await validateSession();
  if (!validatedUser) return { user: null, termsAccepted: false };

  // 3. Check T&C acceptance via backend
  const termsAccepted = await checkTermsAccepted();
  return { user: validatedUser, termsAccepted };
}
