/** Plain TypeScript types shared by the pure (dependency-free) modules. */

export const INTENTS = [
  "sale",
  "purchase",
  "expense",
  "credit_given",
  "credit_received",
  "payment_received",
  "payment_made",
  "query",
  "unknown",
] as const;
export type Intent = (typeof INTENTS)[number];

export const PAYMENT_MODES = ["cash", "upi", "card", "credit", "unknown"] as const;
export type PaymentMode = (typeof PAYMENT_MODES)[number];

export interface TransactionItem {
  name: string;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
}

export interface TransactionIntent {
  intent: Intent;
  amount: number | null;
  party: string | null;
  items: TransactionItem[];
  payment_mode: PaymentMode;
  date: string | null; // ISO YYYY-MM-DD
  notes: string | null;
  confidence: number; // 0..1
  needs_confirmation: boolean;
}

export type Language = "hinglish" | "hi" | "en" | "pa" | "mr" | "ta" | string;
