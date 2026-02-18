import { useEffect, useState, type ReactNode } from "react";
import { TrendingUp, TrendingDown, Package, Download, Upload } from "lucide-react";
import { fetchDashboardSummary } from "../../api/dashboard";
import { Card } from "../ui/card";

interface KPICardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  deltaPercent?: number | null;
}

function formatDeltaPercent(value: number) {
  const rounded = Number.parseFloat(value.toFixed(1));
  const hasDecimal = !Number.isInteger(rounded);
  const sign = rounded > 0 ? "+" : "";
  return `${sign}${hasDecimal ? rounded.toFixed(1) : rounded.toFixed(0)}%`;
}

function KPICard({ label, value, icon, deltaPercent }: KPICardProps) {
  const hasDelta = typeof deltaPercent === "number" && Number.isFinite(deltaPercent);
  const normalizedDelta = hasDelta
    ? Math.abs(deltaPercent) < 0.05
      ? 0
      : deltaPercent
    : null;
  const isNegative = normalizedDelta !== null && normalizedDelta < 0;

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 mb-2">{label}</p>
          <p className="text-3xl text-gray-900">{value}</p>
          {deltaPercent !== undefined && (
            <p
              className={`mt-2 flex items-center gap-1 text-sm ${
                hasDelta ? (isNegative ? "text-red-600" : "text-green-600") : "text-gray-500"
              }`}
            >
              {hasDelta ? (
                isNegative ? (
                  <TrendingDown className="h-4 w-4" />
                ) : (
                  <TrendingUp className="h-4 w-4" />
                )
              ) : null}
              {hasDelta
                ? `${formatDeltaPercent(normalizedDelta as number)} from yesterday`
                : "No baseline from yesterday"}
            </p>
          )}
        </div>
        <div className="text-gray-400">{icon}</div>
      </div>
    </Card>
  );
}

export function DashboardContent() {
  const [totalInvoices, setTotalInvoices] = useState<number | null>(null);
  const [totalPieces, setTotalPieces] = useState<number | null>(null);
  const [todaysDrop, setTodaysDrop] = useState<string | null>(null);
  const [todaysPickup, setTodaysPickup] = useState<string | null>(null);
  const [todaysDropDeltaPct, setTodaysDropDeltaPct] = useState<number | null | undefined>(
    undefined
  );
  const [todaysPickupDeltaPct, setTodaysPickupDeltaPct] = useState<number | null | undefined>(
    undefined
  );

  useEffect(() => {
    let isMounted = true;

    const loadMetrics = async () => {
      try {
        const summary = await fetchDashboardSummary();

        if (!isMounted) return;

        setTotalInvoices(summary.orders_today ?? null);
        setTotalPieces(summary.pieces_today ?? null);
        setTodaysDrop(summary.orders_value_today ?? null);
        setTodaysPickup(summary.collected_today ?? null);
        setTodaysDropDeltaPct(summary.orders_value_change_pct);
        setTodaysPickupDeltaPct(summary.collected_change_pct);
      } catch {
        if (!isMounted) return;
      }
    };

    loadMetrics();

    return () => {
      isMounted = false;
    };
  }, []);

  const formatCount = (value: number | null) => {
    if (value === null || value === undefined) return "—";
    return value.toLocaleString();
  };

  const formatCurrency = (value: string | number | null) => {
    if (value === null || value === undefined || value === "") return "—";
    const amount = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(amount)) return "—";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  return (
    <div>
      <h1 className="text-3xl mb-8 text-gray-800">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <KPICard
          label="Total Invoices"
          value={formatCount(totalInvoices)}
          icon={<TrendingUp className="w-8 h-8" />}
        />
        
        <KPICard
          label="Total Pieces"
          value={formatCount(totalPieces)}
          icon={<Package className="w-8 h-8" />}
        />
        
        <KPICard
          label="Today's Drop"
          value={formatCurrency(todaysDrop)}
          icon={<Download className="w-8 h-8" />}
          deltaPercent={todaysDropDeltaPct}
        />
        
        <KPICard
          label="Today's Pickup"
          value={formatCurrency(todaysPickup)}
          icon={<Upload className="w-8 h-8" />}
          deltaPercent={todaysPickupDeltaPct}
        />
      </div>
    </div>
  );
}
