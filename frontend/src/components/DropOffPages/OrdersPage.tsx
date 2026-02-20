import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { OrderCard } from "./OrderCard";
import { OrdersEmptyState } from "./OrdersEmptyState";
import { OrdersFilters } from "./OrdersFilters";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { StorageLocationScannerDialog } from "./StorageLocationScannerDialog";
import { StorageLocationScanStation } from "./StorageLocationScanStation";

interface Order {
  id: string;
  customer_name: string;
  phone: string;
  status: "in-progress" | "ready" | "picked-up" | "cancelled";
  invoice_number: string;
  order_sku: string;
  total: number;
  created_at: string;
}

interface StorageLocationStatus {
  location_barcode: string;
  rack_number: string | null;
  occupied: boolean;
  current_order_id: number | null;
  current_order_sku: string | null;
  current_order_status: string | null;
  assigned_at: string | null;
}

interface OrdersPageProps {
  orders: Order[];
  loading?: boolean;
  error?: string | null;
  filters?: {
    status: string;
    query: string;
  };
  onFilterChange?: (filters: { status: string; query: string }) => void;
  onCreate?: () => void;
  onViewOrder?: (orderId: string) => void;
  onPrintTag?: (order: Order) => void;
  onLookupStorageLocation?: (barcode: string) => Promise<{
    exists: boolean;
    rack_number: string | null;
  }>;
  onAssignStorageLocation?: (payload: {
    locationBarcode: string;
    orderBarcode: string;
    rackNumber?: string;
  }) => Promise<{
    order_id: number;
    order_sku: string;
    location_barcode: string | null;
    rack_number: string | null;
  }>;
  storageLocationStatus?: StorageLocationStatus[];
  storageLocationStatusLoading?: boolean;
  storageLocationStatusError?: string | null;
  onRefreshStorageLocationStatus?: () => void;
  autoScanSeed?: { token: number; barcode: string } | null;
}

export function OrdersPage({
  orders,
  loading = false,
  error = null,
  filters = { status: "all", query: "" },
  onFilterChange,
  onCreate,
  onViewOrder,
  onPrintTag,
  onLookupStorageLocation,
  onAssignStorageLocation,
  storageLocationStatus = [],
  storageLocationStatusLoading = false,
  storageLocationStatusError = null,
  onRefreshStorageLocationStatus,
  autoScanSeed = null,
}: OrdersPageProps) {
  const [localFilters, setLocalFilters] = useState(filters);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [mode, setMode] = useState<"orders" | "scan-station">("orders");

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  useEffect(() => {
    if (!onLookupStorageLocation || !onAssignStorageLocation) {
      setMode("orders");
    }
  }, [onLookupStorageLocation, onAssignStorageLocation]);

  useEffect(() => {
    if (!autoScanSeed) return;
    if (!onLookupStorageLocation || !onAssignStorageLocation) return;
    setMode("scan-station");
    onRefreshStorageLocationStatus?.();
  }, [
    autoScanSeed?.token,
    onLookupStorageLocation,
    onAssignStorageLocation,
    onRefreshStorageLocationStatus,
  ]);

  const handleStatusChange = (status: string) => {
    const newFilters = { ...localFilters, status };
    setLocalFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleQueryChange = (query: string) => {
    const newFilters = { ...localFilters, query };
    setLocalFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleOpenOrder = (orderId: string) => {
    if (onViewOrder) {
      onViewOrder(orderId);
    }
  };

  const handleCreate = () => {
    if (onCreate) {
      onCreate();
    }
  };

  // Filter orders based on status and query
  const filteredOrders = orders.filter((order) => {
    // Status filter
    if (localFilters.status !== "all" && order.status !== localFilters.status) {
      return false;
    }

    // Query filter
    if (localFilters.query) {
      const query = localFilters.query.toLowerCase();
      return (
        order.customer_name.toLowerCase().includes(query) ||
        order.phone.toLowerCase().includes(query) ||
        order.invoice_number.toLowerCase().includes(query) ||
        order.order_sku.toLowerCase().includes(query)
      );
    }

    return true;
  });

  const canScanLocations = Boolean(onLookupStorageLocation && onAssignStorageLocation);
  const sortedRackStatus = useMemo(() => {
    return [...storageLocationStatus].sort((a, b) => {
      const rackA = (a.rack_number ?? "").toString();
      const rackB = (b.rack_number ?? "").toString();
      const byRack = rackA.localeCompare(rackB, undefined, { numeric: true });
      if (byRack !== 0) return byRack;
      return a.location_barcode.localeCompare(b.location_barcode);
    });
  }, [storageLocationStatus]);

  return (
    <div className="max-w-4xl">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl text-gray-800">
          {mode === "scan-station" ? "Scan Station" : "Orders"}
        </h1>
        {canScanLocations ? (
          <div className="flex flex-wrap gap-2">
            {mode === "scan-station" ? (
              <Button type="button" variant="outline" onClick={() => setMode("orders")}>
                Back to Orders
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setMode("scan-station");
                  onRefreshStorageLocationStatus?.();
                }}
              >
                Open Scan Station
              </Button>
            )}
            <Button type="button" variant="outline" onClick={() => setScannerOpen(true)}>
              Quick Scan
            </Button>
          </div>
        ) : null}
      </div>

      {mode === "scan-station" && canScanLocations ? (
        <div className="space-y-6">
          <StorageLocationScanStation
            onLookupLocation={onLookupStorageLocation!}
            onAssignLocation={onAssignStorageLocation!}
            onAssigned={() => onRefreshStorageLocationStatus?.()}
            scanSeed={autoScanSeed}
          />

          <Card className="gap-3 p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-gray-900">Rack Status</h2>
              <Button
                type="button"
                variant="outline"
                onClick={() => onRefreshStorageLocationStatus?.()}
                disabled={storageLocationStatusLoading}
              >
                Refresh
              </Button>
            </div>

            {storageLocationStatusLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading rack status...
              </div>
            ) : null}

            {storageLocationStatusError ? (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {storageLocationStatusError}
              </div>
            ) : null}

            {!storageLocationStatusLoading &&
            !storageLocationStatusError &&
            sortedRackStatus.length === 0 ? (
              <p className="text-sm text-gray-600">
                No storage locations scanned yet.
              </p>
            ) : null}

            {!storageLocationStatusLoading &&
            !storageLocationStatusError &&
            sortedRackStatus.length > 0 ? (
              <div className="space-y-2">
                {sortedRackStatus.map((entry) => (
                  <div
                    key={entry.location_barcode}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {entry.rack_number ? `Rack ${entry.rack_number}` : "No rack #"} ·{" "}
                        {entry.location_barcode}
                      </p>
                      <p className="text-gray-600">
                        {entry.occupied
                          ? `Occupied by ${entry.current_order_sku ?? "order"}`
                          : "Empty"}
                      </p>
                    </div>
                    <span
                      className={
                        entry.occupied
                          ? "rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700"
                          : "rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700"
                      }
                    >
                      {entry.occupied ? "Occupied" : "Empty"}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </Card>
        </div>
      ) : (
        <>
          <OrdersFilters
            status={localFilters.status}
            query={localFilters.query}
            onStatusChange={handleStatusChange}
            onQueryChange={handleQueryChange}
          />

          <div className="mt-6">
            {/* Loading State */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-16">
                <Loader2 className="mb-4 h-8 w-8 animate-spin text-blue-600" />
                <p className="text-gray-600">Loading orders...</p>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && filteredOrders.length === 0 && orders.length === 0 && (
              <OrdersEmptyState onCreate={handleCreate} />
            )}

            {/* No Results */}
            {!loading && !error && filteredOrders.length === 0 && orders.length > 0 && (
              <div className="py-16 text-center">
                <p className="text-gray-600">No orders match your filters</p>
              </div>
            )}

            {/* Orders List */}
            {!loading && !error && filteredOrders.length > 0 && (
              <div className="space-y-3">
                {filteredOrders.map((order) => (
                  <OrderCard
                    key={order.id}
                    order={order}
                    onOpen={handleOpenOrder}
                    onPrintTag={onPrintTag}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {canScanLocations ? (
        <StorageLocationScannerDialog
          open={scannerOpen}
          onOpenChange={setScannerOpen}
          onLookupLocation={onLookupStorageLocation!}
          onAssignLocation={onAssignStorageLocation!}
        />
      ) : null}
    </div>
  );
}
