import React, { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { createCustomer } from "../api/customers";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { toast } from "../components/ui/use-toast";
import { formatPhoneDisplay, normalizePhoneInput } from "../lib/phone";
import { cn } from "../lib/utils";

type LocationState = {
  phone?: string;
  firstName?: string;
  lastName?: string;
};

type FieldErrors = {
  phone?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  form?: string;
};

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export default function RegisterCustomer(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const phoneRef = useRef<HTMLInputElement>(null);

  const [phoneDigits, setPhoneDigits] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [preferences, setPreferences] = useState("");
  const [popupMessage, setPopupMessage] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    phoneRef.current?.focus();
  }, []);

  useEffect(() => {
    const state = location.state as LocationState | null;
    if (!state) return;
    if (state.phone) setPhoneDigits(state.phone);
    if (state.firstName) setFirstName(state.firstName);
    if (state.lastName) setLastName(state.lastName);
  }, [location.state]);

  const validate = () => {
    const nextErrors: FieldErrors = {};
    if (!phoneDigits.trim()) {
      nextErrors.phone = "Phone is required.";
    }
    if (!firstName.trim()) {
      nextErrors.firstName = "First name is required.";
    }
    if (!lastName.trim()) {
      nextErrors.lastName = "Last name is required.";
    }
    if (email.trim() && !isValidEmail(email.trim())) {
      nextErrors.email = "Enter a valid email.";
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSave = async () => {
    if (saving) return;
    if (!validate()) return;
    setSaving(true);
    setErrors({});
    try {
      const customer = await createCustomer({
        phone: phoneDigits.trim(),
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        email: email.trim(),
        address,
        preferences,
        popupMessage,
      });
      toast({ title: "Customer created" });
      navigate("/drop", { state: { selectedCustomer: customer } });
    } catch {
      setErrors({ form: "Unable to save customer. Please try again." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.32em] text-muted-foreground/70">
          Customer
        </div>
        <h1 className="text-3xl font-semibold">REGISTER</h1>
        <p className="text-sm text-muted-foreground">
          Create a new customer in seconds.
        </p>
      </div>

      <Card className="glass-panel border-border/70">
        <CardContent className="p-6">
          <form
            className="space-y-6"
            onSubmit={(event) => {
              event.preventDefault();
              handleSave();
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                navigate("/drop");
              }
            }}
          >
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="register-phone">Phone</Label>
                <Input
                  id="register-phone"
                  ref={phoneRef}
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="(555) 123-4567"
                  className={cn(
                    "h-12 text-base",
                    errors.phone ? "border-red-400" : ""
                  )}
                  value={formatPhoneDisplay(phoneDigits)}
                  onChange={(event) => setPhoneDigits(normalizePhoneInput(event.target.value))}
                  aria-invalid={Boolean(errors.phone)}
                  aria-describedby={errors.phone ? "register-phone-error" : undefined}
                />
                {errors.phone && (
                  <div id="register-phone-error" className="text-sm text-red-600">
                    {errors.phone}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="register-first">First Name</Label>
                <Input
                  id="register-first"
                  autoComplete="given-name"
                  placeholder="First name"
                  className={cn("h-12 text-base", errors.firstName ? "border-red-400" : "")}
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  aria-invalid={Boolean(errors.firstName)}
                  aria-describedby={errors.firstName ? "register-first-error" : undefined}
                />
                {errors.firstName && (
                  <div id="register-first-error" className="text-sm text-red-600">
                    {errors.firstName}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="register-last">Last Name</Label>
                <Input
                  id="register-last"
                  autoComplete="family-name"
                  placeholder="Last name"
                  className={cn("h-12 text-base", errors.lastName ? "border-red-400" : "")}
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  aria-invalid={Boolean(errors.lastName)}
                  aria-describedby={errors.lastName ? "register-last-error" : undefined}
                />
                {errors.lastName && (
                  <div id="register-last-error" className="text-sm text-red-600">
                    {errors.lastName}
                  </div>
                )}
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="register-email">Email</Label>
                <Input
                  id="register-email"
                  type="email"
                  autoComplete="email"
                  placeholder="name@email.com"
                  className={cn("h-12 text-base", errors.email ? "border-red-400" : "")}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? "register-email-error" : undefined}
                />
                {errors.email && (
                  <div id="register-email-error" className="text-sm text-red-600">
                    {errors.email}
                  </div>
                )}
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="register-address">Address</Label>
                <Textarea
                  id="register-address"
                  placeholder="Street, city, state"
                  className="text-base"
                  value={address}
                  onChange={(event) => setAddress(event.target.value)}
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="register-preferences">Preferences</Label>
                <Textarea
                  id="register-preferences"
                  placeholder="Starch level, folding instructions, etc."
                  className="text-base"
                  value={preferences}
                  onChange={(event) => setPreferences(event.target.value)}
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="register-popup">Pop-up Message</Label>
                <Textarea
                  id="register-popup"
                  placeholder="Visible staff note when the customer checks in."
                  className="text-base"
                  value={popupMessage}
                  onChange={(event) => setPopupMessage(event.target.value)}
                />
              </div>
            </div>

            {errors.form && (
              <div role="alert" className="text-sm text-red-600">
                {errors.form}
              </div>
            )}

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={saving}>
                {saving ? "Saving..." : "SAVE"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="lg"
                className="w-full sm:w-auto"
                onClick={() => navigate("/drop")}
                disabled={saving}
              >
                CANCEL
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
