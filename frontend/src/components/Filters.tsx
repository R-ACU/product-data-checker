import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { forwardRef } from "react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

// Pill dropdown built on Radix (keyboard: Enter, Space or Arrow down opens, arrows
// move, Enter picks, Escape closes). Never a native <select>: its open list cannot be
// styled on Windows.
export function FilterSelect({
  label,
  value,
  options,
  allLabel,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string; count?: number }[];
  allLabel: string;
  onChange: (v: string) => void;
}) {
  const current = options.find((o) => o.value === value);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`${label}: ${current ? current.label : allLabel}`}
          className={cn(
            "select-button group inline-flex h-10 max-w-[260px] items-center gap-2 rounded-full pl-4 pr-3 text-[13.5px] transition-[background-color,transform,color] duration-200 active:scale-[0.97]",
            value ? "bg-accent-soft text-accent-text" : "bg-muted text-fg hover:bg-[var(--line)]",
          )}
        >
          <span className="text-fg-3 group-data-[state=open]:text-fg-2">{label}</span>
          <span className="truncate font-medium">{current ? current.label : allLabel}</span>
          <ChevronDown className="size-4 shrink-0 opacity-70 transition-transform duration-200 group-data-[state=open]:rotate-180" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" collisionPadding={12} className="listbox max-h-[min(380px,var(--radix-dropdown-menu-content-available-height))] w-[min(320px,calc(100vw-24px))] overflow-y-auto">
        <DropdownMenuPrimitive.RadioGroup value={value} onValueChange={onChange}>
          {[{ value: "", label: allLabel }, ...options].map((o) => (
            <DropdownMenuPrimitive.RadioItem
              key={o.value || "__all"}
              value={o.value}
              className="flex cursor-default select-none items-center gap-3 rounded-full px-3.5 py-2.5 text-[13.5px] outline-none transition-colors duration-150 data-[highlighted]:bg-muted [&+&]:mt-1"
            >
              <span className="min-w-0 flex-1 truncate">{o.label}</span>
              {"count" in o && o.count != null ? <span className="num text-[12px] text-fg-3">{o.count}</span> : null}
              <span className="grid size-4 place-items-center">
                <DropdownMenuPrimitive.ItemIndicator>
                  <Check className="size-4 text-accent-text" aria-hidden="true" />
                </DropdownMenuPrimitive.ItemIndicator>
              </span>
            </DropdownMenuPrimitive.RadioItem>
          ))}
        </DropdownMenuPrimitive.RadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export const SearchField = forwardRef<HTMLInputElement, { value: string; onChange: (v: string) => void; placeholder: string; label: string }>(
  ({ value, onChange, placeholder, label }, ref) => (
    <label className="group relative flex h-10 min-w-0 flex-1 basis-full items-center rounded-full bg-muted transition-shadow focus-within:shadow-[0_0_0_2px_var(--accent)] sm:basis-auto sm:max-w-[340px]">
      <Search className="pointer-events-none absolute left-3.5 size-4 text-fg-3" aria-hidden="true" />
      <span className="sr-only">{label}</span>
      <input
        ref={ref}
        type="search"
        data-search=""
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-full w-full min-w-0 rounded-full bg-transparent pl-10 pr-10 text-[13.5px] text-fg outline-none placeholder:text-fg-3 [&::-webkit-search-cancel-button]:hidden"
      />
      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Suche leeren"
          className="absolute right-1.5 grid size-7 place-items-center rounded-full text-fg-3 transition-colors hover:bg-card hover:text-fg active:scale-95"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      ) : (
        <kbd className="pointer-events-none absolute right-3 hidden rounded-[6px] bg-card px-1.5 text-[11.5px] text-fg-3 sm:block">/</kbd>
      )}
    </label>
  ),
);
SearchField.displayName = "SearchField";
