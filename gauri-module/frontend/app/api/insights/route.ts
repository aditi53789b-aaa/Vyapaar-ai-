import { NextResponse } from "next/server";
import { z } from "zod";
import { INTENTS, PAYMENT_MODES } from "@/lib/ai/types";
import { computeStats, type LedgerTxn } from "@/lib/ai/ledgerStats";
import { changesSince, ruleInsights, type InsightLang } from "@/lib/ai/insightRules";
import { narrateInsights } from "@/lib/ai/insights";

export const runtime = "nodejs";

const ISO = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

const Body = z.object({
  transactions: z
    .array(
      z.object({
        id: z.union([z.string(), z.number()]).optional(),
        intent: z.enum(INTENTS),
        amount: z.number().nullable(),
        party: z.string().max(80).nullable().optional(),
        date: ISO,
        payment_mode: z.enum(PAYMENT_MODES).optional(),
      })
    )
    .max(5000),
  asOf: ISO.optional(),
  /** date of the previous insight run; stats for that date are recomputed so the model can describe what changed */
  previousAsOf: ISO.optional(),
  language: z.string().max(20).default("hinglish"),
});

export async function POST(req: Request) {
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  const { transactions, asOf, previousAsOf, language } = parsed.data;

  const txns = transactions as LedgerTxn[];
  const stats = computeStats(txns, asOf);
  const lang: InsightLang = language === "en" ? "en" : "hinglish";
  const insights = ruleInsights(stats, lang);
  const changes =
    previousAsOf && previousAsOf < stats.asOf ? changesSince(computeStats(txns, previousAsOf), stats, lang) : [];

  const narrative = await narrateInsights(stats, insights, { language, changes });
  return NextResponse.json({ stats, insights, changes, narrative });
}
