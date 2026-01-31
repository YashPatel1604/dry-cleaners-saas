import { useEffect, useState } from 'react';
import { OrderCard } from './OrderCard';
import { OrdersEmptyState } from './OrdersEmptyState';
import { OrdersFilters } from './OrdersFilters';
import { Loader2 } from 'lucide-react';

interface Order {
  id: string;
  customer_name: string;
  phone: string;
  status: 'in-progress' | 'ready' | 'picked-up' | 'cancelled';
  invoice_number: string;
  total: number;
  created_at: string;
}

interface OrdersPageProps {
  orders: Order[];
  loading?: boolean;
  error?: string | null;
  filters?: {
    status: string;
    query: string;
  };
  onFilterChange?: (filters: { status: string; query: string }) => void;
  onCreate?: () => void;
  onViewOrder?: (orderId: string) => void;
}

export function OrdersPage({
  orders,
  loading = false,
  error = null,
  filters = { status: 'all', query: '' },
  onFilterChange,
  onCreate,
  onViewOrder,
}: OrdersPageProps) {
  const [localFilters, setLocalFilters] = useState(filters);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleStatusChange = (status: string) => {
    const newFilters = { ...localFilters, status };
    setLocalFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleQueryChange = (query: string) => {
    const newFilters = { ...localFilters, query };
    setLocalFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleOpenOrder = (orderId: string) => {
    if (onViewOrder) {
      onViewOrder(orderId);
    }
  };

  const handleCreate = () => {
    if (onCreate) {
      onCreate();
    }
  };

  // Filter orders based on status and query
  const filteredOrders = orders.filter((order) => {
    // Status filter
    if (localFilters.status !== 'all' && order.status !== localFilters.status) {
      return false;
    }

    // Query filter
    if (localFilters.query) {
      const query = localFilters.query.toLowerCase();
      return (
        order.customer_name.toLowerCase().includes(query) ||
        order.phone.toLowerCase().includes(query) ||
        order.invoice_number.toLowerCase().includes(query)
      );
    }

    return true;
  });

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl mb-8 text-gray-800">Orders</h1>

      <OrdersFilters
        status={localFilters.status}
        query={localFilters.query}
        onStatusChange={handleStatusChange}
        onQueryChange={handleQueryChange}
      />

      <div className="mt-6">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-4" />
            <p className="text-gray-600">Loading orders...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredOrders.length === 0 && orders.length === 0 && (
          <OrdersEmptyState onCreate={handleCreate} />
        )}

        {/* No Results */}
        {!loading && !error && filteredOrders.length === 0 && orders.length > 0 && (
          <div className="text-center py-16">
            <p className="text-gray-600">No orders match your filters</p>
          </div>
        )}

        {/* Orders List */}
        {!loading && !error && filteredOrders.length > 0 && (
          <div className="space-y-3">
            {filteredOrders.map((order) => (
              <OrderCard key={order.id} order={order} onOpen={handleOpenOrder} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
