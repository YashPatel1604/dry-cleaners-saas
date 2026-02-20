import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Card } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Checkbox } from "../ui/checkbox";

type LocationLookupResult = {
  exists: boolean;
  rack_number: string | null;
};

type LocationAssignResult = {
  order_id: number;
  order_sku: string;
  location_barcode: string | null;
  rack_number: string | null;
};

type ScanStep = "location" | "rack" | "order";

const LOCATION_BARCODE_RE = /^LOC-[A-Z0-9][A-Z0-9-]{0,30}$/;
const ORDER_BARCODE_RE = /^ORD-\d{8}$/;

interface StorageLocationScanStationProps {
  onLookupLocation: (barcode: string) => Promise<LocationLookupResult>;
  onAssignLocation: (payload: {
    locationBarcode: string;
    orderBarcode: string;
    rackNumber?: string;
  }) => Promise<LocationAssignResult>;
  onAssigned?: (result: LocationAssignResult) => void;
  scanSeed?: { token: number; barcode: string } | null;
}

export function StorageLocationScanStation({
  onLookupLocation,
  onAssignLocation,
  onAssigned,
  scanSeed = null,
}: StorageLocationScanStationProps) {
  const [step, setStep] = useState<ScanStep>("location");
  const [locationBarcode, setLocationBarcode] = useState("");
  const [rackNumber, setRackNumber] = useState("");
  const [orderBarcode, setOrderBarcode] = useState("");
  const [keepLocation, setKeepLocation] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const locationInputRef = useRef<HTMLInputElement | null>(null);
  const rackInputRef = useRef<HTMLInputElement | null>(null);
  const orderInputRef = useRef<HTMLInputElement | null>(null);

  const normalizedLocationBarcode = useMemo(
    () => locationBarcode.trim().toUpperCase(),
    [locationBarcode]
  );
  const normalizedOrderBarcode = useMemo(
    () => orderBarcode.trim().toUpperCase(),
    [orderBarcode]
  );
  const locationValid = useMemo(
    () => LOCATION_BARCODE_RE.test(normalizedLocationBarcode),
    [normalizedLocationBarcode]
  );
  const orderValid = useMemo(
    () => ORDER_BARCODE_RE.test(normalizedOrderBarcode),
    [normalizedOrderBarcode]
  );

  const focusActiveInput = () => {
    if (step === "location") {
      locationInputRef.current?.focus();
      locationInputRef.current?.select();
      return;
    }
    if (step === "rack") {
      rackInputRef.current?.focus();
      rackInputRef.current?.select();
      return;
    }
    orderInputRef.current?.focus();
    orderInputRef.current?.select();
  };

  useEffect(() => {
    const timer = window.setTimeout(focusActiveInput, 0);
    return () => window.clearTimeout(timer);
  }, [step]);

  const resetToLocationStep = () => {
    setStep("location");
    setLocationBarcode("");
    setRackNumber("");
    setOrderBarcode("");
    setError(null);
  };

  const lookupLocationAndAdvance = async (barcode: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await onLookupLocation(barcode);
      if (result.exists) {
        setRackNumber(result.rack_number ?? "");
        setStep("order");
      } else {
        setRackNumber("");
        setStep("rack");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to check location.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLookupLocation = async () => {
    if (!locationValid || submitting) return;
    await lookupLocationAndAdvance(normalizedLocationBarcode);
  };

  const handleAssign = async () => {
    if (!orderValid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await onAssignLocation({
        locationBarcode: normalizedLocationBarcode,
        orderBarcode: normalizedOrderBarcode,
        rackNumber: rackNumber.trim() || undefined,
      });
      onAssigned?.(result);
      if (keepLocation) {
        setOrderBarcode("");
        setStep("order");
      } else {
        resetToLocationStep();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to assign location.");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (!scanSeed) return;
    const barcode = scanSeed.barcode.trim().toUpperCase();
    setError(null);

    if (LOCATION_BARCODE_RE.test(barcode)) {
      setLocationBarcode(barcode);
      setOrderBarcode("");
      setStep("location");
      void lookupLocationAndAdvance(barcode);
      return;
    }

    if (ORDER_BARCODE_RE.test(barcode)) {
      setOrderBarcode(barcode);
      setStep("location");
      setError("Order barcode scanned first. Scan location barcode first.");
    }
  }, [scanSeed?.token]);

  return (
    <Card className="gap-4 p-4">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-gray-900">Scan Station</h2>
        <p className="text-sm text-gray-600">
          Continuous scanner mode: scan location first, then scan order barcode.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className={step === "location" ? "md:col-span-3" : "md:col-span-1"}>
          <Label htmlFor="station-location-barcode">Location barcode</Label>
          <Input
            id="station-location-barcode"
            ref={locationInputRef}
            value={locationBarcode}
            onChange={(event) => setLocationBarcode(event.target.value.toUpperCase())}
            placeholder="LOC-..."
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleLookupLocation();
              }
            }}
          />
          <p className="mt-1 text-xs text-gray-500">Format: LOC-<code>...</code></p>
        </div>

        {step === "rack" && (
          <div className="md:col-span-2">
            <Label htmlFor="station-rack-number">Rack number (optional)</Label>
            <Input
              id="station-rack-number"
              ref={rackInputRef}
              value={rackNumber}
              inputMode="numeric"
              onChange={(event) => setRackNumber(event.target.value)}
              placeholder="Rack number"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  setStep("order");
                }
              }}
            />
          </div>
        )}

        {(step === "order" || step === "rack") && (
          <div className="md:col-span-3">
            <Label htmlFor="station-order-barcode">Order barcode</Label>
            <Input
              id="station-order-barcode"
              ref={orderInputRef}
              value={orderBarcode}
              onChange={(event) => setOrderBarcode(event.target.value.toUpperCase())}
              placeholder="ORD-########"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleAssign();
                }
              }}
            />
            <p className="mt-1 text-xs text-gray-500">
              Format: ORD-######## (example ORD-00000028)
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <Checkbox
            checked={keepLocation}
            onCheckedChange={setKeepLocation}
            disabled={submitting}
          />
          Keep same location after each assignment
        </label>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={submitting}
            onClick={resetToLocationStep}
          >
            Reset
          </Button>
          {step === "location" ? (
            <Button
              type="button"
              disabled={!locationValid || submitting}
              onClick={handleLookupLocation}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Checking...
                </>
              ) : (
                "Next"
              )}
            </Button>
          ) : (
            <Button
              type="button"
              disabled={!locationValid || !orderValid || submitting}
              onClick={handleAssign}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Assigning...
                </>
              ) : (
                "Assign"
              )}
            </Button>
          )}
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      ) : null}
    </Card>
  );
}
