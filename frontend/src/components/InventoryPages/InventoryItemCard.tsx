import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Edit, Archive } from 'lucide-react';

export interface InventoryItem {
  id: string;
  name: string;
  sku?: string;
  price: number;
  category?: string;
  active: boolean;
}

interface InventoryItemCardProps {
  item: InventoryItem;
  onEdit?: (item: InventoryItem) => void;
  onArchive?: (itemId: string) => void;
}

export function InventoryItemCard({ item, onEdit, onArchive }: InventoryItemCardProps) {
  return (
    <Card className="p-4">
      <div className="space-y-3">
        {/* Name and Status */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-gray-900">{item.name}</h3>
            {item.sku && (
              <p className="text-xs text-gray-500 mt-1">SKU: {item.sku}</p>
            )}
          </div>
          <Badge variant={item.active ? 'default' : 'secondary'}>
            {item.active ? 'Active' : 'Archived'}
          </Badge>
        </div>

        {/* Price */}
        <p className="text-2xl text-gray-900">${item.price.toFixed(2)}</p>

        {/* Category */}
        {item.category && (
          <p className="text-sm text-gray-600">{item.category}</p>
        )}

        {/* Quick Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onEdit && onEdit(item)}
          >
            <Edit className="w-4 h-4 mr-1" />
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onArchive && onArchive(item.id)}
          >
            <Archive className="w-4 h-4 mr-1" />
            Archive
          </Button>
        </div>
      </div>
    </Card>
  );
}
