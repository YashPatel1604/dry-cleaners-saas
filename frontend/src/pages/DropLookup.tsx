import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { searchCustomers, type Customer } from "../api/customers";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Checkbox } from "../components/ui/checkbox";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Skeleton } from "../components/ui/skeleton";
import { formatPhoneDisplay, normalizePhoneInput } from "../lib/phone";
import { cn } from "../lib/utils";

type LocationState = {
  selectedCustomer?: Customer;
};

export default function DropLookup(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const phoneRef = useRef<HTMLInputElement>(null);

  const [phoneDigits, setPhoneDigits] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [usePhoneNumber, setUsePhoneNumber] = useState(true);

  useEffect(() => {
    if (usePhoneNumber) {
      phoneRef.current?.focus();
    }
  }, [usePhoneNumber]);

  useEffect(() => {
    const state = location.state as LocationState | null;
    if (state?.selectedCustomer) {
      setResults([state.selectedCustomer]);
      setSelectedCustomer(state.selectedCustomer);
      setHasSearched(true);
      setFormError(null);
      if (state.selectedCustomer.phone) {
        setPhoneDigits(normalizePhoneInput(state.selectedCustomer.phone));
      }
      if (state.selectedCustomer.name) {
        const [first, ...rest] = state.selectedCustomer.name.split(" ");
        setFirstName(first || "");
        setLastName(rest.join(" "));
      }
    }
  }, [location.state]);

  const queryIsEmpty = useMemo(() => {
    const phoneValue = usePhoneNumber ? phoneDigits.trim() : "";
    return !phoneValue && !firstName.trim() && !lastName.trim();
  }, [phoneDigits, firstName, lastName, usePhoneNumber]);

  const handleFind = async () => {
    if (queryIsEmpty) {
      setFormError("Enter phone or name to search.");
      setResults([]);
      setSelectedCustomer(null);
      setHasSearched(false);
      return;
    }
    setFormError(null);
    setLoading(true);
    setHasSearched(true);
    try {
      const matches = await searchCustomers({
        phone: usePhoneNumber ? phoneDigits.trim() : "",
        firstName: firstName.trim(),
        lastName: lastName.trim(),
      });
      setResults(matches);
      setSelectedCustomer(matches.length === 1 ? matches[0] : null);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = () => {
    navigate("/register", {
      state: {
        phone: usePhoneNumber ? phoneDigits.trim() : "",
        firstName: firstName.trim(),
        lastName: lastName.trim(),
      },
    });
  };

  const showEmptyState = hasSearched && !loading && results.length === 0;

  return (
    <div className="max-w-2xl mx-auto mt-12">
      <h1 className="mb-8 text-3xl text-gray-800">DROP</h1>

      <div className="rounded-lg bg-white p-8 shadow-md space-y-6">
        <form
          className="space-y-6"
          onSubmit={(event) => {
            event.preventDefault();
            handleFind();
          }}
        >
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <Checkbox
                id="use-phone"
                checked={usePhoneNumber}
                onCheckedChange={(checked) => setUsePhoneNumber(checked === true)}
              />
              <Label htmlFor="use-phone" className="text-gray-700">
                Ph. No.
              </Label>
            </div>
            <Input
              id="drop-phone"
              ref={phoneRef}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="Enter phone number"
              className={cn("w-full", formError ? "border-red-400" : "")}
              value={formatPhoneDisplay(phoneDigits)}
              onChange={(event) => setPhoneDigits(normalizePhoneInput(event.target.value))}
              disabled={!usePhoneNumber}
              aria-invalid={Boolean(formError)}
              aria-describedby={formError ? "drop-error" : undefined}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="drop-first" className="text-gray-700">
              First Name
            </Label>
            <Input
              id="drop-first"
              type="text"
              placeholder="Enter first name"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="drop-last" className="text-gray-700">
              Last Name
            </Label>
            <Input
              id="drop-last"
              type="text"
              placeholder="Enter last name"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
              className="w-full"
            />
          </div>

          {formError && (
            <div id="drop-error" role="alert" className="text-sm text-red-600">
              {formError}
            </div>
          )}

          <div className="flex gap-4 pt-4">
            <Button onClick={handleFind} variant="outline" className="flex-1" size="lg">
              FIND
            </Button>
            <Button onClick={handleRegister} className="flex-1" size="lg">
              REGISTER
            </Button>
          </div>
        </form>
      </div>

      <div className="space-y-4">
        {loading && (
          <div className="grid gap-3 md:grid-cols-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        )}

        {!loading && results.length > 1 && (
          <div className="space-y-3">
            <div className="text-sm text-muted-foreground">
              Multiple matches found. Select a customer.
            </div>
            {results.map((customer) => (
              <button
                key={customer.id}
                type="button"
                className={cn(
                  "w-full rounded-xl border px-4 py-4 text-left transition",
                  "hover:bg-muted/60",
                  selectedCustomer?.id === customer.id
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card"
                )}
                onClick={() => setSelectedCustomer(customer)}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-lg font-semibold">{customer.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {customer.phone || "No phone"}
                      {customer.email ? ` | ${customer.email}` : ""}
                    </div>
                  </div>
                  <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Select
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {!loading && selectedCustomer && (
          <Card className="glass-panel border-border/70">
            <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-sm uppercase tracking-[0.26em] text-muted-foreground">
                  Customer Found
                </div>
                <div className="text-2xl font-semibold">{selectedCustomer.name}</div>
                <div className="text-sm text-muted-foreground">
                  {selectedCustomer.phone || "No phone on file"}
                  {selectedCustomer.email ? ` | ${selectedCustomer.email}` : ""}
                </div>
              </div>
              <Button size="lg" className="w-full sm:w-auto" onClick={() => navigate("/orders")}>
                Start Drop-Off
              </Button>
            </CardContent>
          </Card>
        )}

        {showEmptyState && (
          <Card className="glass-panel border-border/70">
            <CardContent className="space-y-4 p-6 text-center">
              <div className="text-lg font-semibold">No customer found</div>
              <div className="text-sm text-muted-foreground">
                We couldn't find a match. Register a new customer to continue.
              </div>
              <Button size="lg" className="w-full sm:w-auto" onClick={handleRegister}>
                Register new customer
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
