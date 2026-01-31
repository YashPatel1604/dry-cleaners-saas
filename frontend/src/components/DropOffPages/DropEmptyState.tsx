import { UserPlus } from 'lucide-react';
import { Button } from '../ui/button';

interface DropEmptyStateProps {
  onRegister: () => void;
}

export function DropEmptyState({ onRegister }: DropEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="bg-gray-100 p-4 rounded-full mb-4">
        <UserPlus className="w-8 h-8 text-gray-400" />
      </div>
      <p className="text-xl text-gray-800 mb-6">No customers found</p>
      <Button onClick={onRegister}>Register new customer</Button>
    </div>
  );
}
