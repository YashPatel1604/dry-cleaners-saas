import { useEffect, useState } from "react";
import { FileText, Package, TrendingDown, TrendingUp } from "lucide-react";
import { fetchDashboardSummary, fetchTotalInvoices } from "../api/dashboard";
import { Card } from "./ui/card";

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
    <div className="max-w-6xl">
      <h1 className="text-3xl mb-8 text-gray-800">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Total Invoices */}
        <Card className="p-6 hover:shadow-lg transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-2">Total Invoices</p>
              <p className="text-4xl text-gray-900">{formatCount(totalInvoices)}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-lg">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </Card>

        {/* Total Pieces */}
        <Card className="p-6 hover:shadow-lg transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-2">Total Pieces</p>
              <p className="text-4xl text-gray-900">{formatCount(totalPieces)}</p>
            </div>
            <div className="bg-purple-100 p-3 rounded-lg">
              <Package className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </Card>

        {/* Today's Drop */}
        <Card className="p-6 hover:shadow-lg transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-2">Today's Drop</p>
              <p className="text-4xl text-gray-900">{formatCurrency(todaysDrop)}</p>
              <p className="text-green-600 text-sm mt-2 flex items-center gap-1">
                <TrendingUp className="w-4 h-4" />
                +12% from yesterday
              </p>
            </div>
            <div className="bg-green-100 p-3 rounded-lg">
              <TrendingDown className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </Card>

        {/* Today's Pickup */}
        <Card className="p-6 hover:shadow-lg transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-2">Today's Pickup</p>
              <p className="text-4xl text-gray-900">{formatCurrency(todaysPickup)}</p>
              <p className="text-green-600 text-sm mt-2 flex items-center gap-1">
                <TrendingUp className="w-4 h-6" />
                +8% from yesterday
              </p>
            </div>
            <div className="bg-orange-100 p-3 rounded-lg">
              <TrendingUp className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
