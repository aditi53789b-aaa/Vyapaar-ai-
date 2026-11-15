import type { TransactionIntent } from "./types";

export const CREDIT_INTENTS = ["credit_given", "credit_received", "payment_received", "payment_made"] as const;

export type Missing = "amount" | "party" | "intent";

export function missingFields(t: TransactionIntent): Missing[] {
  const m: Missing[] = [];
  if (t.intent === "unknown") m.push("intent");
  if (t.intent !== "query" && t.amount == null) m.push("amount");
  if ((CREDIT_INTENTS as readonly string[]).includes(t.intent) && !t.party) m.push("party");
  return m;
}

/** Deterministic guard-rails on top of any parser (LLM or rules). Never lowers an existing flag. */
export function sanityCheck(t: TransactionIntent): TransactionIntent {
  const out: TransactionIntent = { ...t, items: t.items ?? [] };
  if (out.amount == null && out.items.length) {
    const total = out.items.reduce((s, i) => s + (i.quantity ?? 0) * (i.unit_price ?? 0), 0);
    if (total > 0) out.amount = total;
  }
  if (missingFields(out).length) out.needs_confirmation = true;
  if (out.amount != null && out.amount > 1_000_000) out.needs_confirmation = true; // likely mis-heard
  if (out.confidence < 0.6) out.needs_confirmation = true;
  return out;
}

/** Recompute the confirmation flag from scratch (used after merging context). */
export function recheck(t: TransactionIntent): TransactionIntent {
  return sanityCheck({ ...t, needs_confirmation: false });
}
