export interface OrderItem {
  id: string;
  itemId: string;
  name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

interface OrderItemRowProps {
  item: OrderItem;
}

export function OrderItemRow({ item }: OrderItemRowProps) {
  return (
    <tr className="border-b border-gray-200">
      <td className="py-3 text-gray-900">{item.name}</td>
      <td className="py-3 text-gray-900 text-center">{item.quantity}</td>
      <td className="py-3 text-gray-900 text-right">${item.unit_price.toFixed(2)}</td>
      <td className="py-3 text-gray-900 text-right">${item.line_total.toFixed(2)}</td>
    </tr>
  );
}
