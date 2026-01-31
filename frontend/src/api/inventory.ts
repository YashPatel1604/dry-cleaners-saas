import { apiFetch } from "./client";

export type InventoryItemApi = {
  id: number;
  name: string;
  sku?: string;
  unit_price_cents: number;
  is_active: boolean;
  created_at: string;
};

export async function fetchInventoryItems() {
  return apiFetch<InventoryItemApi[]>("/api/inventory-items/");
}

export async function createInventoryItem(payload: {
  name: string;
  sku?: string;
  unit_price_cents: number;
  is_active: boolean;
}) {
  return apiFetch<InventoryItemApi>("/api/inventory-items/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateInventoryItem(
  id: number,
  payload: Partial<{
    name: string;
    sku?: string;
    unit_price_cents: number;
    is_active: boolean;
  }>
) {
  return apiFetch<InventoryItemApi>(`/api/inventory-items/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
