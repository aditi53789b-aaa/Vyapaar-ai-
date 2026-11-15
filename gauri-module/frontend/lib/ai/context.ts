/**
 * Conversational context for multi-turn voice entry.
 *
 *   "Ramesh ko 500 udhaar diya"  -> credit_given, Ramesh, 500
 *   "aur 200 de diya"            -> same party + intent, amount 200        (continuation)
 *   "usko 100 wapas mile"        -> party resolved from the previous turn   (pronoun)
 *   "paanch sau" after "Kitne rupaye?"  -> fills the missing amount         (clarification)
 *
 * Pure functions: the caller keeps the ConversationContext in component state.
 */
import type { Language, TransactionIntent } from "./types";
import { tokenize } from "./numbers";
import { hasPronoun } from "./ruleParser";
import { missingFields, recheck, type Missing } from "./sanity";

export interface Turn {
  text: string;
  intent: TransactionIntent;
}
export interface ConversationContext {
  turns: Turn[];
}

export const MAX_TURNS = 6;
export const emptyContext = (): ConversationContext => ({ turns: [] });

export function pushTurn(ctx: ConversationContext, text: string, intent: TransactionIntent): ConversationContext {
  return { turns: [...ctx.turns, { text, intent }].slice(-MAX_TURNS) };
}

export function pendingOf(ctx: ConversationContext): { intent: TransactionIntent; missing: Missing[] } | null {
  const last = ctx.turns[ctx.turns.length - 1];
  if (!last) return null;
  const missing = missingFields(last.intent);
  return missing.length ? { intent: last.intent, missing } : null;
}

const CONTINUATION = new Set(["aur", "phir", "bhi", "again", "more", "also", "और", "फिर", "भी"]);
const FILLER = new Set(["ko", "se", "ne", "ka", "ki", "ke", "को", "से", "ने", "का", "की", "के", "hai", "hain", "naam", "name"]);

const lastWhere = (ctx: ConversationContext, f: (t: Turn) => boolean): Turn | undefined =>
  [...ctx.turns].reverse().find(f);

export function resolveTurn(
  text: string,
  parsed: TransactionIntent,
  ctx: ConversationContext
): { intent: TransactionIntent; notes: string[] } {
  const toks = tokenize(text);
  const notes: string[] = [];
  const pending = pendingOf(ctx);
  const isFreshEntry = parsed.intent !== "unknown" && parsed.amount != null;

  // 1) answer to a clarification question
  if (pending && !isFreshEntry && toks.length <= 5) {
    const merged: TransactionIntent = { ...pending.intent };
    let used = false;
    if (pending.missing.includes("amount") && parsed.amount != null) {
      merged.amount = parsed.amount;
      used = true;
    }
    if (pending.missing.includes("party") && parsed.amount == null && toks.length <= 3) {
      const words = toks.filter((t) => /^[\p{L}\p{M}]+$/u.test(t.raw) && !FILLER.has(t.n)).map((t) => t.raw);
      if (words.length) {
        merged.party = words.map((w) => (/^[a-z]/i.test(w) ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w)).join(" ");
        used = true;
      }
    }
    if (pending.missing.includes("intent") && parsed.intent !== "unknown") {
      merged.intent = parsed.intent;
      if (!merged.party && parsed.party) merged.party = parsed.party;
      if (merged.payment_mode === "unknown") merged.payment_mode = parsed.payment_mode;
      used = true;
    }
    if (used) {
      notes.push("answered previous question");
      return { intent: recheck({ ...merged, confidence: Math.max(merged.confidence, 0.7) }), notes };
    }
  }

  let out: TransactionIntent = { ...parsed };

  // 2) continuation: "aur 200 de diya"
  if (out.intent === "unknown" && out.amount != null && toks.some((t) => CONTINUATION.has(t.n))) {
    const prev = lastWhere(ctx, (t) => t.intent.intent !== "unknown" && t.intent.intent !== "query");
    if (prev) {
      out = {
        ...prev.intent,
        amount: out.amount,
        items: [],
        date: out.date ?? prev.intent.date,
        confidence: Math.min(prev.intent.confidence, 0.7),
        needs_confirmation: false,
      };
      notes.push(`continued previous entry (${prev.intent.intent})`);
    }
  }

  // 3) pronoun / same party
  if (!out.party && hasPronoun(toks)) {
    const prev = lastWhere(ctx, (t) => !!t.intent.party);
    if (prev) {
      out.party = prev.intent.party;
      notes.push(`party taken from previous entry (${prev.intent.party})`);
    }
  }

  return { intent: recheck(out), notes };
}

const QUESTIONS: Record<string, Record<Missing, string>> = {
  hinglish: {
    amount: "Kitne rupaye?",
    party: "Kiska naam hai? (kisko/kisse)",
    intent: "Yeh bikri hai, kharid, kharcha ya udhaar?",
  },
  hi: {
    amount: "कितने रुपये?",
    party: "किसका नाम है?",
    intent: "यह बिक्री है, खरीद, खर्चा या उधार?",
  },
  en: {
    amount: "How much (in rupees)?",
    party: "Who is the customer/supplier?",
    intent: "Is this a sale, purchase, expense or credit?",
  },
};

/** The one follow-up question to ask next (most important missing field first), or null. */
export function nextQuestion(intent: TransactionIntent, language: Language = "hinglish"): string | null {
  const missing = missingFields(intent);
  if (!missing.length) return null;
  const order: Missing[] = ["intent", "amount", "party"];
  const first = order.find((m) => missing.includes(m));
  if (!first) return null;
  return (QUESTIONS[language] ?? QUESTIONS.hinglish)[first];
}
