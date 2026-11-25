// Accent per target company. The slug comes from public/boot.js, which checks
// ?firma= against the same fixed list before the first paint; here we only read the
// attribute it set. Labels reach the DOM as text, never as markup.
export type Firm = "neutral" | "gedore" | "pohl" | "amalock" | "metergrid";
export type Route = "uebersicht" | "pruefen" | "freigegeben" | "sql" | "strommarkt";

export const FIRMS: Record<Firm, { label: string | null; firstRoute: Route }> = {
  neutral: { label: null, firstRoute: "uebersicht" },
  gedore: { label: "GEDORE Gruppe", firstRoute: "uebersicht" },
  pohl: { label: "POHL Handels GmbH", firstRoute: "uebersicht" },
  amalock: { label: "AMALOCK", firstRoute: "uebersicht" },
  metergrid: { label: "metergrid", firstRoute: "strommarkt" },
};

export function currentFirm(): Firm {
  const slug = document.documentElement.getAttribute("data-theme");
  return slug && Object.prototype.hasOwnProperty.call(FIRMS, slug) ? (slug as Firm) : "neutral";
}

export type Mode = "light" | "dark";
export const currentMode = (): Mode =>
  document.documentElement.getAttribute("data-mode") === "dark" ? "dark" : "light";

export function setMode(mode: Mode) {
  const root = document.documentElement;
  root.classList.add("mode-switching");
  root.setAttribute("data-mode", mode);
  root.style.colorScheme = mode;
  try {
    localStorage.setItem("pdc-mode", mode);
  } catch {
    /* storage blocked: the choice is just not remembered */
  }
  window.setTimeout(() => root.classList.remove("mode-switching"), 320);
}
