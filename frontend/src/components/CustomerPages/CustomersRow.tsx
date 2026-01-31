import { ChevronRight } from "lucide-react";

export interface CustomerListItem {
  id: string;
  name: string;
  phone: string;
  email?: string;
  created_at: string;
}

interface CustomerRowProps {
  customer: CustomerListItem;
  onView: () => void;
}

export function CustomerRow({ customer, onView }: CustomerRowProps) {
  return (
    <button
      type="button"
      onClick={onView}
      className="w-full rounded-lg border border-gray-200 p-4 text-left hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div>
            <p className="text-sm text-gray-600">Customer</p>
            <p className="text-gray-900">{customer.name}</p>
          </div>
          <div className="flex flex-wrap gap-6 text-sm text-gray-600">
            <span>{customer.phone || "—"}</span>
            <span>{customer.email || "—"}</span>
            <span>{customer.created_at}</span>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-gray-400" />
      </div>
    </button>
  );
}
