import { ShoppingBag, Plus, Settings } from "lucide-react";

interface SidebarProps {
  onSelectSection?: (section: string) => void;
}

export function Sidebar({ onSelectSection }: SidebarProps) {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 p-6">
      <nav className="space-y-2">
        <button
          type="button"
          className="w-full flex items-center gap-3 px-4 py-3 text-left text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          onClick={() => onSelectSection?.("orders")}
        >
          <ShoppingBag className="w-5 h-5" />
          <span>ORDERS</span>
        </button>
        <button
          type="button"
          className="w-full flex items-center gap-3 px-4 py-3 text-left text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          onClick={() => onSelectSection?.("extras")}
        >
          <Plus className="w-5 h-5" />
          <span>EXTRAS</span>
        </button>
        <button
          type="button"
          className="w-full flex items-center gap-3 px-4 py-3 text-left text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          onClick={() => onSelectSection?.("admin")}
        >
          <Settings className="w-5 h-5" />
          <span>SETTINGS</span>
        </button>
      </nav>
    </aside>
  );
}
