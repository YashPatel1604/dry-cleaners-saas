import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

interface AdminInviteRowProps {
  id: string;
  email: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
  onRevoke: (invite_id: string) => void;
}

export function AdminInviteRow({
  id,
  email,
  expires_at,
  accepted_at,
  revoked_at,
  created_at,
  onRevoke,
}: AdminInviteRowProps) {
  const getStatus = () => {
    if (revoked_at) return { label: 'Revoked', variant: 'destructive' as const };
    if (accepted_at) return { label: 'Accepted', variant: 'default' as const };
    if (new Date(expires_at) < new Date()) return { label: 'Expired', variant: 'secondary' as const };
    return { label: 'Pending', variant: 'outline' as const };
  };

  const status = getStatus();
  const canRevoke = !accepted_at && !revoked_at && new Date(expires_at) > new Date();

  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-200">
      <div className="flex-1">
        <div className="flex items-center gap-3">
          <p className="text-gray-900">{email}</p>
          <Badge variant={status.variant}>{status.label}</Badge>
        </div>
        <p className="text-sm text-gray-600">
          Sent {new Date(created_at).toLocaleDateString()} • 
          Expires {new Date(expires_at).toLocaleDateString()}
        </p>
      </div>

      <div className="flex items-center gap-4">
        {canRevoke && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onRevoke(id)}
          >
            Revoke
          </Button>
        )}
      </div>
    </div>
  );
}
