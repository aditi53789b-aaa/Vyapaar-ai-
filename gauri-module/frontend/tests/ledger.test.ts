import { test } from "node:test";
import assert from "node:assert/strict";
import { computeStats, deriveProfile, type LedgerTxn } from "../lib/ai/ledgerStats";
import { ruleInsights } from "../lib/ai/insightRules";
import { assessReadiness } from "../lib/ai/readiness";

const ASOF = "2026-11-15";
const t = (intent: LedgerTxn["intent"], amount: number, date: string, extra: Partial<LedgerTxn> = {}): LedgerTxn => ({
  intent, amount, date, ...extra,
});

test("period totals and week-over-week change", () => {
  const stats = computeStats(
    [
      t("sale", 1000, "2026-11-15", { payment_mode: "upi" }),
      t("sale", 1000, "2026-11-12", { payment_mode: "cash" }),
      t("expense", 300, "2026-11-13"),
      t("purchase", 500, "2026-11-10"),
      t("sale", 1000, "2026-11-07"), // previous week
    ],
    ASOF
  );
  assert.equal(stats.thisPeriod.sales, 2000);
  assert.equal(stats.thisPeriod.profit, 2000 - 300 - 500);
  assert.equal(stats.prevPeriod.sales, 1000);
  assert.equal(stats.salesChangePct, 100);
  assert.ok(Math.abs((stats.digitalShare ?? 0) - 1000 / 3000) < 1e-9);
});

test("FIFO udhaar settlement and overdue detection", () => {
  const stats = computeStats(
    [
      t("credit_given", 1000, "2026-09-01", { party: "Ramesh" }), // 75 days old
      t("credit_given", 500, "2026-11-10", { party: "ramesh " }), // same party, different case/space
      t("payment_received", 1000, "2026-11-11", { party: "Ramesh" }), // clears the OLD 1000 first
      t("credit_given", 700, "2026-11-14", { party: "Suresh" }),
    ],
    ASOF
  );
  const ramesh = stats.receivables.parties.find((p) => p.party.toLowerCase() === "ramesh")!;
  assert.equal(ramesh.outstanding, 500);
  assert.equal(ramesh.oldestDate, "2026-11-10"); // old debt cleared first -> not overdue
  assert.equal(stats.overdue.length, 0);
  assert.equal(stats.receivables.total, 1200);
});

test("old unpaid credit is flagged overdue", () => {
  const stats = computeStats([t("credit_given", 800, "2026-09-20", { party: "Mohan" })], ASOF);
  assert.equal(stats.overdue.length, 1);
  assert.equal(stats.overdue[0].daysOld, 56);
  const ins = ruleInsights(stats, "en");
  assert.ok(ins.some((i) => i.id === "overdue" && i.severity === "warn"));
});

test("payables tracked separately", () => {
  const stats = computeStats(
    [t("credit_received", 5000, "2026-11-01", { party: "Anil" }), t("payment_made", 2000, "2026-11-05", { party: "Anil" })],
    ASOF
  );
  assert.equal(stats.payables.total, 3000);
  assert.equal(stats.receivables.total, 0);
});

test("insights: sales drop + few entries", () => {
  const stats = computeStats(
    [t("sale", 5000, "2026-11-08"), t("sale", 1000, "2026-11-14")],
    ASOF
  );
  const ids = ruleInsights(stats).map((i) => i.id);
  assert.ok(ids.includes("sales_down"));
  assert.ok(ids.includes("few_entries"));
});

test("derived profile feeds the readiness score", () => {
  const txns: LedgerTxn[] = [];
  for (let m = 0; m < 6; m++) {
    for (let d = 1; d <= 20; d++) {
      const date = `2026-${String(m + 5).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      txns.push(t("sale", 2000, date, { payment_mode: d % 2 ? "upi" : "cash" }));
      if (d % 5 === 0) txns.push(t("expense", 1500, date));
    }
  }
  const p = deriveProfile(txns, { hasUdyam: true, hasBankAccount: true }, ASOF);
  assert.equal(p.monthsOfRecords, 6);
  assert.equal(p.activeDaysPerMonth, 20);
  assert.equal(p.digitalPaymentShare, 0.5);
  const r = assessReadiness(p);
  assert.ok(r.score >= 55, `score ${r.score}`);
  assert.ok(r.strengths.includes("Udyam registered"));
});
