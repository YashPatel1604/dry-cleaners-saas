import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { InventoryForm } from './InventoryForm';
import type { InventoryFormData } from './InventoryForm';

interface InventoryFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: InventoryFormData) => void;
  loading?: boolean;
  error?: string | null;
  initialData?: Partial<InventoryFormData>;
}

export function InventoryFormDialog({
  open,
  onOpenChange,
  onSave,
  loading = false,
  error = null,
  initialData,
}: InventoryFormDialogProps) {
  const title = initialData ? 'Edit Item' : 'Add Item';

  const handleSubmit = (data: InventoryFormData) => {
    onSave(data);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <InventoryForm
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
