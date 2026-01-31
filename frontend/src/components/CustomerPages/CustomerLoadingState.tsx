import { Loader2 } from 'lucide-react';

export function CustomerLoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-4" />
      <p className="text-gray-600">Loading customer...</p>
    </div>
  );
}
