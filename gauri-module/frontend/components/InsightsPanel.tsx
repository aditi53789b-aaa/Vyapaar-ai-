"use client";
import { useMemo, useState } from "react";
import { computeStats, type LedgerTxn } from "@/lib/ai/ledgerStats";
import { ruleInsights, type InsightLang } from "@/lib/ai/insightRules";
import { todayISO } from "@/lib/ai/dates";

const KEY = "vs_insights_last_asof";
const read = () => { try { return localStorage.getItem(KEY) ?? undefined; } catch { return undefined; } };
const write = (v: string) => { try { localStorage.setItem(KEY, v); } catch { /* private mode */ } };

const TONE = { warn: "border-red-300 bg-red-50", good: "border-emerald-300 bg-emerald-50", info: "border-slate-200" } as const;

/**
 * Weekly business insights. Rule-based cards render instantly and offline; "AI summary" adds a
 * narrated version (compared with the previous check) when online.
 */
export default function InsightsPanel({ transactions, language = "hinglish" }: { transactions: LedgerTxn[]; language?: string }) {
  const lang: InsightLang = language === "en" ? "en" : "hinglish";
  const asOf = todayISO();
  const insights = useMemo(() => ruleInsights(computeStats(transactions, asOf), lang), [transactions, asOf, lang]);

  const [narrative, setNarrative] = useState<string | null>(null);
  const [changes, setChanges] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function summarise() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch("/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transactions, asOf, previousAsOf: read(), language }),
      });
      if (!res.ok) throw new Error("Insights unavailable");
      const data = await res.json();
      setNarrative(data.narrative);
      setChanges(data.changes ?? []);
      if (!data.narrative) setErr("AI summary is not configured; showing rule-based insights only.");
      write(asOf);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Is hafte ka hisaab</h3>
        <button className="rounded-md border px-3 py-1 text-sm disabled:opacity-50" onClick={summarise} disabled={loading}>
          {loading ? "..." : "AI summary"}
        </button>
      </div>
      {err && <p className="text-sm text-amber-700">{err}</p>}
      {changes.length > 0 && (
        <ul className="list-disc pl-5 text-sm">
          {changes.map((c, i) => <li key={i}>{c}</li>)}
        </ul>
      )}
      {narrative && <div className="whitespace-pre-wrap rounded-md bg-muted p-3 text-sm">{narrative}</div>}
      <ul className="space-y-2">
        {insights.map((i) => (
          <li key={i.id} className={`rounded-md border p-3 text-sm ${TONE[i.severity]}`}>
            <div className="font-medium">{i.title}</div>
            <div>{i.detail}</div>
            {i.action && <div className="mt-1 text-xs font-medium">→ {i.action}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}
