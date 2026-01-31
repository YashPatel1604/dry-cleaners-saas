import { AdminSectionHeader } from './AdminSectionHeader';
import { AdminEmptyState } from './AdminEmptyState';
import { AdminLoadingState } from './AdminLoadingState';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';

interface AuditEvent {
  id: string;
  created_at: string;
  action: string;
  actor_user_id: string;
  subject_user_id: string | null;
  metadata: Record<string, any>;
}

interface AdminAuditSectionProps {
  events: AuditEvent[];
  loading?: boolean;
  empty?: boolean;
}

export function AdminAuditSection({
  events,
  loading = false,
  empty = false,
}: AdminAuditSectionProps) {
  if (loading) {
    return <AdminLoadingState message="Loading audit log..." />;
  }

  const getActionColor = (
    action: string
  ): "destructive" | "default" | "secondary" | "outline" => {
    if (action.includes('delete') || action.includes('revoke')) return 'destructive';
    if (action.includes('create') || action.includes('add')) return 'default';
    if (action.includes('update') || action.includes('change')) return 'secondary';
    return 'outline';
  };

  return (
    <div>
      <AdminSectionHeader
        title="Audit Log"
        description="View all administrative actions and changes"
      />

      {empty ? (
        <AdminEmptyState
          title="No audit events"
          description="Administrative actions will appear here"
        />
      ) : (
        <Card className="p-6">
          <div className="space-y-4">
            {events.map((event) => (
              <div
                key={event.id}
                className="flex items-start justify-between py-4 border-b border-gray-200 last:border-0"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge variant={getActionColor(event.action)}>
                      {event.action}
                    </Badge>
                    <span className="text-sm text-gray-600">
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-700">
                    <p>
                      <span className="font-medium">Actor:</span> {event.actor_user_id}
                    </p>
                    {event.subject_user_id && (
                      <p>
                        <span className="font-medium">Subject:</span> {event.subject_user_id}
                      </p>
                    )}
                    {Object.keys(event.metadata).length > 0 && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-blue-600 hover:underline">
                          View details
                        </summary>
                        <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-auto">
                          {JSON.stringify(event.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
