import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { FileText, Package, Users, Wallet } from "lucide-react";

interface ExtrasPageProps {
  onOpenInventory: () => void;
  onOpenCustomers: () => void;
  onOpenDailyEarnings: () => void;
  onOpenReports: () => void;
}

export function ExtrasPage({
  onOpenInventory,
  onOpenCustomers,
  onOpenDailyEarnings,
  onOpenReports,
}: ExtrasPageProps) {
  return (
    <div className="max-w-5xl">
      <h1 className="text-3xl mb-8 text-gray-800">Extras</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="p-6 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="bg-gray-100 w-12 h-12 rounded-full flex items-center justify-center">
              <Package className="w-6 h-6 text-gray-600" />
            </div>
            <div>
              <h3 className="text-lg text-gray-900">Inventory</h3>
              <p className="text-sm text-gray-600">
                Manage items, pricing, and availability.
              </p>
            </div>
          </div>
          <Button className="mt-6" onClick={onOpenInventory}>
            Open Inventory
          </Button>
        </Card>

        <Card className="p-6 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="bg-gray-100 w-12 h-12 rounded-full flex items-center justify-center">
              <Users className="w-6 h-6 text-gray-600" />
            </div>
            <div>
              <h3 className="text-lg text-gray-900">Customers</h3>
              <p className="text-sm text-gray-600">
                Browse and access all customers.
              </p>
            </div>
          </div>
          <Button className="mt-6" onClick={onOpenCustomers}>
            Open Customers
          </Button>
        </Card>

        <Card className="p-6 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="bg-gray-100 w-12 h-12 rounded-full flex items-center justify-center">
              <Wallet className="w-6 h-6 text-gray-600" />
            </div>
            <div>
              <h3 className="text-lg text-gray-900">Daily Earnings</h3>
              <p className="text-sm text-gray-600">
                View totals by payment method for a day.
              </p>
            </div>
          </div>
          <Button className="mt-6" onClick={onOpenDailyEarnings}>
            View Earnings
          </Button>
        </Card>

        <Card className="p-6 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="bg-gray-100 w-12 h-12 rounded-full flex items-center justify-center">
              <FileText className="w-6 h-6 text-gray-600" />
            </div>
            <div>
              <h3 className="text-lg text-gray-900">Reports</h3>
              <p className="text-sm text-gray-600">
                Daily operational summaries and exports.
              </p>
            </div>
          </div>
          <Button className="mt-6" onClick={onOpenReports}>
            Open Reports
          </Button>
        </Card>
      </div>
    </div>
  );
}
