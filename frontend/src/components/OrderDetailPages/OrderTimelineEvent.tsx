export interface TimelineEvent {
  id: string;
  title: string;
  timestamp: string;
  actor?: string;
  note?: string;
}

interface OrderTimelineEventProps {
  event: TimelineEvent;
  isLast?: boolean;
}

export function OrderTimelineEvent({ event, isLast = false }: OrderTimelineEventProps) {
  return (
    <div className="flex gap-4">
      {/* Timeline dot and line */}
      <div className="flex flex-col items-center">
        <div className="w-3 h-3 rounded-full bg-blue-600 flex-shrink-0 mt-1.5" />
        {!isLast && <div className="w-0.5 h-full bg-gray-300 mt-1" />}
      </div>

      {/* Event content */}
      <div className={`flex-1 ${!isLast ? 'pb-6' : ''}`}>
        <p className="text-gray-900">{event.title}</p>
        <p className="text-sm text-gray-600">{event.timestamp}</p>
        {event.actor && (
          <p className="text-sm text-gray-600 mt-1">by {event.actor}</p>
        )}
        {event.note && (
          <p className="text-sm text-gray-700 mt-2 p-2 bg-gray-50 rounded">{event.note}</p>
        )}
      </div>
    </div>
  );
}
