import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { ChevronRight, Printer } from 'lucide-react';

interface Order {
  id: string;
  customer_name: string;
  phone: string;
  status: 'in-progress' | 'ready' | 'picked-up' | 'cancelled';
  invoice_number: string;
  order_sku: string;
  total: number;
  created_at: string;
}

interface OrderCardProps {
  order: Order;
  onOpen: (orderId: string) => void;
  onPrintTag?: (order: Order) => void;
}

const statusConfig = {
  'in-progress': { label: 'In Progress', variant: 'default' as const },
  'ready': { label: 'Ready', variant: 'default' as const },
  'picked-up': { label: 'Picked Up', variant: 'secondary' as const },
  'cancelled': { label: 'Cancelled', variant: 'destructive' as const },
};

export function OrderCard({ order, onOpen, onPrintTag }: OrderCardProps) {
  const statusInfo = statusConfig[order.status];

  return (
    <Card
      className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={() => onOpen(order.id)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          {/* Customer Name and Status */}
          <div className="flex items-center gap-3">
            <p className="text-gray-900">{order.customer_name}</p>
            <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          </div>

          {/* Phone */}
          <p className="text-sm text-gray-600">{order.phone}</p>

          {/* Invoice and Total */}
          <div className="flex gap-4 text-sm">
            <span className="text-gray-600">
              Invoice: <span className="text-gray-900">{order.invoice_number}</span>
            </span>
            <span className="text-gray-600">
              SKU: <span className="text-gray-900">{order.order_sku}</span>
            </span>
            <span className="text-gray-600">
              Total: <span className="text-gray-900">${order.total.toFixed(2)}</span>
            </span>
          </div>

          {/* Created Date */}
          <p className="text-xs text-gray-500">
            {new Date(order.created_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          {onPrintTag && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 px-2 text-xs"
              onClick={(event) => {
                event.stopPropagation();
                onPrintTag(order);
              }}
            >
              <Printer className="mr-1 h-3.5 w-3.5" />
              Print Tag
            </Button>
          )}
          <ChevronRight className="w-5 h-5 text-gray-400 mt-1" />
        </div>
      </div>
    </Card>
  );
}
