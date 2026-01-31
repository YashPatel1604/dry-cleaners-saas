import { FileText } from 'lucide-react';
import { Button } from '../ui/button';

interface OrdersEmptyStateProps {
  onCreate: () => void;
}

export function OrdersEmptyState({ onCreate }: OrdersEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="bg-gray-100 p-4 rounded-full mb-4">
        <FileText className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-xl text-gray-800 mb-2">No orders yet</h3>
      <p className="text-gray-600 mb-6">Get started by creating your first order</p>
      <Button onClick={onCreate}>Create Order</Button>
    </div>
  );
}
