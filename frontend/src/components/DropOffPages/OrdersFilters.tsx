import { Input } from '../ui/input';
import { Search } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';

interface OrdersFiltersProps {
  status: string;
  query: string;
  onStatusChange: (status: string) => void;
  onQueryChange: (query: string) => void;
}

export function OrdersFilters({
  status,
  query,
  onStatusChange,
  onQueryChange,
}: OrdersFiltersProps) {
  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search name, phone, invoice #, or order SKU"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Status Filter Tabs */}
      <Tabs value={status} onValueChange={onStatusChange}>
        <TabsList className="w-full">
          <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
          <TabsTrigger value="in-progress" className="flex-1">In Progress</TabsTrigger>
          <TabsTrigger value="ready" className="flex-1">Ready</TabsTrigger>
          <TabsTrigger value="picked-up" className="flex-1">Picked Up</TabsTrigger>
          <TabsTrigger value="cancelled" className="flex-1">Cancelled</TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  );
}
