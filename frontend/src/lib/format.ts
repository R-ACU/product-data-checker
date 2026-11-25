// German number formats, one place. Every number in the UI goes through these.
export const fmtInt = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });
export const fmt1 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const fmt2 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const int = (v: number) => fmtInt.format(Math.round(v));
export const one = (v: number) => fmt1.format(v);
export const two = (v: number) => fmt2.format(v);
export const pct = (v: number | null | undefined) => (v == null ? "–" : `${fmt1.format(v)} %`);
/** Signed with a real minus sign. */
export const signed = (v: number, f: (n: number) => string = one) =>
  `${v > 0 ? "+" : v < 0 ? "−" : "±"}${f(Math.abs(v))}`;

export const MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
export const MONTHS_LONG = [
  "Januar",
  "Februar",
  "März",
  "April",
  "Mai",
  "Juni",
  "Juli",
  "August",
  "September",
  "Oktober",
  "November",
  "Dezember",
];
