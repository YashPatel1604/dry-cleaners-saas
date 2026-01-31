import { Input } from "../ui/input";
import { Card } from "../ui/card";
import { Search } from "lucide-react";
import { CustomerRow, type CustomerListItem } from "./CustomersRow";

interface CustomersPageProps {
  customers: CustomerListItem[];
  loading?: boolean;
  error?: string | null;
  query: string;
  onQueryChange: (value: string) => void;
  onViewCustomer: (customerId: string) => void;
}

export function CustomersPage({
  customers,
  loading = false,
  error = null,
  query,
  onQueryChange,
  onViewCustomer,
}: CustomersPageProps) {
  return (
    <div className="max-w-5xl">
      <h1 className="text-3xl mb-6 text-gray-800">Customers</h1>

      <Card className="p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search by name, phone, or email..."
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            className="pl-10"
          />
        </div>
      </Card>

      {loading && (
        <div className="py-12 text-center text-gray-600">Loading customers...</div>
      )}

      {error && !loading && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {!loading && !error && customers.length === 0 && (
        <div className="py-12 text-center text-gray-600">
          {query.trim() ? "No customers match your search." : "No customers found."}
        </div>
      )}

      {!loading && !error && customers.length > 0 && (
        <div className="space-y-3">
          {customers.map((customer) => (
            <CustomerRow
              key={customer.id}
              customer={customer}
              onView={() => onViewCustomer(customer.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
