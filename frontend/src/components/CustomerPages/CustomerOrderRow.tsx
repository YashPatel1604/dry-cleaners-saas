import { ChevronRight } from 'lucide-react';
import { Badge } from '../ui/badge';

export interface CustomerOrder {
  id: string;
  invoice_number: string;
  created_at: string;
  status: 'in-progress' | 'ready' | 'picked-up' | 'cancelled';
  total: number;
}

interface CustomerOrderRowProps {
  order: CustomerOrder;
  onViewOrder: (orderId: string) => void;
}

export function CustomerOrderRow({ order, onViewOrder }: CustomerOrderRowProps) {
  const getStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
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
    <button
      onClick={() => onViewOrder(order.id)}
      className="w-full flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left"
    >
      <div className="flex-1 grid grid-cols-3 gap-4">
        <div>
          <p className="text-sm text-gray-600">Order</p>
          <p className="text-gray-900">{order.invoice_number}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Date</p>
          <p className="text-gray-900">{order.created_at}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Total</p>
          <p className="text-gray-900">${order.total.toFixed(2)}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 ml-4">
        <Badge variant={getStatusVariant(order.status)}>
          {getStatusLabel(order.status)}
        </Badge>
        <ChevronRight className="w-5 h-5 text-gray-400" />
      </div>
    </button>
  );
}
