// Shape of data.json as written by `pdc build` (dashboard/__init__.py).
export interface Finding {
  label: string;
  detail: string;
  field: string;
}
export interface Mark {
  s: number;
  e: number;
  k: string;
  n: string;
}
export interface Product {
  row: number;
  sku: string | null;
  supplier: string;
  ean: string | null;
  name: string | null;
  brand: string | null;
  category: string | null;
  categorySource: string | null;
  variant: string | null;
  nominal: number | null;
  length: number | null;
  weight: number | null;
  material: string | null;
  pieces: number | null;
  price: number | null;
  title: string;
  description: string;
  marks: Record<string, Mark[]>;
  facts: Record<string, unknown>;
  raw: Record<string, string>;
  blocking: Finding[];
  notes: Finding[];
  missing: string[];
}
export interface Query {
  name: string;
  title: string;
  description: string;
  file: string;
  sql: string;
  columns: string[];
  rows: (string | number | null)[][];
}
export interface Monthly {
  month: string;
  avg_price_eur_mwh: number;
  renewable_share_pct: number;
  solar_share_pct: number;
  wind_share_pct: number;
  negative_price_hours: number;
  hours: number;
  price_sum: number;
  load_mwh: number;
  renewable_mwh: number;
  solar_mwh: number;
  wind_mwh: number;
}
export interface Daily {
  day: string;
  avg_price_eur_mwh: number;
  min_price_eur_mwh: number;
  max_price_eur_mwh: number;
  renewable_share_pct: number;
  negative_price_hours: number;
}
export interface Smard {
  overview: {
    first_day: string;
    last_day: string;
    hours: number;
    avg_price_eur_mwh: number;
    median_price_eur_mwh: number;
    negative_price_hours: number;
    min_price_eur_mwh: number;
    max_price_eur_mwh: number;
    renewable_share_pct: number;
    solar_share_pct: number;
    load_twh: number;
  };
  monthly: Monthly[];
  daily: Daily[];
  heatmap: { month: number; hour: number; avg_price_eur_mwh: number; negative_hours: number }[];
  buckets: { share_bucket_pct: number; hours: number; avg_price_eur_mwh: number; negative_share_pct: number }[];
  source: string;
  license: string;
  licenseUrl: string;
  sourceUrl: string;
}
export interface Payload {
  meta: {
    sourceFile: string;
    provider: string;
    rows: number;
    seconds: number;
    generatedAt: string;
    textModel: string;
    classifyModel: string;
    titleMax: number;
    descriptionMax: number;
  };
  pipeline: {
    read: number;
    dataBlocked: number;
    textWritten: number;
    textBlocked: number;
    released: number;
    classified: number;
  };
  overview: {
    articles: number;
    released: number;
    to_review: number;
    release_rate_pct: number;
    filled_before_pct: number;
    usable_before_pct: number;
    usable_released_pct: number;
    complete_articles_before_pct: number;
  };
  suppliers: {
    supplier: string;
    articles: number;
    blocked: number;
    error_rate_pct: number;
    top_reason: string | null;
    top_reason_count: number | null;
  }[];
  reasons: {
    reason: string;
    code: string;
    findings: number;
    articles: number;
    share_of_all_pct: number;
    stage: "Daten" | "Text";
  }[];
  fields: { field: string; required_in: number; filled_pct: number; usable_pct: number }[];
  matrix: { supplier: string; field: string; field_order: number; usable_pct: number }[];
  autoFixes: { label: string; count: number }[];
  review: Product[];
  released: Product[];
  queries: Query[];
  smard: Smard | null;
}

/** Stage at which a review article failed: data checks first, then the text check. */
export const stageOf = (p: Product): "Daten" | "Text" =>
  p.blocking.some((b) => b.field !== "Text") ? "Daten" : "Text";
