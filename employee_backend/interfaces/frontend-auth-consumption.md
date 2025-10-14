# Frontend Auth Consumption Guide

Purpose:
Ensure the frontend reads `access_token` from POST /auth/login, stores it, and handles errors clearly when the token is absent.

Backend contract:
- POST /auth/login (200) returns JSON:
  {
    "access_token": "<non-empty string>",
    "token_type": "bearer"
  }
- On invalid credentials, returns 401 with structured error JSON:
  {"error": {"code": 401, "message": "Invalid credentials", "correlationId": "..."}}
- CORS headers and Vary: Origin are present on both success and error responses.

Example authApi.login (React/TypeScript):
// PUBLIC_INTERFACE
export async function login(email: string, password: string): Promise<string> {
  /** Authenticate and return the JWT access token string. Throws on failures with clear messages. */
  const baseUrl = process.env.REACT_APP_API_BASE_URL; // Must be set in frontend .env
  if (!baseUrl) {
    throw new Error("API base URL is not configured.");
  }
  const res = await fetch(`${baseUrl}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  // Fast path: HTTP errors
  if (!res.ok) {
    let errMsg = "Login failed.";
    try {
      const body = await res.json();
      if (body?.error?.message) errMsg = body.error.message;
      // Optionally surface correlationId for support
      if (body?.error?.correlationId) {
        errMsg += ` (Ref: ${body.error.correlationId})`;
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(errMsg);
  }

  // Success path
  const data = await res.json();
  if (!data?.access_token || typeof data.access_token !== "string" || data.access_token.trim() === "") {
    throw new Error("Login succeeded but token is missing from response.");
  }
  return data.access_token;
}

Example AuthContext usage:
import React from "react";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  loginWithCredentials: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = React.createContext<AuthContextValue>({
  token: null,
  isAuthenticated: false,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  loginWithCredentials: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(() => {
    try {
      return localStorage.getItem("auth_token");
    } catch {
      return null;
    }
  });

  const loginWithCredentials = React.useCallback(async (email: string, password: string) => {
    const t = await login(email, password);
    setToken(t);
    try {
      localStorage.setItem("auth_token", t);
    } catch {
      // Storage may be blocked; proceed with memory token but warn user
      console.warn("Unable to persist auth token; session may not survive page reloads.");
    }
    // redirect to protected route
    window.location.replace("/dashboard");
  }, []);

  const logout = React.useCallback(() => {
    setToken(null);
    try {
      localStorage.removeItem("auth_token");
    } catch {
      // ignore
    }
    window.location.replace("/login");
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: Boolean(token),
        loginWithCredentials,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

Login form handler guardrails:
- Display server-provided error message if present (401: "Invalid credentials").
- If access_token missing, show: "Login succeeded but token was missing. Please try again or contact support."

Notes:
- Set REACT_APP_API_BASE_URL in the frontend .env (e.g., http://localhost:3002).
- Ensure Axios/fetch includes credentials if needed for CORS scenarios.
