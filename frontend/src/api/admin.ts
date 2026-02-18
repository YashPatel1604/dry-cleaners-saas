import { apiFetch } from "./client";

export type ApiRole = "OWNER_ADMIN" | "OPERATOR";
export type UiRole = "admin" | "manager" | "staff";

export const mapUiRoleToApi = (role: UiRole): ApiRole =>
  role === "admin" ? "OWNER_ADMIN" : "OPERATOR";

export const mapApiRoleToUi = (role: ApiRole): UiRole =>
  role === "OWNER_ADMIN" ? "admin" : "staff";

export type Membership = {
  id: number;
  user: { id: number; username: string };
  role: ApiRole;
  is_active: boolean;
  created_at: string;
};

export type Invite = {
  id: number;
  email: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
  is_active?: boolean;
};

export type TenantSettings = {
  default_turnaround_days: number;
  default_ready_hour: number;
  default_ready_minute: number;
  require_paid_in_full_at_pickup: boolean;
  collects_tax: boolean;
  tax_rate_bps: number;
  order_tag_label_size: "2x1" | "4x2";
  order_tag_copies: number;
};

export type MembershipAuditEvent = {
  id: number;
  created_at: string;
  actor_user_id: number | null;
  subject_user_id: number;
  subject_user_email?: string | null;
  action: string;
  old_role?: string | null;
  new_role?: string | null;
  is_active_before?: boolean | null;
  is_active_after?: boolean | null;
  metadata?: Record<string, unknown> | null;
};

export type ConfigAuditEvent = {
  id: number;
  created_at: string;
  actor_user_id: number | null;
  key: string;
  old_value: string;
  new_value: string;
};

export type InviteAuditEvent = {
  id: number;
  created_at: string;
  actor_user_id: number | null;
  email: string;
  event_type: string;
  metadata?: Record<string, unknown> | null;
};

export async function fetchMembers() {
  return apiFetch<Membership[]>("/api/tenant/memberships/");
}

export async function addMember(input: {
  username: string;
  role: ApiRole;
  is_active?: boolean;
}) {
  return apiFetch<Membership>("/api/tenant/memberships/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateMember(userId: number, payload: {
  role?: ApiRole;
  is_active?: boolean;
}) {
  return apiFetch<Membership>(`/api/tenant/memberships/${userId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function fetchInvites() {
  return apiFetch<Invite[]>("/api/tenant/invites/");
}

export async function createInvite(email: string) {
  return apiFetch<Invite>("/api/tenant/invites/", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function revokeInvite(inviteId: number) {
  return apiFetch<void>(`/api/tenant/invites/${inviteId}/revoke/`, {
    method: "POST",
  });
}

export async function fetchSettings() {
  return apiFetch<TenantSettings>("/api/tenant/defaults/");
}

export async function updateSettings(payload: Partial<TenantSettings>) {
  return apiFetch<TenantSettings>("/api/tenant/defaults/", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function fetchMembershipAudit() {
  return apiFetch<MembershipAuditEvent[]>("/api/tenant/audit/memberships/");
}

export async function fetchConfigAudit() {
  return apiFetch<ConfigAuditEvent[]>("/api/tenant/audit/config/");
}

export async function fetchInviteAudit() {
  return apiFetch<InviteAuditEvent[]>("/api/tenant/audit/invites/");
}
