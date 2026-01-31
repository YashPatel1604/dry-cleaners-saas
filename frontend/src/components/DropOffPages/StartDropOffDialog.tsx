import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { OrderCreateForm } from './OrderCreateForm';

interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
}

interface InventoryItemOption {
  id: string;
  name: string;
  sku?: string;
  price: number;
}

interface StartDropOffDialogProps {
  customer: Customer | null;
  items: InventoryItemOption[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: {
    dueDate: string;
    notes: string;
    items: { itemId: string; quantity: number }[];
    payment?: {
      amount: number;
      method: "CASH" | "CARD" | "ONLINE" | "OTHER";
      reference?: string;
    };
  }) => void;
  loading?: boolean;
  error?: string | null;
}

export function StartDropOffDialog({
  customer,
  items,
  open,
  onOpenChange,
  onCreate,
  loading = false,
  error = null,
}: StartDropOffDialogProps) {
  if (!customer) return null;

  const handleSubmit = (data: {
    dueDate: string;
    notes: string;
    items: { itemId: string; quantity: number }[];
    payment?: {
      amount: number;
      method: "CASH" | "CARD" | "ONLINE" | "OTHER";
      reference?: string;
    };
  }) => {
    onCreate(data);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Start Drop‑Off</DialogTitle>
        </DialogHeader>
        <OrderCreateForm
          customer={customer}
          items={items}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
          error={error}
        />
      </DialogContent>
    </Dialog>
  );
}
