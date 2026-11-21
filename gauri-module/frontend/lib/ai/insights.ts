import { generateText } from "ai";
import { getChatModel, hasLLM } from "./model";
import type { LedgerStats } from "./ledgerStats";
import type { Insight } from "./insightRules";

const SYSTEM = `You are "Vyapaar Sathi", a friendly accountant for a small Indian shopkeeper.
You receive FACTS computed from the merchant's ledger (JSON). Write a short weekly summary.

Rules:
- Use ONLY numbers that appear in the FACTS. Never invent, estimate or round differently.
- Reply in {language}. Simple words, short sentences. Hinglish = Roman-script Hindi mixed with English.
- Format: 3 to 4 bullet points, then one line starting with "Kal ka kaam:" (or "Tomorrow:" in English) giving ONE concrete action.
- If CHANGES SINCE LAST CHECK is non-empty, mention the most important change in the first bullet.
- No greetings, no markdown headings, no disclaimers about being an AI.`;

/** Returns null when no LLM is configured or the call fails: the UI then just shows the rule-based insights. */
export async function narrateInsights(
  stats: LedgerStats,
  rules: Insight[],
  opts: { language?: string; changes?: string[] } = {}
): Promise<string | null> {
  if (!hasLLM()) return null;
  try {
    const { text } = await generateText({
      model: getChatModel(),
      system: SYSTEM.replace("{language}", opts.language ?? "hinglish"),
      temperature: 0.3,
      prompt:
        `FACTS:\n${JSON.stringify({ stats, insights: rules })}\n\n` +
        `CHANGES SINCE LAST CHECK:\n${(opts.changes ?? []).join("\n") || "(none)"}`,
    });
    return text.trim() || null;
  } catch (e) {
    console.warn("insight narration failed:", (e as Error).message);
    return null;
  }
}
