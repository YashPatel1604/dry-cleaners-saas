import { useState } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger } from '../ui/select';
import { Calendar, Package, Shirt, Sparkles, ShoppingBag } from 'lucide-react';

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

  const normalizeKeyword = (value: string) => value.toLowerCase().trim();
  const getItemIcon = (name: string) => {
    const keyword = normalizeKeyword(name);
    if (keyword.includes("shirt") || keyword.includes("blouse")) return Shirt;
    if (keyword.includes("pant") || keyword.includes("trouser")) return ShoppingBag;
    if (keyword.includes("dress") || keyword.includes("gown")) return Sparkles;
    return Package;
  };
  const getDefaultImagePath = (name: string) => {
    const keyword = normalizeKeyword(name);
    if (keyword.includes("shirt") || keyword.includes("blouse")) return "/item-art/shirt.svg";
    if (keyword.includes("pant") || keyword.includes("trouser")) return "/item-art/pants.svg";
    if (keyword.includes("dress") || keyword.includes("gown")) return "/item-art/dress.svg";
    return "/item-art/default.svg";
  };
  const getTileColors = (name: string) => {
    const keyword = normalizeKeyword(name);
    if (keyword.includes("shirt")) {
      return {
        wrapper: "from-sky-100 to-blue-200",
        icon: "text-blue-700",
      };
    }
    if (keyword.includes("pant") || keyword.includes("trouser")) {
      return {
        wrapper: "from-amber-100 to-orange-200",
        icon: "text-orange-700",
      };
    }
    if (keyword.includes("dress")) {
      return {
        wrapper: "from-emerald-100 to-lime-200",
        icon: "text-emerald-700",
      };
    }
    return {
      wrapper: "from-slate-100 to-slate-200",
      icon: "text-slate-700",
    };
  };

  const incrementItem = (itemId: string) => {
    setItemQuantities((current) => ({
      ...current,
      [itemId]: (current[itemId] ?? 0) + 1,
    }));
  };

  const decrementItem = (itemId: string) => {
    setItemQuantities((current) => ({
      ...current,
      [itemId]: Math.max(0, (current[itemId] ?? 0) - 1),
    }));
  };
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
    <form onSubmit={handleSubmit} className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <section className="space-y-4 rounded-xl border border-gray-200 bg-gray-50 p-4 lg:sticky lg:top-0 lg:h-[70vh] lg:overflow-y-auto">
        <div className="space-y-2">
          <h3 className="text-gray-900">Customer info</h3>
          <div className="space-y-2 rounded-lg border border-gray-200 bg-white p-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Name</p>
              <p className="text-gray-900">{customer.name}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Phone</p>
              <p className="text-gray-900">{customer.phone}</p>
            </div>
            {customer.email && (
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">Email</p>
                <p className="text-gray-900">{customer.email}</p>
              </div>
            )}
          </div>
        </div>

        <div>
          <Label htmlFor="dueDate">Due Date</Label>
          <div className="relative mt-2">
            <Input
              id="dueDate"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="pr-10"
            />
            <Calendar className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Order summary</Label>
          <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
            <p className="text-sm text-gray-600">Selected items</p>
            {selectedItems.length === 0 ? (
              <p className="text-sm text-gray-500">No items selected yet.</p>
            ) : (
              <ul className="mt-2 space-y-1">
                {selectedItems.map((selection) => {
                  const selectedItem = items.find((item) => item.id === selection.itemId);
                  if (!selectedItem) return null;
                  return (
                    <li key={selection.itemId} className="flex items-center justify-between text-sm">
                      <span className="text-gray-800">{selectedItem.name}</span>
                      <span className="text-gray-600">x{selection.quantity}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
          {estimatedTotal > 0 && (
            <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
              <p className="text-xs uppercase tracking-wide text-blue-600">Estimated total</p>
              <p className="text-xl text-blue-900">${estimatedTotal.toFixed(2)}</p>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <Label>Payment (optional)</Label>
          <div className="grid gap-2 sm:grid-cols-[1fr_150px]">
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
                <SelectItem value="">Method</SelectItem>
                <SelectItem value="CASH">Cash</SelectItem>
                <SelectItem value="CARD">Card</SelectItem>
                <SelectItem value="ONLINE">Online</SelectItem>
                <SelectItem value="OTHER">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Input
            value={paymentReference}
            onChange={(e) => setPaymentReference(e.target.value)}
            placeholder="Reference (optional)"
          />
          {paymentMethod === "CASH" && (
            <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
              <p className="text-sm text-gray-600">Cashback due</p>
              <p className="text-lg text-gray-900">
                {cashBackDue > 0 ? `$${cashBackDue.toFixed(2)}` : "$0.00"}
              </p>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="notes">Notes</Label>
          <Textarea
            id="notes"
            placeholder="Add any special instructions or notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={4}
          />
        </div>

        {(localError || error) && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-800">{localError || error}</p>
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <Button type="submit" className="flex-1" disabled={loading}>
            {loading ? 'Creating...' : 'CREATE ORDER'}
          </Button>
          <Button type="button" onClick={onCancel} variant="outline" className="flex-1" disabled={loading}>
            CANCEL
          </Button>
        </div>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-4 lg:h-[70vh] lg:overflow-y-auto">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-gray-900">Tap item image to add</h3>
          <p className="text-sm text-gray-500">
            {selectedItems.reduce((sum, item) => sum + item.quantity, 0)} pieces selected
          </p>
        </div>

        {items.length === 0 ? (
          <p className="text-sm text-gray-600">No inventory items available.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((item) => {
              const Icon = getItemIcon(item.name);
              const colors = getTileColors(item.name);
              const quantity = itemQuantities[item.id] ?? 0;
              const imagePath = item.imageUrl || getDefaultImagePath(item.name);

              return (
                <div
                  key={item.id}
                  className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm"
                >
                  <button
                    type="button"
                    onClick={() => incrementItem(item.id)}
                    className={`group relative flex h-36 w-full items-center justify-center bg-gradient-to-br ${colors.wrapper} transition hover:brightness-95`}
                    title={`Add ${item.name}`}
                  >
                    <img
                      src={imagePath}
                      alt={item.name}
                      className="h-full w-full object-cover"
                      onError={(event) => {
                        const fallbackPath = getDefaultImagePath(item.name);
                        if (event.currentTarget.src.endsWith(fallbackPath)) return;
                        event.currentTarget.src = fallbackPath;
                      }}
                    />
                    <div className="absolute inset-0 bg-black/0 transition group-hover:bg-black/5" />
                    <div className="absolute left-2 top-2 rounded-full bg-white/90 p-2 shadow-sm">
                      <Icon className={`h-4 w-4 ${colors.icon}`} />
                    </div>
                    <span className="absolute right-2 top-2 rounded-full bg-white/90 px-2 py-1 text-xs text-gray-700">
                      Click to add
                    </span>
                  </button>
                  <div className="space-y-2 p-3">
                    <div>
                      <p className="text-gray-900">{item.name}</p>
                      <p className="text-xs text-gray-500">
                        {item.sku ? `SKU: ${item.sku} • ` : ""}${item.price.toFixed(2)}
                      </p>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => decrementItem(item.id)}
                          className="h-8 w-8 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                        >
                          -
                        </button>
                        <span className="min-w-[24px] text-center text-sm text-gray-900">{quantity}</span>
                        <button
                          type="button"
                          onClick={() => incrementItem(item.id)}
                          className="h-8 w-8 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                        >
                          +
                        </button>
                      </div>
                      <p className="text-sm text-gray-600">Subtotal ${(item.price * quantity).toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </form>
  );
}
