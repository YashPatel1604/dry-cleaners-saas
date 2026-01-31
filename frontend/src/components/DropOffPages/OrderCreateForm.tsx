import { useState } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger } from '../ui/select';
import { Calendar } from 'lucide-react';

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

interface OrderCreateFormProps {
  customer: Customer;
  items: InventoryItemOption[];
  onSubmit: (data: {
    dueDate: string;
    notes: string;
    items: { itemId: string; quantity: number }[];
    payment?: {
      amount: number;
      method: "CASH" | "CARD" | "ONLINE" | "OTHER";
      reference?: string;
    };
  }) => void;
  onCancel: () => void;
  loading?: boolean;
  error?: string | null;
}

export function OrderCreateForm({
  customer,
  items,
  onSubmit,
  onCancel,
  loading = false,
  error = null,
}: OrderCreateFormProps) {
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [itemQuantities, setItemQuantities] = useState<Record<string, number>>({});
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<"" | "CASH" | "CARD" | "ONLINE" | "OTHER">("");
  const [paymentReference, setPaymentReference] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const selectedItems = Object.entries(itemQuantities)
    .map(([itemId, quantity]) => ({ itemId, quantity }))
    .filter((item) => item.quantity > 0);
  const estimatedTotal = selectedItems.reduce((sum, selection) => {
    const item = items.find((option) => option.id === selection.itemId);
    if (!item) return sum;
    return sum + item.price * selection.quantity;
  }, 0);
  const parsedPaymentAmount = Number(paymentAmount);
  const cashBackDue =
    paymentMethod === "CASH" && estimatedTotal > 0 && parsedPaymentAmount > estimatedTotal
      ? parsedPaymentAmount - estimatedTotal
      : 0;
  const effectivePaymentAmount =
    paymentMethod === "CASH" && estimatedTotal > 0 && parsedPaymentAmount > estimatedTotal
      ? estimatedTotal
      : parsedPaymentAmount;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amountValue = parsedPaymentAmount;
    if (paymentAmount && (!amountValue || amountValue <= 0)) {
      setLocalError("Enter a valid payment amount.");
      return;
    }

    if (amountValue > 0 && !paymentMethod) {
      setLocalError("Select a payment method.");
      return;
    }

    if (
      amountValue > 0 &&
      paymentMethod &&
      paymentMethod !== "CASH" &&
      estimatedTotal > 0 &&
      amountValue > estimatedTotal
    ) {
      setLocalError("Amount exceeds estimated total.");
      return;
    }

    setLocalError(null);

    onSubmit({
      dueDate,
      notes,
      items: selectedItems,
      payment:
        amountValue > 0 && paymentMethod
          ? {
              amount: effectivePaymentAmount,
              method: paymentMethod,
              reference: paymentReference.trim() ? paymentReference.trim() : undefined,
            }
          : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Customer Summary Block */}
      <div className="bg-gray-50 p-4 rounded-lg space-y-2">
        <div>
          <p className="text-sm text-gray-600">Name</p>
          <p className="text-gray-900">{customer.name}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Phone</p>
          <p className="text-gray-900">{customer.phone}</p>
        </div>
        {customer.email && (
          <div>
            <p className="text-sm text-gray-600">Email</p>
            <p className="text-gray-900">{customer.email}</p>
          </div>
        )}
      </div>

      {/* Form Fields */}
      <div>
        <Label htmlFor="dueDate">Due Date</Label>
        <div className="relative">
          <Input
            id="dueDate"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="pr-10"
          />
          <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      <div>
        <Label>Items</Label>
        {items.length === 0 ? (
          <p className="text-sm text-gray-600 mt-2">
            No inventory items available.
          </p>
        ) : (
          <div className="space-y-3 mt-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
              >
                <div>
                  <p className="text-gray-900">{item.name}</p>
                  <p className="text-xs text-gray-500">
                    {item.sku ? `SKU: ${item.sku} • ` : ""}${item.price.toFixed(2)}
                  </p>
                </div>
                <Input
                  type="number"
                  min={0}
                  value={itemQuantities[item.id] ?? ""}
                  onChange={(e) =>
                    setItemQuantities({
                      ...itemQuantities,
                      [item.id]: Math.max(0, Number(e.target.value)),
                    })
                  }
                  className="w-20 text-right"
                  placeholder="0"
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-3">
        <Label>Payment (optional)</Label>
        <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
          <Input
            type="number"
            min={0}
            step="0.01"
            value={paymentAmount}
            onChange={(e) => setPaymentAmount(e.target.value)}
            placeholder="Amount"
          />
          <Select
            value={paymentMethod}
            onValueChange={(value) => setPaymentMethod(value as typeof paymentMethod)}
          >
            <SelectTrigger />
            <SelectContent>
              <SelectItem value="">Select method</SelectItem>
              <SelectItem value="CASH">Cash</SelectItem>
              <SelectItem value="CARD">Card</SelectItem>
              <SelectItem value="ONLINE">Online</SelectItem>
              <SelectItem value="OTHER">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {estimatedTotal > 0 && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
            <p className="text-sm text-gray-600">Estimated total</p>
            <p className="text-lg text-gray-900">${estimatedTotal.toFixed(2)}</p>
          </div>
        )}
        <Input
          value={paymentReference}
          onChange={(e) => setPaymentReference(e.target.value)}
          placeholder="Reference (optional)"
        />
        {paymentMethod === "CASH" && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
            <p className="text-sm text-gray-600">Cashback due</p>
            <p className="text-lg text-gray-900">
              {cashBackDue > 0 ? `$${cashBackDue.toFixed(2)}` : "$0.00"}
            </p>
          </div>
        )}
      </div>

      <div>
        <Label htmlFor="notes">Notes</Label>
        <Textarea
          id="notes"
          placeholder="Add any special instructions or notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
        />
      </div>

      {/* Error Message */}
      {(localError || error) && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{localError || error}</p>
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-3 pt-2">
        <Button type="submit" className="flex-1" disabled={loading}>
          {loading ? 'Creating...' : 'CREATE ORDER'}
        </Button>
        <Button type="button" onClick={onCancel} variant="outline" className="flex-1" disabled={loading}>
          CANCEL
        </Button>
      </div>
    </form>
  );
}
