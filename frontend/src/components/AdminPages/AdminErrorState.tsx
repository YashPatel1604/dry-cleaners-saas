import { AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';

interface AdminErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export function AdminErrorState({ error, onRetry }: AdminErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="bg-red-100 p-4 rounded-full mb-4">
        <AlertCircle className="w-8 h-8 text-red-600" />
      </div>
      <h3 className="text-xl text-gray-800 mb-2">Something went wrong</h3>
      <p className="text-gray-600 mb-4 max-w-md">{error}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline">
          Try Again
        </Button>
      )}
    </div>
  );
}
