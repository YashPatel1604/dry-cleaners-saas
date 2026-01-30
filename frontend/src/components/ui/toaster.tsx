import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Toast, ToastDescription, ToastTitle } from "./toast";
import { useToast } from "./use-toast";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-3 px-4 sm:items-end"
      )}
      aria-live="polite"
      aria-relevant="additions"
    >
      {toasts.map((toastItem) => (
        <Toast
          key={toastItem.id}
          variant={toastItem.variant}
          className="pointer-events-auto w-full max-w-sm"
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 space-y-1">
              {toastItem.title && <ToastTitle>{toastItem.title}</ToastTitle>}
              {toastItem.description && (
                <ToastDescription>{toastItem.description}</ToastDescription>
              )}
            </div>
            <button
              type="button"
              className="rounded-md p-1 text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
              onClick={() => dismiss(toastItem.id)}
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </Toast>
      ))}
    </div>
  );
}
