import { AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';

interface CustomerErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export function CustomerErrorState({ error, onRetry }: CustomerErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="bg-red-100 p-4 rounded-full mb-4">
        <AlertCircle className="w-8 h-8 text-red-600" />
      </div>
      <h3 className="text-xl text-gray-800 mb-2">Error Loading Customer</h3>
      <p className="text-gray-600 mb-6">{error}</p>
      {onRetry && (
        <Button onClick={onRetry}>Retry</Button>
      )}
    </div>
  );
}
