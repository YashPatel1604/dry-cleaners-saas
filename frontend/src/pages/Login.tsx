import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function Login(): JSX.Element {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email.trim(), password);
      navigate("/select-tenant", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.body) {
        const body = err.body as any;
        const detail = body?.detail;
        const nonField = Array.isArray(body?.non_field_errors)
          ? body.non_field_errors.join(" ")
          : body?.non_field_errors;
        setError(detail || nonField || "Login failed");
      } else {
        setError("Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <Card className="w-full max-w-md glass-panel border-border/70">
        <CardContent className="p-6 space-y-5">
          <div>
            <div className="text-xs uppercase tracking-[0.35em] text-muted-foreground/70">
              Dry Cleaners Console
            </div>
            <h1 className="text-3xl font-semibold">Welcome back</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Sign in with your email or username to continue.
            </p>
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">Email or username</Label>
              <Input
                id="email"
                type="text"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="owner@location.com or username"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && <div className="text-sm text-red-600">{error}</div>}

            <Button className="w-full" type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
