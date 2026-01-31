import { Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { OrderDetailHeader } from './OrderDetailHeader';
import { OrderSummaryCard } from './OrderSummaryCard';
import type { OrderSummary } from './OrderSummaryCard';
import { OrderItemsTable } from './OrderItemsTable';
import type { OrderItem } from './OrderItemRow';
import { OrderPaymentsCard } from './OrderPaymentsCard';
import type { Payment } from './OrderPaymentsCard';
import { OrderNotesCard } from './OrderNotesCard';
import { OrderTimeline } from './OrderTimeline';
import type { TimelineEvent } from './OrderTimelineEvent';

interface OrderDetailPageProps {
  order: OrderSummary & { id: string; number: string };
  items: OrderItem[];
  payments: Payment[];
  timeline: TimelineEvent[];
  notes?: string;
  loading?: boolean;
  error?: string | null;
  onBack: () => void;
  onAddNote?: (note: string) => void;
  onMarkReady?: () => void;
  onMarkPickedUp?: () => void;
  onEditItems?: () => void;
  canEditItems?: boolean;
  allowCollectPayment?: boolean;
  collectingPayment?: boolean;
  collectPaymentError?: string | null;
  onCollectPayment?: (payload: {
    amount: number;
    method: "CASH" | "CARD" | "ONLINE" | "OTHER";
    reference?: string;
  }) => void;
  onCancelOrder?: () => void;
  canCancelOrder?: boolean;
  cancelingOrder?: boolean;
  onViewCustomer?: () => void;
  canViewCustomer?: boolean;
}

export function OrderDetailPage({
  order,
  items,
  payments,
  timeline,
  notes,
  loading = false,
  error = null,
  onBack,
  onAddNote,
  onMarkReady,
  onMarkPickedUp,
  onEditItems,
  canEditItems = false,
  allowCollectPayment = false,
  collectingPayment = false,
  collectPaymentError = null,
  onCollectPayment,
  onCancelOrder,
  canCancelOrder = false,
  cancelingOrder = false,
  onViewCustomer,
  canViewCustomer = false,
}: OrderDetailPageProps) {
  // Calculate payment totals
  const totalPaid = payments
    .filter(p => p.status === 'captured')
    .reduce((sum, p) => sum + p.amount, 0);
  const changeDue = Math.max(0, totalPaid - order.total);
  const balanceDue = Math.max(0, order.total - totalPaid);

  const canMarkReady =
    order.status !== "ready" && order.status !== "picked-up" && order.status !== "cancelled";
  const canMarkPickedUp = order.status === "ready";
  const showActions =
    canMarkReady ||
    canMarkPickedUp ||
    (onCancelOrder && canCancelOrder) ||
    (onViewCustomer && canViewCustomer);

  return (
    <div className="max-w-5xl">
      <OrderDetailHeader
        orderNumber={order.number}
        status={order.status}
        onBack={onBack}
      />

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-4" />
          <p className="text-gray-600">Loading order details...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Order Content */}
      {!loading && !error && (
        <div className="space-y-6">
          {/* Action Buttons */}
          {showActions && (
            <div className="flex items-center justify-between gap-3">
              <div className="flex gap-3">
                {onViewCustomer && canViewCustomer && (
                  <Button variant="outline" onClick={onViewCustomer}>
                    View Customer
                  </Button>
                )}
                {canMarkReady && (
                <Button onClick={onMarkReady}>Mark Ready</Button>
              )}
                {canMarkPickedUp && (
                  <Button onClick={onMarkPickedUp}>Mark Picked Up</Button>
                )}
              </div>
              {onCancelOrder && canCancelOrder && (
                <Button
                  onClick={onCancelOrder}
                  variant="destructive"
                  disabled={cancelingOrder}
                >
                  {cancelingOrder ? "Cancelling..." : "Cancel Order"}
                </Button>
              )}
            </div>
          )}

          {/* Order Summary */}
          <OrderSummaryCard order={order} />

          {/* Items Table */}
          <OrderItemsTable items={items} onEditItems={onEditItems} canEdit={canEditItems} />

          {/* Payments */}
          <OrderPaymentsCard
            payments={payments}
            totalPaid={totalPaid}
            changeDue={changeDue}
            balanceDue={balanceDue}
            allowCollect={allowCollectPayment}
            collecting={collectingPayment}
            collectError={collectPaymentError}
            onCollectPayment={onCollectPayment}
          />

          {/* Notes */}
          <OrderNotesCard notes={notes} onAddNote={onAddNote} />

          {/* Timeline */}
          <OrderTimeline timeline={timeline} />
        </div>
      )}
    </div>
  );
}
