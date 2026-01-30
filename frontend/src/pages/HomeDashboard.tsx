import React, { useEffect, useMemo, useState } from "react";
import { FileText, Package, TrendingDown, TrendingUp } from "lucide-react";

import { fetchDashboardMetrics, type DashboardMetrics } from "../api/metrics";
import { Card } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { cn } from "../lib/utils";

type MetricCardProps = {
  label: string;
  value: number | null;
  loading: boolean;
  format: "count" | "currency";
  icon: React.ElementType;
  iconWrapperClassName: string;
  iconClassName: string;
  change?: string;
};

function MetricCard({
  label,
  value,
  loading,
  format,
  icon: Icon,
  iconWrapperClassName,
  iconClassName,
  change,
}: MetricCardProps) {
  const displayValue = useMemo(() => {
    if (value === null) return "--";
    if (format === "currency") {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(value);
    }
    return value.toLocaleString("en-US");
  }, [value, format]);

  return (
    <Card className="border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-lg">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-600">{label}</p>
          <p className="mt-2 text-4xl text-gray-900">
            {loading ? <Skeleton className="h-10 w-32" /> : displayValue}
          </p>
          {change && (
            <p className="mt-2 flex items-center gap-1 text-sm text-green-600">
              <TrendingUp className="h-4 w-4" />
              {change}
            </p>
          )}
        </div>
        <div className={cn("rounded-lg p-3", iconWrapperClassName)}>
          <Icon className={cn("h-6 w-6", iconClassName)} />
        </div>
      </div>
    </Card>
  );
}

export default function HomeDashboard(): JSX.Element {
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalInvoices: null,
    totalPieces: null,
    todaysDrop: null,
    todaysPickup: null,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchDashboardMetrics()
      .then((data) => {
        if (!active) return;
        setMetrics(data);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="max-w-6xl">
      <h1 className="mb-8 text-3xl text-gray-800">Dashboard</h1>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <MetricCard
          label="Total Invoices"
          value={metrics.totalInvoices}
          loading={loading}
          format="count"
          icon={FileText}
          iconWrapperClassName="bg-blue-100"
          iconClassName="text-blue-600"
        />
        <MetricCard
          label="Total Pieces"
          value={metrics.totalPieces}
          loading={loading}
          format="count"
          icon={Package}
          iconWrapperClassName="bg-purple-100"
          iconClassName="text-purple-600"
        />
        <MetricCard
          label="Today's Drop"
          value={metrics.todaysDrop}
          loading={loading}
          format="currency"
          icon={TrendingDown}
          iconWrapperClassName="bg-green-100"
          iconClassName="text-green-600"
          change="+12% from yesterday"
        />
        <MetricCard
          label="Today's Pickup"
          value={metrics.todaysPickup}
          loading={loading}
          format="currency"
          icon={TrendingUp}
          iconWrapperClassName="bg-orange-100"
          iconClassName="text-orange-600"
          change="+8% from yesterday"
        />
      </div>
    </div>
  );
}
