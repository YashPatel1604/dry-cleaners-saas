import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { CustomerEditForm } from './CustomerEditForm';
import type { CustomerFormData } from './CustomerEditForm';

interface CustomerEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: CustomerFormData) => void;
  loading?: boolean;
  error?: string | null;
  initialData?: Partial<CustomerFormData>;
}

export function CustomerEditDialog({
  open,
  onOpenChange,
  onSave,
  loading = false,
  error = null,
  initialData,
}: CustomerEditDialogProps) {
  const handleSubmit = (data: CustomerFormData) => {
    onSave(data);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Customer</DialogTitle>
        </DialogHeader>
        <CustomerEditForm
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
          error={error}
          initialData={initialData}
        />
      </DialogContent>
    </Dialog>
  );
}
