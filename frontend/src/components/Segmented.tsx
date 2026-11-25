import { motion } from "motion/react";
import { SPRING } from "@/lib/motion";
import { cn } from "@/lib/utils";

// Segmented control: a grey track, the choice a raised pill that glides. Keyboard:
// arrows move, like a radio group.
export function Segmented<T extends string>({
  id,
  label,
  options,
  value,
  onChange,
}: {
  id: string;
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  const idx = options.findIndex((o) => o.value === value);
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex gap-1 rounded-full bg-seg p-1"
      onKeyDown={(e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        e.preventDefault();
        const next = (idx + (e.key === "ArrowRight" ? 1 : options.length - 1)) % options.length;
        onChange(options[next].value);
        const btn = e.currentTarget.querySelectorAll<HTMLButtonElement>("button")[next];
        btn?.focus();
      }}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative h-8 rounded-full px-3.5 text-[13px] font-medium transition-[color,background-color,transform] duration-200 active:scale-[0.97]",
              active ? "text-fg" : "text-fg-2 hover:bg-[color-mix(in_srgb,var(--pill)_55%,transparent)] hover:text-fg",
            )}
          >
            {active ? (
              <motion.span
                layoutId={`seg-${id}`}
                transition={SPRING}
                className="pill-bg shadow-pill absolute inset-0 rounded-full bg-pill"
                aria-hidden="true"
              />
            ) : null}
            <span className="relative">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}
