import { Card } from '../ui/card';
import { Button } from '../ui/button';

interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
}

interface DropResultsCardProps {
  customer: Customer;
  onStartDropOff: (customer: Customer) => void;
}

export function DropResultsCard({ customer, onStartDropOff }: DropResultsCardProps) {
  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div>
          <p className="text-sm text-gray-600">Name</p>
          <p className="text-lg text-gray-900">{customer.name}</p>
        </div>
        
        <div>
          <p className="text-sm text-gray-600">Phone</p>
          <p className="text-lg text-gray-900">{customer.phone}</p>
        </div>
        
        {customer.email && (
          <div>
            <p className="text-sm text-gray-600">Email</p>
            <p className="text-lg text-gray-900">{customer.email}</p>
          </div>
        )}
        
        <Button 
          className="w-full mt-4" 
          onClick={() => onStartDropOff(customer)}
        >
          Start Drop‑Off
        </Button>
      </div>
    </Card>
  );
}
