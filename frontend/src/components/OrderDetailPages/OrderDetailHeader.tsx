import { ArrowLeft } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

interface OrderDetailHeaderProps {
  orderNumber: string;
  status: string;
  onBack: () => void;
}

export function OrderDetailHeader({ orderNumber, status, onBack }: OrderDetailHeaderProps) {
  const getStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case 'pending':
        return 'secondary';
      case 'in-progress':
        return 'default';
      case 'ready':
        return 'outline';
      case 'picked-up':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'in-progress':
        return 'In Progress';
      case 'ready':
        return 'Ready';
      case 'picked-up':
        return 'Picked Up';
      default:
        return status;
    }
  };

  return (
    <div className="mb-6">
      <Button variant="ghost" onClick={onBack} className="mb-4 -ml-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Orders
      </Button>
      <div className="flex items-center justify-between">
        <h1 className="text-3xl text-gray-800">Order #{orderNumber}</h1>
        <Badge variant={getStatusVariant(status)}>
          {getStatusLabel(status)}
        </Badge>
      </div>
    </div>
  );
}
