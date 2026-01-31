import { Package } from 'lucide-react';
import { Button } from '../ui/button';

interface InventoryEmptyStateProps {
  onCreate: () => void;
}

export function InventoryEmptyState({ onCreate }: InventoryEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="bg-gray-100 p-4 rounded-full mb-4">
        <Package className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-xl text-gray-800 mb-2">No items yet</h3>
      <p className="text-gray-600 mb-6">Get started by adding your first inventory item</p>
      <Button onClick={onCreate}>Add Item</Button>
    </div>
  );
}
