import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

type Membership = {
  id: number;
  user: { id: number; username: string };
  role: "OWNER_ADMIN" | "OPERATOR";
  is_active: boolean;
  created_at: string;
};

export default function Team(): JSX.Element {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<"OWNER_ADMIN" | "OPERATOR">("OPERATOR");
  const [error, setError] = useState<string | null>(null);

  const loadMembers = async () => {
    try {
      const resp = await apiJson<Membership[]>("/api/tenant/memberships/");
      setMemberships(resp);
    } catch {
      setError("Unable to load team");
    }
  };

  useEffect(() => {
    loadMembers();
  }, []);

  const addMember = async () => {
    setError(null);
    try {
      await apiJson("/api/tenant/memberships/", {
        method: "POST",
        body: { username, role, is_active: true },
      });
      setUsername("");
      await loadMembers();
    } catch {
      setError("Failed to add member");
    }
  };

  const updateMember = async (userId: number, updates: Partial<Membership>) => {
    await apiJson(`/api/tenant/memberships/${userId}/`, {
      method: "PATCH",
      body: {
        role: updates.role,
        is_active: updates.is_active,
      },
    });
    await loadMembers();
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Team
        </div>
        <h1 className="text-3xl font-semibold">Manage access</h1>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Add member</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <select
            className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value as "OWNER_ADMIN" | "OPERATOR")}
          >
            <option value="OPERATOR">OPERATOR</option>
            <option value="OWNER_ADMIN">OWNER_ADMIN</option>
          </select>
          <Button onClick={addMember}>Add</Button>
        </CardContent>
        {error && <div className="px-6 pb-4 text-sm text-red-600">{error}</div>}
      </Card>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Members</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {memberships.map((member) => (
            <div
              key={member.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2"
            >
              <div>
                <div className="font-medium">{member.user.username}</div>
                <div className="text-xs text-muted-foreground">
                  {member.role} · {member.is_active ? "Active" : "Inactive"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <select
                  className="h-9 rounded-lg border border-input bg-card px-2 text-xs"
                  value={member.role}
                  onChange={(e) =>
                    updateMember(member.user.id, { role: e.target.value as Membership["role"] })
                  }
                >
                  <option value="OPERATOR">OPERATOR</option>
                  <option value="OWNER_ADMIN">OWNER_ADMIN</option>
                </select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateMember(member.user.id, { is_active: !member.is_active })}
                >
                  {member.is_active ? "Deactivate" : "Activate"}
                </Button>
              </div>
            </div>
          ))}
          {memberships.length === 0 && (
            <div className="text-sm text-muted-foreground">No members yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
