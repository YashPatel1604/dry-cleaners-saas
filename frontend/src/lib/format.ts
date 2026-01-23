export function formatCurrency(cents: number | null | undefined): string {
  const value = typeof cents === "number" ? cents : 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value / 100);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
  }).format(date);
}

export function statusTone(status?: string | null): "default" | "success" | "warning" | "danger" | "muted" {
  switch (status) {
    case "READY":
    case "COMPLETED":
    case "PICKED_UP":
      return "success";
    case "IN_PROGRESS":
      return "warning";
    case "CANCELLED":
      return "danger";
    case "RECEIVED":
      return "default";
    default:
      return "muted";
  }
}
