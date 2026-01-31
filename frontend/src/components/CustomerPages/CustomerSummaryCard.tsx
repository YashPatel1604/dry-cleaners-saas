import { Card } from '../ui/card';

export interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
  address?: string;
  preferences?: string;
  popUpMessage?: string;
  created_at: string;
}

interface CustomerSummaryCardProps {
  customer: Customer;
}

export function CustomerSummaryCard({ customer }: CustomerSummaryCardProps) {
  return (
    <Card className="p-6">
      <h2 className="text-xl text-gray-800 mb-4">Customer Summary</h2>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Name</p>
            <p className="text-gray-900">{customer.name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Phone</p>
            <p className="text-gray-900">{customer.phone}</p>
          </div>
        </div>

        {customer.email && (
          <div>
            <p className="text-sm text-gray-600">Email</p>
            <p className="text-gray-900">{customer.email}</p>
          </div>
        )}

        {customer.address && (
          <div>
            <p className="text-sm text-gray-600">Address</p>
            <p className="text-gray-900 whitespace-pre-wrap">{customer.address}</p>
          </div>
        )}

        {customer.preferences && (
          <div>
            <p className="text-sm text-gray-600">Preferences</p>
            <p className="text-gray-900 whitespace-pre-wrap">{customer.preferences}</p>
          </div>
        )}

        <div className="border-t pt-3 mt-4">
          <p className="text-sm text-gray-600">Created Date</p>
          <p className="text-gray-900">{customer.created_at}</p>
        </div>
      </div>
    </Card>
  );
}
