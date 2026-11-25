import { ChevronRight, RotateCcw, SearchX } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { ArticleSheet } from "@/components/ArticleSheet";
import { FilterSelect, SearchField } from "@/components/Filters";
import { Segmented } from "@/components/Segmented";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { int } from "@/lib/format";
import { reasonIcon } from "@/lib/icons";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";
import { stageOf, type Payload, type Product } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EmptyState } from "./EmptyState";
import { PageHead } from "./PageHead";

type Stage = "" | "Daten" | "Text";
interface Filters {
  q: string;
  supplier: string;
  reason: string;
  stage: Stage;
}
const EMPTY: Filters = { q: "", supplier: "", reason: "", stage: "" };
let remembered: Filters = EMPTY; // the list keeps its filters while you look at other views

const STAGE_PARAM: Record<string, Stage> = { daten: "Daten", text: "Text" };

/** Filters from the link (#/pruefen?stufe=daten&lieferant=...), checked against the data. */
function fromParams(params: URLSearchParams, data: Payload): Filters | null {
  const keys = ["stufe", "lieferant", "grund"];
  if (!keys.some((k) => params.has(k))) return null;
  const supplier = params.get("lieferant") ?? "";
  const reason = params.get("grund") ?? "";
  return {
    q: "",
    stage: STAGE_PARAM[params.get("stufe") ?? ""] ?? "",
    supplier: data.suppliers.some((s) => s.supplier === supplier) ? supplier : "",
    reason: data.reasons.some((r) => r.reason === reason) ? reason : "",
  };
}

export function matches(p: Product, f: Filters): boolean {
  if (f.stage && stageOf(p) !== f.stage) return false;
  if (f.supplier && p.supplier !== f.supplier) return false;
  if (f.reason && !p.blocking.some((b) => b.label === f.reason)) return false;
  if (f.q) {
    const hay = `${p.sku ?? ""} ${p.name ?? ""} ${p.ean ?? ""} ${p.brand ?? ""} ${p.supplier}`.toLowerCase();
    if (!hay.includes(f.q.trim().toLowerCase())) return false;
  }
  return true;
}

export function Review({ data, params }: { data: Payload; params: URLSearchParams }) {
  const [f, setF] = useState<Filters>(() => fromParams(params, data) ?? remembered);
  const [open, setOpen] = useState<Product | null>(null);
  const reduced = useReducedMotionPref();
  const paramKey = params.toString();

  useEffect(() => {
    const next = fromParams(new URLSearchParams(paramKey), data);
    if (next) setF(next);
  }, [paramKey, data]);
  useEffect(() => {
    remembered = f;
  }, [f]);

  const set = (patch: Partial<Filters>) => setF((cur) => ({ ...cur, ...patch }));
  const rows = useMemo(() => data.review.filter((p) => matches(p, f)), [data, f]);
  const codeOf = useMemo(() => new Map(data.reasons.map((r) => [r.reason, r.code])), [data]);
  const active = f.q || f.supplier || f.reason || f.stage;
  const reset = () => {
    setF(EMPTY);
    if (window.location.hash !== "#/pruefen") window.history.replaceState(null, "", "#/pruefen");
  };

  return (
    <div className="space-y-5">
      <PageHead title="Prüfliste" />

      <Card className="overflow-hidden">
        <div className="toolbar flex flex-wrap items-center gap-2 p-3">
          <SearchField value={f.q} onChange={(q) => set({ q })} placeholder="Nummer, Name oder EAN" label="Artikel suchen" />
          <FilterSelect
            label="Lieferant"
            allLabel="Alle"
            value={f.supplier}
            onChange={(supplier) => set({ supplier })}
            options={data.suppliers.map((s) => ({ value: s.supplier, label: s.supplier, count: s.blocked }))}
          />
          <FilterSelect
            label="Grund"
            allLabel="Alle"
            value={f.reason}
            onChange={(reason) => set({ reason })}
            options={data.reasons.map((r) => ({ value: r.reason, label: r.reason, count: r.articles }))}
          />
          <Segmented
            id="stage"
            label="Stufe"
            value={f.stage}
            onChange={(stage) => set({ stage })}
            options={[
              { value: "" as Stage, label: "Alle" },
              { value: "Daten" as Stage, label: "Daten" },
              { value: "Text" as Stage, label: "Text" },
            ]}
          />
          <div className="ml-auto flex items-center gap-2 pr-2">
            {active ? (
              <Button variant="ghost" size="sm" onClick={reset}>
                <RotateCcw />
                Zurücksetzen
              </Button>
            ) : null}
            <span className="count-line num text-[13px] text-fg-3" aria-live="polite">
              {int(rows.length)} von {int(data.review.length)} Artikeln
            </span>
          </div>
        </div>

        {rows.length ? (
          <div className="overflow-x-auto px-2 pb-3 sm:px-3">
            <table className="w-full table-fixed border-separate border-spacing-y-1 text-left text-[13.5px] md:min-w-[760px]">
              <thead>
                <tr className="text-[12.5px] text-fg-3">
                  <th className="px-3 py-2 font-normal sm:px-4 md:w-[34%]">Artikel</th>
                  <th className="hidden px-4 py-2 font-normal md:table-cell md:w-[12%]">Nummer</th>
                  <th className="hidden px-4 py-2 font-normal md:table-cell md:w-[20%]">Lieferant</th>
                  <th className="px-3 py-2 font-normal sm:px-4">Grund</th>
                  <th className="hidden w-[84px] px-4 py-2 font-normal sm:table-cell">Stufe</th>
                  <th className="w-[44px] sm:w-[52px]" aria-label="Öffnen" />
                </tr>
              </thead>
              <tbody>
                {rows.map((p, i) => {
                  const stage = stageOf(p);
                  const first = p.blocking[0];
                  const Icon = reasonIcon(first ? (codeOf.get(first.label) ?? "") : "");
                  return (
                    <motion.tr
                      key={p.row}
                      initial={reduced ? false : { opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, ease: EASE_OUT, delay: Math.min(i, 14) * 0.02 }}
                      tabIndex={0}
                      onClick={() => setOpen(p)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setOpen(p);
                        }
                      }}
                      aria-label={`${p.name ?? p.sku ?? "Artikel"} öffnen`}
                      className={cn(
                        "group cursor-pointer outline-none transition-colors duration-150",
                        "[&>td]:bg-transparent hover:[&>td]:bg-muted focus-visible:[&>td]:bg-accent-soft",
                        "[&>td:first-child]:rounded-l-full [&>td:last-child]:rounded-r-full",
                      )}
                    >
                      <td className="truncate px-3 py-3 font-medium text-fg sm:px-4">{p.name || "Ohne Bezeichnung"}</td>
                      <td className="num hidden truncate px-4 py-3 text-[13px] text-fg-3 md:table-cell">{p.sku || "ohne"}</td>
                      <td className="hidden truncate px-4 py-3 text-fg-2 md:table-cell">{p.supplier}</td>
                      <td className="px-3 py-2 sm:px-4">
                        <span className="flex min-w-0 items-center gap-2.5">
                          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-muted text-fg-2 transition-colors duration-150 group-hover:bg-card">
                            <Icon className="size-[15px]" strokeWidth={1.9} aria-hidden="true" />
                          </span>
                          <span className="truncate text-fg">{first?.label ?? "Ohne Befund"}</span>
                          {p.blocking.length > 1 ? <span className="num shrink-0 text-[12.5px] text-fg-3">+{p.blocking.length - 1}</span> : null}
                        </span>
                      </td>
                      <td className="hidden px-4 py-2 sm:table-cell">
                        <Badge className={stage === "Text" ? "bg-accent-soft text-accent-text" : ""}>{stage}</Badge>
                      </td>
                      <td className="pr-2 sm:pr-3">
                        <span className="grid size-8 place-items-center rounded-full text-fg-3 transition-[background-color,color,transform] duration-200 group-hover:translate-x-0.5 group-hover:bg-card group-hover:text-fg">
                          <ChevronRight className="size-4" aria-hidden="true" />
                        </span>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">
            <EmptyState
              icon={SearchX}
              title="Keine Artikel für diese Filter"
              text="Weniger Filter oder ein anderer Suchbegriff"
              action={
                <Button variant="primary" onClick={reset}>
                  <RotateCcw />
                  Filter zurücksetzen
                </Button>
              }
            />
          </div>
        )}
      </Card>

      <ArticleSheet product={open} kind="review" limits={{ title: data.meta.titleMax, description: data.meta.descriptionMax }} onClose={() => setOpen(null)} />
    </div>
  );
}
