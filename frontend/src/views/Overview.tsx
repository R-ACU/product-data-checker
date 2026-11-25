import { ArrowUpRight, Gauge as GaugeIcon, ListChecks, PackageCheck, Sparkles, type LucideIcon } from "lucide-react";
import { useMemo, type ReactNode } from "react";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { TipCard } from "@/components/charts/ChartTip";
import { Gauge } from "@/components/charts/Gauge";
import { HBarList } from "@/components/charts/HBarList";
import { SupplierPills, type SupplierRow } from "@/components/charts/SupplierPills";
import { ArrowLink, Card, HeroCard, IconCircle, Inset } from "@/components/ui/card";
import { int, one, pct, signed, two } from "@/lib/format";
import { fixIcon, reasonIcon } from "@/lib/icons";
import { stageOf, type Payload } from "@/lib/types";
import { sum } from "@/lib/utils";
import { PageHead } from "./PageHead";

const go = (hash: string) => {
  window.location.hash = hash;
};
export const supplierHref = (name: string) => `#/pruefen?lieferant=${encodeURIComponent(name)}`;

export function Overview({ data }: { data: Payload }) {
  const o = data.overview;
  const p = data.pipeline;
  const fixTotal = sum(data.autoFixes.map((f) => f.count));

  // Per supplier: released, stopped at the data check, stopped at the text check.
  const bySupplier = useMemo<SupplierRow[]>(() => {
    const rows = data.suppliers.map((s) => ({
      supplier: s.supplier,
      articles: s.articles,
      errorRate: s.error_rate_pct,
      topReason: s.top_reason,
      released: 0,
      daten: 0,
      text: 0,
    }));
    const find = (name: string) => rows.find((r) => r.supplier === name);
    for (const r of data.released) {
      const row = find(r.supplier);
      if (row) row.released += 1;
    }
    for (const r of data.review) {
      const row = find(r.supplier);
      if (row) row[stageOf(r) === "Daten" ? "daten" : "text"] += 1;
    }
    return rows.sort((a, b) => b.released / b.articles - a.released / a.articles);
  }, [data]);

  return (
    <div className="space-y-5">
      <PageHead title="Übersicht" lede={`${data.suppliers.length} Lieferanten, in ${two(data.meta.seconds)} s geprüft`} />

      <div className="grid gap-5 xl:grid-cols-12">
        <HeroCard className="flex flex-col p-6 md:p-7 xl:col-span-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <IconCircle icon={PackageCheck} tone="hero" />
              <h2 className="text-[16px] font-medium tracking-[-0.01em]">Ergebnis je Lieferant</h2>
            </div>
            <HeroLegend />
          </div>
          <div className="mt-6 flex flex-1 flex-col gap-8 md:flex-row md:items-end">
            <div className="shrink-0 md:w-[220px] md:pb-[54px]">
              <p className="text-[14px] text-[var(--hero-fg-2)]">Shopfertig</p>
              <AnimatedNumber value={o.released} format={int} className="mt-1 block text-[64px] font-medium leading-none tracking-[-0.035em]" />
              <p className="mt-3 flex items-center gap-2 text-[13.5px] text-[var(--hero-fg-2)]">
                <span className="num rounded-full bg-[var(--hero-inner)] px-2.5 py-1 text-[12.5px] font-semibold text-[var(--hero-accent-2)]">{pct(o.release_rate_pct)}</span>
                von {int(o.articles)}
              </p>
              <a
                href="#/pruefen"
                className="group mt-6 inline-flex h-10 items-center gap-2.5 rounded-full bg-[var(--hero-inner)] pl-4 pr-1.5 text-[13.5px] font-medium text-[var(--hero-fg)] transition-[background-color,transform] duration-200 hover:bg-[#2e2e33] active:scale-[0.97]"
              >
                <span className="num">{int(o.to_review)}</span> zur Prüfung
                <span className="grid size-7 place-items-center rounded-full bg-[var(--hero-bg)] transition-transform duration-200 group-hover:translate-x-0.5">
                  <ArrowUpRight className="size-4" aria-hidden="true" />
                </span>
              </a>
            </div>
            <div className="min-w-0 flex-1">
              <SupplierPills
                label="Freigabe je Lieferant, ein Klick öffnet die Prüfliste des Lieferanten"
                rows={bySupplier}
                height={300}
                onSelect={(r) => go(supplierHref(r.supplier))}
                tooltip={(r) => (
                  <TipCard
                    title={r.supplier}
                    rows={[
                      { label: "Freigegeben", value: int(r.released), color: "var(--hero-accent)" },
                      { label: "Daten", value: int(r.daten), color: "var(--hero-accent-2)" },
                      { label: "Text", value: int(r.text), color: "var(--hero-hatch)" },
                      { label: "Freigabequote", value: pct((100 * r.released) / r.articles), strong: true },
                    ]}
                    foot={r.topReason ? `Häufigster Grund: ${r.topReason}` : undefined}
                  />
                )}
              />
            </div>
          </div>
        </HeroCard>

        <Card className="flex flex-col xl:col-span-4">
          <CardTop icon={GaugeIcon} title="Vollständig" />
          <div className="flex flex-1 flex-col px-6 pb-6 pt-5">
            <Inset className="flex flex-1 flex-col items-center justify-center px-5 pb-6 pt-7">
              <div className="relative w-full max-w-[300px]">
                <Gauge
                  value={o.complete_articles_before_pct}
                  target={o.usable_released_pct}
                  label={`Vollständig bei Lieferung ${one(o.complete_articles_before_pct)} %, bei den freigegebenen ${one(o.usable_released_pct)} %`}
                />
                <div className="absolute inset-x-0 bottom-0 text-center">
                  <AnimatedNumber value={o.complete_articles_before_pct} format={(v) => `${one(v)} %`} className="text-[34px] font-medium leading-none tracking-[-0.025em] text-fg" />
                  <div className="mt-1.5 text-[12.5px] text-fg-3">bei Lieferung</div>
                </div>
              </div>
            </Inset>
            <div className="mt-4 flex items-center justify-between gap-3 px-1">
              <span className="flex items-center gap-2.5 text-[13.5px] text-fg-2">
                <svg className="h-2.5 w-4" viewBox="0 0 16 10" aria-hidden="true">
                  <defs>
                    <pattern id="gauge-legend-hatch" patternUnits="userSpaceOnUse" width={4} height={4} patternTransform="rotate(45)">
                      <rect width={4} height={4} fill="var(--muted)" />
                      <rect width={1.6} height={4} fill="var(--accent)" />
                    </pattern>
                  </defs>
                  <rect width={16} height={10} rx={5} fill="url(#gauge-legend-hatch)" />
                </svg>
                Freigegeben
              </span>
              <span className="flex items-baseline gap-2">
                <span className="num rounded-full bg-good-soft px-2 py-0.5 text-[12px] font-semibold text-good">
                  {signed(o.usable_released_pct - o.complete_articles_before_pct)} Pp
                </span>
                <span className="num text-[17px] font-medium text-fg">{pct(o.usable_released_pct)}</span>
              </span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-12">
        <Card className="flex flex-col xl:col-span-6">
          <CardTop icon={ListChecks} title="Zur Prüfung" href="#/pruefen" hrefLabel="Zur Prüfliste" />
          <BigStat value={o.to_review} unit="Artikel" aside={`${int(p.dataBlocked)} Daten · ${int(p.textBlocked)} Text`} />
          <div className="px-4 pb-4 pt-3">
            <HBarList
              label="Gründe für die Prüfung"
              rows={data.reasons.slice(0, 6).map((r) => ({
                key: r.code,
                label: r.reason,
                icon: reasonIcon(r.code),
                value: r.articles,
                display: int(r.articles),
                color: "var(--chart-1)",
                onClick: () => go(`#/pruefen?grund=${encodeURIComponent(r.reason)}`),
                tip: (
                  <TipCard
                    title={r.reason}
                    rows={[
                      { label: "Artikel", value: int(r.articles), color: "var(--chart-1)", strong: true },
                      { label: "Befunde", value: int(r.findings) },
                      { label: "Anteil an allen", value: pct(r.share_of_all_pct) },
                    ]}
                    foot={r.stage === "Daten" ? "Datenprüfung" : "Textprüfung"}
                  />
                ),
              }))}
            />
          </div>
        </Card>

        <Card className="flex flex-col xl:col-span-6">
          <CardTop icon={Sparkles} title="Automatisch bereinigt" />
          <BigStat value={fixTotal} unit="Korrekturen" aside="blockieren nichts" />
          <div className="px-4 pb-4 pt-3">
            <HBarList
              label="Automatische Korrekturen je Art"
              rows={data.autoFixes.map((f) => ({
                key: f.label,
                label: f.label,
                icon: fixIcon(f.label),
                value: f.count,
                display: int(f.count),
                color: "var(--chart-1)",
                tip: (
                  <TipCard
                    title={f.label}
                    rows={[
                      { label: "Korrekturen", value: int(f.count), color: "var(--chart-1)", strong: true },
                      { label: "Anteil", value: pct((100 * f.count) / (fixTotal || 1)) },
                    ]}
                    foot="Im Excel-Blatt Sauber unter Hinweise"
                  />
                ),
              }))}
            />
          </div>
        </Card>
      </div>
    </div>
  );
}

function CardTop({ icon, title, href, hrefLabel }: { icon: LucideIcon; title: string; href?: string; hrefLabel?: string }) {
  return (
    <div className="flex items-center gap-3.5 px-6 pt-6">
      <IconCircle icon={icon} />
      <h2 className="min-w-0 flex-1 text-[16px] font-medium tracking-[-0.01em] text-fg">{title}</h2>
      {href ? <ArrowLink href={href} label={hrefLabel ?? title} /> : null}
    </div>
  );
}

function BigStat({ value, unit, aside }: { value: number; unit: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-6 pt-5">
      <span className="flex items-baseline gap-2">
        <AnimatedNumber value={value} format={int} className="text-[40px] font-medium leading-none tracking-[-0.03em] text-fg" />
        <span className="text-[14px] text-fg-3">{unit}</span>
      </span>
      {aside ? <span className="num text-[13px] text-fg-3">{aside}</span> : null}
    </div>
  );
}

function HeroLegend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[13px] text-[var(--hero-fg-2)]">
      <li className="flex items-center gap-2">
        <span className="h-2.5 w-4 rounded-full bg-[var(--hero-accent)]" aria-hidden="true" />
        Freigegeben
      </li>
      <li className="flex items-center gap-2">
        <span className="h-2.5 w-4 rounded-full bg-[var(--hero-accent-2)]" aria-hidden="true" />
        Daten
      </li>
      <li className="flex items-center gap-2">
        <svg className="h-2.5 w-4" viewBox="0 0 16 10" aria-hidden="true">
          <defs>
            <pattern id="legend-hatch" patternUnits="userSpaceOnUse" width={5} height={5} patternTransform="rotate(45)">
              <rect width={5} height={5} fill="var(--hero-inner)" />
              <rect width={1.8} height={5} fill="var(--hero-fg-2)" />
            </pattern>
          </defs>
          <rect width={16} height={10} rx={5} fill="url(#legend-hatch)" />
        </svg>
        Text
      </li>
    </ul>
  );
}
