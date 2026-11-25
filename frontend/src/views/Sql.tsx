import { Check, ChevronDown, Copy, FileCode2 } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { Segmented } from "@/components/Segmented";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, Inset } from "@/components/ui/card";
import { Tip } from "@/components/ui/tooltip";
import { fmt1, fmtInt } from "@/lib/format";
import { EASE_OUT } from "@/lib/motion";
import type { Payload, Query } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PageHead } from "./PageHead";

type Group = "quality" | "smard";
let rememberedGroup: Group = "quality";

const KEYWORDS = new Set(
  "select from where group by order with as join left inner on and or not null is case when then else end over partition limit having distinct union all asc desc count sum avg min max round cast filter coalesce in between true false interval date extract hour month nullif greatest least row_number lag lead".split(" "),
);

/** SQL as coloured spans. Plain text nodes only, never HTML. */
function highlight(sql: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(--[^\n]*)|('(?:[^']|'')*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(\s+|[^\sA-Za-z0-9_'-]+|-)/g;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(sql))) {
    const [t, cm, str, nm, word] = m;
    if (cm) out.push(<span key={k++} className="text-[var(--code-cm)]">{t}</span>);
    else if (str) out.push(<span key={k++} className="text-[var(--code-str)]">{t}</span>);
    else if (nm) out.push(<span key={k++} className="text-[var(--code-nm)]">{t}</span>);
    else if (word && KEYWORDS.has(word.toLowerCase())) {
      const fn = sql[re.lastIndex] === "(";
      out.push(
        <span key={k++} className={fn ? "text-[var(--code-fn)]" : "font-medium text-[var(--code-kw)]"}>
          {t}
        </span>,
      );
    } else out.push(t);
  }
  return out;
}

const cellText = (v: string | number | null) =>
  v == null ? "" : typeof v === "number" ? (Number.isInteger(v) ? fmtInt.format(v) : fmt1.format(v)) : String(v);

function QueryCard({ q, index }: { q: Query; index: number }) {
  const [showSql, setShowSql] = useState(index === 0);
  const [all, setAll] = useState(false);
  const [copied, setCopied] = useState(false);
  const rows = all ? q.rows : q.rows.slice(0, 8);
  const numeric = q.columns.map((_, ci) => q.rows.length > 0 && typeof q.rows[0][ci] === "number");

  const copy = () => {
    navigator.clipboard?.writeText(q.sql).then(
      () => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1400);
      },
      () => undefined,
    );
  };

  return (
    <Card className="query-card">
      <CardHeader
        icon={FileCode2}
        title={q.title}
        description={q.description}
        action={
          <>
            <Badge className="hidden font-mono md:inline-flex">{q.file}</Badge>
            <Tip label={copied ? "Kopiert" : "SQL kopieren"}>
              <Button variant="ghost" size="icon" className="bg-muted" onClick={copy} aria-label="SQL kopieren">
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span
                    key={copied ? "ok" : "copy"}
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.6 }}
                    transition={{ type: "spring", duration: 0.25, bounce: 0.2 }}
                    className="grid place-items-center"
                  >
                    {copied ? <Check className="text-good" /> : <Copy />}
                  </motion.span>
                </AnimatePresence>
              </Button>
            </Tip>
          </>
        }
      />
      <CardBody className="space-y-3">
        <Inset className="overflow-hidden">
          <button
            type="button"
            onClick={() => setShowSql((v) => !v)}
            aria-expanded={showSql}
            className="flex w-full items-center gap-2 px-5 py-3 text-left text-[13px] font-medium text-fg-2 transition-colors hover:text-fg"
          >
            <ChevronDown className={cn("size-4 transition-transform duration-200", showSql ? "rotate-0" : "-rotate-90")} aria-hidden="true" />
            {showSql ? "SQL ausblenden" : "SQL anzeigen"}
            <span className="num ml-auto text-[12px] font-normal text-fg-3">{q.sql.split("\n").length} Zeilen</span>
          </button>
          <AnimatePresence initial={false}>
            {showSql ? (
              <motion.div
                key="sql"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.28, ease: EASE_OUT }}
                className="overflow-hidden"
              >
                <pre className="sql max-h-[320px] overflow-auto bg-[var(--code-bg)] px-5 py-4 font-mono text-[12.5px] leading-relaxed text-[var(--code-text)]">
                  <code>{highlight(q.sql)}</code>
                </pre>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </Inset>
        <div className="overflow-x-auto">
          <table className="result w-full border-separate border-spacing-y-1 text-[13px]">
            <thead>
              <tr className="text-[12px] text-fg-3">
                {q.columns.map((c, ci) => (
                  <th key={c} className={cn("whitespace-nowrap px-3 py-1.5 font-mono font-normal", numeric[ci] ? "text-right" : "text-left")}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri} className="transition-colors hover:[&>td]:bg-muted [&>td:first-child]:rounded-l-full [&>td:last-child]:rounded-r-full">
                  {row.map((v, ci) => (
                    <td key={ci} className={cn("whitespace-nowrap px-3 py-1.5", numeric[ci] ? "num text-right text-fg" : "text-fg-2")}>
                      {cellText(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {q.rows.length > 8 ? (
          <Button variant="ghost" size="sm" onClick={() => setAll((v) => !v)} className="bg-muted">
            {all ? "Weniger zeigen" : `Alle ${fmtInt.format(q.rows.length)} Zeilen zeigen`}
          </Button>
        ) : null}
      </CardBody>
    </Card>
  );
}

export function Sql({ data }: { data: Payload }) {
  const [group, setGroupState] = useState<Group>(rememberedGroup);
  const setGroup = (g: Group) => {
    rememberedGroup = g;
    setGroupState(g);
  };
  const queries = data.queries.filter((q) => (group === "smard" ? q.name.startsWith("smard_") : !q.name.startsWith("smard_")));
  const hasSmard = data.queries.some((q) => q.name.startsWith("smard_"));
  return (
    <div className="space-y-5">
      <PageHead
        title="SQL-Kennzahlen"
        lede="Jede Zahl im Dashboard, als DuckDB-Abfrage aus sql/"
        action={
          hasSmard ? (
            <Segmented
              id="sql-group"
              label="Gruppe"
              value={group}
              onChange={setGroup}
              options={[
                { value: "quality" as Group, label: "Datenqualität" },
                { value: "smard" as Group, label: "Strommarkt" },
              ]}
            />
          ) : null
        }
      />
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={group}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4, transition: { duration: 0.12 } }}
          transition={{ duration: 0.25, ease: EASE_OUT }}
          className="space-y-5"
        >
          {queries.map((q, i) => (
            <QueryCard key={q.name} q={q} index={i} />
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
