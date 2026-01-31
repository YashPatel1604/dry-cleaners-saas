import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Input } from "../ui/input";
import { Button } from "../ui/button";

interface InventoryItemOption {
  id: string;
  name: string;
  sku?: string;
  price: number;
}

interface OrderItemEdit {
  itemId: string;
  quantity: number;
}

interface OrderItemsEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: InventoryItemOption[];
  initialItems: OrderItemEdit[];
  onSave: (items: OrderItemEdit[]) => void;
  loading?: boolean;
  error?: string | null;
}

export function OrderItemsEditorDialog({
  open,
  onOpenChange,
  items,
  initialItems,
  onSave,
  loading = false,
  error = null,
}: OrderItemsEditorDialogProps) {
  const [itemQuantities, setItemQuantities] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!open) return;
    const next: Record<string, number> = {};
    initialItems.forEach((item) => {
      next[item.itemId] = item.quantity;
    });
    setItemQuantities(next);
  }, [initialItems, open]);

  const handleSave = () => {
    const selectedItems = Object.entries(itemQuantities)
      .map(([itemId, quantity]) => ({ itemId, quantity }))
      .filter((item) => item.quantity > 0);
    onSave(selectedItems);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Items</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {items.length === 0 ? (
            <p className="text-sm text-gray-600">No inventory items available.</p>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                >
                  <div>
                    <p className="text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-500">
                      {item.sku ? `SKU: ${item.sku} • ` : ""}
                      ${item.price.toFixed(2)}
                    </p>
                  </div>
                  <Input
                    type="number"
                    min={0}
                    value={itemQuantities[item.id] ?? ""}
                    onChange={(event) =>
                      setItemQuantities({
                        ...itemQuantities,
                        [item.id]: Math.max(0, Number(event.target.value)),
                      })
                    }
                    className="w-20 text-right"
                    placeholder="0"
                  />
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button type="button" className="flex-1" onClick={handleSave} disabled={loading}>
              {loading ? "Saving..." : "Save Changes"}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
