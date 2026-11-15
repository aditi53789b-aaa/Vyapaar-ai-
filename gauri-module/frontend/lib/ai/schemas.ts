import { z } from "zod";
import { INTENTS, PAYMENT_MODES, type TransactionIntent } from "./types";

export type { TransactionIntent } from "./types";

// NOTE: no .default()/.min()/.max() on purpose. OpenAI strict structured-output mode and several
// Llama hosts reject those keywords. Ranges are enforced in code (sanity.ts / intent.ts) instead.

export const TransactionItemSchema = z.object({
  name: z.string(),
  quantity: z.number().nullable(),
  unit: z.string().nullable().describe("kg, g, litre, piece, dozen, packet..."),
  unit_price: z.number().nullable(),
});

/** Structured JSON block produced from a spoken/typed ledger entry. */
export const TransactionIntentSchema = z.object({
  intent: z
    .enum(INTENTS)
    .describe(
      "sale=goods sold for cash/UPI; purchase=stock bought; expense=rent/electricity/etc; credit_given=sold on udhaar (customer owes merchant); credit_received=bought on udhaar (merchant owes supplier); payment_received=customer paid old dues; payment_made=merchant paid supplier dues; query=asking a question about the ledger"
    ),
  amount: z.number().nullable().describe("Total amount in INR. null if not stated."),
  party: z.string().nullable().describe("Customer / supplier name, if mentioned"),
  items: z.array(TransactionItemSchema),
  payment_mode: z.enum(PAYMENT_MODES),
  date: z.string().nullable().describe("ISO date YYYY-MM-DD. Resolve 'kal', 'parso', 'aaj' against today's date."),
  notes: z.string().nullable(),
  confidence: z.number().describe("Confidence in this parse, 0 to 1"),
  needs_confirmation: z.boolean().describe("true if amount/party/intent is missing or ambiguous"),
}) satisfies z.ZodType<TransactionIntent>;

export const HistoryTurnSchema = z.object({
  text: z.string().max(500),
  intent: TransactionIntentSchema,
});

export const ParseRequestSchema = z.object({
  text: z.string().min(1).max(1000),
  language: z.string().max(20).optional(), // "hi", "pa", "ta", "hinglish"
  today: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  /** previous turns of this entry session (oldest first); enables pronouns, "aur 200", follow-up answers */
  history: z.array(HistoryTurnSchema).max(6).optional(),
});
