import { Loader2 } from 'lucide-react';

interface AdminLoadingStateProps {
  message?: string;
}

export function AdminLoadingState({ message = 'Loading...' }: AdminLoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-4" />
      <p className="text-gray-600">{message}</p>
    </div>
  );
}
