import { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { AdminSectionHeader } from './AdminSectionHeader';
import { AdminInviteRow } from './AdminInviteRow';
import { AdminEmptyState } from './AdminEmptyState';
import { AdminLoadingState } from './AdminLoadingState';
import { AdminErrorState } from './AdminErrorState';
import { Card } from '../ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { Label } from '../ui/label';

interface Invite {
  id: string;
  email: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

interface AdminInvitesSectionProps {
  invites: Invite[];
  onInvite: (email: string) => void;
  onRevoke: (invite_id: string) => void;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
}

export function AdminInvitesSection({
  invites,
  onInvite,
  onRevoke,
  loading = false,
  error = null,
  empty = false,
}: AdminInvitesSectionProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');

  const handleSubmit = () => {
    if (newEmail) {
      onInvite(newEmail);
      setNewEmail('');
      setIsDialogOpen(false);
    }
  };

  if (loading) {
    return <AdminLoadingState message="Loading invites..." />;
  }

  if (error) {
    return <AdminErrorState error={error} />;
  }

  return (
    <div>
      <AdminSectionHeader
        title="Invites"
        description="Send and manage team invitations"
        action={
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button>Invite</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Send Invitation</DialogTitle>
                <DialogDescription>
                  Send an invitation to join your organization
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter email address"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSubmit}>Invite</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {empty ? (
        <AdminEmptyState
          title="No invites sent"
          description="Send your first invitation to add team members"
          action={
            <Button onClick={() => setIsDialogOpen(true)}>Invite</Button>
          }
        />
      ) : (
        <Card className="p-6">
          {invites.map((invite) => (
            <AdminInviteRow
              key={invite.id}
              {...invite}
              onRevoke={onRevoke}
            />
          ))}
        </Card>
      )}
    </div>
  );
}
