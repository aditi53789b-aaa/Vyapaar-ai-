/**
 * Rule-based business insights (works offline, no LLM). The LLM layer in insights.ts only rewrites
 * these facts in the merchant's language; it is never the source of a number.
 */
import type { LedgerStats } from "./ledgerStats";

export type InsightLang = "hinglish" | "en";
export interface Insight {
  id: string;
  severity: "good" | "info" | "warn";
  title: string;
  detail: string;
  action?: string;
}

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;
const pick = (lang: InsightLang, hinglish: string, en: string) => (lang === "en" ? en : hinglish);
const RANK = { warn: 0, good: 1, info: 2 } as const;

/** What changed since the previous insight run (the "loop": each run is compared with the last). */
export function changesSince(prev: LedgerStats, cur: LedgerStats, lang: InsightLang = "hinglish"): string[] {
  const out: string[] = [];
  const dRec = cur.receivables.total - prev.receivables.total;
  if (Math.abs(dRec) >= 100) {
    out.push(
      pick(
        lang,
        `Baaki udhaar ${dRec > 0 ? "badha" : "ghata"}: ${inr(prev.receivables.total)} se ${inr(cur.receivables.total)}.`,
        `Receivables ${dRec > 0 ? "rose" : "fell"} from ${inr(prev.receivables.total)} to ${inr(cur.receivables.total)}.`
      )
    );
  }
  const prevOver = new Set(prev.overdue.map((p) => p.party.toLowerCase()));
  const curOver = new Set(cur.overdue.map((p) => p.party.toLowerCase()));
  const cleared = [...prevOver].filter((p) => !curOver.has(p));
  const fresh = [...curOver].filter((p) => !prevOver.has(p));
  if (cleared.length) out.push(pick(lang, `Purana udhaar chuka: ${cleared.join(", ")}.`, `Overdue cleared: ${cleared.join(", ")}.`));
  if (fresh.length) out.push(pick(lang, `Naya overdue: ${fresh.join(", ")}.`, `Newly overdue: ${fresh.join(", ")}.`));
  const dProfit = cur.thisPeriod.profit - prev.thisPeriod.profit;
  if (prev.thisPeriod.txnCount > 0 && Math.abs(dProfit) >= 500) {
    out.push(
      pick(
        lang,
        `Munafa ${dProfit > 0 ? "badha" : "ghata"} ${inr(Math.abs(dProfit))} (pichhli baar se).`,
        `Profit ${dProfit > 0 ? "up" : "down"} ${inr(Math.abs(dProfit))} since last check.`
      )
    );
  }
  return out;
}

export function ruleInsights(s: LedgerStats, lang: InsightLang = "hinglish"): Insight[] {
  const out: Insight[] = [];
  const { thisPeriod: cur, prevPeriod: prev } = s;

  if (cur.txnCount < 3) {
    out.push({
      id: "few_entries",
      severity: "info",
      title: pick(lang, "Entries kam hain", "Not enough entries"),
      detail: pick(
        lang,
        `Is hafte sirf ${cur.txnCount} entry hain. Roz entry daalne se sahi insights aur loan score milta hai.`,
        `Only ${cur.txnCount} entries this week. Log daily for accurate insights and a better credit score.`
      ),
    });
  }

  if (s.salesChangePct != null && Math.abs(s.salesChangePct) >= 10) {
    const up = s.salesChangePct > 0;
    const pct = Math.abs(Math.round(s.salesChangePct));
    out.push({
      id: up ? "sales_up" : "sales_down",
      severity: up ? "good" : "warn",
      title: up ? pick(lang, `Bikri ${pct}% badhi`, `Sales up ${pct}%`) : pick(lang, `Bikri ${pct}% ghati`, `Sales down ${pct}%`),
      detail: pick(
        lang,
        `Is hafte ${inr(cur.sales)}, pichhle hafte ${inr(prev.sales)}.`,
        `This week ${inr(cur.sales)} vs ${inr(prev.sales)} last week.`
      ),
      action: up ? undefined : pick(lang, "Kaunsa saamaan kam bika, dekhein", "Check which items slowed down"),
    });
  }

  if (cur.profit < 0 && cur.txnCount >= 3) {
    out.push({
      id: "loss",
      severity: "warn",
      title: pick(lang, "Is hafte ghata", "Loss this week"),
      detail: pick(
        lang,
        `Bikri ${inr(cur.sales)} thi par maal + kharcha ${inr(cur.purchases + cur.expenses)}.`,
        `Sales ${inr(cur.sales)} but purchases + expenses ${inr(cur.purchases + cur.expenses)}.`
      ),
    });
  }

  if (prev.expenses > 0 && cur.expenses > prev.expenses * 1.5 && cur.expenses > 500) {
    out.push({
      id: "expense_spike",
      severity: "warn",
      title: pick(lang, "Kharcha achanak badha", "Expenses spiked"),
      detail: pick(
        lang,
        `Kharcha ${inr(cur.expenses)} (pichhle hafte ${inr(prev.expenses)}).`,
        `Expenses ${inr(cur.expenses)} (${inr(prev.expenses)} last week).`
      ),
    });
  }

  if (s.overdue.length) {
    const top = s.overdue.slice(0, 3).map((p) => `${p.party} ${inr(p.outstanding)} (${p.daysOld}d)`).join(", ");
    out.push({
      id: "overdue",
      severity: "warn",
      title: pick(lang, `${s.overdue.length} ka udhaar 30+ din purana`, `${s.overdue.length} overdue customer(s)`),
      detail: `${top}. ${pick(lang, "Kul", "Total")} ${inr(s.overdueTotal)}.`,
      action: pick(lang, "Aaj hi yaad dilayein", "Send a reminder today"),
    });
  } else if (s.receivables.total > 0 && s.receivables.total > Math.max(cur.sales, 1)) {
    out.push({
      id: "heavy_credit",
      severity: "warn",
      title: pick(lang, "Baaki bikri se zyada", "Receivables exceed weekly sales"),
      detail: pick(
        lang,
        `Logon se ${inr(s.receivables.total)} lena hai, is hafte ki bikri ${inr(cur.sales)}.`,
        `${inr(s.receivables.total)} outstanding vs ${inr(cur.sales)} sales this week.`
      ),
    });
  }

  if (s.digitalShare != null && s.digitalShare < 0.3 && cur.sales > 0) {
    out.push({
      id: "low_digital",
      severity: "info",
      title: pick(lang, "UPI kam hai", "Low UPI share"),
      detail: pick(
        lang,
        `Sirf ${Math.round(s.digitalShare * 100)}% bikri UPI/card se. Bank record jitna zyada, loan milna utna aasaan.`,
        `Only ${Math.round(s.digitalShare * 100)}% of sales via UPI/card. A bank trail makes loan approval easier.`
      ),
      action: pick(lang, "Dukaan par QR lagayein", "Display your UPI QR"),
    });
  }

  if (s.bestDay && cur.txnCount >= 3) {
    out.push({
      id: "best_day",
      severity: "info",
      title: pick(lang, "Sabse achha din", "Best day"),
      detail: `${s.bestDay.date}: ${inr(s.bestDay.sales)}`,
    });
  }

  return out.sort((a, b) => RANK[a.severity] - RANK[b.severity]);
}
