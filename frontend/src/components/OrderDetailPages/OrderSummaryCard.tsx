import { Card } from '../ui/card';
import { Badge } from '../ui/badge';

export interface OrderSummary {
  customer_name: string;
  phone: string;
  email?: string;
  order_sku?: string;
  location_barcode?: string;
  rack_number?: string;
  barcode_data_uri?: string;
  created_date: string;
  due_date: string;
  total: number;
  paid: number;
  balance_due: number;
  status: string;
}

interface OrderSummaryCardProps {
  order: OrderSummary;
}

export function OrderSummaryCard({ order }: OrderSummaryCardProps) {
  const getStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case 'pending':
        return 'secondary';
      case 'in-progress':
        return 'default';
      case 'ready':
        return 'outline';
      case 'picked-up':
        return 'secondary';
      case 'cancelled':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'in-progress':
        return 'In Progress';
      case 'ready':
        return 'Ready';
      case 'picked-up':
        return 'Picked Up';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  };

  return (
    <Card className="p-6">
      <h2 className="text-xl text-gray-800 mb-4">Order Summary</h2>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Customer name</p>
            <p className="text-gray-900">{order.customer_name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Phone</p>
            <p className="text-gray-900">{order.phone}</p>
          </div>
        </div>

        {order.email && (
          <div>
            <p className="text-sm text-gray-600">Email</p>
            <p className="text-gray-900">{order.email}</p>
          </div>
        )}

        {order.order_sku && (
          <div>
            <p className="text-sm text-gray-600">Order SKU</p>
            <p className="text-gray-900">{order.order_sku}</p>
          </div>
        )}

        {order.barcode_data_uri && (
          <div className="rounded-lg border border-gray-200 bg-white p-3">
            <p className="text-sm text-gray-600 mb-2">Barcode</p>
            <img
              src={order.barcode_data_uri}
              alt={`Barcode ${order.order_sku ?? ""}`.trim()}
              className="h-20 w-full object-contain"
            />
          </div>
        )}

        {(order.location_barcode || order.rack_number) && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <p className="text-sm text-gray-600 mb-2">Storage location</p>
            {order.location_barcode && (
              <p className="text-gray-900">Barcode: {order.location_barcode}</p>
            )}
            {order.rack_number && (
              <p className="text-gray-900">Rack: {order.rack_number}</p>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Created date</p>
            <p className="text-gray-900">{order.created_date}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Due date</p>
            <p className="text-gray-900">{order.due_date}</p>
          </div>
        </div>

        <div className="border-t pt-3 mt-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Total</p>
              <p className="text-gray-900">${order.total.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Paid</p>
              <p className="text-gray-900">${order.paid.toFixed(2)}</p>
            </div>
          </div>
          <div className="mt-3">
            <p className="text-sm text-gray-600">Balance Due</p>
            <p className="text-xl text-gray-900">${order.balance_due.toFixed(2)}</p>
          </div>
        </div>

        <div className="border-t pt-3 mt-4">
          <p className="text-sm text-gray-600 mb-2">Status</p>
          <Badge variant={getStatusVariant(order.status)}>
            {getStatusLabel(order.status)}
          </Badge>
        </div>
      </div>
    </Card>
  );
}
