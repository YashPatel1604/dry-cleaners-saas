import { Card } from "../ui/card";
import { Input } from "../ui/input";

interface DailyEarningsRow {
  method: string;
  count: number;
  in_cents: number;
  out_cents: number;
  net_cents: number;
}

interface DailyEarningsSummary {
  date: string;
  totals: {
    count: number;
    in_cents: number;
    out_cents: number;
    net_cents: number;
  };
  by_method: DailyEarningsRow[];
}

interface DailyEarningsPageProps {
  date: string;
  summary: DailyEarningsSummary | null;
  loading?: boolean;
  error?: string | null;
  onDateChange: (value: string) => void;
}

const PAYMENT_METHODS = ["CASH", "CARD", "ONLINE", "OTHER"] as const;

export function DailyEarningsPage({
  date,
  summary,
  loading = false,
  error = null,
  onDateChange,
}: DailyEarningsPageProps) {
  const formatCurrency = (cents: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(cents / 100);

  const byMethod = PAYMENT_METHODS.map((method) => {
    const row = summary?.by_method.find((item) => item.method === method);
    return (
      row ?? {
        method,
        count: 0,
        in_cents: 0,
        out_cents: 0,
        net_cents: 0,
      }
    );
  });

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl mb-6 text-gray-800">Daily Earnings</h1>

      <Card className="p-4 mb-6">
        <div className="flex flex-col gap-2">
          <label className="text-sm text-gray-600" htmlFor="earnings-date">
            Date
          </label>
          <Input
            id="earnings-date"
            type="date"
            value={date}
            onChange={(event) => onDateChange(event.target.value)}
            className="max-w-xs"
          />
        </div>
      </Card>

      {loading && (
        <div className="py-10 text-center text-gray-600">
          Loading daily earnings...
        </div>
      )}

      {error && !loading && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {!loading && !error && summary && (
        <div className="space-y-4">
          <Card className="p-6">
            <h2 className="text-lg text-gray-800 mb-4">Totals</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">Collected</p>
                <p className="text-2xl text-gray-900">
                  {formatCurrency(summary.totals.in_cents)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Refunded</p>
                <p className="text-2xl text-gray-900">
                  {formatCurrency(summary.totals.out_cents)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Net</p>
                <p className="text-2xl text-gray-900">
                  {formatCurrency(summary.totals.net_cents)}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg text-gray-800 mb-4">By Payment Method</h2>
            <div className="space-y-3">
              {byMethod.map((row) => (
                <div
                  key={row.method}
                  className="flex flex-col gap-2 rounded-lg border border-gray-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="text-sm text-gray-600">Method</p>
                    <p className="text-gray-900">{row.method}</p>
                  </div>
                  <div className="flex flex-wrap gap-6 text-sm text-gray-700">
                    <span>In: {formatCurrency(row.in_cents)}</span>
                    <span>Out: {formatCurrency(row.out_cents)}</span>
                    <span className="font-semibold">
                      Net: {formatCurrency(row.net_cents)}
                    </span>
                    <span>Count: {row.count}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
