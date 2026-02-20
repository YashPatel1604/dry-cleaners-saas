import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

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

interface StorageLocationScannerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLookupLocation: (barcode: string) => Promise<LocationLookupResult>;
  onAssignLocation: (payload: {
    locationBarcode: string;
    orderBarcode: string;
    rackNumber?: string;
  }) => Promise<LocationAssignResult>;
}

type ScanStep = "location" | "rack" | "order";

const LOCATION_BARCODE_RE = /^LOC-[A-Z0-9][A-Z0-9-]{0,30}$/;
const ORDER_BARCODE_RE = /^ORD-\d{8}$/;

export function StorageLocationScannerDialog({
  open,
  onOpenChange,
  onLookupLocation,
  onAssignLocation,
}: StorageLocationScannerDialogProps) {
  const [step, setStep] = useState<ScanStep>("location");
  const [locationBarcode, setLocationBarcode] = useState("");
  const [rackNumber, setRackNumber] = useState("");
  const [orderBarcode, setOrderBarcode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedLocationBarcode = locationBarcode.trim().toUpperCase();
  const normalizedOrderBarcode = orderBarcode.trim().toUpperCase();

  useEffect(() => {
    if (!open) return;
    setStep("location");
    setLocationBarcode("");
    setRackNumber("");
    setOrderBarcode("");
    setSubmitting(false);
    setError(null);
  }, [open]);

  const canSubmitLocation = useMemo(
    () => LOCATION_BARCODE_RE.test(normalizedLocationBarcode),
    [normalizedLocationBarcode]
  );
  const canSubmitOrder = useMemo(
    () => ORDER_BARCODE_RE.test(normalizedOrderBarcode),
    [normalizedOrderBarcode]
  );

  const handleLookupLocation = async () => {
    if (!canSubmitLocation || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await onLookupLocation(normalizedLocationBarcode);
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

  const handleAssign = async () => {
    if (!canSubmitOrder || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await onAssignLocation({
        locationBarcode: normalizedLocationBarcode,
        orderBarcode: normalizedOrderBarcode,
        rackNumber: rackNumber.trim() || undefined,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to assign location.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Order Location</DialogTitle>
          <DialogDescription>
            Scan location barcode first, then scan order barcode.
          </DialogDescription>
        </DialogHeader>

        {step === "location" && (
          <div className="space-y-3">
            <Label htmlFor="locationBarcode">Location barcode</Label>
            <Input
              id="locationBarcode"
              value={locationBarcode}
              onChange={(event) =>
                setLocationBarcode(event.target.value.toUpperCase())
              }
              placeholder="Scan location barcode"
              autoFocus
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleLookupLocation();
                }
              }}
            />
            <p className="text-xs text-gray-500">Format: LOC-...</p>
          </div>
        )}

        {step === "rack" && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              New location barcode detected. Rack number is optional.
            </p>
            <Label htmlFor="rackNumber">Rack number (optional)</Label>
            <Input
              id="rackNumber"
              type="text"
              inputMode="numeric"
              value={rackNumber}
              onChange={(event) => setRackNumber(event.target.value)}
              placeholder="Enter rack number"
              autoFocus
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  setStep("order");
                }
              }}
            />
          </div>
        )}

        {step === "order" && (
          <div className="space-y-3">
            <div className="rounded-md border border-gray-200 bg-gray-50 p-3 text-sm">
              <p className="text-gray-700">
                <span className="font-medium">Location:</span>{" "}
                {locationBarcode.trim()}
              </p>
              {rackNumber.trim() ? (
                <p className="text-gray-700">
                  <span className="font-medium">Rack:</span> {rackNumber.trim()}
                </p>
              ) : null}
            </div>
            <Label htmlFor="orderBarcode">Order barcode / SKU</Label>
            <Input
              id="orderBarcode"
              value={orderBarcode}
              onChange={(event) =>
                setOrderBarcode(event.target.value.toUpperCase())
              }
              placeholder="Scan order barcode"
              autoFocus
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleAssign();
                }
              }}
            />
            <p className="text-xs text-gray-500">Format: ORD-########</p>
          </div>
        )}

        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <DialogFooter className="gap-2 sm:justify-between">
          {step === "location" && (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleLookupLocation}
                disabled={!canSubmitLocation || submitting}
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
            </>
          )}

          {step === "rack" && (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep("location")}
                disabled={submitting}
              >
                Back
              </Button>
              <Button
                type="button"
                onClick={() => setStep("order")}
                disabled={submitting}
              >
                Continue
              </Button>
            </>
          )}

          {step === "order" && (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep("location")}
                disabled={submitting}
              >
                Restart
              </Button>
              <Button
                type="button"
                onClick={handleAssign}
                disabled={!canSubmitOrder || submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Assigning...
                  </>
                ) : (
                  "Assign Location"
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
