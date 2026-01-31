import { useEffect, useState, type ReactNode } from "react";
import { TrendingUp, Package, Download, Upload } from "lucide-react";
import { fetchDashboardSummary, fetchTotalInvoices } from "../../api/dashboard";
import { Card } from "../ui/card";

interface KPICardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  delta?: string;
}

function KPICard({ label, value, icon, delta }: KPICardProps) {
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 mb-2">{label}</p>
          <p className="text-3xl text-gray-900">{value}</p>
          {delta && (
            <p className="text-sm text-green-600 mt-2">{delta}</p>
          )}
        </div>
        <div className="text-gray-400">{icon}</div>
      </div>
    </Card>
  );
}

export function DashboardContent() {
  const [totalInvoices, setTotalInvoices] = useState<number | null>(null);
  const [totalPieces] = useState<number | null>(null);
  const [todaysDrop, setTodaysDrop] = useState<string | null>(null);
  const [todaysPickup, setTodaysPickup] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadMetrics = async () => {
      try {
        const [summary, invoicesCount] = await Promise.all([
          fetchDashboardSummary(),
          fetchTotalInvoices(),
        ]);

        if (!isMounted) return;

        setTotalInvoices(invoicesCount);
        setTodaysDrop(summary.orders_value_today ?? null);
        setTodaysPickup(summary.collected_today ?? null);
      } catch (err) {
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
          delta="+12% from yesterday"
        />
        
        <KPICard
          label="Today's Pickup"
          value={formatCurrency(todaysPickup)}
          icon={<Upload className="w-8 h-8" />}
          delta="+8% from yesterday"
        />
      </div>
    </div>
  );
}
