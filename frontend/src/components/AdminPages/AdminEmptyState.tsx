import { Inbox } from 'lucide-react';

interface AdminEmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function AdminEmptyState({
  title,
  description,
  action,
}: AdminEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="bg-gray-100 p-4 rounded-full mb-4">
        <Inbox className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-xl text-gray-800 mb-2">{title}</h3>
      {description && (
        <p className="text-gray-600 mb-4 max-w-md">{description}</p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}
