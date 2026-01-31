import { useState } from 'react';
import { CustomerHeader } from './CustomerHeader';
import { CustomerSummaryCard } from './CustomerSummaryCard';
import type { Customer } from './CustomerSummaryCard';
import { CustomerNotesCard } from './CustomerNotesCard';
import { CustomerOrderHistory } from './CustomerOrderHistory';
import type { CustomerOrder } from './CustomerOrderRow';
import { CustomerLoadingState } from './CustomerLoadingState';
import { CustomerErrorState } from './CustomerErrorState';
import { CustomerEmptyState } from './CustomerEmptyState';
import { CustomerEditDialog } from './CustomerEditDialog';
import type { CustomerFormData } from './CustomerEditForm';

interface CustomerProfilePageProps {
  customer: Customer | null;
  orders: CustomerOrder[];
  loading?: boolean;
  error?: string | null;
  onEdit?: (customerId: string, data: CustomerFormData) => void;
  onStartDropOff?: (customerId: string) => void;
  onViewOrder?: (orderId: string) => void;
  onUpdateCustomer?: (customerId: string, data: CustomerFormData) => Promise<void> | void;
  onBack: () => void;
  onRetry?: () => void;
}

export function CustomerProfilePage({
  customer,
  orders,
  loading = false,
  error = null,
  onEdit,
  onStartDropOff,
  onViewOrder,
  onUpdateCustomer,
  onBack,
  onRetry,
}: CustomerProfilePageProps) {
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const handleEdit = () => {
    setEditError(null);
    setEditDialogOpen(true);
  };

  const handleStartDropOff = () => {
    if (customer && onStartDropOff) {
      onStartDropOff(customer.id);
    }
  };

  const handleViewOrder = (orderId: string) => {
    if (onViewOrder) {
      onViewOrder(orderId);
    }
  };

  const handleSaveCustomer = async (data: CustomerFormData) => {
    if (!customer) return;

    setEditLoading(true);
    setEditError(null);

    try {
      if (onUpdateCustomer) {
        await onUpdateCustomer(customer.id, data);
      }
      if (onEdit) {
        onEdit(customer.id, data);
      }
      setEditDialogOpen(false);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Unable to update.");
      return;
    } finally {
      setEditLoading(false);
    }
  };

  return (
    <div className="max-w-5xl">
      <h1 className="text-3xl text-gray-800 mb-6">Customer</h1>

      {/* Loading State */}
      {loading && <CustomerLoadingState />}

      {/* Error State */}
      {error && !loading && (
        <CustomerErrorState error={error} onRetry={onRetry} />
      )}

      {/* Empty State */}
      {!loading && !error && !customer && (
        <CustomerEmptyState onBack={onBack} />
      )}

      {/* Customer Content */}
      {!loading && !error && customer && (
        <>
          <CustomerHeader
            customerName={customer.name}
            onBack={onBack}
            onEdit={handleEdit}
            onStartDropOff={handleStartDropOff}
          />

          <div className="space-y-6">
            <CustomerSummaryCard customer={customer} />
            
            <CustomerNotesCard 
              popUpMessage={customer.popUpMessage} 
              onEdit={handleEdit}
            />
            
            <CustomerOrderHistory 
              orders={orders} 
              onViewOrder={handleViewOrder}
            />
          </div>
        </>
      )}

      {/* Edit Dialog */}
      {customer && (
        <CustomerEditDialog
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          onSave={handleSaveCustomer}
          loading={editLoading}
          error={editError}
          initialData={{
            phone: customer.phone,
            firstName: customer.name.split(' ')[0] || '',
            lastName: customer.name.split(' ').slice(1).join(' ') || '',
            email: customer.email || '',
            address: customer.address || '',
            preferences: customer.preferences || '',
            popUpMessage: customer.popUpMessage || '',
          }}
        />
      )}
    </div>
  );
}
