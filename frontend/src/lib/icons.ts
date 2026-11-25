import {
  ArrowRightLeft,
  Asterisk,
  BadgeAlert,
  Ban,
  Barcode,
  Binary,
  CaseSensitive,
  CopyX,
  Drill,
  EyeOff,
  FileX,
  Hash,
  Nut,
  Package,
  Ruler,
  RulerDimensionLine,
  ScanBarcode,
  Scissors,
  Screw,
  ShieldCheck,
  Sparkles,
  SquareFunction,
  Tags,
  ToolCase,
  Wrench,
  type LucideIcon,
} from "lucide-react";

// One picture per reason, fix and category, so lists read at a glance. Unknown keys
// fall back to a neutral icon; the labels themselves still come from data.json.
const REASON: Record<string, LucideIcon> = {
  MISSING_DIMENSION: Ruler,
  MISSING_REQUIRED: Asterisk,
  EAN_CHECKSUM: Barcode,
  DUPLICATE_EAN: CopyX,
  UNREADABLE_VALUE: EyeOff,
  TEXT_NUMBER_MISMATCH: Hash,
  EAN_SCIENTIFIC: Binary,
  TEXT_UNSUPPORTED_CLAIM: BadgeAlert,
  TEXT_RULE_VIOLATION: Ban,
  EAN_FORMAT: ScanBarcode,
  CATEGORY_UNCLEAR: Tags,
  TEXT_UNAVAILABLE: FileX,
};

const FIX: Record<string, LucideIcon> = {
  "Einheit umgerechnet": ArrowRightLeft,
  "Schreibweise vereinheitlicht": CaseSensitive,
  "Einheit angenommen": RulerDimensionLine,
  "Kategorie vom Modell eingeordnet": Tags,
  "Formel neutralisiert": SquareFunction,
  "Anweisung im Lieferantentext ignoriert": ShieldCheck,
};

const CATEGORY: Record<string, LucideIcon> = {
  Bohrer: Drill,
  Steckschlüsseleinsätze: Nut,
  Maulschlüssel: Wrench,
  Zangen: Scissors,
  Schraubendreher: Screw,
  "Bit-Sets": ToolCase,
};

export const reasonIcon = (code: string): LucideIcon => REASON[code] ?? BadgeAlert;
export const fixIcon = (label: string): LucideIcon => FIX[label] ?? Sparkles;
export const categoryIcon = (category: string | null): LucideIcon => (category && CATEGORY[category]) || Package;
