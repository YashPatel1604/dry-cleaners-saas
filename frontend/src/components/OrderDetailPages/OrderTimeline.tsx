import { Card } from '../ui/card';
import { OrderTimelineEvent } from './OrderTimelineEvent';
import type { TimelineEvent } from './OrderTimelineEvent';

interface OrderTimelineProps {
  timeline: TimelineEvent[];
}

export function OrderTimeline({ timeline }: OrderTimelineProps) {
  return (
    <Card className="p-6">
      <h2 className="text-xl text-gray-800 mb-4">Timeline</h2>
      
      {timeline.length === 0 ? (
        <p className="text-gray-600 text-center py-8">No activity yet</p>
      ) : (
        <div className="space-y-0">
          {timeline.map((event, index) => (
            <OrderTimelineEvent
              key={event.id}
              event={event}
              isLast={index === timeline.length - 1}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
