import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";

import { fetchTenants } from "./api/auth";
import type { TenantSummary } from "./api/auth";
import {
  clearAuth,
  clearTenantSlug,
  getAccessToken,
  getTenantSlug,
  setTenantSlug,
} from "./api/client";
import {
  createCustomer,
  fetchCustomers,
  fetchCustomerDetail,
  fetchCustomerOrders,
  searchCustomers,
  updateCustomer,
} from "./api/customers";
import { fetchPaymentsDailySummary } from "./api/payments";
import {
  createInventoryItem,
  fetchInventoryItems,
  resolveInventoryImageUrl,
  updateInventoryItem,
  type InventoryItemApi,
} from "./api/inventory";
import {
  assignStorageLocationByScan,
  clearOrderStorageLocation,
  createDropoffOrder,
  createOrderItem,
  fetchStorageLocationStatus,
  fetchOrderStorageLocation,
  deleteOrderItem,
  fetchOrderCards,
  lookupStorageLocation,
  updateOrderItem,
  type OrderCard,
  type StorageLocationAssignment,
  type StorageLocationStatusRow,
} from "./api/orders";
import { fetchSettings, type TenantSettings } from "./api/admin";
import {
  addOrderNote,
  fetchOrderBarcodeSvg,
  createPickupPayment,
  fetchOrderNotes,
  fetchOrderReceipt,
  fetchOrderTimeline,
  markOrderPickedUp,
  markOrderReady,
  updateOrderStatus,
} from "./api/orderDetail";
import { DashboardContent } from "./components/DropOffPages/DashboardContent";
import { DropPage } from "./components/DropOffPages/DropPage";
import { OrdersPage } from "./components/DropOffPages/OrdersPage";
import {
  RegisterCustomerPage,
  type CustomerFormData as RegisterCustomerFormData,
} from "./components/DropOffPages/RegisterCustomerPage";
import { StartDropOffDialog } from "./components/DropOffPages/StartDropOffDialog";
import { OrderDetailPage } from "./components/OrderDetailPages/OrderDetailPage";
import { OrderItemsEditorDialog } from "./components/OrderDetailPages/OrderItemsEditorDialog";
import type { OrderSummary } from "./components/OrderDetailPages/OrderSummaryCard";
import type { OrderItem } from "./components/OrderDetailPages/OrderItemRow";
import type { Payment } from "./components/OrderDetailPages/OrderPaymentsCard";
import type { TimelineEvent } from "./components/OrderDetailPages/OrderTimelineEvent";
import {
  CustomerProfilePage,
} from "./components/CustomerPages/CustomerProfilePage";
import type { Customer as CustomerProfile } from "./components/CustomerPages/CustomerSummaryCard";
import type { CustomerOrder } from "./components/CustomerPages/CustomerOrderRow";
import type { CustomerFormData as CustomerEditFormData } from "./components/CustomerPages/CustomerEditForm";
import type { CustomerListItem } from "./components/CustomerPages/CustomersRow";
import { CustomersPage } from "./components/CustomerPages/CustomersPage";
import { DailyEarningsPage } from "./components/ExtrasPages/DailyEarningsPage";
import { DefaultReportsPage } from "./components/ExtrasPages/DefaultReportsPage";
import { InventoryPage } from "./components/InventoryPages/InventoryPage";
import type { InventoryItem } from "./components/InventoryPages/InventoryItemCard";
import type { InventoryFormData } from "./components/InventoryPages/InventoryForm";
import { ExtrasPage } from "./components/ExtrasPage";
import { LoginPage } from "./components/LoginPage";
import { DashboardSection } from "./components/DashboardPages/DashboardSection";
import { AIAssistantDialog } from "./components/AIAssistantDialog";
import { Sidebar } from "./components/Sidebar";
import { TenantSelector } from "./components/TenantSelector";
import { TopNav } from "./components/TopNav";
import { AdminPage } from "./components/AdminPages/AdminPage";
import { Button } from "./components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./components/ui/dialog";
import { Toaster } from "./components/ui/toaster";
import { toast } from "./components/ui/use-toast";
import {
  formatOrderSku,
  openOrderSkuTagPrint,
  type OrderTagLabelSize,
} from "./lib/orderTags";

const LOCATION_SCANNER_RE = /^LOC-[A-Z0-9][A-Z0-9-]{0,30}$/;
const ORDER_SCANNER_RE = /^ORD-\d{8}$/;

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(getAccessToken()));
  const [activeSection, setActiveSection] = useState("home");
  const [aiOpen, setAiOpen] = useState(false);
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [needsTenantSelection, setNeedsTenantSelection] = useState(false);
  const [dropMode, setDropMode] = useState<"lookup" | "register">("lookup");
  const [registerPrefill, setRegisterPrefill] = useState<
    Partial<RegisterCustomerFormData>
  >(
    {}
  );
  const [lastCreatedCustomer, setLastCreatedCustomer] = useState<{
    id: string;
    name: string;
    phone: string;
    email?: string;
  } | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<{
    id: string;
    name: string;
    phone: string;
    email?: string;
  } | null>(null);
  const [dropDialogOpen, setDropDialogOpen] = useState(false);
  const [dropDialogLoading, setDropDialogLoading] = useState(false);
  const [dropDialogError, setDropDialogError] = useState<string | null>(null);
  const [orderTagPrintSettings, setOrderTagPrintSettings] = useState<{
    labelSize: OrderTagLabelSize;
    copies: number;
  }>({
    labelSize: "2x1",
    copies: 1,
  });
  const [orders, setOrders] = useState<
    {
      id: string;
      customer_name: string;
      phone: string;
      status: "in-progress" | "ready" | "picked-up" | "cancelled";
      invoice_number: string;
      order_sku: string;
      barcode_svg_url?: string;
      total: number;
      created_at: string;
    }[]
  >([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [storageLocationStatus, setStorageLocationStatus] = useState<
    StorageLocationStatusRow[]
  >([]);
  const [storageLocationStatusLoading, setStorageLocationStatusLoading] =
    useState(false);
  const [storageLocationStatusError, setStorageLocationStatusError] = useState<
    string | null
  >(null);
  const [ordersAutoScanSeed, setOrdersAutoScanSeed] = useState<{
    token: number;
    barcode: string;
  } | null>(null);
  const [ordersView, setOrdersView] = useState<"list" | "detail">("list");
  const [ordersFilters, setOrdersFilters] = useState({ status: "all", query: "" });
  const [orderDetailId, setOrderDetailId] = useState<string | null>(null);
  const [orderDetailLoading, setOrderDetailLoading] = useState(false);
  const [orderDetailError, setOrderDetailError] = useState<string | null>(null);
  const [orderDetailSummary, setOrderDetailSummary] = useState<
    (OrderSummary & { id: string; number: string }) | null
  >(null);
  const [orderDetailItems, setOrderDetailItems] = useState<OrderItem[]>([]);
  const [orderDetailPayments, setOrderDetailPayments] = useState<Payment[]>([]);
  const [orderDetailTimeline, setOrderDetailTimeline] = useState<TimelineEvent[]>([]);
  const [orderDetailNotes, setOrderDetailNotes] = useState<string>("");
  const [orderDetailRawStatus, setOrderDetailRawStatus] = useState<string | null>(
    null
  );
  const [orderDetailCustomerId, setOrderDetailCustomerId] = useState<string | null>(
    null
  );
  const [editItemsOpen, setEditItemsOpen] = useState(false);
  const [editItemsLoading, setEditItemsLoading] = useState(false);
  const [editItemsError, setEditItemsError] = useState<string | null>(null);
  const [pickupPaymentLoading, setPickupPaymentLoading] = useState(false);
  const [pickupPaymentError, setPickupPaymentError] = useState<string | null>(null);
  const [cancelOrderLoading, setCancelOrderLoading] = useState(false);
  const [customerProfileId, setCustomerProfileId] = useState<string | null>(null);
  const [customerProfileLoading, setCustomerProfileLoading] = useState(false);
  const [customerProfileError, setCustomerProfileError] = useState<string | null>(null);
  const [customerProfile, setCustomerProfile] = useState<CustomerProfile | null>(
    null
  );
  const [customerProfileOrders, setCustomerProfileOrders] = useState<CustomerOrder[]>(
    []
  );
  const [customerProfileNotesExtras, setCustomerProfileNotesExtras] = useState<
    string[]
  >([]);
  const [extrasView, setExtrasView] = useState<
    "menu" | "inventory" | "customers" | "earnings" | "reports"
  >("menu");
  const [pendingExtrasView, setPendingExtrasView] = useState<
    "menu" | "inventory" | "customers" | "earnings" | "reports" | null
  >(null);
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [inventoryError, setInventoryError] = useState<string | null>(null);
  const [dropInventoryItems, setDropInventoryItems] = useState<InventoryItem[]>([]);
  const [customersList, setCustomersList] = useState<CustomerListItem[]>([]);
  const [customersLoading, setCustomersLoading] = useState(false);
  const [customersError, setCustomersError] = useState<string | null>(null);
  const [customersQuery, setCustomersQuery] = useState("");
  const [earningsDate, setEarningsDate] = useState(() => {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${now.getFullYear()}-${month}-${day}`;
  });
  const [earningsLoading, setEarningsLoading] = useState(false);
  const [earningsError, setEarningsError] = useState<string | null>(null);
  const [earningsSummary, setEarningsSummary] = useState<{
    date: string;
    totals: { count: number; in_cents: number; out_cents: number; net_cents: number };
    by_method: Array<{
      method: string;
      count: number;
      in_cents: number;
      out_cents: number;
      net_cents: number;
    }>;
  } | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    description: string;
    confirmLabel: string;
    cancelLabel: string;
    confirmVariant: "default" | "destructive";
  }>({
    open: false,
    title: "",
    description: "",
    confirmLabel: "Yes",
    cancelLabel: "Cancel",
    confirmVariant: "default",
  });
  const confirmResolverRef = useRef<((value: boolean) => void) | null>(null);

  const requestConfirmation = (options: {
    title: string;
    description: string;
    confirmLabel?: string;
    cancelLabel?: string;
    confirmVariant?: "default" | "destructive";
  }) =>
    new Promise<boolean>((resolve) => {
      confirmResolverRef.current = resolve;
      setConfirmDialog({
        open: true,
        title: options.title,
        description: options.description,
        confirmLabel: options.confirmLabel ?? "Yes",
        cancelLabel: options.cancelLabel ?? "Cancel",
        confirmVariant: options.confirmVariant ?? "default",
      });
    });

  const resolveConfirmation = (value: boolean) => {
    const resolver = confirmResolverRef.current;
    confirmResolverRef.current = null;
    setConfirmDialog((prev) => ({ ...prev, open: false }));
    if (resolver) resolver(value);
  };

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    clearAuth();
    setIsLoggedIn(false);
    setNeedsTenantSelection(false);
    setActiveSection("home");
  };

  const handleSwitchStore = () => {
    if (tenants.length <= 1) return;
    setNeedsTenantSelection(true);
  };

  const handleSelectSection = (section: string) => {
    // Global navigation should always exit customer profile context.
    setCustomerProfileId(null);
    setCustomerProfileError(null);
    setActiveSection(section);
  };

  const handleRegisterSave = async (data: RegisterCustomerFormData) => {
    const fullName = `${data.firstName.trim()} ${data.lastName.trim()}`.trim();
    const normalizedPhone = data.phone.replace(/\D/g, "");
    const notes = buildCustomerNotes({
      address: data.address,
      preferences: data.preferences,
      popUpMessage: data.popUpMessage,
    });

    try {
      const created = await createCustomer({
        name: fullName,
        phone: normalizedPhone || null,
        email: data.email.trim() ? data.email.trim() : null,
        notes,
      });

      setLastCreatedCustomer({
        id: String(created.id),
        name: created.name,
        phone: created.phone || normalizedPhone,
        email: created.email ?? undefined,
      });
      setDropMode("lookup");
      toast({ title: "Customer created." });
    } catch (err) {
      toast({
        title: "Unable to create customer.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
    }
  };

  const parseCustomerNotes = (notes?: string | null) => {
    const result = {
      address: "",
      preferences: "",
      popUpMessage: "",
      extras: [] as string[],
    };
    if (!notes) return result;
    const lines = notes.split("\n").map((line) => line.trim()).filter(Boolean);
    lines.forEach((line) => {
      const lower = line.toLowerCase();
      if (lower.startsWith("address:")) {
        result.address = line.split(":").slice(1).join(":").trim();
        return;
      }
      if (lower.startsWith("preferences:")) {
        result.preferences = line.split(":").slice(1).join(":").trim();
        return;
      }
      if (lower.startsWith("pop-up:") || lower.startsWith("popup:")) {
        result.popUpMessage = line.split(":").slice(1).join(":").trim();
        return;
      }
      result.extras.push(line);
    });
    return result;
  };

  const buildCustomerNotes = (
    data: { address?: string; preferences?: string; popUpMessage?: string },
    extras: string[] = []
  ) => {
    const notesParts = [
      data.address ? `Address: ${data.address}` : "",
      data.preferences ? `Preferences: ${data.preferences}` : "",
      data.popUpMessage ? `Pop-up: ${data.popUpMessage}` : "",
      ...extras,
    ].filter(Boolean);
    return notesParts.length ? notesParts.join("\n") : null;
  };

  const extractPopUpMessage = (notes?: string | null) => {
    return parseCustomerNotes(notes).popUpMessage;
  };

  const mapOrderStatus = (
    status: string
  ): "in-progress" | "ready" | "picked-up" | "cancelled" => {
    if (status === "READY") return "ready";
    if (status === "PICKED_UP" || status === "COMPLETED") return "picked-up";
    if (status === "CANCELLED") return "cancelled";
    return "in-progress";
  };

  const mapCustomerOrderStatus = (
    status: string
  ): "in-progress" | "ready" | "picked-up" | "cancelled" => {
    if (status === "READY") return "ready";
    if (status === "PICKED_UP" || status === "COMPLETED") return "picked-up";
    if (status === "CANCELLED") return "cancelled";
    return "in-progress";
  };

  const mapCustomerListItem = (customer: {
    id: number;
    name: string;
    phone?: string | null;
    email?: string | null;
    created_at?: string;
  }): CustomerListItem => ({
    id: String(customer.id),
    name: customer.name,
    phone: customer.phone ?? "",
    email: customer.email ?? undefined,
    created_at: formatDateTime(customer.created_at),
  });

  const mapOrderCard = (card: OrderCard) => ({
    id: String(card.order_id),
    customer_name: card.customer?.name ?? "Unknown",
    phone: card.customer?.phone ?? "",
    status: mapOrderStatus(card.status),
    invoice_number: card.pickup_id ?? String(card.order_id),
    order_sku: card.order_sku ?? formatOrderSku(card.order_id),
    barcode_svg_url: card.barcode_svg_url,
    total: Number((card.money?.total_cents ?? 0) / 100),
    created_at: card.created_at,
  });

  const normalizeOrderTagSettings = (
    settings: Partial<TenantSettings> | null | undefined
  ) => {
    const labelSize: OrderTagLabelSize =
      settings?.order_tag_label_size === "4x2" ? "4x2" : "2x1";
    const parsedCopies = Number(settings?.order_tag_copies ?? 1);
    const copies = Number.isFinite(parsedCopies)
      ? Math.max(1, Math.min(20, Math.trunc(parsedCopies)))
      : 1;
    return { labelSize, copies };
  };

  const barcodeSvgToDataUri = (svg: string) =>
    `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;

  const fetchOrderBarcodeDataUri = async (orderId: number | string) => {
    try {
      const svg = await fetchOrderBarcodeSvg(orderId);
      return barcodeSvgToDataUri(svg);
    } catch {
      return null;
    }
  };

  const printOrderTag = async (options: {
    orderId: number | string;
    orderSku?: string;
    customerName?: string;
    copies?: number;
    openedWindow?: Window | null;
  }) => {
    const openedWindow =
      options.openedWindow ??
      window.open("", "_blank", "width=480,height=640");
    if (!openedWindow) {
      toast({
        title: "Couldn't open print window.",
        description: "Allow pop-ups to print SKU tags.",
        variant: "error",
      });
      return false;
    }
    openedWindow.document.write(
      "<!doctype html><html><body style='font-family: Arial, sans-serif; padding: 24px;'>Preparing SKU tag...</body></html>"
    );
    openedWindow.document.close();

    const barcodeDataUri = await fetchOrderBarcodeDataUri(options.orderId);
    const printed = openOrderSkuTagPrint({
      ...options,
      openedWindow,
      labelSize: orderTagPrintSettings.labelSize,
      copies:
        options.copies !== undefined
          ? options.copies
          : orderTagPrintSettings.copies,
      barcodeDataUri: barcodeDataUri ?? undefined,
    });
    if (!printed) {
      toast({
        title: "Couldn't open print window.",
        description: "Allow pop-ups to print SKU tags.",
        variant: "error",
      });
      return false;
    }
    if (!barcodeDataUri) {
      toast({
        title: "Barcode unavailable for this print.",
        description: "Tag printed with SKU text only.",
      });
    }
    return true;
  };

  const loadOrders = async () => {
    setOrdersLoading(true);
    setOrdersError(null);
    try {
      const data = await fetchOrderCards({ limit: 200, offset: 0 });
      setOrders(data.results.map(mapOrderCard));
    } catch (err) {
      setOrdersError(err instanceof Error ? err.message : "Unable to load orders.");
    } finally {
      setOrdersLoading(false);
    }
  };

  const loadStorageLocationStatus = async () => {
    setStorageLocationStatusLoading(true);
    setStorageLocationStatusError(null);
    try {
      const payload = await fetchStorageLocationStatus();
      setStorageLocationStatus(payload.results);
    } catch (err) {
      setStorageLocationStatusError(
        err instanceof Error ? err.message : "Unable to load rack status."
      );
    } finally {
      setStorageLocationStatusLoading(false);
    }
  };

  const handleLookupStorageLocation = async (barcode: string) => {
    const result = await lookupStorageLocation(barcode);
    return {
      exists: result.exists,
      rack_number: result.rack_number,
    };
  };

  const handleAssignStorageLocation = async (payload: {
    locationBarcode: string;
    orderBarcode: string;
    rackNumber?: string;
  }) => {
    let assignment: StorageLocationAssignment;
    try {
      assignment = await assignStorageLocationByScan({
        location_barcode: payload.locationBarcode,
        order_barcode: payload.orderBarcode,
        rack_number: payload.rackNumber,
      });
    } catch (err) {
      const apiError = err as Error & {
        status?: number;
        data?: {
          code?: string;
          rack_number?: string | null;
          current_order_sku?: string;
        };
      };
      const isRackOccupied =
        apiError.status === 409 && apiError.data?.code === "storage_location_occupied";
      if (!isRackOccupied) {
        throw err;
      }

      const rackText = apiError.data?.rack_number
        ? `Rack ${apiError.data.rack_number}`
        : "This rack";
      const occupiedSku = apiError.data?.current_order_sku
        ? ` (${apiError.data.current_order_sku})`
        : "";
      const confirmed = await requestConfirmation({
        title: "Rack full",
        description: `${rackText} is already full with another order${occupiedSku}. Do you want to clear rack and continue?`,
        confirmLabel: "Yes",
        cancelLabel: "Cancel",
      });
      if (!confirmed) {
        throw new Error("Rack already full.");
      }

      assignment = await assignStorageLocationByScan({
        location_barcode: payload.locationBarcode,
        order_barcode: payload.orderBarcode,
        rack_number: payload.rackNumber,
        force_clear: true,
      });
    }

    await loadOrders();
    void loadStorageLocationStatus();
    if (ordersView === "detail" && orderDetailId && String(assignment.order_id) === orderDetailId) {
      await loadOrderDetail(orderDetailId);
    }

    toast({
      title: "Location assigned.",
      description: assignment.rack_number
        ? `Order ${assignment.order_sku} -> ${assignment.location_barcode} (Rack ${assignment.rack_number})`
        : `Order ${assignment.order_sku} -> ${assignment.location_barcode}`,
    });

    return assignment;
  };

  const mapReceiptStatus = (status: string) => {
    if (status === "READY") return "ready";
    if (status === "PICKED_UP" || status === "COMPLETED") return "picked-up";
    if (status === "CANCELLED") return "cancelled";
    return "in-progress";
  };

  const mapPaymentMethod = (method: string): Payment["method"] => {
    const normalized = method.toLowerCase();
    if (normalized === "cash") return "cash";
    if (normalized === "card") return "card";
    if (normalized === "online") return "online";
    return "other";
  };

  const formatDateTime = (value: string | null | undefined) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  };

  const formatDate = (value: string | null | undefined) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString();
  };

  const loadOrderDetail = async (orderId: string) => {
    setOrderDetailLoading(true);
    setOrderDetailError(null);
    setOrderDetailItems([]);
    setOrderDetailPayments([]);
    setOrderDetailTimeline([]);
    setOrderDetailNotes("");
    setOrderDetailRawStatus(null);
    setOrderDetailCustomerId(null);
    setPickupPaymentError(null);
    try {
      const [receipt, timeline, notes, barcodeDataUri, storageLocation] = await Promise.all([
        fetchOrderReceipt(orderId),
        fetchOrderTimeline(orderId),
        fetchOrderNotes(orderId),
        fetchOrderBarcodeSvg(orderId)
          .then(barcodeSvgToDataUri)
          .catch(() => null),
        fetchOrderStorageLocation(orderId).catch(() => null),
      ]);

      const summary: OrderSummary & { id: string; number: string } = {
        id: String(receipt.id),
        number: String(receipt.order_number ?? receipt.id),
        customer_name: receipt.customer?.name ?? "Unknown",
        phone: receipt.customer?.phone ?? "",
        email: receipt.customer?.email ?? undefined,
        order_sku: receipt.order_sku ?? formatOrderSku(receipt.id),
        location_barcode: storageLocation?.location_barcode ?? undefined,
        rack_number: storageLocation?.rack_number ?? undefined,
        barcode_data_uri: barcodeDataUri ?? undefined,
        created_date: formatDate(receipt.created_at),
        due_date: formatDate(receipt.due_at),
        total: Number(receipt.total_cents / 100),
        paid: Number(receipt.net_paid_cents / 100),
        balance_due: Number(receipt.balance_due_cents / 100),
        status: mapReceiptStatus(receipt.status),
      };

      const items: OrderItem[] = receipt.items.map((item) => ({
        id: String(item.id),
        itemId: String(item.item),
        name: item.item_name,
        quantity: item.quantity,
        unit_price: Number(item.unit_price_cents / 100),
        line_total: Number(item.line_total_cents / 100),
      }));

      const payments: Payment[] = receipt.payments.map((payment) => ({
        id: String(payment.id),
        method: mapPaymentMethod(payment.method),
        amount:
          payment.direction === "OUT"
            ? -Number(payment.amount_cents / 100)
            : Number(payment.amount_cents / 100),
        status: payment.status === "CAPTURED" ? "captured" : "void",
        timestamp: formatDateTime(payment.created_at),
      }));

      const events: TimelineEvent[] = timeline.map((event: any) => ({
        id: String(event.id),
        title: event.title ?? event.event_type ?? "Event",
        timestamp: formatDateTime(event.created_at ?? event.at),
        actor: event.actor?.label ?? undefined,
        note: event.meta?.note || event.summary || undefined,
      }));

      const notesText = [
        receipt.notes ?? "",
        ...notes.map((note: any) => note.note).filter(Boolean),
      ]
        .filter(Boolean)
        .join("\n");

      setOrderDetailSummary(summary);
      setOrderDetailRawStatus(receipt.status);
      setOrderDetailCustomerId(
        receipt.customer?.id ? String(receipt.customer.id) : null
      );
      setOrderDetailItems(items);
      setOrderDetailPayments(payments);
      setOrderDetailTimeline(events);
      setOrderDetailNotes(notesText);
    } catch (err) {
      setOrderDetailError(
        err instanceof Error ? err.message : "Unable to load order details."
      );
    } finally {
      setOrderDetailLoading(false);
    }
  };

  const mapInventoryItem = (item: InventoryItemApi): InventoryItem => ({
    id: String(item.id),
    name: item.name,
    sku: item.sku ?? "",
    imageUrl: resolveInventoryImageUrl(item.image_url),
    price: Number(item.unit_price_cents / 100),
    category: "",
    active: item.is_active,
  });

  const loadInventory = async () => {
    setInventoryLoading(true);
    setInventoryError(null);
    try {
      const data = await fetchInventoryItems();
      setInventoryItems(data.map(mapInventoryItem));
    } catch (err) {
      setInventoryError(
        err instanceof Error ? err.message : "Unable to load inventory."
      );
    } finally {
      setInventoryLoading(false);
    }
  };

  const handlePickupPayment = async (payload: {
    amount: number;
    method: "CASH" | "CARD" | "ONLINE" | "OTHER";
    reference?: string;
  }) => {
    if (!orderDetailId) return;
    setPickupPaymentLoading(true);
    setPickupPaymentError(null);
    try {
      await createPickupPayment(orderDetailId, {
        amount_cents: Math.round(payload.amount * 100),
        method: payload.method,
        reference: payload.reference,
      });
      await loadOrderDetail(orderDetailId);
      await loadOrders();
      toast({ title: "Payment recorded." });
    } catch (err) {
      setPickupPaymentError(
        err instanceof Error ? err.message : "Unable to record payment."
      );
    } finally {
      setPickupPaymentLoading(false);
    }
  };

  const handleCancelOrder = async () => {
    if (!orderDetailId) return;
    const confirmed = await requestConfirmation({
      title: "Cancel order?",
      description: "Cancel this order? This cannot be undone.",
      confirmLabel: "Yes",
      cancelLabel: "Cancel",
      confirmVariant: "destructive",
    });
    if (!confirmed) return;
    setCancelOrderLoading(true);
    try {
      await updateOrderStatus(orderDetailId, "CANCELLED");
      await loadOrderDetail(orderDetailId);
      await loadOrders();
      toast({ title: "Order cancelled." });
    } catch (err) {
      toast({
        title: "Unable to cancel order.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setCancelOrderLoading(false);
    }
  };

  const loadDropInventory = async () => {
    try {
      const data = await fetchInventoryItems();
      setDropInventoryItems(data.map(mapInventoryItem));
    } catch (err) {
      toast({
        title: "Unable to load inventory.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
    }
  };

  const loadCustomersList = async (query: string) => {
    setCustomersLoading(true);
    setCustomersError(null);
    try {
      if (query.trim().length >= 2) {
        const results = await searchCustomers(query.trim());
        setCustomersList(results.map(mapCustomerListItem));
      } else {
        const results = await fetchCustomers({ limit: 200, offset: 0 });
        setCustomersList(results.map(mapCustomerListItem));
      }
    } catch (err) {
      setCustomersError(
        err instanceof Error ? err.message : "Unable to load customers."
      );
    } finally {
      setCustomersLoading(false);
    }
  };

  const loadDailyEarnings = async (date: string) => {
    setEarningsLoading(true);
    setEarningsError(null);
    try {
      const summary = await fetchPaymentsDailySummary(date);
      setEarningsSummary({
        date: summary.date,
        totals: {
          count: summary.totals.count,
          in_cents: summary.totals.in_cents,
          out_cents: summary.totals.out_cents,
          net_cents: summary.totals.net_cents,
        },
        by_method: summary.by_method.map((row) => ({
          method: row.method,
          count: row.count,
          in_cents: row.in_cents,
          out_cents: row.out_cents,
          net_cents: row.net_cents,
        })),
      });
    } catch (err) {
      setEarningsError(
        err instanceof Error ? err.message : "Unable to load earnings."
      );
    } finally {
      setEarningsLoading(false);
    }
  };

  const loadCustomerProfile = async (customerId: string) => {
    setCustomerProfileLoading(true);
    setCustomerProfileError(null);
    setCustomerProfile(null);
    setCustomerProfileOrders([]);
    setCustomerProfileNotesExtras([]);
    try {
      const [detail, ordersData] = await Promise.all([
        fetchCustomerDetail(customerId),
        fetchCustomerOrders(customerId, { limit: 200, offset: 0 }),
      ]);

      const parsedNotes = parseCustomerNotes(detail.notes);
      setCustomerProfileNotesExtras(parsedNotes.extras);

      setCustomerProfile({
        id: String(detail.id),
        name: detail.name,
        phone: detail.phone ?? "",
        email: detail.email ?? undefined,
        address: parsedNotes.address || undefined,
        preferences: parsedNotes.preferences || undefined,
        popUpMessage: parsedNotes.popUpMessage || undefined,
        created_at: formatDate(detail.created_at),
      });

      const mappedOrders: CustomerOrder[] = ordersData.results.map((order) => ({
        id: String(order.id),
        invoice_number: String(order.id),
        created_at: formatDateTime(order.created_at),
        status: mapCustomerOrderStatus(order.status),
        total: Number(order.total_cents / 100),
      }));

      setCustomerProfileOrders(mappedOrders);
    } catch (err) {
      setCustomerProfileError(
        err instanceof Error ? err.message : "Unable to load customer."
      );
    } finally {
      setCustomerProfileLoading(false);
    }
  };

  const handleUpdateCustomer = async (customerId: string, data: CustomerEditFormData) => {
    const fullName = `${data.firstName.trim()} ${data.lastName.trim()}`.trim();
    const normalizedPhone = data.phone.replace(/\D/g, "");
    const notes = buildCustomerNotes(
      {
        address: data.address,
        preferences: data.preferences,
        popUpMessage: data.popUpMessage,
      },
      customerProfileNotesExtras
    );

    await updateCustomer(customerId, {
      name: fullName,
      phone: normalizedPhone || null,
      email: data.email.trim() ? data.email.trim() : null,
      notes,
    });

    await loadCustomerProfile(customerId);
    toast({ title: "Customer updated." });
  };

  const handleSaveOrderItems = async (
    updatedItems: { itemId: string; quantity: number }[]
  ) => {
    if (!orderDetailId) return;
    setEditItemsLoading(true);
    setEditItemsError(null);
    try {
      const existingItems = orderDetailItems;
      const existingByItemId = new Map(
        existingItems.map((item) => [item.itemId, item])
      );
      const desiredItemIds = new Set(
        updatedItems.filter((item) => item.quantity > 0).map((item) => item.itemId)
      );

      const operations: Promise<unknown>[] = [];

      updatedItems.forEach((item) => {
        if (item.quantity <= 0) return;
        const existing = existingByItemId.get(item.itemId);
        if (existing) {
          if (existing.quantity !== item.quantity) {
            operations.push(
              updateOrderItem(existing.id, { quantity: item.quantity })
            );
          }
        } else {
          operations.push(
            createOrderItem({
              order: Number(orderDetailId),
              item: Number(item.itemId),
              quantity: item.quantity,
            })
          );
        }
      });

      existingItems.forEach((item) => {
        if (!desiredItemIds.has(item.itemId)) {
          operations.push(deleteOrderItem(item.id));
        }
      });

      if (!operations.length) {
        setEditItemsOpen(false);
        return;
      }

      await Promise.all(operations);
      await loadOrderDetail(orderDetailId);
      await loadOrders();
      toast({ title: "Order items updated." });
      setEditItemsOpen(false);
    } catch (err) {
      setEditItemsError(
        err instanceof Error ? err.message : "Unable to update items."
      );
    } finally {
      setEditItemsLoading(false);
    }
  };

  const handleCreateInventory = async (data: InventoryFormData) => {
    try {
      const price = Number(data.price);
      await createInventoryItem({
        name: data.name.trim(),
        sku: data.sku.trim(),
        image: data.imageFile,
        unit_price_cents: Math.round(price * 100),
        is_active: data.active,
      });
      await loadInventory();
      toast({ title: "Inventory item created." });
    } catch (err) {
      toast({
        title: "Unable to create item.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
      throw err;
    }
  };

  const handleEditInventory = async (id: string, data: InventoryFormData) => {
    try {
      const price = Number(data.price);
      await updateInventoryItem(Number(id), {
        name: data.name.trim(),
        sku: data.sku.trim(),
        image: data.imageFile,
        clear_image: data.removeImage,
        unit_price_cents: Math.round(price * 100),
        is_active: data.active,
      });
      await loadInventory();
      toast({ title: "Inventory item updated." });
    } catch (err) {
      toast({
        title: "Unable to update item.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
      throw err;
    }
  };

  const handleArchiveInventory = async (id: string) => {
    try {
      await updateInventoryItem(Number(id), { is_active: false });
      await loadInventory();
      toast({ title: "Inventory item archived." });
    } catch (err) {
      toast({
        title: "Unable to archive item.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
      throw err;
    }
  };

  useEffect(() => {
    if (!isLoggedIn) return;
    if (activeSection !== "orders") return;
    void loadOrders();
    void loadStorageLocationStatus();
    setOrdersView("list");
    setOrderDetailId(null);
  }, [activeSection, isLoggedIn]);

  useEffect(() => {
    if (activeSection !== "extras") return;
    if (pendingExtrasView) {
      setExtrasView(pendingExtrasView);
      setPendingExtrasView(null);
      return;
    }
    setExtrasView("menu");
  }, [activeSection, pendingExtrasView]);

  useEffect(() => {
    if (!isLoggedIn) return;
    if (activeSection !== "extras") return;
    if (extrasView !== "inventory") return;
    void loadInventory();
  }, [activeSection, extrasView, isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) return;
    if (activeSection !== "extras") return;
    if (extrasView !== "customers") return;
    const handle = setTimeout(() => {
      void loadCustomersList(customersQuery);
    }, 250);
    return () => clearTimeout(handle);
  }, [activeSection, extrasView, customersQuery, isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) return;
    if (activeSection !== "extras") return;
    if (extrasView !== "earnings") return;
    void loadDailyEarnings(earningsDate);
  }, [activeSection, extrasView, earningsDate, isLoggedIn]);

  useEffect(() => {
    if (!dropDialogOpen && !editItemsOpen) return;
    void loadDropInventory();
  }, [dropDialogOpen, editItemsOpen]);

  useEffect(() => {
    if (!customerProfileId) return;
    void loadCustomerProfile(customerProfileId);
  }, [customerProfileId]);

  useEffect(() => {
    if (!isLoggedIn || needsTenantSelection) return;
    let isMounted = true;
    fetchSettings()
      .then((settings) => {
        if (!isMounted) return;
        setOrderTagPrintSettings(normalizeOrderTagSettings(settings));
      })
      .catch(() => {
        if (!isMounted) return;
        setOrderTagPrintSettings({ labelSize: "2x1", copies: 1 });
      });
    return () => {
      isMounted = false;
    };
  }, [isLoggedIn, needsTenantSelection]);

  useEffect(() => {
    return () => {
      if (confirmResolverRef.current) {
        confirmResolverRef.current(false);
        confirmResolverRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!isLoggedIn || needsTenantSelection) return;

    let buffer = "";
    let startedAt = 0;
    let lastAt = 0;

    const resetBuffer = () => {
      buffer = "";
      startedAt = 0;
      lastAt = 0;
    };

    const isEditableTarget = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) return false;
      if (target.isContentEditable) return true;
      const editable = target.closest("input, textarea, [contenteditable='true']");
      return Boolean(editable);
    };

    const onWindowKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (isEditableTarget(event.target)) return;

      const now = Date.now();
      if (buffer && now - lastAt > 120) {
        resetBuffer();
      }

      if (event.key === "Enter") {
        if (!buffer) return;
        const scanValue = buffer.trim().toUpperCase();
        const elapsedMs = startedAt ? now - startedAt : 0;
        resetBuffer();

        const looksLikeScannerInput =
          scanValue.length >= 6 && elapsedMs > 0 && elapsedMs <= 1000;
        const supportedBarcode =
          LOCATION_SCANNER_RE.test(scanValue) || ORDER_SCANNER_RE.test(scanValue);
        if (!looksLikeScannerInput || !supportedBarcode) return;

        setCustomerProfileId(null);
        setCustomerProfileError(null);
        setActiveSection("orders");
        setOrdersView("list");
        setOrderDetailId(null);
        setOrdersAutoScanSeed({
          token: Date.now(),
          barcode: scanValue,
        });
        return;
      }

      if (event.key.length === 1) {
        if (!buffer) startedAt = now;
        buffer += event.key;
        lastAt = now;
      }
    };

    window.addEventListener("keydown", onWindowKeyDown, true);
    return () => {
      window.removeEventListener("keydown", onWindowKeyDown, true);
    };
  }, [isLoggedIn, needsTenantSelection]);

  useEffect(() => {
    if (!isLoggedIn) return;
    let isMounted = true;

    fetchTenants()
      .then((list) => {
        if (!isMounted) return;
        setTenants(list);

        if (!list.length) {
          clearAuth();
          setIsLoggedIn(false);
          return;
        }

        const currentSlug = getTenantSlug();
        if (currentSlug && list.some((t) => t.tenant_slug === currentSlug)) {
          setNeedsTenantSelection(false);
          return;
        }

        if (list.length === 1) {
          setTenantSlug(list[0].tenant_slug);
          setNeedsTenantSelection(false);
          return;
        }

        clearTenantSlug();
        setNeedsTenantSelection(true);
      })
      .catch(() => {
        if (!isMounted) return;
        clearAuth();
        setIsLoggedIn(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isLoggedIn]);

  if (!isLoggedIn) {
    return (
      <>
        <LoginPage onLogin={handleLogin} />
        <Toaster />
      </>
    );
  }

  if (needsTenantSelection) {
    return (
      <>
        <TenantSelector
          tenants={tenants}
          onSelectStore={(slug) => {
            setTenantSlug(slug);
            setNeedsTenantSelection(false);
          }}
        />
        <Toaster />
      </>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <TopNav activeSection={activeSection} setActiveSection={handleSelectSection} />
      <AIAssistantDialog open={aiOpen} onOpenChange={setAiOpen} />
      <button
        type="button"
        onClick={() => setAiOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
        aria-label="Open AI assistant"
        title="Open AI assistant"
      >
        <Sparkles className="h-5 w-5" />
      </button>
      <div className="flex flex-1">
        <Sidebar onSelectSection={handleSelectSection} />
        <main className="flex-1 p-8">
          {customerProfileId ? (
            <CustomerProfilePage
              customer={customerProfile}
              orders={customerProfileOrders}
              loading={customerProfileLoading}
              error={customerProfileError}
              onBack={() => {
                setCustomerProfileId(null);
                setCustomerProfileError(null);
              }}
              onRetry={() => {
                if (customerProfileId) {
                  void loadCustomerProfile(customerProfileId);
                }
              }}
              onUpdateCustomer={handleUpdateCustomer}
              onStartDropOff={(customerId) => {
                if (!customerProfile) return;
                if (customerProfile.id !== customerId) return;
                setSelectedCustomer({
                  id: customerProfile.id,
                  name: customerProfile.name,
                  phone: customerProfile.phone,
                  email: customerProfile.email,
                });
                setActiveSection("drop");
                setDropMode("lookup");
                setCustomerProfileId(null);
                setDropDialogOpen(true);
              }}
              onViewOrder={(orderId) => {
                const order = customerProfileOrders.find((item) => item.id === orderId);
                setActiveSection("orders");
                setOrdersView("detail");
                if (customerProfile) {
                  setOrderDetailSummary({
                    id: orderId,
                    number: order?.invoice_number ?? orderId,
                    customer_name: customerProfile.name,
                    phone: customerProfile.phone,
                    email: customerProfile.email,
                    created_date: order ? order.created_at : "—",
                    due_date: "—",
                    total: order?.total ?? 0,
                    paid: 0,
                    balance_due: order?.total ?? 0,
                    status: order?.status ?? "in-progress",
                  });
                } else {
                  setOrderDetailSummary(null);
                }
                setOrderDetailId(orderId);
                setCustomerProfileId(null);
                void loadOrderDetail(orderId);
              }}
            />
          ) : (
            <>
              {activeSection === "home" && <DashboardContent />}
              {activeSection === "drop" && dropMode === "lookup" && (
                <DropPage
                  initialCustomer={lastCreatedCustomer}
                  onRegister={(prefill) => {
                    setRegisterPrefill({
                      phone: prefill.phone ?? "",
                      firstName: prefill.firstName ?? "",
                      lastName: prefill.lastName ?? "",
                    });
                    setDropMode("register");
                  }}
                  onStartDropOff={(customer) => {
                    setSelectedCustomer(customer);
                    setDropDialogOpen(true);
                    fetchCustomerDetail(customer.id)
                      .then((detail) => {
                        const message = extractPopUpMessage(detail.notes);
                        if (message) {
                          toast({
                            title: "Customer Pop-up",
                            description: message,
                          });
                        }
                      })
                      .catch(() => {
                        // Silent failure: don't block drop-off flow.
                      });
                  }}
                />
              )}
              {activeSection === "drop" && dropMode === "register" && (
                <RegisterCustomerPage
                  initialData={registerPrefill}
                  onCancel={() => setDropMode("lookup")}
                  onSave={handleRegisterSave}
                />
              )}
              {activeSection === "admin" && (
                <AdminPage
                  onLogout={handleLogout}
                  onSwitchStore={handleSwitchStore}
                  canSwitchStore={tenants.length > 1}
                  onSettingsChange={(settings) => {
                    setOrderTagPrintSettings(normalizeOrderTagSettings(settings));
                  }}
                />
              )}
              {activeSection === "orders" && (
                <>
                  {ordersView === "list" && (
                    <OrdersPage
                      orders={orders}
                      loading={ordersLoading}
                      error={ordersError}
                      filters={ordersFilters}
                      onFilterChange={setOrdersFilters}
                      onLookupStorageLocation={handleLookupStorageLocation}
                      onAssignStorageLocation={handleAssignStorageLocation}
                      storageLocationStatus={storageLocationStatus}
                      storageLocationStatusLoading={storageLocationStatusLoading}
                      storageLocationStatusError={storageLocationStatusError}
                      onRefreshStorageLocationStatus={() => {
                        void loadStorageLocationStatus();
                      }}
                      autoScanSeed={ordersAutoScanSeed}
                      onPrintTag={(order) => {
                        void printOrderTag({
                          orderId: order.id,
                          orderSku: order.order_sku,
                          customerName: order.customer_name,
                        });
                      }}
                      onCreate={() => {
                        setActiveSection("drop");
                        setDropMode("lookup");
                      }}
                      onViewOrder={(orderId) => {
                        const existing = orders.find((order) => order.id === orderId);
                        if (existing) {
                          setOrderDetailSummary({
                            id: existing.id,
                            number: existing.invoice_number,
                            customer_name: existing.customer_name,
                            phone: existing.phone,
                            created_date: formatDate(existing.created_at),
                            due_date: "—",
                            total: existing.total,
                            paid: 0,
                            balance_due: existing.total,
                            status: existing.status,
                          });
                        } else {
                          setOrderDetailSummary(null);
                        }
                        setOrderDetailId(orderId);
                        setOrdersView("detail");
                        void loadOrderDetail(orderId);
                      }}
                    />
                  )}
                  {ordersView === "detail" && orderDetailSummary && (
                    <OrderDetailPage
                      order={orderDetailSummary}
                      items={orderDetailItems}
                      payments={orderDetailPayments}
                      timeline={orderDetailTimeline}
                      notes={orderDetailNotes}
                      loading={orderDetailLoading}
                      error={orderDetailError}
                      onBack={() => {
                        setOrdersView("list");
                        setOrderDetailId(null);
                        setPickupPaymentError(null);
                        setOrderDetailCustomerId(null);
                      }}
                      onEditItems={() => {
                        setEditItemsError(null);
                        setEditItemsOpen(true);
                      }}
                      canEditItems={
                        Boolean(orderDetailRawStatus) &&
                        orderDetailRawStatus !== "PICKED_UP" &&
                        orderDetailRawStatus !== "CANCELLED"
                      }
                      allowCollectPayment={
                        orderDetailRawStatus === "READY" ||
                        orderDetailRawStatus === "COMPLETED"
                      }
                      collectingPayment={pickupPaymentLoading}
                      collectPaymentError={pickupPaymentError}
                      onCollectPayment={handlePickupPayment}
                      onCancelOrder={handleCancelOrder}
                      canCancelOrder={
                        orderDetailRawStatus === "RECEIVED" ||
                        orderDetailRawStatus === "IN_PROGRESS" ||
                        orderDetailRawStatus === "READY"
                      }
                      cancelingOrder={cancelOrderLoading}
                      onViewCustomer={() => {
                        if (!orderDetailCustomerId) return;
                        setCustomerProfileId(orderDetailCustomerId);
                      }}
                      canViewCustomer={Boolean(orderDetailCustomerId)}
                      onAddNote={async (note) => {
                        if (!orderDetailId) return;
                        try {
                          await addOrderNote(orderDetailId, note);
                          await loadOrderDetail(orderDetailId);
                          toast({ title: "Note added." });
                        } catch (err) {
                          toast({
                            title: "Unable to add note.",
                            description:
                              err instanceof Error ? err.message : "Please try again.",
                            variant: "error",
                          });
                        }
                      }}
                      onMarkReady={async () => {
                        if (!orderDetailId) return;
                        try {
                          if (orderDetailRawStatus === "RECEIVED") {
                            await updateOrderStatus(orderDetailId, "IN_PROGRESS");
                          }
                          await markOrderReady(orderDetailId);
                          await loadOrderDetail(orderDetailId);
                          await loadOrders();
                          toast({ title: "Order marked ready." });
                        } catch (err) {
                          toast({
                            title: "Unable to mark ready.",
                            description:
                              err instanceof Error ? err.message : "Please try again.",
                            variant: "error",
                          });
                        }
                      }}
                      onMarkPickedUp={async () => {
                        if (!orderDetailId) return;
                        try {
                          await markOrderPickedUp(orderDetailId);
                          if (orderDetailSummary.location_barcode) {
                            const clearLocation = await requestConfirmation({
                              title: "Clear location?",
                              description:
                                "Pickup complete. Clear the stored location for this order?",
                              confirmLabel: "Yes",
                              cancelLabel: "No",
                            });
                            if (clearLocation) {
                              await clearOrderStorageLocation(orderDetailId);
                            }
                          }
                          await loadOrderDetail(orderDetailId);
                          await loadOrders();
                          void loadStorageLocationStatus();
                          toast({ title: "Order picked up." });
                        } catch (err) {
                          toast({
                            title: "Unable to pick up order.",
                            description:
                              err instanceof Error ? err.message : "Please try again.",
                            variant: "error",
                          });
                        }
                      }}
                    />
                  )}
                </>
              )}
          {activeSection === "extras" && extrasView === "menu" && (
            <ExtrasPage
              onOpenInventory={() => {
                setExtrasView("inventory");
              }}
              onOpenCustomers={() => {
                setCustomersQuery("");
                setExtrasView("customers");
              }}
              onOpenDailyEarnings={() => {
                setExtrasView("earnings");
              }}
              onOpenReports={() => {
                setExtrasView("reports");
              }}
            />
          )}
          {activeSection === "extras" && extrasView === "inventory" && (
            <div className="space-y-4">
              <button
                type="button"
                className="text-sm text-gray-600 hover:text-gray-900"
                onClick={() => setExtrasView("menu")}
              >
                ← Back to Extras
              </button>
              <InventoryPage
                items={inventoryItems}
                loading={inventoryLoading}
                error={inventoryError}
                onCreate={handleCreateInventory}
                onEdit={handleEditInventory}
                onArchive={handleArchiveInventory}
              />
            </div>
          )}
          {activeSection === "extras" && extrasView === "customers" && (
            <div className="space-y-4">
              <button
                type="button"
                className="text-sm text-gray-600 hover:text-gray-900"
                onClick={() => setExtrasView("menu")}
              >
                ← Back to Extras
              </button>
              <CustomersPage
                customers={customersList}
                loading={customersLoading}
                error={customersError}
                query={customersQuery}
                onQueryChange={setCustomersQuery}
                onViewCustomer={(customerId) => {
                  setCustomerProfileId(customerId);
                }}
              />
            </div>
          )}
          {activeSection === "extras" && extrasView === "earnings" && (
            <div className="space-y-4">
              <button
                type="button"
                className="text-sm text-gray-600 hover:text-gray-900"
                onClick={() => setExtrasView("menu")}
              >
                ← Back to Extras
              </button>
              <DailyEarningsPage
                date={earningsDate}
                summary={earningsSummary}
                loading={earningsLoading}
                error={earningsError}
                onDateChange={setEarningsDate}
              />
            </div>
          )}
          {activeSection === "extras" && extrasView === "reports" && (
            <div className="space-y-4">
              <button
                type="button"
                className="text-sm text-gray-600 hover:text-gray-900"
                onClick={() => setExtrasView("menu")}
              >
                ← Back to Extras
              </button>
              <DefaultReportsPage />
            </div>
          )}
              {activeSection === "dashboard" && (
                <DashboardSection
                  onOpenOrders={(filters) => {
                    setOrdersFilters({
                      status: filters?.status ?? "all",
                      query: filters?.query ?? "",
                    });
                    setActiveSection("orders");
                    setOrdersView("list");
                  }}
                  onOpenDrop={() => {
                    setActiveSection("drop");
                    setDropMode("lookup");
                  }}
                  onOpenCustomers={() => {
                    setPendingExtrasView("customers");
                    setActiveSection("extras");
                  }}
                  onOpenReports={() => {
                    setPendingExtrasView("reports");
                    setActiveSection("extras");
                  }}
                />
              )}
            </>
          )}
        </main>
      </div>
      <OrderItemsEditorDialog
        open={editItemsOpen}
        onOpenChange={setEditItemsOpen}
        items={dropInventoryItems}
        initialItems={orderDetailItems.map((item) => ({
          itemId: item.itemId,
          quantity: item.quantity,
        }))}
        onSave={handleSaveOrderItems}
        loading={editItemsLoading}
        error={editItemsError ?? undefined}
      />
      <StartDropOffDialog
        customer={selectedCustomer}
        items={dropInventoryItems.filter((item) => item.active)}
        open={dropDialogOpen}
        onOpenChange={setDropDialogOpen}
        loading={dropDialogLoading}
        error={dropDialogError ?? undefined}
        onCreate={async ({ dueDate, notes, items, payment }) => {
          if (!selectedCustomer) return;
          const preparedPrintWindow = window.open(
            "",
            "_blank",
            "width=480,height=640"
          );
          if (preparedPrintWindow) {
            preparedPrintWindow.document.write(
              "<!doctype html><html><body style='font-family: Arial, sans-serif; padding: 24px;'>Preparing SKU tag...</body></html>"
            );
            preparedPrintWindow.document.close();
          }
          setDropDialogLoading(true);
          setDropDialogError(null);
          try {
            const dueAt = dueDate ? `${dueDate}T00:00:00` : null;
            const trimmedNotes = notes.trim();
            const orderPayload: {
              customer: number;
              due_at?: string | null;
              notes?: string;
              initial_payment?: {
                amount_cents: number;
                method: "CASH" | "CARD" | "ONLINE" | "OTHER";
                reference?: string;
              };
            } = {
              customer: Number(selectedCustomer.id),
              due_at: dueAt,
            };
            if (trimmedNotes) {
              orderPayload.notes = trimmedNotes;
            }
            if (payment && payment.amount > 0) {
              orderPayload.initial_payment = {
                amount_cents: Math.round(payment.amount * 100),
                method: payment.method,
                reference: payment.reference,
              };
            }
            const createdOrder = await createDropoffOrder(orderPayload);
            const orderId = Number((createdOrder as { id?: number }).id);
            if (orderId && items.length) {
              await Promise.all(
                items.map((item) =>
                  createOrderItem({
                    order: orderId,
                    item: Number(item.itemId),
                    quantity: item.quantity,
                  })
                )
              );
            }
            if (orderId) {
              const orderSku = formatOrderSku(orderId);
              const totalPieces = Math.max(
                1,
                items.reduce((sum, item) => sum + item.quantity, 0)
              );
              await printOrderTag({
                orderId,
                orderSku,
                customerName: selectedCustomer.name,
                copies: totalPieces,
                openedWindow: preparedPrintWindow,
              });
              toast({
                title: "Order created.",
                description: `SKU ${orderSku} opened for printing (${totalPieces} tags).`,
              });
            } else {
              if (preparedPrintWindow && !preparedPrintWindow.closed) {
                preparedPrintWindow.close();
              }
              toast({ title: "Order created." });
            }
            setDropDialogOpen(false);
            void loadOrders();
          } catch (err) {
            if (preparedPrintWindow && !preparedPrintWindow.closed) {
              preparedPrintWindow.close();
            }
            setDropDialogError(
              err instanceof Error ? err.message : "Unable to create order."
            );
          } finally {
            setDropDialogLoading(false);
          }
        }}
      />
      <Dialog
        open={confirmDialog.open}
        onOpenChange={(open) => {
          if (!open && confirmDialog.open) {
            resolveConfirmation(false);
          }
        }}
      >
        <DialogContent className="sm:max-w-md" showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>{confirmDialog.title}</DialogTitle>
            <DialogDescription>{confirmDialog.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => resolveConfirmation(false)}
            >
              {confirmDialog.cancelLabel}
            </Button>
            <Button
              type="button"
              variant={confirmDialog.confirmVariant}
              onClick={() => resolveConfirmation(true)}
            >
              {confirmDialog.confirmLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Toaster />
    </div>
  );
}
