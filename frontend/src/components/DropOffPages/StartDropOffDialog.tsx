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
  imageUrl?: string;
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
      <DialogContent className="w-[95vw] max-w-[95vw] p-0 sm:max-w-[1120px]">
        <DialogHeader>
          <DialogTitle className="px-6 pt-6">Start Drop‑Off</DialogTitle>
        </DialogHeader>
        <div className="px-6 pb-6 pt-2">
          <OrderCreateForm
            customer={customer}
            items={items}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            loading={loading}
            error={error}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
