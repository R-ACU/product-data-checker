import { useEffect, useState } from "react";
import { FIRMS, currentFirm, type Route } from "./theme";

export const ROUTES: Route[] = ["uebersicht", "pruefen", "freigegeben", "sql", "strommarkt"];
export const TITLES: Record<Route, string> = {
  uebersicht: "Übersicht",
  pruefen: "Prüfliste",
  freigegeben: "Freigegeben",
  sql: "SQL-Kennzahlen",
  strommarkt: "Strommarkt",
};

export interface Location {
  route: Route | null; // null: unknown route, the 404 view
  params: URLSearchParams;
}

export function parseHash(): Location {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [key, query = ""] = raw.split("?");
  const route = key || FIRMS[currentFirm()].firstRoute;
  return {
    route: (ROUTES as string[]).includes(route) ? (route as Route) : null,
    params: new URLSearchParams(query),
  };
}

export function useHashRoute(): Location {
  const [loc, setLoc] = useState(parseHash);
  useEffect(() => {
    const on = () => setLoc(parseHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return loc;
}
