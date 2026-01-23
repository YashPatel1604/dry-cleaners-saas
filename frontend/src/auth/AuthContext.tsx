import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { apiFetch, apiJson, ApiError, setAccessToken, setTenantSlug } from "../lib/api";

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function getStoredAccessToken(): string | null {
  try {
    return localStorage.getItem(ACCESS_KEY);
  } catch {
    return null;
  }
}

function getStoredRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

function setRefreshToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(REFRESH_KEY, token);
    } else {
      localStorage.removeItem(REFRESH_KEY);
    }
  } catch {
    // ignore storage errors
  }
}

function clearAuthStorage(): void {
  setAccessToken(null);
  setRefreshToken(null);
  setTenantSlug(null);
}

export function AuthProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [token, setToken] = useState<string | null>(() => getStoredAccessToken());
  const refreshInFlight = useRef<Promise<boolean> | null>(null);

  const logout = useCallback(() => {
    clearAuthStorage();
    setToken(null);
  }, []);

  const refreshAccessToken = useCallback(async (): Promise<boolean> => {
    if (refreshInFlight.current) {
      return refreshInFlight.current;
    }

    const refreshToken = getStoredRefreshToken();
    if (!refreshToken) {
      logout();
      return false;
    }

    const attempt = apiJson<{ access: string }>("/api/auth/refresh/", {
      method: "POST",
      body: { refresh: refreshToken },
      tenant: false,
    })
      .then((data) => {
        if (data?.access) {
          setAccessToken(data.access);
          setToken(data.access);
          return true;
        }
        logout();
        return false;
      })
      .catch(() => {
        logout();
        return false;
      })
      .finally(() => {
        refreshInFlight.current = null;
      });

    refreshInFlight.current = attempt;
    return attempt;
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const payloads: Array<Record<string, string>> = [
      { email, password },
      { username: email, password },
    ];

    let lastError: unknown = null;

    for (const body of payloads) {
      try {
        const response = await apiFetch("/api/auth/token/", {
          method: "POST",
          body,
          tenant: false,
        });

        let parsed: any = null;
        const contentType = response.headers.get("Content-Type") || "";
        if (contentType.includes("application/json")) {
          try {
            parsed = await response.json();
          } catch {
            parsed = null;
          }
        } else {
          try {
            parsed = await response.text();
          } catch {
            parsed = null;
          }
        }

        if (!response.ok) {
          lastError = new ApiError(response.status, parsed);
          continue;
        }

        if (parsed?.access && parsed?.refresh) {
          setAccessToken(parsed.access);
          setRefreshToken(parsed.refresh);
          setToken(parsed.access);
          return;
        }
        lastError = new Error("Missing access/refresh token");
      } catch (err) {
        lastError = err;
      }
    }

    throw lastError ?? new Error("Login failed");
  }, []);

  const isAuthenticated = !!token;

  useEffect(() => {
    const handleUnauthorized = () => {
      refreshAccessToken().then((ok) => {
        if (!ok) {
          logout();
          window.location.assign("/login");
        }
      });
    };

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
    };
  }, [logout, refreshAccessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated,
      login,
      logout,
      refreshAccessToken,
    }),
    [token, isAuthenticated, login, logout, refreshAccessToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
