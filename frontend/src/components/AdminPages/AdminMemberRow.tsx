import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Badge } from '../ui/badge';

interface AdminMemberRowProps {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  onRoleChange: (user_id: string, role: string) => void;
  onToggleActive: (user_id: string, is_active: boolean) => void;
}

export function AdminMemberRow({
  id,
  username,
  role,
  is_active,
  created_at,
  onRoleChange,
  onToggleActive,
}: AdminMemberRowProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-200">
      <div className="flex-1">
        <div className="flex items-center gap-3">
          <p className="text-gray-900">{username}</p>
          {!is_active && (
            <Badge variant="secondary" className="text-xs">
              Inactive
            </Badge>
          )}
        </div>
        <p className="text-sm text-gray-600">
          Member since {new Date(created_at).toLocaleDateString()}
        </p>
      </div>

      <div className="flex items-center gap-4">
        <Select value={role} onValueChange={(value) => onRoleChange(id, value)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Select role" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="admin">Admin</SelectItem>
            <SelectItem value="manager">Manager</SelectItem>
            <SelectItem value="staff">Staff</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant={is_active ? 'outline' : 'default'}
          size="sm"
          onClick={() => onToggleActive(id, !is_active)}
        >
          {is_active ? 'Deactivate' : 'Activate'}
        </Button>
      </div>
    </div>
  );
}
