import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { formatCurrency, formatDateTime } from "../lib/format";

type InventoryItem = {
  id: number;
  name: string;
  sku: string;
  unit_price_cents: number;
  is_active: boolean;
  created_at: string;
};

export default function Inventory(): JSX.Element {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadItems = async () => {
    try {
      const resp = await apiJson<InventoryItem[]>("/api/inventory-items/");
      setItems(resp);
    } catch {
      setError("Unable to load inventory");
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const createItem = async () => {
    setError(null);
    const unitPrice = parseInt(price || "0", 10);
    if (!name.trim() || !unitPrice) return;
    try {
      await apiJson("/api/inventory-items/", {
        method: "POST",
        body: {
          name,
          sku,
          unit_price_cents: unitPrice,
          is_active: true,
        },
      });
      setName("");
      setSku("");
      setPrice("");
      await loadItems();
    } catch {
      setError("Failed to create inventory item");
    }
  };

  const toggleActive = async (item: InventoryItem) => {
    await apiJson(`/api/inventory-items/${item.id}/`, {
      method: "PATCH",
      body: { is_active: !item.is_active },
    });
    await loadItems();
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Inventory
        </div>
        <h1 className="text-3xl font-semibold">Service catalog</h1>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Add item</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[1.2fr_1fr_1fr_auto]">
          <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="SKU" value={sku} onChange={(e) => setSku(e.target.value)} />
          <Input
            placeholder="Unit price (cents)"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
          <Button onClick={createItem}>Create</Button>
        </CardContent>
        {error && <div className="px-6 pb-4 text-sm text-red-600">{error}</div>}
      </Card>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Items</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-white/70 px-4 py-3"
            >
              <div>
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-muted-foreground">
                  {item.sku || "No SKU"} · Added {formatDateTime(item.created_at)}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-sm font-semibold">{formatCurrency(item.unit_price_cents)}</div>
                <Button variant="outline" onClick={() => toggleActive(item)}>
                  {item.is_active ? "Deactivate" : "Activate"}
                </Button>
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <div className="text-sm text-muted-foreground">No items yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
