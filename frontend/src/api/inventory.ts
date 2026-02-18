import { apiFetch } from "./client";

export type InventoryItemApi = {
  id: number;
  name: string;
  sku?: string;
  image_url?: string;
  unit_price_cents: number;
  is_active: boolean;
  created_at: string;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export function resolveInventoryImageUrl(imageUrl?: string): string {
  if (!imageUrl) return "";
  if (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")) {
    return imageUrl;
  }
  if (imageUrl.startsWith("/") && API_BASE) {
    return `${API_BASE}${imageUrl}`;
  }
  return imageUrl;
}

export async function fetchInventoryItems() {
  return apiFetch<InventoryItemApi[]>("/api/inventory-items/");
}

export async function createInventoryItem(payload: {
  name: string;
  sku?: string;
  unit_price_cents: number;
  is_active: boolean;
  image?: File | null;
}) {
  const body = new FormData();
  body.append("name", payload.name);
  body.append("sku", payload.sku ?? "");
  body.append("unit_price_cents", String(payload.unit_price_cents));
  body.append("is_active", String(payload.is_active));
  if (payload.image) {
    body.append("image", payload.image);
  }

  return apiFetch<InventoryItemApi>("/api/inventory-items/", {
    method: "POST",
    body,
  });
}

export async function updateInventoryItem(
  id: number,
  payload: Partial<{
    name: string;
    sku?: string;
    unit_price_cents: number;
    is_active: boolean;
    image?: File | null;
    clear_image?: boolean;
  }>
) {
  if (payload.image) {
    const body = new FormData();
    if (payload.name !== undefined) body.append("name", payload.name);
    if (payload.sku !== undefined) body.append("sku", payload.sku);
    if (payload.unit_price_cents !== undefined) {
      body.append("unit_price_cents", String(payload.unit_price_cents));
    }
    if (payload.is_active !== undefined) {
      body.append("is_active", String(payload.is_active));
    }
    body.append("image", payload.image);

    return apiFetch<InventoryItemApi>(`/api/inventory-items/${id}/`, {
      method: "PATCH",
      body,
    });
  }

  const jsonPayload: Record<string, unknown> = {};
  if (payload.name !== undefined) jsonPayload.name = payload.name;
  if (payload.sku !== undefined) jsonPayload.sku = payload.sku;
  if (payload.unit_price_cents !== undefined) {
    jsonPayload.unit_price_cents = payload.unit_price_cents;
  }
  if (payload.is_active !== undefined) {
    jsonPayload.is_active = payload.is_active;
  }
  if (payload.clear_image) {
    jsonPayload.image = null;
  }

  return apiFetch<InventoryItemApi>(`/api/inventory-items/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(jsonPayload),
  });
}
