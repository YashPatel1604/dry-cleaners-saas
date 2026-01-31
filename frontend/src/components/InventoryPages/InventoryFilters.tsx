import { Input } from '../ui/input';
import { Search } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';

interface InventoryFiltersProps {
  query: string;
  status: string;
  onQueryChange: (query: string) => void;
  onStatusChange: (status: string) => void;
}

export function InventoryFilters({
  query,
  status,
  onQueryChange,
  onStatusChange,
}: InventoryFiltersProps) {
  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search item name or SKU"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Status Filter Tabs */}
      <Tabs value={status} onValueChange={onStatusChange}>
        <TabsList className="w-full">
          <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
          <TabsTrigger value="active" className="flex-1">Active</TabsTrigger>
          <TabsTrigger value="archived" className="flex-1">Archived</TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  );
}
