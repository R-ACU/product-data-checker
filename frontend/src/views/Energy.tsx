import { Activity, BarChart3, Database, Grid3x3, Leaf, LineChart as LineChartIcon, Plug, Sun, TrendingDown, TrendingUp, Wind } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader, HeroCard, IconCircle } from "@/components/ui/card";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { KpiCard } from "@/components/KpiCard";
import { Segmented } from "@/components/Segmented";
import { TipCard } from "@/components/charts/ChartTip";
import { Columns } from "@/components/charts/Columns";
import { Legend } from "@/components/charts/common";
import { Donut } from "@/components/charts/Donut";
import { Heatmap } from "@/components/charts/Heatmap";
import { HeroBars } from "@/components/charts/HeroBars";
import { PriceArea, withRollingMean } from "@/components/charts/PriceArea";
import { MiniBars, Sparkline } from "@/components/charts/Spark";
import { MONTHS, MONTHS_LONG, int, one, pct, signed, two } from "@/lib/format";
import type { Payload, Smard } from "@/lib/types";
import { sum } from "@/lib/utils";
import { EmptyState } from "./EmptyState";
import { PageHead } from "./PageHead";

type RangeKey = "jahr" | "q1" | "q2" | "q3" | "q4";
const RANGES: { value: RangeKey; label: string; months: number[] }[] = [
  { value: "jahr", label: "Jahr", months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] },
  { value: "q1", label: "Q1", months: [1, 2, 3] },
  { value: "q2", label: "Q2", months: [4, 5, 6] },
  { value: "q3", label: "Q3", months: [7, 8, 9] },
  { value: "q4", label: "Q4", months: [10, 11, 12] },
];

// Months combine exactly: SQL delivers sums, so a quarter's average is sum / hours.
function rangeStats(s: Smard, months: number[]) {
  const ms = s.monthly.filter((m) => months.includes(Number(m.month.slice(5, 7))));
  const hours = sum(ms.map((m) => m.hours));
  const load = sum(ms.map((m) => m.load_mwh));
  return {
    hours,
    avg: sum(ms.map((m) => m.price_sum)) / hours,
    negative: sum(ms.map((m) => m.negative_price_hours)),
    renew: (100 * sum(ms.map((m) => m.renewable_mwh))) / load,
    solar: (100 * sum(ms.map((m) => m.solar_mwh))) / load,
    wind: (100 * sum(ms.map((m) => m.wind_mwh))) / load,
    loadTwh: load / 1e6,
  };
}

let rememberedRange: RangeKey = "jahr";

export function Energy({ data }: { data: Payload }) {
  const s = data.smard;
  const [range, setRangeState] = useState<RangeKey>(rememberedRange);
  const setRange = (r: RangeKey) => {
    rememberedRange = r;
    setRangeState(r);
  };
  const r = RANGES.find((x) => x.value === range) ?? RANGES[0];
  const whole = range === "jahr";
  const periodLabel = whole ? "2025" : `${r.label} 2025`;

  const stats = useMemo(() => (s ? rangeStats(s, r.months) : null), [s, r]);
  const year = useMemo(() => (s ? rangeStats(s, RANGES[0].months) : null), [s]);
  const allDays = useMemo(() => (s ? withRollingMean(s.daily) : []), [s]);
  const days = useMemo(() => allDays.filter((d) => r.months.includes(Number(d.day.slice(5, 7)))), [allDays, r]);
  const hi = whole ? null : r.months.map((m) => m - 1);

  const head = (
    <PageHead
      title="Strommarkt Deutschland 2025"
      lede="Offene SMARD-Daten, dieselbe SQL-Logik"
      action={s ? <Segmented id="range" label="Zeitraum" options={RANGES} value={range} onChange={setRange} /> : null}
    />
  );
  if (!s || !stats || !year) {
    return (
      <div className="space-y-5">
        {head}
        <Card>
          <EmptyState
            icon={Database}
            title="Keine Strommarktdaten"
            text="Die Datei data/smard/smard_hourly.csv fehlt. Mit scripts/fetch_smard.py einmal abrufen, dann pdc build."
          />
        </Card>
      </div>
    );
  }

  const inRange = (i: number) => r.months.includes(i + 1);
  const avgDelta = (100 * (stats.avg - year.avg)) / year.avg;
  const other = Math.max(0, stats.renew - stats.wind - stats.solar);
  const mix = [
    { key: "wind", label: "Wind", value: stats.wind, color: "var(--chart-1)", display: pct(stats.wind) },
    { key: "pv", label: "Photovoltaik", value: stats.solar, color: "var(--chart-2)", display: pct(stats.solar) },
    { key: "other", label: "Biomasse, Wasser, Sonstige", value: other, color: "var(--chart-3)", display: pct(other) },
    { key: "rest", label: "Nicht erneuerbar, Import", value: Math.max(0, 100 - stats.renew), color: "var(--rest)", display: pct(Math.max(0, 100 - stats.renew)) },
  ];

  const monthly = s.monthly.map((m, i) => ({
    month: MONTHS[i],
    i,
    wind: m.wind_share_pct,
    pv: m.solar_share_pct,
    other: Math.max(0, m.renewable_share_pct - m.wind_share_pct - m.solar_share_pct),
    renew: m.renewable_share_pct,
    price: m.avg_price_eur_mwh,
    negative: m.negative_price_hours,
  }));
  const buckets = s.buckets.map((b) => ({
    bucket: b.share_bucket_pct >= 100 ? "≥100" : `${b.share_bucket_pct}`,
    price: b.avg_price_eur_mwh,
    hours: b.hours,
    neg: b.negative_share_pct,
    raw: b.share_bucket_pct,
  }));

  return (
    <div className="space-y-5">
      {head}

      <div className="grid gap-5 xl:grid-cols-12">
        <HeroCard className="flex flex-col p-7 xl:col-span-8" data-testid="price-hero">
          <div className="flex items-center gap-3.5">
            <IconCircle icon={Activity} tone="hero" />
            <h2 className="min-w-0 flex-1 text-[16px] font-medium tracking-[-0.01em]">Ø Day-Ahead-Preis {periodLabel}</h2>
            <span className="hidden rounded-full bg-[var(--hero-inner)] px-3 py-1 text-[12.5px] text-[var(--hero-fg-2)] sm:inline">DE-LU</span>
          </div>
          <div className="mt-6 grid flex-1 gap-6 md:grid-cols-[minmax(0,0.85fr)_minmax(0,1.4fr)]">
            <div className="flex flex-col justify-end">
              <span className="flex items-center gap-2 text-[14px] text-[var(--hero-fg-2)]">
                {whole ? "Median" : "gegenüber dem Jahr"}
                <span className="num inline-flex items-center gap-1 rounded-full bg-[var(--hero-inner)] px-2.5 py-1 text-[12.5px] font-semibold text-[var(--hero-accent-2)]">
                  {whole ? (
                    `${two(s.overview.median_price_eur_mwh)} €`
                  ) : (
                    <>
                      {avgDelta <= 0 ? <TrendingDown className="size-3.5" aria-hidden="true" /> : <TrendingUp className="size-3.5" aria-hidden="true" />}
                      {signed(avgDelta, int)} %
                    </>
                  )}
                </span>
              </span>
              <span className="mt-2 flex items-baseline gap-2">
                <AnimatedNumber value={stats.avg} format={two} className="text-[60px] font-medium leading-none tracking-[-0.035em]" />
                <span className="text-[16px] text-[var(--hero-fg-2)]">€/MWh</span>
              </span>
              <div className="mt-5 flex gap-2">
                <HeroStat label="Tief" value={`${int(s.overview.min_price_eur_mwh)} €`} />
                <HeroStat label="Hoch" value={`${int(s.overview.max_price_eur_mwh)} €`} />
              </div>
            </div>
            <HeroBars
              compact
              label="Ø Preis je Monat"
              height={232}
              dim={(i) => !inRange(i)}
              bars={s.monthly.map((m, i) => ({
                key: m.month,
                label: MONTHS[i],
                value: m.avg_price_eur_mwh,
                display: int(m.avg_price_eur_mwh),
                color: "var(--hero-accent)",
              }))}
            />
          </div>
        </HeroCard>
        <Card className="xl:col-span-4">
          <CardHeader icon={Leaf} title={`Strommix ${periodLabel}`} />
          <CardBody>
            <Donut
              label="Ringdiagramm: Strommix nach Quelle"
              parts={mix}
              center={stats.renew}
              centerLabel="erneuerbar"
              format={(v) => `${one(v)} %`}
              size={196}
            />
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          index={0}
          icon={TrendingDown}
          label="Negative Preise"
          value={stats.negative}
          format={int}
          unit={`von ${int(stats.hours)}`}
          viz={<MiniBars values={s.monthly.map((m) => m.negative_price_hours)} highlight={hi} label="Negative Stunden je Monat" />}
          foot={<Badge>{pct((100 * stats.negative) / stats.hours)} der Stunden</Badge>}
        />
        <KpiCard
          index={1}
          icon={Leaf}
          label="Erneuerbar"
          value={stats.renew}
          format={one}
          unit="%"
          viz={<Sparkline values={s.monthly.map((m) => m.renewable_share_pct)} highlight={hi} label="Anteil Erneuerbarer je Monat" />}
          foot={
            <Badge tone="accent">
              <Wind aria-hidden="true" />
              Wind {pct(stats.wind)}
            </Badge>
          }
        />
        <KpiCard
          index={2}
          icon={Sun}
          label="Photovoltaik"
          value={stats.solar}
          format={one}
          unit="%"
          viz={<MiniBars values={s.monthly.map((m) => m.solar_share_pct)} highlight={hi} label="Anteil Photovoltaik je Monat" />}
        />
        <KpiCard
          index={3}
          icon={Plug}
          label="Verbrauch"
          value={stats.loadTwh}
          format={one}
          unit="TWh"
          viz={<MiniBars values={s.monthly.map((m) => m.load_mwh)} highlight={hi} fromMin label="Verbrauch je Monat" />}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-12">
        <Card className="xl:col-span-8">
          <CardHeader
            icon={LineChartIcon}
            title={`Preisverlauf ${periodLabel}`}
            action={
              <Legend
                items={[
                  { name: "7-Tage-Mittel", color: "var(--chart-1)" },
                  { name: "Tageswert", color: "var(--day-band)" },
                  { name: `Ø ${two(stats.avg)}`, color: "var(--text-3)", dashed: true },
                ]}
              />
            }
          />
          <CardBody>
            <PriceArea key={range} days={days} average={stats.avg} height={320} />
          </CardBody>
        </Card>
        <Card className="xl:col-span-4">
          <CardHeader icon={BarChart3} title="Preis nach Anteil Erneuerbarer" />
          <CardBody>
            <Columns
              label="Säulen: Durchschnittspreis je Klasse des Anteils Erneuerbarer"
              data={buckets}
              xKey="bucket"
              height={320}
              barSize={18}
              radius={9}
              zeroLine
              yFormat={(v) => int(v)}
              series={[{ key: "price", name: "Ø Preis", color: "var(--chart-1)" }]}
              colorOf={(b) => (b.price < 0 ? "var(--chart-2)" : "var(--chart-1)")}
              tooltip={(b) => (
                <TipCard
                  title={`Erneuerbare ${b.raw >= 100 ? "ab 100" : `${b.raw - 10} bis ${b.raw}`} % der Last`}
                  rows={[
                    { label: "Ø Preis", value: `${two(b.price)} €/MWh`, color: b.price < 0 ? "var(--chart-2)" : "var(--chart-1)", strong: true },
                    { label: "Stunden", value: int(b.hours) },
                    { label: "davon negativ", value: pct(b.neg) },
                  ]}
                />
              )}
            />
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-12">
        <Card className="xl:col-span-5">
          <CardHeader
            icon={Wind}
            title="Erneuerbare je Monat"
            action={
              <Legend
                items={[
                  { name: "Wind", color: "var(--chart-1)" },
                  { name: "PV", color: "var(--chart-2)" },
                  { name: "Sonstige", color: "var(--chart-3)" },
                ]}
              />
            }
          />
          <CardBody>
            <Columns
              label="Gestapelte Säulen: Anteil Erneuerbarer je Monat nach Quelle"
              data={monthly}
              xKey="month"
              height={300}
              barSize={20}
              radius={10}
              yFormat={(v) => `${int(v)} %`}
              dim={(i) => !inRange(i)}
              series={[
                { key: "wind", name: "Wind", color: "var(--chart-1)" },
                { key: "pv", name: "Photovoltaik", color: "var(--chart-2)" },
                { key: "other", name: "Sonstige", color: "var(--chart-3)" },
              ]}
              tooltip={(m) => (
                <TipCard
                  title={`${MONTHS_LONG[m.i]} 2025`}
                  rows={[
                    { label: "Wind", value: pct(m.wind), color: "var(--chart-1)" },
                    { label: "Photovoltaik", value: pct(m.pv), color: "var(--chart-2)" },
                    { label: "Sonstige", value: pct(m.other), color: "var(--chart-3)" },
                    { label: "Erneuerbar gesamt", value: pct(m.renew), strong: true },
                  ]}
                  foot={`Ø ${two(m.price)} €/MWh, ${int(m.negative)} Stunden unter null`}
                />
              )}
            />
          </CardBody>
        </Card>
        <Card className="xl:col-span-7">
          <CardHeader icon={Grid3x3} title="Preis nach Tagesstunde" />
          <CardBody>
            <Heatmap smard={s} inRange={inRange} />
          </CardBody>
        </Card>
      </div>

      <p className="px-1 text-[12.5px] text-fg-3">
        Quelle:{" "}
        <a className="font-medium text-accent-text underline-offset-2 hover:underline" href={s.sourceUrl} rel="noopener noreferrer" target="_blank">
          {s.source}
        </a>
        , Lizenz{" "}
        <a className="font-medium text-accent-text underline-offset-2 hover:underline" href={s.licenseUrl} rel="noopener noreferrer" target="_blank">
          {s.license}
        </a>
        , Kennzahlen eigene Berechnung
      </p>
    </div>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-[16px] bg-[var(--hero-inner)] px-3.5 py-2">
      <span className="block text-[12px] text-[var(--hero-fg-2)]">{label}</span>
      <span className="num block text-[15px] font-medium text-[var(--hero-fg)]">{value}</span>
    </span>
  );
}
