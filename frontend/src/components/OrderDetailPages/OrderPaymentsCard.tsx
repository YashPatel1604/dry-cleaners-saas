import { useState } from "react";
import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "../ui/select";

export interface Payment {
  id: string;
  method: "cash" | "card" | "online" | "other";
  amount: number;
  status: "captured" | "void";
  timestamp: string;
}

interface OrderPaymentsCardProps {
  payments: Payment[];
  totalPaid: number;
  changeDue: number;
  balanceDue: number;
  allowCollect?: boolean;
  collecting?: boolean;
  collectError?: string | null;
  onCollectPayment?: (payload: {
    amount: number;
    method: "CASH" | "CARD" | "ONLINE" | "OTHER";
    reference?: string;
  }) => void;
}

export function OrderPaymentsCard({ 
  payments, 
  totalPaid, 
  changeDue, 
  balanceDue,
  allowCollect = false,
  collecting = false,
  collectError = null,
  onCollectPayment,
}: OrderPaymentsCardProps) {
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<"CASH" | "CARD" | "ONLINE" | "OTHER">("CASH");
  const [reference, setReference] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const parsedAmount = Number(amount);
  const cashBackDue =
    method === "CASH" && parsedAmount > 0 && parsedAmount > balanceDue
      ? parsedAmount - balanceDue
      : 0;
  const effectiveAmount =
    method === "CASH" && parsedAmount > 0 && parsedAmount > balanceDue
      ? balanceDue
      : parsedAmount;

  const getMethodLabel = (method: Payment["method"]): string => {
    if (method === "cash") return "Cash";
    if (method === "card") return "Card";
    if (method === "online") return "Online";
    return "Other";
  };

  const getStatusVariant = (status: Payment["status"]): "default" | "secondary" => {
    return status === 'captured' ? 'default' : 'secondary';
  };

  const getStatusLabel = (status: Payment["status"]): string => {
    return status === 'captured' ? 'Captured' : 'Void';
  };

  const handleCollect = () => {
    if (!onCollectPayment) return;
    const parsed = Number(amount);
    if (!parsed || parsed <= 0) {
      setLocalError("Enter a payment amount.");
      return;
    }
    if (balanceDue <= 0) {
      setLocalError("Balance due is $0.");
      return;
    }
    if (method !== "CASH" && parsed > balanceDue) {
      setLocalError("Amount exceeds balance due.");
      return;
    }
    setLocalError(null);
    onCollectPayment({
      amount: effectiveAmount,
      method,
      reference: reference.trim() ? reference.trim() : undefined,
    });
  };

  return (
    <Card className="p-6">
      <h2 className="text-xl text-gray-800 mb-4">Payments</h2>

      {allowCollect && (
        <div className="space-y-3 mb-6">
          <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
            <div>
              <Label htmlFor="paymentAmount">Amount</Label>
              <Input
                id="paymentAmount"
                type="number"
                min={0}
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.00"
              />
            </div>
            <div>
              <Label>Method</Label>
              <Select value={method} onValueChange={(value) => setMethod(value as typeof method)}>
                <SelectTrigger />
                <SelectContent>
                  <SelectItem value="CASH">Cash</SelectItem>
                  <SelectItem value="CARD">Card</SelectItem>
                  <SelectItem value="ONLINE">Online</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label htmlFor="paymentReference">Reference (optional)</Label>
            <Input
              id="paymentReference"
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              placeholder="Receipt # or note"
            />
          </div>
          {method === "CASH" && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
              <p className="text-sm text-gray-600">Cashback due</p>
              <p className="text-lg text-gray-900">
                {cashBackDue > 0 ? `$${cashBackDue.toFixed(2)}` : "$0.00"}
              </p>
            </div>
          )}
          {(localError || collectError) && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{localError || collectError}</p>
            </div>
          )}
          <Button type="button" onClick={handleCollect} disabled={collecting}>
            {collecting ? "Recording..." : "Record Payment"}
          </Button>
        </div>
      )}
      
      {payments.length === 0 ? (
        <p className="text-gray-600 text-center py-8">No payments recorded</p>
      ) : (
        <div className="space-y-4">
          {/* Payment rows */}
          {payments.map((payment) => (
            <div key={payment.id} className="flex items-center justify-between border-b border-gray-200 pb-3">
              <div>
                <p className="text-gray-900">{getMethodLabel(payment.method)}</p>
                <p className="text-sm text-gray-600">{payment.timestamp}</p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-gray-900">${payment.amount.toFixed(2)}</p>
                <Badge variant={getStatusVariant(payment.status)}>
                  {getStatusLabel(payment.status)}
                </Badge>
              </div>
            </div>
          ))}

          {/* Totals section */}
          <div className="border-t border-gray-300 pt-4 mt-4 space-y-2">
            <div className="flex justify-between">
              <p className="text-gray-700">Total Paid</p>
              <p className="text-gray-900">${totalPaid.toFixed(2)}</p>
            </div>
            <div className="flex justify-between">
              <p className="text-gray-700">Change Due</p>
              <p className="text-gray-900">${changeDue.toFixed(2)}</p>
            </div>
            <div className="flex justify-between">
              <p className="text-gray-700">Balance Due</p>
              <p className="text-xl text-gray-900">${balanceDue.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
