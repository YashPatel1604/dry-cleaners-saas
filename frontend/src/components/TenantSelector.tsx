import { useEffect, useState } from "react";
import { Store } from "lucide-react";
import { fetchTenants } from "../api/auth";
import type { TenantSummary } from "../api/auth";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { toast } from "./ui/use-toast";

interface TenantSelectorProps {
  onSelectStore: (storeId: string) => void;
  tenants?: TenantSummary[];
}

export function TenantSelector({ onSelectStore, tenants }: TenantSelectorProps) {
  const [stores, setStores] = useState<TenantSummary[]>(tenants ?? []);

  useEffect(() => {
    let isMounted = true;
    if (tenants && tenants.length) {
      setStores(tenants);
      return undefined;
    }

    fetchTenants()
      .then((data) => {
        if (!isMounted) return;
        setStores(data);
      })
      .catch((err) => {
        if (!isMounted) return;
        const message = err instanceof Error ? err.message : "Unable to load stores.";
        toast({
          title: "Unable to load stores.",
          description: message,
          variant: "error",
        });
      });

    return () => {
      isMounted = false;
    };
  }, [tenants]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-gray-100 p-8">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl text-gray-800 mb-2">Select Your Store</h1>
          <p className="text-gray-600">Choose which store you want to manage</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {stores.map((store) => (
            <Card
              key={store.tenant_id}
              className="p-6 hover:shadow-xl transition-all cursor-pointer group"
              onClick={() => onSelectStore(store.tenant_slug)}
            >
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="bg-blue-100 p-4 rounded-full group-hover:bg-blue-200 transition-colors">
                  <Store className="w-8 h-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl text-gray-800 mb-2">{store.tenant_name}</h3>
                  <p className="text-sm text-gray-600">{store.tenant_slug}</p>
                </div>
                <Button className="w-full mt-2" variant="outline">
                  Select Store
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
