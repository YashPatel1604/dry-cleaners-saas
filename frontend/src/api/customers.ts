import { clientJson } from "./client";

export type Customer = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type CustomerSearchInput = {
  phone?: string;
  firstName?: string;
  lastName?: string;
};

export type CreateCustomerInput = {
  phone: string;
  firstName: string;
  lastName: string;
  email?: string;
  address?: string;
  preferences?: string;
  popupMessage?: string;
};

function buildSearchQuery(input: CustomerSearchInput): string {
  const phone = input.phone?.trim();
  if (phone) return phone;
  const parts = [input.firstName?.trim(), input.lastName?.trim()].filter(Boolean);
  return parts.join(" ").trim();
}

function buildNotes(input: CreateCustomerInput): string {
  const lines: string[] = [];
  if (input.address?.trim()) {
    lines.push(`Address: ${input.address.trim()}`);
  }
  if (input.preferences?.trim()) {
    lines.push(`Preferences: ${input.preferences.trim()}`);
  }
  if (input.popupMessage?.trim()) {
    lines.push(`Pop-up Message: ${input.popupMessage.trim()}`);
  }
  return lines.join("\n");
}

export async function searchCustomers(input: CustomerSearchInput): Promise<Customer[]> {
  const query = buildSearchQuery(input);
  if (!query) return [];
  try {
    const resp = await clientJson<Customer[]>(
      `/api/customers/search/?q=${encodeURIComponent(query)}`
    );
    return resp;
  } catch {
    return [];
  }
}

export async function createCustomer(input: CreateCustomerInput): Promise<Customer> {
  const name = [input.firstName.trim(), input.lastName.trim()].filter(Boolean).join(" ");
  const notes = buildNotes(input);
  const payload = {
    name,
    phone: input.phone.trim() || null,
    email: input.email?.trim() ? input.email.trim().toLowerCase() : null,
    notes: notes || undefined,
  };
  return clientJson<Customer>("/api/customers/", {
    method: "POST",
    body: payload,
  });
}
