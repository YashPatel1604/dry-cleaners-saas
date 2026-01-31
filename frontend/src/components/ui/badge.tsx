import * as React from "react";

import { cn } from "@/lib/utils";

export type BadgeVariant = "default" | "secondary" | "outline" | "destructive";

const badgeVariants: Record<BadgeVariant, string> = {
  default: "bg-blue-100 text-blue-800",
  secondary: "bg-gray-100 text-gray-800",
  outline: "border border-gray-200 text-gray-800",
  destructive: "bg-red-100 text-red-800",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        badgeVariants[variant],
        className
      )}
      {...props}
    />
  );
}
