import { useState } from 'react';
import { Card } from '../ui/card';
import { Input } from '../ui/input';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { Search } from 'lucide-react';
import { CustomerOrderRow } from './CustomerOrderRow';
import type { CustomerOrder } from './CustomerOrderRow';

interface CustomerOrderHistoryProps {
  orders: CustomerOrder[];
  onViewOrder: (orderId: string) => void;
}

export function CustomerOrderHistory({ orders, onViewOrder }: CustomerOrderHistoryProps) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');

  // Filter orders
  const filteredOrders = orders.filter((order) => {
    // Status filter
    if (status !== 'all' && order.status !== status) {
      return false;
    }

    // Query filter
    if (query) {
      const q = query.toLowerCase();
      return (
        order.invoice_number.toLowerCase().includes(q) ||
        order.created_at.toLowerCase().includes(q)
      );
    }

    return true;
  });

  return (
    <Card className="p-6">
      <h2 className="text-xl text-gray-800 mb-4">Order History</h2>
      
      {/* Search Input */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search orders..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Status Tabs */}
      <Tabs value={status} onValueChange={setStatus} className="mb-4">
        <TabsList className="w-full">
          <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
          <TabsTrigger value="in-progress" className="flex-1">In Progress</TabsTrigger>
          <TabsTrigger value="ready" className="flex-1">Ready</TabsTrigger>
          <TabsTrigger value="picked-up" className="flex-1">Picked Up</TabsTrigger>
          <TabsTrigger value="cancelled" className="flex-1">Cancelled</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Orders List */}
      {filteredOrders.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-600">
            {orders.length === 0 ? 'No orders yet' : 'No orders match your filters'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredOrders.map((order) => (
            <CustomerOrderRow 
              key={order.id} 
              order={order} 
              onViewOrder={onViewOrder} 
            />
          ))}
        </div>
      )}
    </Card>
  );
}
