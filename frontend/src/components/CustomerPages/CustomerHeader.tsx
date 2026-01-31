import { ArrowLeft } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

interface CustomerHeaderProps {
  customerName: string;
  onBack: () => void;
  onEdit: () => void;
  onStartDropOff: () => void;
}

export function CustomerHeader({ 
  customerName, 
  onBack, 
  onEdit, 
  onStartDropOff 
}: CustomerHeaderProps) {
  return (
    <div className="mb-6">
      <Button variant="ghost" onClick={onBack} className="mb-4 -ml-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Customers
      </Button>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl text-gray-800">{customerName}</h1>
          <Badge variant="default">Active</Badge>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onEdit}>
            Edit Customer
          </Button>
          <Button onClick={onStartDropOff}>
            Start Drop-Off
          </Button>
        </div>
      </div>
    </div>
  );
}
