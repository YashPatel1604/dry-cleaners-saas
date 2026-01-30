import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { apiJson } from "../lib/api";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { formatCurrency, formatDateTime, statusTone } from "../lib/format";

type Order = {
  id: number;
  customer: number | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  status: string;
  due_at: string | null;
  notes: string;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  paid_cents: number;
  net_paid_cents: number;
  balance_due_cents: number;
  change_due_cents: number;
  settled_at: string | null;
  created_at: string;
  received_at: string | null;
  in_progress_at: string | null;
  ready_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  picked_up_at: string | null;
};

type Receipt = {
  id: number;
  status: string;
  due_at: string | null;
  notes: string;
  created_at: string;
  settled_at: string | null;
  customer: { id: number; name: string; phone: string | null; email: string | null } | null;
  items: Array<{
    id: number;
    item: number;
    item_name: string;
    sku: string;
    quantity: number;
    unit_price_cents: number;
    line_total_cents: number;
  }>;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  paid_cents: number;
  adjustments_net_cents: number;
  net_paid_cents: number;
  balance_due_cents: number;
  change_due_cents: number;
  payments: Array<{
    id: number;
    method: string;
    status: string;
    direction: string;
    amount_cents: number;
    reference: string;
    note: string;
    created_at: string;
  }>;
  adjustments: Array<{
    id: number;
    kind: string;
    status: string;
    direction: string;
    amount_cents: number;
    reference: string | null;
    note: string;
    created_at: string;
  }>;
  pdf_url?: string;
};

type Note = {
  id: number;
  note: string;
  created_at: string;
  author_id: number | null;
  author_username: string | null;
};

type TimelineEvent = {
  id: string;
  event_type: string;
  created_at: string;
  title: string;
  summary: string;
  meta: Record<string, any>;
};

type InventoryItem = {
  id: number;
  name: string;
  sku: string;
  unit_price_cents: number;
  is_active: boolean;
};

type Customer = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
};

const STATUS_OPTIONS = ["RECEIVED", "IN_PROGRESS", "READY", "COMPLETED", "PICKED_UP", "CANCELLED"];

export default function OrderDetail(): JSX.Element {
  const { id } = useParams();
  const navigate = useNavigate();
  const orderId = Number(id);

  const [order, setOrder] = useState<Order | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [itemId, setItemId] = useState("");
  const [itemQty, setItemQty] = useState("1");
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("CASH");
  const [paymentRef, setPaymentRef] = useState("");
  const [paymentNote, setPaymentNote] = useState("");
  const [pickupAmount, setPickupAmount] = useState("");
  const [pickupMethod, setPickupMethod] = useState("CASH");
  const [pickupRef, setPickupRef] = useState("");
  const [pickupNote, setPickupNote] = useState("");
  const [cashOutAmount, setCashOutAmount] = useState("");
  const [cashOutMethod, setCashOutMethod] = useState("CASH");
  const [cashOutRef, setCashOutRef] = useState("");
  const [cashOutNote, setCashOutNote] = useState("");
  const [receiptEmail, setReceiptEmail] = useState("");
  const [adjustmentAmount, setAdjustmentAmount] = useState("");
  const [adjustmentKind, setAdjustmentKind] = useState("OTHER");
  const [adjustmentDirection, setAdjustmentDirection] = useState("OUT");
  const [adjustmentNote, setAdjustmentNote] = useState("");
  const [newNote, setNewNote] = useState("");
  const [customerQuery, setCustomerQuery] = useState("");
  const [customerResults, setCustomerResults] = useState<Customer[]>([]);

  const fetchAll = useCallback(async () => {
    if (!orderId) return;
    setLoading(true);
    setError(null);
    try {
      const [orderData, receiptData, notesData, timelineData, inventoryData] = await Promise.all([
        apiJson<Order>(`/api/orders/${orderId}/`),
        apiJson<Receipt>(`/api/orders/${orderId}/receipt/`),
        apiJson<Note[]>(`/api/orders/${orderId}/notes/`),
        apiJson<TimelineEvent[]>(`/api/orders/${orderId}/timeline/`),
        apiJson<InventoryItem[]>("/api/inventory-items/"),
      ]);
      setOrder(orderData);
      setReceipt(receiptData);
      setNotes(notesData);
      setTimeline(timelineData);
      setInventory(inventoryData);
    } catch {
      setError("Unable to load order");
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const statusBadge = useMemo(() => statusTone(order?.status), [order?.status]);

  const addItem = async () => {
    if (!itemId) return;
    const qty = Math.max(1, parseInt(itemQty || "1", 10));
    await apiJson("/api/order-items/", {
      method: "POST",
      body: { order: orderId, item: Number(itemId), quantity: qty },
    });
    setItemId("");
    setItemQty("1");
    await fetchAll();
  };

  const updateItem = async (orderItemId: number, quantity: number) => {
    await apiJson(`/api/order-items/${orderItemId}/`, {
      method: "PATCH",
      body: { quantity },
    });
    await fetchAll();
  };

  const deleteItem = async (orderItemId: number) => {
    await apiJson(`/api/order-items/${orderItemId}/`, { method: "DELETE" });
    await fetchAll();
  };

  const addPayment = async () => {
    const amount = parseInt(paymentAmount || "0", 10);
    if (!amount) return;
    await apiJson("/api/payments/", {
      method: "POST",
      body: {
        order: orderId,
        amount_cents: amount,
        method: paymentMethod,
        reference: paymentRef,
        note: paymentNote,
      },
    });
    setPaymentAmount("");
    setPaymentRef("");
    setPaymentNote("");
    await fetchAll();
  };

  const addPickupPayment = async () => {
    const amount = parseInt(pickupAmount || "0", 10);
    if (!amount) return;
    await apiJson(`/api/orders/${orderId}/pickup-payment/`, {
      method: "POST",
      body: {
        amount_cents: amount,
        method: pickupMethod,
        reference: pickupRef,
        note: pickupNote,
      },
    });
    setPickupAmount("");
    setPickupRef("");
    setPickupNote("");
    await fetchAll();
  };

  const addCashOut = async () => {
    const amount = parseInt(cashOutAmount || "0", 10);
    if (!amount) return;
    await apiJson(`/api/orders/${orderId}/cash-out/`, {
      method: "POST",
      body: {
        amount_cents: amount,
        method: cashOutMethod,
        reference: cashOutRef,
        note: cashOutNote,
      },
    });
    setCashOutAmount("");
    setCashOutRef("");
    setCashOutNote("");
    await fetchAll();
  };

  const emailReceipt = async () => {
    await apiJson(`/api/orders/${orderId}/receipt/email/`, {
      method: "POST",
      body: { to_email: receiptEmail },
    });
    setReceiptEmail("");
  };

  const addAdjustment = async () => {
    const amount = parseInt(adjustmentAmount || "0", 10);
    if (!amount) return;
    await apiJson("/api/adjustments/", {
      method: "POST",
      body: {
        order: orderId,
        kind: adjustmentKind,
        direction: adjustmentDirection,
        amount_cents: amount,
        note: adjustmentNote,
      },
    });
    setAdjustmentAmount("");
    setAdjustmentNote("");
    await fetchAll();
  };

  const addNote = async () => {
    const noteText = newNote.trim();
    if (!noteText) return;
    await apiJson(`/api/orders/${orderId}/notes/`, {
      method: "POST",
      body: { note: noteText },
    });
    setNewNote("");
    await fetchAll();
  };

  const markReady = async () => {
    await apiJson(`/api/orders/${orderId}/mark_ready/`, { method: "POST" });
    await fetchAll();
  };

  const pickup = async () => {
    await apiJson(`/api/orders/${orderId}/pickup/`, { method: "POST", body: {} });
    await fetchAll();
  };

  const settle = async () => {
    await apiJson(`/api/orders/${orderId}/settle/`, { method: "POST" });
    await fetchAll();
  };

  const setStatus = async (value: string) => {
    await apiJson(`/api/orders/${orderId}/`, {
      method: "PATCH",
      body: { status: value },
    });
    await fetchAll();
  };

  const searchCustomers = async (query: string) => {
    setCustomerQuery(query);
    if (query.trim().length < 2) {
      setCustomerResults([]);
      return;
    }
    const resp = await apiJson<Customer[]>(`/api/tenant/customers/search/?q=${encodeURIComponent(query)}`);
    setCustomerResults(resp);
  };

  const setCustomer = async (customerId: number | null) => {
    await apiJson(`/api/orders/${orderId}/customer/`, {
      method: "PATCH",
      body: { customer_id: customerId },
    });
    await fetchAll();
  };

  if (!orderId) {
    return (
      <Card>
        <CardContent className="p-6">Order not found.</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">Order</div>
          <h1 className="text-3xl font-semibold">Ticket #{orderId}</h1>
          {order && (
            <div className="text-sm text-muted-foreground">
              Opened {formatDateTime(order.created_at)}
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => navigate("/orders")}>
            Back to orders
          </Button>
          {receipt?.pdf_url && (
            <Button asChild variant="secondary">
              <a href={receipt.pdf_url} target="_blank" rel="noreferrer">
                Receipt PDF
              </a>
            </Button>
          )}
          <Button asChild variant="outline">
            <a href={`/api/orders/${orderId}/ticket.pdf/`} target="_blank" rel="noreferrer">
              Ticket PDF
            </a>
          </Button>
          <Button asChild variant="outline">
            <a href={`/api/orders/${orderId}/labels/`} target="_blank" rel="noreferrer">
              Labels JSON
            </a>
          </Button>
          <Button onClick={markReady}>Mark ready</Button>
          <Button variant="secondary" onClick={pickup}>
            Mark pickup
          </Button>
          <Button variant="outline" onClick={settle}>
            Settle
          </Button>
        </div>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}
      {loading && <div className="text-sm text-muted-foreground">Loading order...</div>}

      {order && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card className="glass-panel border-border/70">
            <CardHeader className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <CardTitle>Order overview</CardTitle>
              <Badge variant={statusBadge}>{order.status}</Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Due</div>
                  <div className="font-medium">{order.due_at ? formatDateTime(order.due_at) : "Not set"}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Settlement</div>
                  <div className="font-medium">{order.settled_at ? formatDateTime(order.settled_at) : "Open"}</div>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-4 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Total</div>
                  <div className="font-semibold">{formatCurrency(order.total_cents)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Paid</div>
                  <div className="font-semibold">{formatCurrency(order.net_paid_cents)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Balance</div>
                  <div className="font-semibold">{formatCurrency(order.balance_due_cents)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Change</div>
                  <div className="font-semibold">{formatCurrency(order.change_due_cents)}</div>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Status
                </label>
                <select
                  className="h-9 rounded-lg border border-input bg-card px-3 text-sm"
                  value={order.status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-panel border-border/70">
            <CardHeader>
              <CardTitle>Customer</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-muted-foreground">Linked customer</div>
                <div className="flex items-center gap-2">
                  <div className="font-medium">{order.customer_name || "Unassigned"}</div>
                  {order.customer && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/customers/${order.customer}`)}
                    >
                      Open profile
                    </Button>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {order.customer_email || order.customer_phone || ""}
                </div>
              </div>
              <div className="space-y-2">
                <Input
                  placeholder="Search customers by name, phone, or email"
                  value={customerQuery}
                  onChange={(e) => searchCustomers(e.target.value)}
                />
                {customerResults.length > 0 && (
                  <div className="space-y-2">
                    {customerResults.map((cust) => (
                      <button
                        key={cust.id}
                        className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-left text-xs hover:bg-muted/60"
                        onClick={() => setCustomer(cust.id)}
                      >
                        <div className="font-medium">{cust.name}</div>
                        <div className="text-muted-foreground">
                          {cust.phone || cust.email || "No contact"}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                <Button variant="outline" onClick={() => setCustomer(null)}>
                  Clear customer
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Items</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-[1.2fr_0.6fr_auto]">
              <select
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
                value={itemId}
                onChange={(e) => setItemId(e.target.value)}
              >
                <option value="">Select item</option>
                {inventory.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({formatCurrency(item.unit_price_cents)})
                  </option>
                ))}
              </select>
              <Input
                type="number"
                min="1"
                value={itemQty}
                onChange={(e) => setItemQty(e.target.value)}
              />
              <Button onClick={addItem}>Add</Button>
            </div>
            {receipt?.items?.length ? (
              <div className="space-y-3">
                {receipt.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2"
                  >
                    <div>
                      <div className="font-medium">{item.item_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.quantity} x {formatCurrency(item.unit_price_cents)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min="1"
                        className="w-20"
                        value={item.quantity}
                        onChange={(e) => updateItem(item.id, Number(e.target.value))}
                      />
                      <Button variant="outline" onClick={() => deleteItem(item.id)}>
                        Remove
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No items yet.</div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Payments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2">
              <Input
                placeholder="Amount (cents)"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
              />
              <select
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                <option value="CASH">CASH</option>
                <option value="CARD">CARD</option>
                <option value="ONLINE">ONLINE</option>
                <option value="OTHER">OTHER</option>
              </select>
              <Input
                placeholder="Reference (optional)"
                value={paymentRef}
                onChange={(e) => setPaymentRef(e.target.value)}
              />
              <Input
                placeholder="Note"
                value={paymentNote}
                onChange={(e) => setPaymentNote(e.target.value)}
              />
              <Button onClick={addPayment}>Add payment</Button>
            </div>
            <div className="space-y-2 text-sm">
              {(receipt?.payments ?? []).map((p) => (
                <div key={p.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{p.method}</span>
                    <span>{formatCurrency(p.amount_cents)}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{p.direction} · {p.status}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 border-t border-border/60 pt-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Pickup payment
              </div>
              <div className="grid gap-2 mt-2">
                <Input
                  placeholder="Amount (cents)"
                  value={pickupAmount}
                  onChange={(e) => setPickupAmount(e.target.value)}
                />
                <select
                  className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
                  value={pickupMethod}
                  onChange={(e) => setPickupMethod(e.target.value)}
                >
                  <option value="CASH">CASH</option>
                  <option value="CARD">CARD</option>
                  <option value="ONLINE">ONLINE</option>
                  <option value="OTHER">OTHER</option>
                </select>
                <Input
                  placeholder="Reference"
                  value={pickupRef}
                  onChange={(e) => setPickupRef(e.target.value)}
                />
                <Input
                  placeholder="Note"
                  value={pickupNote}
                  onChange={(e) => setPickupNote(e.target.value)}
                />
                <Button variant="secondary" onClick={addPickupPayment}>
                  Record pickup payment
                </Button>
              </div>
            </div>
            <div className="mt-4 border-t border-border/60 pt-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Cash out
              </div>
              <div className="grid gap-2 mt-2">
                <Input
                  placeholder="Amount (cents)"
                  value={cashOutAmount}
                  onChange={(e) => setCashOutAmount(e.target.value)}
                />
                <select
                  className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
                  value={cashOutMethod}
                  onChange={(e) => setCashOutMethod(e.target.value)}
                >
                  <option value="CASH">CASH</option>
                  <option value="CARD">CARD</option>
                  <option value="ONLINE">ONLINE</option>
                  <option value="OTHER">OTHER</option>
                </select>
                <Input
                  placeholder="Reference"
                  value={cashOutRef}
                  onChange={(e) => setCashOutRef(e.target.value)}
                />
                <Input
                  placeholder="Note"
                  value={cashOutNote}
                  onChange={(e) => setCashOutNote(e.target.value)}
                />
                <Button variant="outline" onClick={addCashOut}>
                  Record cash out
                </Button>
              </div>
            </div>
            <div className="mt-4 border-t border-border/60 pt-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Email receipt
              </div>
              <div className="grid gap-2 mt-2">
                <Input
                  placeholder="Recipient email"
                  value={receiptEmail}
                  onChange={(e) => setReceiptEmail(e.target.value)}
                />
                <Button variant="outline" onClick={emailReceipt}>
                  Send receipt email
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Adjustments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2">
              <Input
                placeholder="Amount (cents)"
                value={adjustmentAmount}
                onChange={(e) => setAdjustmentAmount(e.target.value)}
              />
              <select
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
                value={adjustmentKind}
                onChange={(e) => setAdjustmentKind(e.target.value)}
              >
                <option value="REFUND">REFUND</option>
                <option value="CHARGEBACK">CHARGEBACK</option>
                <option value="WRITE_OFF">WRITE_OFF</option>
                <option value="CREDIT_APPLIED">CREDIT_APPLIED</option>
                <option value="OTHER">OTHER</option>
              </select>
              <select
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
                value={adjustmentDirection}
                onChange={(e) => setAdjustmentDirection(e.target.value)}
              >
                <option value="OUT">OUT</option>
                <option value="IN">IN</option>
              </select>
              <Input
                placeholder="Note"
                value={adjustmentNote}
                onChange={(e) => setAdjustmentNote(e.target.value)}
              />
              <Button variant="secondary" onClick={addAdjustment}>
                Add adjustment
              </Button>
            </div>
            <div className="space-y-2 text-sm">
              {(receipt?.adjustments ?? []).map((adj) => (
                <div key={adj.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{adj.kind}</span>
                    <span>{formatCurrency(adj.amount_cents)}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{adj.direction} · {adj.status}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder="Add a note for the team"
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
            />
            <Button onClick={addNote}>Add note</Button>
            <div className="space-y-2 text-sm">
              {notes.map((note) => (
                <div key={note.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                  <div className="text-xs text-muted-foreground">
                    {note.author_username || "system"} · {formatDateTime(note.created_at)}
                  </div>
                  <div className="font-medium">{note.note}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Timeline</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {timeline.length === 0 && <div className="text-muted-foreground">No events yet.</div>}
          {timeline.map((event) => (
            <div key={event.id} className="rounded-lg border border-border bg-muted/40 px-3 py-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{event.event_type}</span>
                <span>{formatDateTime(event.created_at)}</span>
              </div>
              <div className="font-medium">{event.title}</div>
              <div className="text-xs text-muted-foreground">{event.summary}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
