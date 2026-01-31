import * as React from "react";

import { cn } from "@/lib/utils";

type SelectOption = { value: string; label: React.ReactNode };

type SelectContextValue = {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
};

const SelectContext = React.createContext<SelectContextValue | null>(null);

function collectOptions(children: React.ReactNode): SelectOption[] {
  const options: SelectOption[] = [];

  React.Children.forEach(children, (child) => {
    if (!React.isValidElement(child)) return;

    if (child.type === SelectItem) {
      const { value, children: label } = (child.props ?? {}) as {
        value: string;
        children: React.ReactNode;
      };
      options.push({ value, label });
      return;
    }

    const childProps = child.props as { children?: React.ReactNode };
    if (childProps && childProps.children) {
      options.push(...collectOptions(childProps.children));
    }
  });

  return options;
}

export function Select({
  value,
  onValueChange,
  children,
}: {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
}) {
  const options = React.useMemo(() => collectOptions(children), [children]);

  return (
    <SelectContext.Provider value={{ value, onValueChange, options }}>
      {children}
    </SelectContext.Provider>
  );
}

export function SelectTrigger({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const context = React.useContext(SelectContext);
  if (!context) return null;

  return (
    <div className={cn("relative", className)} {...props}>
      <select
        className={
          "h-10 w-full appearance-none rounded-md border border-gray-300 bg-white px-3 pr-8 text-sm text-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40"
        }
        value={context.value}
        onChange={(event) => context.onValueChange(event.target.value)}
      >
        {context.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-gray-400">
        ▾
      </span>
    </div>
  );
}

export function SelectValue(props: { placeholder?: string }) {
  void props;
  return null;
}

export function SelectContent({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export function SelectItem(props: {
  value: string;
  children: React.ReactNode;
}) {
  void props;
  return null;
}

SelectItem.displayName = "SelectItem";
