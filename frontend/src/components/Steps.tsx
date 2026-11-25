import { ChevronDown, ChevronRight, FileSpreadsheet, PackageCheck, ScanBarcode, SpellCheck, Terminal, WandSparkles, type LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { int, pct, two } from "@/lib/format";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";
import type { Payload } from "@/lib/types";
import { cn } from "@/lib/utils";

// The run as a flow of five steps: file, data check, texts, text check, released. Each
// step is an icon, a number and one or two words. Nothing is marked unless the list
// below is filtered to a step (the two checks), so the bar never competes with the tabs.
export type StepKey = "read" | "data" | "texts" | "text" | "released";

interface Step {
  key: StepKey;
  icon: LucideIcon;
  label: string;
  value: number;
  note?: string;
  href?: string;
  aria: string;
}

export function Steps({ data, active }: { data: Payload; active: StepKey | null }) {
  const p = data.pipeline;
  const reduced = useReducedMotionPref();
  const steps: Step[] = [
    { key: "read", icon: FileSpreadsheet, label: data.meta.sourceFile, value: p.read, note: "Zeilen", aria: "" },
    {
      key: "data",
      icon: ScanBarcode,
      label: "Datenprüfung",
      value: p.read - p.dataBlocked,
      note: `−${int(p.dataBlocked)}`,
      href: "#/pruefen?stufe=daten",
      aria: `Schritt 2, Datenprüfung: ${int(p.read - p.dataBlocked)} bestanden, ${int(p.dataBlocked)} zur Prüfung`,
    },
    {
      key: "texts",
      icon: WandSparkles,
      label: "Texte geschrieben",
      value: p.textWritten,
      note: `${int(p.classified)} Kategorien`,
      aria: `Schritt 3, Texte geschrieben: ${int(p.textWritten)}, ${int(p.classified)} Kategorien vom Modell ergänzt`,
    },
    {
      key: "text",
      icon: SpellCheck,
      label: "Textprüfung",
      value: p.textWritten - p.textBlocked,
      note: `−${int(p.textBlocked)}`,
      href: "#/pruefen?stufe=text",
      aria: `Schritt 4, Textprüfung: ${int(p.textWritten - p.textBlocked)} bestanden, ${int(p.textBlocked)} zur Prüfung`,
    },
    {
      key: "released",
      icon: PackageCheck,
      label: "Freigegeben",
      value: p.released,
      note: pct((100 * p.released) / p.read),
      href: "#/freigegeben",
      aria: `Schritt 5, Freigegeben: ${int(p.released)}, ${pct((100 * p.released) / p.read)} der Liste`,
    },
  ];

  return (
    <nav aria-label="Ablauf des Laufs" className="flow shadow-card overflow-x-auto rounded-[28px] bg-card p-2">
      <ol className="grid grid-cols-5 items-center sm:flex sm:min-w-max lg:min-w-0">
        {steps.map((s, i) => (
          <motion.li
            key={s.key}
            className={cn("flex min-w-0 items-center", i === 0 ? "sm:min-w-[200px] sm:flex-[1.15]" : "sm:min-w-[196px] sm:flex-1")}
            initial={reduced ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: EASE_OUT, delay: reduced ? 0 : 0.04 + i * 0.05 }}
          >
            {i > 0 ? (
              <span className="hidden w-5 shrink-0 justify-center text-[var(--line-strong)] sm:flex" aria-hidden="true">
                <ChevronRight className="size-4" strokeWidth={2.25} />
              </span>
            ) : null}
            <div className="min-w-0 flex-1">
              {s.key === "read" ? <FileStep step={s} data={data} /> : <FlowStep step={s} on={active === s.key} />}
            </div>
          </motion.li>
        ))}
      </ol>
    </nav>
  );
}

function StepBody({ step, on, interactive = true, trailing }: { step: Step; on: boolean; interactive?: boolean; trailing?: ReactNode }) {
  const Icon = step.icon;
  return (
    <>
      <span
        className={cn(
          "relative grid size-10 shrink-0 place-items-center rounded-full transition-colors duration-200 sm:size-11",
          on ? "bg-accent text-on-accent" : "bg-muted text-fg-2",
          !on && interactive && "group-hover:bg-card group-hover:text-fg group-data-[state=open]:bg-card",
        )}
      >
        <Icon className="size-[19px]" strokeWidth={1.9} aria-hidden="true" />
      </span>
      <span className="min-w-0 text-center sm:flex-1 sm:text-left">
        <span className={cn("hidden truncate text-[12.5px] transition-colors sm:block", on ? "text-fg" : "text-fg-3")}>{step.label}</span>
        <span className="flex flex-col items-center sm:flex-row sm:items-baseline sm:gap-1.5">
          <span className="num text-[16px] font-medium leading-tight tracking-[-0.015em] text-fg sm:text-[20px]">{int(step.value)}</span>
          {step.note ? <span className="num hidden truncate text-[12.5px] text-fg-3 min-[400px]:block">{step.note}</span> : null}
        </span>
      </span>
      {trailing}
    </>
  );
}

const stepClass =
  "step relative flex w-full flex-col items-center gap-1.5 rounded-[20px] px-1 py-2 text-left transition-[background-color,transform] duration-200 sm:flex-row sm:gap-3 sm:rounded-[22px] sm:pl-2 sm:pr-3";

function FlowStep({ step, on }: { step: Step; on: boolean }) {
  if (!step.href) {
    return (
      <div className={stepClass} aria-label={step.aria} role="group">
        <StepBody step={step} on={false} interactive={false} />
      </div>
    );
  }
  return (
    <a
      href={step.href}
      aria-label={step.aria}
      aria-current={on ? "step" : undefined}
      className={cn(stepClass, "group active:scale-[0.985]", on ? "bg-muted" : "hover:bg-muted")}
    >
      <StepBody step={step} on={on} />
    </a>
  );
}

function FileStep({ step, data }: { step: Step; data: Payload }) {
  const when = new Date(data.meta.generatedAt).toLocaleString("de-DE", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
  const mock = data.meta.provider === "mock";
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`Schritt 1, eingelesen: ${data.meta.sourceFile}, ${int(data.meta.rows)} Zeilen. Details`}
          className={cn(stepClass, "group hover:bg-muted active:scale-[0.985] data-[state=open]:bg-muted")}
        >
          <StepBody
            step={step}
            on={false}
            trailing={<ChevronDown className="hidden size-4 shrink-0 text-fg-3 transition-transform duration-200 group-data-[state=open]:rotate-180 sm:block" aria-hidden="true" />}
          />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[320px]">
        <DropdownMenuLabel>Geprüfte Liste</DropdownMenuLabel>
        <dl className="grid grid-cols-2 gap-1.5 px-1 pb-1">
          <Fact label="Zeilen" value={int(data.meta.rows)} />
          <Fact label="Lieferanten" value={int(data.suppliers.length)} />
          <Fact label="Dauer" value={`${two(data.meta.seconds)} s`} />
          <Fact label="Texte" value={mock ? "Mock" : "Claude"} />
        </dl>
        <p className="num px-2.5 pb-1 pt-1.5 text-[12.5px] text-fg-3">Lauf vom {when}</p>
        <DropdownMenuSeparator />
        <div className="flex items-start gap-2.5 px-2.5 py-2 text-[12.5px] text-fg-3">
          <Terminal className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <code className="rounded-[6px] bg-muted px-1.5 py-0.5 font-mono text-[12px] text-fg-2">uv run pdc build --input liste.xlsx</code>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[14px] bg-muted px-3 py-2">
      <dt className="text-[12px] text-fg-3">{label}</dt>
      <dd className="num text-[15px] font-medium text-fg">{value}</dd>
    </div>
  );
}
