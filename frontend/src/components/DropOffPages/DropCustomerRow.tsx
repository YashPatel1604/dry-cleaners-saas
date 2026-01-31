import { ChevronRight } from 'lucide-react';

interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
}

interface DropCustomerRowProps {
  customer: Customer;
  onSelect: (customer: Customer) => void;
}

export function DropCustomerRow({ customer, onSelect }: DropCustomerRowProps) {
  return (
    <button
      onClick={() => onSelect(customer)}
      className="w-full flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left"
    >
      <div className="flex-1">
        <p className="text-gray-900">{customer.name}</p>
        <div className="flex gap-4 mt-1">
          <p className="text-sm text-gray-600">{customer.phone}</p>
          {customer.email && (
            <p className="text-sm text-gray-600">{customer.email}</p>
          )}
        </div>
      </div>
      
      <ChevronRight className="w-5 h-5 text-gray-400" />
    </button>
  );
}
