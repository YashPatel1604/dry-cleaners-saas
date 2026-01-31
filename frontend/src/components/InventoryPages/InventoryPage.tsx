import { useState } from 'react';
import { Button } from '../ui/button';
import { Plus, Loader2 } from 'lucide-react';
import { InventoryItemCard } from './InventoryItemCard';
import type { InventoryItem } from './InventoryItemCard';
import { InventoryEmptyState } from './InventoryEmptyState';
import { InventoryFilters } from './InventoryFilters';
import { InventoryFormDialog } from './InventoryFormDialog';
import type { InventoryFormData } from './InventoryForm';

interface InventoryPageProps {
  items: InventoryItem[];
  loading?: boolean;
  error?: string | null;
  filters?: {
    query: string;
    status: string;
  };
  onFilterChange?: (filters: { query: string; status: string }) => void;
  onCreate?: (data: InventoryFormData) => void | Promise<void>;
  onEdit?: (id: string, data: InventoryFormData) => void | Promise<void>;
  onArchive?: (id: string) => void | Promise<void>;
}

export function InventoryPage({
  items,
  loading = false,
  error = null,
  filters = { query: '', status: 'all' },
  onFilterChange,
  onCreate,
  onEdit,
  onArchive,
}: InventoryPageProps) {
  const [localFilters, setLocalFilters] = useState(filters);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [dialogLoading, setDialogLoading] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const handleQueryChange = (query: string) => {
    const newFilters = { ...localFilters, query };
    setLocalFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleStatusChange = (status: string) => {
    const newFilters = { ...localFilters, status };
    setLocalFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleOpenDialog = (item?: InventoryItem) => {
    if (item) {
      setEditingItem(item);
    } else {
      setEditingItem(null);
    }
    setDialogError(null);
    setDialogOpen(true);
  };

  const handleSaveItem = async (data: InventoryFormData) => {
    setDialogLoading(true);
    setDialogError(null);

    try {
      if (editingItem) {
        if (onEdit) {
          await onEdit(editingItem.id, data);
        }
      } else {
        if (onCreate) {
          await onCreate(data);
        }
      }
      setDialogOpen(false);
      setEditingItem(null);
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : 'Unable to save item.');
    } finally {
      setDialogLoading(false);
    }
  };

  const handleArchiveItem = async (itemId: string) => {
    if (!onArchive) return;
    try {
      await onArchive(itemId);
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : 'Unable to archive item.');
    }
  };

  // Filter items based on status and query
  const filteredItems = items.filter((item) => {
    // Status filter
    if (localFilters.status === 'active' && !item.active) return false;
    if (localFilters.status === 'archived' && item.active) return false;

    // Query filter
    if (localFilters.query) {
      const query = localFilters.query.toLowerCase();
      return (
        item.name.toLowerCase().includes(query) ||
        (item.sku && item.sku.toLowerCase().includes(query))
      );
    }

    return true;
  });

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl text-gray-800">Inventory</h1>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="w-4 h-4 mr-2" />
          Add Item
        </Button>
      </div>

      <InventoryFilters
        query={localFilters.query}
        status={localFilters.status}
        onQueryChange={handleQueryChange}
        onStatusChange={handleStatusChange}
      />

      <div className="mt-6">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-4" />
            <p className="text-gray-600">Loading inventory...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredItems.length === 0 && items.length === 0 && (
          <InventoryEmptyState onCreate={() => handleOpenDialog()} />
        )}

        {/* No Results */}
        {!loading && !error && filteredItems.length === 0 && items.length > 0 && (
          <div className="text-center py-16">
            <p className="text-gray-600">No items match your filters</p>
          </div>
        )}

        {/* Items Grid */}
        {!loading && !error && filteredItems.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredItems.map((item) => (
              <InventoryItemCard
                key={item.id}
                item={item}
                onEdit={handleOpenDialog}
                onArchive={handleArchiveItem}
              />
            ))}
          </div>
        )}
      </div>

      {/* Form Dialog */}
      <InventoryFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleSaveItem}
        loading={dialogLoading}
        error={dialogError}
        initialData={editingItem ? {
          name: editingItem.name,
          sku: editingItem.sku || '',
          price: editingItem.price.toString(),
          category: editingItem.category || '',
          active: editingItem.active,
        } : undefined}
      />
    </div>
  );
}
