import { useState } from "react";
import { createCustomer, searchCustomers } from "../api/customers";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Checkbox } from "./ui/checkbox";
import { toast } from "./ui/use-toast";

export function DropPage() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [usePhoneNumber, setUsePhoneNumber] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  const normalizedPhone = usePhoneNumber ? phoneNumber.replace(/\D/g, "") : "";
  const fullName = `${firstName.trim()} ${lastName.trim()}`.trim();

  const buildQuery = () => {
    const parts = [];
    if (normalizedPhone) parts.push(normalizedPhone);
    if (firstName.trim()) parts.push(firstName.trim());
    if (lastName.trim()) parts.push(lastName.trim());
    return parts.join(" ").trim();
  };

  const handleFind = async () => {
    const query = buildQuery();
    if (!query) {
      toast({
        title: "Enter phone or name to search.",
        variant: "error",
      });
      return;
    }

    setIsSearching(true);
    try {
      const results = await searchCustomers(query);
      if (!results.length) {
        toast({
          title: "No matches found.",
          description: "Use REGISTER to add a new customer.",
        });
      } else if (results.length === 1) {
        toast({
          title: "Customer found.",
          description: results[0].name,
        });
      } else {
        toast({
          title: "Multiple matches found.",
          description: `${results.length} customers returned.`,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Search failed.";
      toast({
        title: "Search failed.",
        description: message,
        variant: "error",
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleRegister = async () => {
    if (!fullName) {
      toast({
        title: "Name required.",
        description: "Enter first and last name to register.",
        variant: "error",
      });
      return;
    }

    setIsRegistering(true);
    try {
      const customer = await createCustomer({
        name: fullName,
        phone: normalizedPhone || null,
      });
      toast({
        title: "Customer created.",
        description: customer.name,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed.";
      toast({
        title: "Registration failed.",
        description: message,
        variant: "error",
      });
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-12">
      <h1 className="text-3xl mb-8 text-gray-800">DROP</h1>
      
      <div className="bg-white rounded-lg shadow-md p-8 space-y-6">
        {/* Phone Number */}
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
            type="tel"
            placeholder="Enter phone number"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            className="w-full"
            disabled={!usePhoneNumber}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleFind();
              }
            }}
          />
        </div>

        {/* First Name */}
        <div className="space-y-2">
          <Label htmlFor="first-name" className="text-gray-700">
            First Name
          </Label>
          <Input
            id="first-name"
            type="text"
            placeholder="Enter first name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="w-full"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleFind();
              }
            }}
          />
        </div>

        {/* Last Name */}
        <div className="space-y-2">
          <Label htmlFor="last-name" className="text-gray-700">
            Last Name
          </Label>
          <Input
            id="last-name"
            type="text"
            placeholder="Enter last name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="w-full"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleFind();
              }
            }}
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-4 pt-4">
          <Button
            onClick={handleFind}
            variant="outline"
            className="flex-1"
            size="lg"
            disabled={isSearching || isRegistering}
          >
            FIND
          </Button>
          <Button
            onClick={handleRegister}
            className="flex-1"
            size="lg"
            disabled={isSearching || isRegistering}
          >
            REGISTER
          </Button>
        </div>
      </div>
    </div>
  );
}
