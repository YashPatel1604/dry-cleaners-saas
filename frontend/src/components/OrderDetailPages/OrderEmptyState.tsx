import { Package } from 'lucide-react';

interface OrderEmptyStateProps {
  text?: string;
}

export function OrderEmptyState({ text = 'No items added' }: OrderEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="bg-gray-100 p-4 rounded-full mb-3">
        <Package className="w-6 h-6 text-gray-400" />
      </div>
      <p className="text-gray-600">{text}</p>
    </div>
  );
}
