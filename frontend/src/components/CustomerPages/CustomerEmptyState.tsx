import { UserX } from 'lucide-react';
import { Button } from '../ui/button';

interface CustomerEmptyStateProps {
  onBack: () => void;
}

export function CustomerEmptyState({ onBack }: CustomerEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="bg-gray-100 p-4 rounded-full mb-4">
        <UserX className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-xl text-gray-800 mb-2">No customer data available</h3>
      <Button onClick={onBack} className="mt-6">Back to Customers</Button>
    </div>
  );
}
