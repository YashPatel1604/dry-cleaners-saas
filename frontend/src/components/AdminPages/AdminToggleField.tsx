import { Switch } from '../ui/switch';
import { Label } from '../ui/label';

interface AdminToggleFieldProps {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  description?: string;
  disabled?: boolean;
}

export function AdminToggleField({
  id,
  label,
  checked,
  onCheckedChange,
  description,
  disabled = false,
}: AdminToggleFieldProps) {
  return (
    <div className="flex items-start justify-between py-4 border-b border-gray-200">
      <div className="flex-1 pr-4">
        <Label htmlFor={id} className="text-gray-900 cursor-pointer">
          {label}
        </Label>
        {description && (
          <p className="text-sm text-gray-600 mt-1">{description}</p>
        )}
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
      />
    </div>
  );
}
