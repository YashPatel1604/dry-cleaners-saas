import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatDateTime } from "../lib/format";

type MembershipEvent = {
  id: number;
  created_at: string;
  actor_user_id: number | null;
  subject_user_id: number | null;
  subject_user_email: string;
  action: string;
  old_role: string | null;
  new_role: string | null;
  is_active_before: boolean | null;
  is_active_after: boolean | null;
  metadata: Record<string, any>;
};

type ConfigEvent = {
  id: number;
  created_at: string;
  actor_user_id: number | null;
  key: string;
  old_value: string | null;
  new_value: string | null;
  metadata: Record<string, any>;
};

type InviteEvent = {
  id: number;
  created_at: string;
  actor_user_id: number | null;
  email: string;
  event_type: string;
  metadata: Record<string, any>;
};

export default function Audit(): JSX.Element {
  const [membershipEvents, setMembershipEvents] = useState<MembershipEvent[]>([]);
  const [configEvents, setConfigEvents] = useState<ConfigEvent[]>([]);
  const [inviteEvents, setInviteEvents] = useState<InviteEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiJson<MembershipEvent[]>("/api/tenant/audit/memberships/"),
      apiJson<ConfigEvent[]>("/api/tenant/audit/config/"),
      apiJson<InviteEvent[]>("/api/tenant/audit/invites/"),
    ])
      .then(([members, configs, invites]) => {
        setMembershipEvents(members);
        setConfigEvents(configs);
        setInviteEvents(invites);
      })
      .catch(() => setError("Unable to load audit events"));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Audit
        </div>
        <h1 className="text-3xl font-semibold">Security activity log</h1>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Memberships</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {membershipEvents.map((event) => (
              <div key={event.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                <div className="font-medium">{event.action}</div>
                <div className="text-xs text-muted-foreground">
                  Subject {event.subject_user_id || event.subject_user_email || "unknown"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatDateTime(event.created_at)}
                </div>
              </div>
            ))}
            {membershipEvents.length === 0 && (
              <div className="text-sm text-muted-foreground">No membership events.</div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {configEvents.map((event) => (
              <div key={event.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                <div className="font-medium">{event.key}</div>
                <div className="text-xs text-muted-foreground">
                  {event.old_value} → {event.new_value}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatDateTime(event.created_at)}
                </div>
              </div>
            ))}
            {configEvents.length === 0 && (
              <div className="text-sm text-muted-foreground">No config events.</div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Invites</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {inviteEvents.map((event) => (
              <div key={event.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                <div className="font-medium">{event.event_type}</div>
                <div className="text-xs text-muted-foreground">{event.email}</div>
                <div className="text-xs text-muted-foreground">
                  {formatDateTime(event.created_at)}
                </div>
              </div>
            ))}
            {inviteEvents.length === 0 && (
              <div className="text-sm text-muted-foreground">No invite events.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
