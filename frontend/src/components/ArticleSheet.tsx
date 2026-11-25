import { CircleAlert, CircleCheck, FileText, Info, Sparkles, X } from "lucide-react";
import { Fragment, useRef, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Inset } from "@/components/ui/card";
import { useAnimatedDialog } from "@/components/HelpDialog";
import { fmt2, fmtInt } from "@/lib/format";
import { stageOf, type Mark, type Product } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Generated copy with its checks as <mark> spans. Text nodes only, never HTML. */
export function MarkedText({ text, marks }: { text: string; marks?: Mark[] }) {
  if (!text) return <span className="text-fg-3">Kein Text erzeugt.</span>;
  const sorted = [...(marks ?? [])].sort((a, b) => a.s - b.s);
  const out: ReactNode[] = [];
  let at = 0;
  sorted.forEach((m, i) => {
    if (m.s < at) return;
    if (m.s > at) out.push(text.slice(at, m.s));
    out.push(
      <mark key={i} className={m.k} title={m.n || TITLES[m.k] || undefined}>
        {text.slice(m.s, m.e)}
      </mark>,
    );
    at = m.e;
  });
  if (at < text.length) out.push(text.slice(at));
  return <>{out}</>;
}
const TITLES: Record<string, string> = {
  ok: "Zahl steht so in der Quelle",
  bad: "Zahl steht nicht in der Quelle",
  claim: "Eigenschaft ohne Beleg in der Quelle",
};

const num = (v: number | null, unit: string) => (v == null ? "" : `${fmt2.format(v).replace(/,00$/, "")} ${unit}`);

/** Supplier value next to the cleaned value, per field. */
function cleanedRows(p: Product): [string, string, string][] {
  const cleaned: Record<string, string> = {
    Artikelnummer: p.sku ?? "",
    Lieferant: p.supplier,
    EAN: p.ean ?? "",
    Bezeichnung: p.name ?? "",
    Marke: p.brand ?? "",
    Kategorie: p.category ? `${p.category}${p.categorySource === "Modell" ? " (vom Modell)" : ""}` : "",
    Ausführung: p.variant ?? "",
    Nennmaß: num(p.nominal, "mm"),
    Länge: num(p.length, "mm"),
    Gewicht: num(p.weight, "g"),
    Material: p.material ?? "",
    Teile: p.pieces == null ? "" : fmtInt.format(p.pieces),
    "EK netto": p.price == null ? "" : `${fmt2.format(p.price)} €`,
  };
  return Object.entries(p.raw)
    .filter(([k, v]) => k in cleaned && (String(v).trim() || cleaned[k]))
    .map(([k, v]) => [k, String(v), cleaned[k]]);
}

/** Length of a generated text against its limit, as a thin pill bar. */
function Meter({ len, max, label }: { len: number; max: number; label: string }) {
  return (
    <div className="min-w-0 flex-1">
      <div className="flex justify-between text-[12px] text-fg-3">
        <span>{label}</span>
        <span className="num">
          {len}/{max}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-track">
        <div className="h-full rounded-full bg-accent" style={{ width: `${Math.min(100, (100 * len) / max)}%` }} />
      </div>
    </div>
  );
}

export function ArticleSheet({
  product,
  kind,
  limits,
  onClose,
}: {
  product: Product | null;
  kind: "review" | "released";
  limits: { title: number; description: number };
  onClose: () => void;
}) {
  const ref = useAnimatedDialog(!!product, onClose);
  // keep showing the last article while the sheet slides out
  const last = useRef<Product | null>(product);
  if (product) last.current = product;
  const p = last.current;
  return (
    <dialog ref={ref} id="drawer" className="sheet" aria-labelledby="drawer-title">
      {p ? (
        <div className="flex h-full flex-col">
          <div className="flex items-start gap-3 px-7 pb-5 pt-6">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="font-mono">{p.sku || "ohne Nummer"}</Badge>
                {kind === "review" ? (
                  <Badge tone="danger">
                    <CircleAlert aria-hidden="true" />
                    {stageOf(p) === "Daten" ? "Datenprüfung" : "Textprüfung"}
                  </Badge>
                ) : (
                  <Badge tone="good">
                    <CircleCheck aria-hidden="true" />
                    Freigegeben
                  </Badge>
                )}
              </div>
              <h2 id="drawer-title" className="mt-3 text-[20px] font-medium leading-snug tracking-[-0.01em] text-fg">
                {p.title || p.name || "Ohne Bezeichnung"}
              </h2>
              <p className="mt-1 text-[13.5px] text-fg-3">{p.supplier}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label="Detail schließen" className="-mr-2 bg-muted">
              <X />
            </Button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-7 pb-8">
            {p.blocking.length ? (
              <Section icon={CircleAlert} title="Warum zur Prüfung" tone="danger">
                <ul className="space-y-2">
                  {p.blocking.map((b, i) => (
                    <li key={i} className="rounded-[16px] bg-card px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-fg">{b.label}</span>
                        <Badge>{b.field}</Badge>
                      </div>
                      <p className="mt-1 text-[13px] text-fg-2">{b.detail}</p>
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            <Section icon={FileText} title="Erzeugter Text">
              <div className="rounded-[16px] bg-card px-4 py-3.5">
                <div className="text-[12px] text-fg-3">Titel</div>
                <p className="marked mt-1 text-[14.5px] font-medium leading-relaxed text-fg">
                  <MarkedText text={p.title} marks={p.marks.title} />
                </p>
                <div className="mt-3 text-[12px] text-fg-3">Beschreibung</div>
                <p className="marked mt-1 text-[14px] leading-relaxed text-fg-2">
                  <MarkedText text={p.description} marks={p.marks.description} />
                </p>
              </div>
              {p.title ? (
                <div className="mt-3 flex gap-4 px-1">
                  <Meter len={p.title.length} max={limits.title} label="Titel" />
                  <Meter len={p.description.length} max={limits.description} label="Beschreibung" />
                </div>
              ) : null}
              <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 px-1 text-[12.5px] text-fg-3">
                <li className="flex items-center gap-1.5">
                  <mark className="ok legend px-1">6 mm</mark> aus der Quelle
                </li>
                <li className="flex items-center gap-1.5">
                  <mark className="bad legend px-1">12 mm</mark> nicht in der Quelle
                </li>
                <li className="flex items-center gap-1.5">
                  <mark className="claim legend px-1">rostfrei</mark> ohne Beleg
                </li>
              </ul>
            </Section>

            <Section icon={Info} title="Daten vom Lieferanten und bereinigt">
              <div className="overflow-hidden rounded-[16px] bg-card">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="text-[12px] text-fg-3">
                      <th className="px-4 pb-1.5 pt-3 font-normal">Feld</th>
                      <th className="px-4 pb-1.5 pt-3 font-normal">Lieferant</th>
                      <th className="px-4 pb-1.5 pt-3 font-normal">Bereinigt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cleanedRows(p).map(([field, raw, clean]) => {
                      const changed = raw.trim() !== clean.trim();
                      const flagged = p.blocking.some((b) => b.field === field);
                      return (
                        <tr key={field} className="align-top">
                          <td className="px-4 py-1.5 text-fg-3">{field}</td>
                          <td className="break-all px-4 py-1.5 font-mono text-[12.5px] text-fg-2">{raw.trim() ? raw : <span className="text-fg-3">leer</span>}</td>
                          <td className={cn("px-4 py-1.5", flagged ? "font-medium text-danger" : changed ? "font-medium text-fg" : "text-fg-2")}>
                            {clean || <span className={flagged ? "text-danger" : "text-fg-3"}>fehlt</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="h-2" />
              </div>
            </Section>

            {p.notes.length ? (
              <Section icon={Sparkles} title="Automatisch bereinigt">
                <ul className="space-y-1.5">
                  {p.notes.map((n, i) => (
                    <li key={i} className="flex flex-wrap items-baseline gap-x-2 rounded-[14px] bg-card px-4 py-2.5 text-[13px]">
                      <span className="font-medium text-fg">{n.label}</span>
                      <span className="text-fg-3">{n.field}</span>
                      <span className="w-full text-fg-2">{n.detail}</span>
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {p.missing.length ? (
              <Section icon={Info} title="Fehlt für einen Text">
                <p className="text-[13.5px] text-fg-2">
                  {p.missing.map((m, i) => (
                    <Fragment key={m}>
                      {i ? ", " : ""}
                      {m}
                    </Fragment>
                  ))}
                </p>
              </Section>
            ) : null}
          </div>
        </div>
      ) : null}
    </dialog>
  );
}

function Section({ icon: Icon, title, tone, children }: { icon: typeof Info; title: string; tone?: "danger"; children: ReactNode }) {
  return (
    <Inset className="p-4">
      <h3 className="mb-3 flex items-center gap-2.5 text-[14px] font-medium text-fg">
        <span className={cn("grid size-8 place-items-center rounded-full", tone === "danger" ? "bg-danger-soft text-danger" : "bg-card text-fg-2")}>
          <Icon className="size-4" aria-hidden="true" />
        </span>
        {title}
      </h3>
      {children}
    </Inset>
  );
}
