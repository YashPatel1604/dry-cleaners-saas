import { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { AdminSectionHeader } from './AdminSectionHeader';
import { AdminMemberRow } from './AdminMemberRow';
import { AdminEmptyState } from './AdminEmptyState';
import { AdminLoadingState } from './AdminLoadingState';
import { AdminErrorState } from './AdminErrorState';
import { Card } from '../ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
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

interface Member {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface AdminMembersSectionProps {
  members: Member[];
  onAddMember: (username: string, role: string) => void;
  onRoleChange: (user_id: string, role: string) => void;
  onToggleActive: (user_id: string, is_active: boolean) => void;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
}

export function AdminMembersSection({
  members,
  onAddMember,
  onRoleChange,
  onToggleActive,
  loading = false,
  error = null,
  empty = false,
}: AdminMembersSectionProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newRole, setNewRole] = useState('staff');

  const handleSubmit = () => {
    if (newUsername) {
      onAddMember(newUsername, newRole);
      setNewUsername('');
      setNewRole('staff');
      setIsDialogOpen(false);
    }
  };

  if (loading) {
    return <AdminLoadingState message="Loading members..." />;
  }

  if (error) {
    return <AdminErrorState error={error} />;
  }

  return (
    <div>
      <AdminSectionHeader
        title="Members"
        description="Manage team members and their roles"
        action={
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button>Add Member</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Member</DialogTitle>
                <DialogDescription>
                  Add a new team member to your organization
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    placeholder="Enter username"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Select value={newRole} onValueChange={setNewRole}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="manager">Manager</SelectItem>
                      <SelectItem value="staff">Staff</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSubmit}>Add Member</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {empty ? (
        <AdminEmptyState
          title="No members yet"
          description="Get started by adding your first team member"
          action={
            <Button onClick={() => setIsDialogOpen(true)}>Add Member</Button>
          }
        />
      ) : (
        <Card className="p-6">
          {members.map((member) => (
            <AdminMemberRow
              key={member.id}
              {...member}
              onRoleChange={onRoleChange}
              onToggleActive={onToggleActive}
            />
          ))}
        </Card>
      )}
    </div>
  );
}
