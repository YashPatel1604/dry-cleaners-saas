import { useEffect, useState } from "react";
import {
  addMember,
  createInvite,
  fetchConfigAudit,
  fetchInviteAudit,
  fetchInvites,
  fetchMembers,
  fetchMembershipAudit,
  fetchSettings,
  mapApiRoleToUi,
  mapUiRoleToApi,
  revokeInvite,
  updateMember,
  updateSettings,
  type Invite as ApiInvite,
  type Membership,
  type MembershipAuditEvent,
  type ConfigAuditEvent,
  type InviteAuditEvent,
  type TenantSettings,
  type UiRole,
} from "../../api/admin";
import { toast } from "../ui/use-toast";
import { AdminMembersSection } from "./AdminMembersSection";
import { AdminInvitesSection } from "./AdminInvitesSection";
import { AdminSettingsSection } from "./AdminSettingsSection";
import { AdminAuditSection } from "./AdminAuditSection";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

interface Member {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface Invite {
  id: string;
  email: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

interface Settings {
  default_turnaround_days: number;
  default_ready_hour: number;
  default_ready_minute: number;
  require_paid_in_full_at_pickup: boolean;
  collects_tax: boolean;
  tax_rate_bps: number;
  order_tag_label_size: "2x1" | "4x2";
  order_tag_copies: number;
}

interface AuditEvent {
  id: string;
  created_at: string;
  action: string;
  actor_user_id: string;
  subject_user_id: string | null;
  metadata: Record<string, any>;
}

interface AdminPageProps {
  members?: Member[];
  invites?: Invite[];
  settings?: Settings;
  audits?: AuditEvent[];
  loading?: boolean;
  error?: string | null;
  onLogout?: () => void;
  onSwitchStore?: () => void;
  canSwitchStore?: boolean;
  onSettingsChange?: (settings: Settings) => void;
}

const defaultSettings: Settings = {
  default_turnaround_days: 2,
  default_ready_hour: 17,
  default_ready_minute: 0,
  require_paid_in_full_at_pickup: false,
  collects_tax: false,
  tax_rate_bps: 0,
  order_tag_label_size: "2x1",
  order_tag_copies: 1,
};

const mapMember = (member: Membership): Member => ({
  id: String(member.user.id),
  username: member.user.username,
  role: mapApiRoleToUi(member.role),
  is_active: member.is_active,
  created_at: member.created_at,
});

const mapInvite = (invite: ApiInvite): Invite => ({
  id: String(invite.id),
  email: invite.email,
  expires_at: invite.expires_at,
  accepted_at: invite.accepted_at ?? null,
  revoked_at: invite.revoked_at ?? null,
  created_at: invite.created_at,
});

const mapMembershipAudit = (event: MembershipAuditEvent): AuditEvent => {
  const actionMap: Record<string, string> = {
    CREATED: "member created",
    ROLE_CHANGED: "role change",
    DEACTIVATED: "member deactivated",
    REACTIVATED: "member reactivated",
  };

  return {
    id: `membership-${event.id}`,
    created_at: event.created_at,
    action: actionMap[event.action] ?? event.action.toLowerCase(),
    actor_user_id: event.actor_user_id ? String(event.actor_user_id) : "",
    subject_user_id: event.subject_user_id ? String(event.subject_user_id) : null,
    metadata: {
      old_role: event.old_role ?? undefined,
      new_role: event.new_role ?? undefined,
      is_active_before: event.is_active_before ?? undefined,
      is_active_after: event.is_active_after ?? undefined,
      ...(event.metadata ?? {}),
    },
  };
};

const mapConfigAudit = (event: ConfigAuditEvent): AuditEvent => ({
  id: `config-${event.id}`,
  created_at: event.created_at,
  action: `config change: ${event.key}`,
  actor_user_id: event.actor_user_id ? String(event.actor_user_id) : "",
  subject_user_id: null,
  metadata: {
    old_value: event.old_value,
    new_value: event.new_value,
  },
});

const mapInviteAudit = (event: InviteAuditEvent): AuditEvent => ({
  id: `invite-${event.id}`,
  created_at: event.created_at,
  action: `invite ${event.event_type.toLowerCase()}`,
  actor_user_id: event.actor_user_id ? String(event.actor_user_id) : "",
  subject_user_id: null,
  metadata: {
    email: event.email,
    ...(event.metadata ?? {}),
  },
});

const toErrorMessage = (err: unknown, fallback: string) =>
  err instanceof Error ? err.message : fallback;

export function AdminPage({
  members: initialMembers = [],
  invites: initialInvites = [],
  settings: initialSettings = defaultSettings,
  audits: initialAudits = [],
  onLogout,
  onSwitchStore,
  canSwitchStore = false,
  onSettingsChange,
}: AdminPageProps) {
  const [activeTab, setActiveTab] = useState("members");

  const [members, setMembers] = useState<Member[]>(initialMembers);
  const [membersLoading, setMembersLoading] = useState(true);
  const [membersError, setMembersError] = useState<string | null>(null);

  const [invites, setInvites] = useState<Invite[]>(initialInvites);
  const [invitesLoading, setInvitesLoading] = useState(true);
  const [invitesError, setInvitesError] = useState<string | null>(null);

  const [settings, setSettings] = useState<Settings>(initialSettings);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  const [audits, setAudits] = useState<AuditEvent[]>(initialAudits);
  const [auditsLoading, setAuditsLoading] = useState(true);

  const loadMembers = async () => {
    setMembersLoading(true);
    setMembersError(null);

    try {
      const data = await fetchMembers();
      setMembers(data.map(mapMember));
    } catch (err) {
      setMembersError(toErrorMessage(err, "Unable to load members."));
    } finally {
      setMembersLoading(false);
    }
  };

  const loadInvites = async () => {
    setInvitesLoading(true);
    setInvitesError(null);

    try {
      const data = await fetchInvites();
      setInvites(data.map(mapInvite));
    } catch (err) {
      setInvitesError(toErrorMessage(err, "Unable to load invites."));
    } finally {
      setInvitesLoading(false);
    }
  };

  const loadSettings = async () => {
    setSettingsError(null);

    try {
      const data = await fetchSettings();
      const mappedSettings = {
        default_turnaround_days: data.default_turnaround_days,
        default_ready_hour: data.default_ready_hour,
        default_ready_minute: data.default_ready_minute,
        require_paid_in_full_at_pickup: data.require_paid_in_full_at_pickup,
        collects_tax: data.collects_tax,
        tax_rate_bps: data.tax_rate_bps,
        order_tag_label_size: data.order_tag_label_size,
        order_tag_copies: data.order_tag_copies,
      };
      setSettings(mappedSettings);
      onSettingsChange?.(mappedSettings);
    } catch (err) {
      setSettingsError(toErrorMessage(err, "Unable to load settings."));
    }
  };

  const loadAudits = async () => {
    setAuditsLoading(true);

    try {
      const [membership, config, invitesData] = await Promise.all([
        fetchMembershipAudit(),
        fetchConfigAudit(),
        fetchInviteAudit(),
      ]);

      const combined = [
        ...membership.map(mapMembershipAudit),
        ...config.map(mapConfigAudit),
        ...invitesData.map(mapInviteAudit),
      ].sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setAudits(combined);
    } catch (err) {
      toast({
        title: "Unable to load audit log.",
        description: toErrorMessage(err, "Audit log is unavailable."),
        variant: "error",
      });
      setAudits([]);
    } finally {
      setAuditsLoading(false);
    }
  };

  useEffect(() => {
    void loadMembers();
    void loadInvites();
    void loadSettings();
    void loadAudits();
  }, []);

  const handleAddMember = async (username: string, role: string) => {
    const mappedRole = mapUiRoleToApi(role as UiRole);
    setMembersLoading(true);

    try {
      await addMember({ username, role: mappedRole, is_active: true });
      await loadMembers();
      toast({ title: "Member added." });
    } catch (err) {
      toast({
        title: "Unable to add member.",
        description: toErrorMessage(err, "Please try again."),
        variant: "error",
      });
    } finally {
      setMembersLoading(false);
    }
  };

  const handleRoleChange = async (user_id: string, role: string) => {
    const mappedRole = mapUiRoleToApi(role as UiRole);
    setMembersLoading(true);

    try {
      await updateMember(Number(user_id), { role: mappedRole });
      await loadMembers();
      toast({ title: "Role updated." });
    } catch (err) {
      toast({
        title: "Unable to update role.",
        description: toErrorMessage(err, "Please try again."),
        variant: "error",
      });
    } finally {
      setMembersLoading(false);
    }
  };

  const handleToggleActive = async (user_id: string, is_active: boolean) => {
    setMembersLoading(true);

    try {
      await updateMember(Number(user_id), { is_active });
      await loadMembers();
      toast({ title: is_active ? "Member activated." : "Member deactivated." });
    } catch (err) {
      toast({
        title: "Unable to update member.",
        description: toErrorMessage(err, "Please try again."),
        variant: "error",
      });
    } finally {
      setMembersLoading(false);
    }
  };

  const handleInvite = async (email: string) => {
    setInvitesLoading(true);

    try {
      await createInvite(email);
      await loadInvites();
      toast({ title: "Invite sent." });
    } catch (err) {
      toast({
        title: "Unable to send invite.",
        description: toErrorMessage(err, "Please try again."),
        variant: "error",
      });
    } finally {
      setInvitesLoading(false);
    }
  };

  const handleRevoke = async (invite_id: string) => {
    setInvitesLoading(true);

    try {
      await revokeInvite(Number(invite_id));
      await loadInvites();
      toast({ title: "Invite revoked." });
    } catch (err) {
      toast({
        title: "Unable to revoke invite.",
        description: toErrorMessage(err, "Please try again."),
        variant: "error",
      });
    } finally {
      setInvitesLoading(false);
    }
  };

  const handleSaveSettings = async (newSettings: Settings) => {
    setSettingsSaving(true);
    setSettingsError(null);

    try {
      const saved = await updateSettings(newSettings as TenantSettings);
      setSettings(saved);
      onSettingsChange?.(saved);
      toast({ title: "Settings saved." });
    } catch (err) {
      setSettingsError(toErrorMessage(err, "Unable to save settings."));
      toast({
        title: "Unable to save settings.",
        description: toErrorMessage(err, "Please try again."),
        variant: "error",
      });
    } finally {
      setSettingsSaving(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <h1 className="text-3xl text-gray-800">Settings</h1>
        <div className="flex items-center gap-3">
          {canSwitchStore && onSwitchStore ? (
            <button
              type="button"
              className="rounded-md border border-gray-200 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              onClick={onSwitchStore}
            >
              Switch Store
            </button>
          ) : null}
          {onLogout ? (
            <button
              type="button"
              className="rounded-md border border-gray-200 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              onClick={onLogout}
            >
              Logout
            </button>
          ) : null}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="invites">Invites</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
        </TabsList>

        <TabsContent value="members">
          <AdminMembersSection
            members={members}
            onAddMember={handleAddMember}
            onRoleChange={handleRoleChange}
            onToggleActive={handleToggleActive}
            loading={membersLoading}
            error={membersError}
            empty={members.length === 0}
          />
        </TabsContent>

        <TabsContent value="invites">
          <AdminInvitesSection
            invites={invites}
            onInvite={handleInvite}
            onRevoke={handleRevoke}
            loading={invitesLoading}
            error={invitesError}
            empty={invites.length === 0}
          />
        </TabsContent>

        <TabsContent value="settings">
          <AdminSettingsSection
            settings={settings}
            onSave={handleSaveSettings}
            saving={settingsSaving}
            error={settingsError}
          />
        </TabsContent>

        <TabsContent value="audit">
          <AdminAuditSection
            events={audits}
            loading={auditsLoading}
            empty={audits.length === 0}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
