import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { formatDateTime } from "../lib/format";

type Customer = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
};

export default function Customers(): JSX.Element {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");

  const loadCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (query.trim().length >= 2) {
        const resp = await apiJson<Customer[]>(
          `/api/tenant/customers/search/?q=${encodeURIComponent(query.trim())}`
        );
        setCustomers(resp);
      } else {
        const resp = await apiJson<Customer[]>("/api/tenant/customers/");
        setCustomers(resp);
      }
    } catch {
      setError("Unable to load customers");
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  const createCustomer = async () => {
    setError(null);
    try {
      const resp = await apiJson<Customer>("/api/tenant/customers/", {
        method: "POST",
        body: { name, phone, email, notes },
      });
      setName("");
      setPhone("");
      setEmail("");
      setNotes("");
      navigate(`/customers/${resp.id}`);
    } catch {
      setError("Failed to create customer");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Customers
        </div>
        <h1 className="text-3xl font-semibold">Customer directory</h1>
        <p className="text-sm text-muted-foreground">
          {loading ? "Loading..." : `${customers.length} results`}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Search customers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Search by name, phone, or email"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {error && <div className="text-sm text-red-600">{error}</div>}
            <div className="space-y-3">
              {customers.map((customer) => (
                <button
                  key={customer.id}
                  className="w-full rounded-xl border border-border bg-white/70 px-4 py-3 text-left transition hover:bg-white"
                  onClick={() => navigate(`/customers/${customer.id}`)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{customer.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {customer.email || customer.phone || "No contact"}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {customer.created_at ? formatDateTime(customer.created_at) : ""}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Create customer</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />
            <Input placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <Input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Textarea
              placeholder="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <Button onClick={createCustomer} disabled={!name.trim()}>
              Create customer
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
