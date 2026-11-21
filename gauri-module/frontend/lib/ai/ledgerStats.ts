/**
 * Deterministic ledger analytics. Every number the Copilot / Insights panel shows comes from here;
 * the LLM only narrates it. Pure functions: works offline, on IndexedDB rows or server rows alike.
 */
import type { Intent, PaymentMode } from "./types";
import type { MerchantProfile } from "./readiness";
import { daysBetween, monthOf, todayISO } from "./dates";

export interface LedgerTxn {
  id?: string | number;
  intent: Intent;
  amount: number | null;
  party?: string | null;
  date: string; // YYYY-MM-DD
  payment_mode?: PaymentMode;
}

export interface PeriodTotals {
  sales: number; // cash/UPI sales + sales on credit (turnover)
  purchases: number;
  expenses: number;
  profit: number; // sales - purchases - expenses
  txnCount: number;
  activeDays: number;
}

export interface PartyBalance {
  party: string;
  outstanding: number;
  oldestDate: string | null; // oldest still-unpaid credit
  daysOld: number | null;
}

export interface LedgerStats {
  asOf: string;
  periodDays: number;
  thisPeriod: PeriodTotals;
  prevPeriod: PeriodTotals;
  salesChangePct: number | null;
  receivables: { total: number; parties: PartyBalance[] };
  payables: { total: number; parties: PartyBalance[] };
  overdue: PartyBalance[]; // receivables older than OVERDUE_DAYS
  overdueTotal: number;
  digitalShare: number | null; // share of cash-type sales paid via UPI/card (last 30 days)
  bestDay: { date: string; sales: number } | null;
}

export const OVERDUE_DAYS = 30;
const amt = (t: LedgerTxn) => (typeof t.amount === "number" && t.amount > 0 ? t.amount : 0);
const key = (p: string) => p.trim().toLowerCase();

function totals(txns: LedgerTxn[]): PeriodTotals {
  let sales = 0, purchases = 0, expenses = 0;
  const days = new Set<string>();
  for (const t of txns) {
    days.add(t.date);
    if (t.intent === "sale" || t.intent === "credit_given") sales += amt(t);
    else if (t.intent === "purchase") purchases += amt(t);
    else if (t.intent === "expense") expenses += amt(t);
  }
  return { sales, purchases, expenses, profit: sales - purchases - expenses, txnCount: txns.length, activeDays: days.size };
}

/** First-in-first-out settlement: payments clear the oldest credit first. */
function balances(txns: LedgerTxn[], creditIntent: Intent, payIntent: Intent, asOf: string): PartyBalance[] {
  const names = new Map<string, string>();
  const credits = new Map<string, { date: string; left: number }[]>();
  const paid = new Map<string, number>();

  for (const t of [...txns].sort((a, b) => a.date.localeCompare(b.date))) {
    if (!t.party || !amt(t)) continue;
    const k = key(t.party);
    if (!names.has(k)) names.set(k, t.party.trim());
    if (t.intent === creditIntent) {
      if (!credits.has(k)) credits.set(k, []);
      credits.get(k)!.push({ date: t.date, left: amt(t) });
    } else if (t.intent === payIntent) {
      paid.set(k, (paid.get(k) ?? 0) + amt(t));
    }
  }

  const out: PartyBalance[] = [];
  for (const [k, list] of credits) {
    let pay = paid.get(k) ?? 0;
    for (const c of list) {
      const used = Math.min(c.left, pay);
      c.left -= used;
      pay -= used;
    }
    const open = list.filter((c) => c.left > 0.001);
    const outstanding = open.reduce((s, c) => s + c.left, 0);
    if (outstanding > 0) {
      const oldestDate = open[0].date;
      out.push({ party: names.get(k)!, outstanding, oldestDate, daysOld: daysBetween(oldestDate, asOf) });
    }
  }
  return out.sort((a, b) => b.outstanding - a.outstanding);
}

export function computeStats(all: LedgerTxn[], asOf: string = todayISO(), periodDays = 7): LedgerStats {
  const txns = all.filter((t) => t.date <= asOf); // "as of" means: ignore anything recorded later
  const inWindow = (t: LedgerTxn, fromAgo: number, toAgo: number) => {
    const d = daysBetween(t.date, asOf);
    return d >= fromAgo && d <= toAgo;
  };
  const thisPeriod = totals(txns.filter((t) => inWindow(t, 0, periodDays - 1)));
  const prevPeriod = totals(txns.filter((t) => inWindow(t, periodDays, 2 * periodDays - 1)));

  const receivables = balances(txns, "credit_given", "payment_received", asOf);
  const payables = balances(txns, "credit_received", "payment_made", asOf);
  const overdue = receivables.filter((p) => (p.daysOld ?? 0) > OVERDUE_DAYS);

  // digital share over the last 30 days of direct (non-credit) sales
  let direct = 0, digital = 0;
  const perDay = new Map<string, number>();
  for (const t of txns) {
    if (t.intent === "sale" || t.intent === "credit_given") {
      perDay.set(t.date, (perDay.get(t.date) ?? 0) + amt(t));
    }
    if (t.intent === "sale" && inWindow(t, 0, 29)) {
      direct += amt(t);
      if (t.payment_mode === "upi" || t.payment_mode === "card") digital += amt(t);
    }
  }
  const best = [...perDay.entries()]
    .filter(([d]) => inWindow({ date: d } as LedgerTxn, 0, periodDays - 1))
    .sort((a, b) => b[1] - a[1])[0];

  return {
    asOf,
    periodDays,
    thisPeriod,
    prevPeriod,
    salesChangePct: prevPeriod.sales > 0 ? ((thisPeriod.sales - prevPeriod.sales) / prevPeriod.sales) * 100 : null,
    receivables: { total: receivables.reduce((s, p) => s + p.outstanding, 0), parties: receivables },
    payables: { total: payables.reduce((s, p) => s + p.outstanding, 0), parties: payables },
    overdue,
    overdueTotal: overdue.reduce((s, p) => s + p.outstanding, 0),
    digitalShare: direct > 0 ? digital / direct : null,
    bestDay: best ? { date: best[0], sales: best[1] } : null,
  };
}

/** Turns raw ledger rows into the inputs the credit-readiness score needs (no backend endpoint required). */
export function deriveProfile(
  txns: LedgerTxn[],
  base: Partial<MerchantProfile> = {},
  asOf: string = todayISO()
): MerchantProfile {
  const months = new Set(txns.map((t) => monthOf(t.date)));
  const n = Math.max(months.size, 1);
  const all = totals(txns);

  let direct = 0, digital = 0;
  for (const t of txns) {
    if (t.intent === "sale") {
      direct += amt(t);
      if (t.payment_mode === "upi" || t.payment_mode === "card") digital += amt(t);
    }
  }
  const stats = computeStats(txns, asOf);

  return {
    ...base,
    monthsOfRecords: months.size,
    avgMonthlyTurnover: all.sales / n,
    avgMonthlyExpenses: (all.purchases + all.expenses) / n,
    activeDaysPerMonth: new Set(txns.map((t) => t.date)).size / n,
    digitalPaymentShare: direct > 0 ? digital / direct : 0,
    overdueCreditShare: stats.receivables.total > 0 ? stats.overdueTotal / stats.receivables.total : 0,
  };
}
