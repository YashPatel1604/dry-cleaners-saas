import { useEffect, useState } from "react";
import { searchCustomers } from "../../api/customers";
import { toast } from "../ui/use-toast";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { DropResultsCard } from "./DropResultsCard";
import { DropCustomerRow } from "./DropCustomerRow";
import { DropEmptyState } from "./DropEmptyState";

interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
}

interface DropPageProps {
  onRegister?: (prefill: { phone?: string; firstName?: string; lastName?: string }) => void;
  onStartDropOff?: (customer: Customer) => void;
  initialCustomer?: Customer | null;
}

type SearchState = 'empty' | 'searching' | 'no-results' | 'single-result' | 'multiple-results';

export function DropPage({ onRegister, onStartDropOff, initialCustomer }: DropPageProps) {
  const [phoneNo, setPhoneNo] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [searchState, setSearchState] = useState<SearchState>('empty');
  const [searchResults, setSearchResults] = useState<Customer[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const formatPhoneDisplay = (digits: string) => {
    if (!digits) return "";
    const clean = digits.replace(/\D/g, "");
    const trimmed = clean.length > 10 ? clean.slice(-10) : clean;
    if (trimmed.length <= 3) return trimmed;
    if (trimmed.length <= 6) {
      return `(${trimmed.slice(0, 3)}) ${trimmed.slice(3)}`;
    }
    return `(${trimmed.slice(0, 3)}) ${trimmed.slice(3, 6)}-${trimmed.slice(6, 10)}`;
  };

  useEffect(() => {
    if (!initialCustomer) return;
    setSearchResults([initialCustomer]);
    setSearchState("single-result");
  }, [initialCustomer]);

  const handleFind = async () => {
    const hasInput = phoneNo.trim() || firstName.trim() || lastName.trim();
    if (!hasInput) {
      setSearchState("empty");
      setSearchResults([]);
      return;
    }

    const query = [phoneNo.trim(), firstName.trim(), lastName.trim()]
      .filter(Boolean)
      .join(" ")
      .trim();

    setIsSearching(true);
    setSearchState("searching");
    try {
      const results = await searchCustomers(query);
      const mapped = results.map((customer) => {
        const rawPhone = customer.phone ?? "";
        const digits = rawPhone.replace(/\D/g, "");
        return {
          id: String(customer.id),
          name: customer.name,
          phone: formatPhoneDisplay(digits) || rawPhone,
          email: customer.email ?? undefined,
        };
      });

      setSearchResults(mapped);
      if (!mapped.length) {
        setSearchState("no-results");
      } else if (mapped.length === 1) {
        setSearchState("single-result");
      } else {
        setSearchState("multiple-results");
      }
    } catch (err) {
      setSearchResults([]);
      setSearchState("no-results");
      toast({
        title: "Search failed.",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleRegister = () => {
    if (onRegister) {
      onRegister({
        phone: phoneNo,
        firstName,
        lastName,
      });
    }
  };

  const handleSelectCustomer = (customer: Customer) => {
    if (onStartDropOff) {
      onStartDropOff(customer);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl mb-8 text-gray-800">Drop</h1>

      <Card className="p-6 mb-6">
        <div className="space-y-4">
          <div>
            <Label htmlFor="phone">Phone No.</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="Enter phone number"
              value={formatPhoneDisplay(phoneNo)}
              onChange={(e) => setPhoneNo(e.target.value.replace(/\D/g, ""))}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleFind();
                }
              }}
            />
          </div>

          <div>
            <Label htmlFor="firstName">First Name</Label>
            <Input
              id="firstName"
              type="text"
              placeholder="Enter first name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleFind();
                }
              }}
            />
          </div>

          <div>
            <Label htmlFor="lastName">Last Name</Label>
            <Input
              id="lastName"
              type="text"
              placeholder="Enter last name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleFind();
                }
              }}
            />
          </div>

          <div className="flex gap-3 pt-2">
            <Button onClick={handleFind} className="flex-1" disabled={isSearching}>
              FIND
            </Button>
            <Button onClick={handleRegister} variant="outline" className="flex-1">
              REGISTER
            </Button>
          </div>
        </div>
      </Card>

      {/* Results Section */}
      {searchState === 'empty' && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">Enter phone or name to search.</p>
        </div>
      )}

      {searchState === 'no-results' && (
        <DropEmptyState onRegister={handleRegister} />
      )}

      {searchState === 'single-result' && searchResults[0] && (
        <DropResultsCard
          customer={searchResults[0]}
          onStartDropOff={handleSelectCustomer}
        />
      )}

      {searchState === 'multiple-results' && (
        <div className="space-y-3">
          {searchResults.map((customer) => (
            <DropCustomerRow
              key={customer.id}
              customer={customer}
              onSelect={handleSelectCustomer}
            />
          ))}
        </div>
      )}
    </div>
  );
}
