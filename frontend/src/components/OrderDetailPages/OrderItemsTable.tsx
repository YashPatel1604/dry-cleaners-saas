import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { OrderItemRow } from './OrderItemRow';
import type { OrderItem } from './OrderItemRow';
import { OrderEmptyState } from './OrderEmptyState';

interface OrderItemsTableProps {
  items: OrderItem[];
  onEditItems?: () => void;
  canEdit?: boolean;
}

export function OrderItemsTable({ items, onEditItems, canEdit = false }: OrderItemsTableProps) {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl text-gray-800">Items</h2>
        {onEditItems && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onEditItems}
            disabled={!canEdit}
          >
            Edit Items
          </Button>
        )}
      </div>
      
      {items.length === 0 ? (
        <OrderEmptyState text="No items added" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-300">
                <th className="py-3 text-left text-sm text-gray-700">Item</th>
                <th className="py-3 text-center text-sm text-gray-700">Qty</th>
                <th className="py-3 text-right text-sm text-gray-700">Unit Price</th>
                <th className="py-3 text-right text-sm text-gray-700">Line Total</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <OrderItemRow key={item.id} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
