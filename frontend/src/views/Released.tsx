import { ArrowUpRight, PackageOpen, RotateCcw } from "lucide-react";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { ArticleSheet } from "@/components/ArticleSheet";
import { FilterSelect, SearchField } from "@/components/Filters";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fmt2, int } from "@/lib/format";
import { categoryIcon } from "@/lib/icons";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";
import type { Payload, Product } from "@/lib/types";
import { EmptyState } from "./EmptyState";
import { PageHead } from "./PageHead";

const PAGE = 24;

export function Released({ data }: { data: Payload }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [shown, setShown] = useState(PAGE);
  const [open, setOpen] = useState<Product | null>(null);
  const reduced = useReducedMotionPref();

  const categories = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of data.released) if (p.category) m.set(p.category, (m.get(p.category) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [data]);
  const rows = useMemo(
    () =>
      data.released.filter((p) => {
        if (category && p.category !== category) return false;
        if (!q) return true;
        const hay = `${p.sku ?? ""} ${p.title} ${p.name ?? ""} ${p.ean ?? ""} ${p.supplier}`.toLowerCase();
        return hay.includes(q.trim().toLowerCase());
      }),
    [data, q, category],
  );
  const reset = () => {
    setQ("");
    setCategory("");
  };

  return (
    <div className="space-y-5">
      <PageHead title="Freigegeben" />

      <Card className="p-3">
        <div className="toolbar flex flex-wrap items-center gap-2">
          <SearchField
            value={q}
            onChange={(v) => {
              setQ(v);
              setShown(PAGE);
            }}
            placeholder="Titel, Nummer oder EAN"
            label="Freigegebene Artikel suchen"
          />
          <FilterSelect
            label="Kategorie"
            allLabel="Alle"
            value={category}
            onChange={(v) => {
              setCategory(v);
              setShown(PAGE);
            }}
            options={categories.map(([c, n]) => ({ value: c, label: c, count: n }))}
          />
          <span className="count-line num ml-auto pr-3 text-[13px] text-fg-3" aria-live="polite">
            {int(rows.length)} von {int(data.released.length)} Artikeln
          </span>
        </div>
      </Card>

      {rows.length ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            {rows.slice(0, shown).map((p, i) => {
              const Icon = categoryIcon(p.category);
              return (
                <motion.button
                  key={p.row}
                  type="button"
                  onClick={() => setOpen(p)}
                  initial={reduced ? false : { opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, ease: EASE_OUT, delay: Math.min(i % PAGE, 12) * 0.03 }}
                  aria-label={`${p.title} öffnen`}
                  className="product-card card-hover kpi-hover shadow-card group flex min-h-[188px] flex-col rounded-[28px] bg-card p-5 text-left active:scale-[0.99]"
                >
                  <div className="flex items-center gap-3">
                    <span className="grid size-11 shrink-0 place-items-center rounded-full bg-accent-soft text-accent-text">
                      <Icon className="size-[19px]" strokeWidth={1.9} aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[13px] text-fg-3">{p.category}</span>
                    <span className="grid size-9 place-items-center rounded-full bg-muted text-fg transition-[background-color,color] duration-200 group-hover:bg-primary group-hover:text-on-primary">
                      <ArrowUpRight className="size-4" aria-hidden="true" />
                    </span>
                  </div>
                  <h3 className="mt-4 line-clamp-2 text-[15px] font-medium leading-snug text-fg">{p.title}</h3>
                  <div className="mt-auto flex items-baseline justify-between gap-3 pt-4">
                    <span className="truncate text-[13px] text-fg-3">{p.supplier}</span>
                    <span className="num shrink-0 text-[17px] font-medium tracking-[-0.01em] text-fg">{p.price == null ? "" : `${fmt2.format(p.price)} €`}</span>
                  </div>
                </motion.button>
              );
            })}
          </div>
          {shown < rows.length ? (
            <div className="flex justify-center">
              <Button onClick={() => setShown((n) => n + PAGE)}>
                Weitere {int(Math.min(PAGE, rows.length - shown))} anzeigen
              </Button>
            </div>
          ) : null}
        </>
      ) : (
        <Card className="empty">
          <EmptyState
            icon={PackageOpen}
            title="Keine Artikel für diese Filter"
            text="Ein anderer Suchbegriff oder alle Kategorien"
            action={
              <Button variant="primary" onClick={reset}>
                <RotateCcw />
                Filter zurücksetzen
              </Button>
            }
          />
        </Card>
      )}

      <ArticleSheet product={open} kind="released" limits={{ title: data.meta.titleMax, description: data.meta.descriptionMax }} onClose={() => setOpen(null)} />
    </div>
  );
}
