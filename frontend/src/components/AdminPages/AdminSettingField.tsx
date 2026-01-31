import { Input } from '../ui/input';
import { Label } from '../ui/label';

interface AdminSettingFieldProps {
  id: string;
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  type?: 'text' | 'number' | 'email';
  description?: string;
  disabled?: boolean;
}

export function AdminSettingField({
  id,
  label,
  value,
  onChange,
  type = 'text',
  description,
  disabled = false,
}: AdminSettingFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-gray-700">
        {label}
      </Label>
      {description && (
        <p className="text-sm text-gray-600">{description}</p>
      )}
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="max-w-md"
      />
    </div>
  );
}
