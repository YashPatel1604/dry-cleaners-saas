import * as React from "react";

import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "success" | "error";

const toastVariants: Record<ToastVariant, string> = {
  default: "border-border bg-card text-foreground",
  success: "border-emerald-200 bg-emerald-50 text-emerald-950",
  error: "border-red-200 bg-red-50 text-red-950",
};

const Toast = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { variant?: ToastVariant }
>(({ className, variant = "default", ...props }, ref) => (
  <div
    ref={ref}
    role="status"
    className={cn(
      "w-full rounded-xl border px-4 py-3 shadow-lg",
      toastVariants[variant],
      className
    )}
    {...props}
  />
));
Toast.displayName = "Toast";

const ToastTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn("text-sm font-semibold", className)} {...props} />
));
ToastTitle.displayName = "ToastTitle";

const ToastDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
));
ToastDescription.displayName = "ToastDescription";

export { Toast, ToastTitle, ToastDescription };
