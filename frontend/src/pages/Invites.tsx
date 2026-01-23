import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { formatDateTime } from "../lib/format";

type Invite = {
  id: number;
  email: string;
  expires_at: string;
  token?: string;
};

export default function Invites(): JSX.Element {
  const [email, setEmail] = useState("");
  const [invites, setInvites] = useState<Invite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tokenReveal, setTokenReveal] = useState<string | null>(null);

  const loadInvites = async () => {
    try {
      const resp = await apiJson<Invite[]>("/api/tenant/invites/");
      setInvites(resp);
    } catch {
      setError("Unable to load invites");
    }
  };

  useEffect(() => {
    loadInvites();
  }, []);

  const createInvite = async () => {
    setError(null);
    try {
      const resp = await apiJson<Invite>("/api/tenant/invites/", {
        method: "POST",
        body: { email },
      });
      setEmail("");
      setTokenReveal(resp.token || null);
      await loadInvites();
    } catch {
      setError("Failed to create invite");
    }
  };

  const revokeInvite = async (inviteId: number) => {
    await apiJson(`/api/tenant/invites/${inviteId}/revoke/`, { method: "POST" });
    await loadInvites();
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Invites
        </div>
        <h1 className="text-3xl font-semibold">Invite team members</h1>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Create invite</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <Input
              placeholder="operator@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Button onClick={createInvite} disabled={!email.trim()}>
              Send invite
            </Button>
          </div>
          {tokenReveal && (
            <div className="rounded-xl border border-border bg-white/70 px-3 py-2 text-xs">
              Invite token (debug): {tokenReveal}
            </div>
          )}
          {error && <div className="text-sm text-red-600">{error}</div>}
        </CardContent>
      </Card>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Active invites</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {invites.map((invite) => (
            <div key={invite.id} className="rounded-xl border border-border bg-white/70 px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium">{invite.email}</div>
                  <div className="text-xs text-muted-foreground">
                    Expires {formatDateTime(invite.expires_at)}
                  </div>
                </div>
                <Button variant="outline" onClick={() => revokeInvite(invite.id)}>
                  Revoke
                </Button>
              </div>
            </div>
          ))}
          {invites.length === 0 && (
            <div className="text-sm text-muted-foreground">No invites yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
