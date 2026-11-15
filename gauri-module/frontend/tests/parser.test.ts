import { test } from "node:test";
import assert from "node:assert/strict";
import { numbersIn } from "../lib/ai/numbers";
import { ruleParse } from "../lib/ai/ruleParser";
import { emptyContext, nextQuestion, pushTurn, resolveTurn } from "../lib/ai/context";

const TODAY = "2026-11-15";

test("spoken numbers", () => {
  const cases: [string, number[]][] = [
    ["paanch sau", [500]],
    ["do hazaar paanch sau", [2500]],
    ["2 hazaar paanch sau", [2500]],
    ["dedh sau", [150]],
    ["dhai hazaar", [2500]],
    ["sawa sau", [125]],
    ["saade teen sau", [350]],
    ["paune do sau", [175]],
    ["ek lakh paanch hazaar", [105000]],
    ["sawa lakh", [125000]],
    ["five hundred", [500]],
    ["twenty five", [25]],
    ["two thousand", [2000]],
    ["2k", [2000]],
    ["1,500", [1500]],
    ["५०० रुपये", [500]],
    ["पाँच सौ", [500]],
    ["तीन हज़ार", [3000]],
    ["sau rupaye", [100]],
    ["pachpan", [55]],
    ["500 200", [500, 200]],
    ["hello world", []],
  ];
  for (const [text, want] of cases) assert.deepEqual(numbersIn(text), want, text);
});

test("udhaar given", () => {
  const r = ruleParse("Ramesh ko 500 udhaar diya", { today: TODAY });
  assert.equal(r.intent, "credit_given");
  assert.equal(r.amount, 500);
  assert.equal(r.party, "Ramesh");
  assert.equal(r.payment_mode, "credit");
  assert.equal(r.date, TODAY);
  assert.equal(r.needs_confirmation, false);
});

test("udhaar taken from supplier, yesterday, spoken amount", () => {
  const r = ruleParse("kal Suresh se do hazaar paanch sau ka maal udhaar liya", { today: TODAY });
  assert.equal(r.intent, "credit_received");
  assert.equal(r.amount, 2500);
  assert.equal(r.party, "Suresh");
  assert.equal(r.date, "2026-11-14");
});

test("sale with item, quantity and UPI (qty is not the amount)", () => {
  const r = ruleParse("aaj 5 kilo chawal 250 rupaye mein becha UPI se", { today: TODAY });
  assert.equal(r.intent, "sale");
  assert.equal(r.amount, 250);
  assert.equal(r.payment_mode, "upi");
  assert.equal(r.party, null); // "UPI se" is not a person
  assert.deepEqual(r.items, [{ name: "chawal", quantity: 5, unit: "kg", unit_price: null }]);
});

test("customer pays old dues", () => {
  const r = ruleParse("Mohan ne 300 wapas diye", { today: TODAY });
  assert.equal(r.intent, "payment_received");
  assert.equal(r.party, "Mohan");
  assert.equal(r.amount, 300);
});

test("honorific names", () => {
  const r = ruleParse("Ramesh bhai ko 1000 udhaar diya", { today: TODAY });
  assert.equal(r.party, "Ramesh Bhai");
});

test("expense and purchase", () => {
  assert.equal(ruleParse("bijli bill 1200 bhara", { today: TODAY }).intent, "expense");
  const p = ruleParse("dedh sau ka maal kharida", { today: TODAY });
  assert.equal(p.intent, "purchase");
  assert.equal(p.amount, 150);
});

test("payment to supplier", () => {
  const r = ruleParse("supplier Anil ko 5000 chukaya", { today: TODAY });
  assert.equal(r.intent, "payment_made");
  assert.equal(r.amount, 5000);
});

test("Devanagari entry", () => {
  const r = ruleParse("रमेश को ५०० रुपये उधार दिया", { today: TODAY });
  assert.equal(r.intent, "credit_given");
  assert.equal(r.amount, 500);
  assert.equal(r.party, "रमेश");
});

test("query has no amount and needs no party", () => {
  const r = ruleParse("Ramesh ka kitna baaki hai?", { today: TODAY });
  assert.equal(r.intent, "query");
});

test("'de do' is not amount=2; missing data triggers confirmation", () => {
  const r = ruleParse("Ramesh ko paise de do", { today: TODAY });
  assert.equal(r.amount, null);
  assert.equal(r.needs_confirmation, true);
});

test("large mis-heard amounts need confirmation", () => {
  assert.equal(ruleParse("Ramesh ko 50 lakh udhaar diya", { today: TODAY }).needs_confirmation, true);
});

// ---- conversation context ----
test("continuation: 'aur 200 de diya'", () => {
  let ctx = emptyContext();
  const t1 = ruleParse("Ramesh ko 500 udhaar diya", { today: TODAY });
  ctx = pushTurn(ctx, "Ramesh ko 500 udhaar diya", t1);
  const text = "aur 200 de diya";
  const { intent } = resolveTurn(text, ruleParse(text, { today: TODAY }), ctx);
  assert.equal(intent.intent, "credit_given");
  assert.equal(intent.party, "Ramesh");
  assert.equal(intent.amount, 200);
});

test("pronoun resolves party from previous turn", () => {
  let ctx = emptyContext();
  ctx = pushTurn(ctx, "Ramesh ko 500 udhaar diya", ruleParse("Ramesh ko 500 udhaar diya", { today: TODAY }));
  const text = "usko 100 wapas mile";
  const { intent, notes } = resolveTurn(text, ruleParse(text, { today: TODAY }), ctx);
  assert.equal(intent.party, "Ramesh");
  assert.equal(intent.intent, "payment_received");
  assert.ok(notes.length > 0);
});

test("clarification loop: missing amount, then answer", () => {
  let ctx = emptyContext();
  const t1 = ruleParse("Ramesh ko udhaar diya", { today: TODAY });
  assert.equal(t1.needs_confirmation, true);
  assert.equal(nextQuestion(t1, "hinglish"), "Kitne rupaye?");
  ctx = pushTurn(ctx, "Ramesh ko udhaar diya", t1);

  const ans = "paanch sau";
  const { intent } = resolveTurn(ans, ruleParse(ans, { today: TODAY }), ctx);
  assert.equal(intent.amount, 500);
  assert.equal(intent.intent, "credit_given");
  assert.equal(intent.party, "Ramesh");
  assert.equal(intent.needs_confirmation, false);
  assert.equal(nextQuestion(intent), null);
});

test("clarification loop: missing party, then answer", () => {
  let ctx = emptyContext();
  const t1 = ruleParse("500 udhaar diya", { today: TODAY });
  assert.equal(t1.party, null);
  ctx = pushTurn(ctx, "500 udhaar diya", t1);
  const { intent } = resolveTurn("Suresh", ruleParse("Suresh", { today: TODAY }), ctx);
  assert.equal(intent.party, "Suresh");
  assert.equal(intent.needs_confirmation, false);
});

test("a fresh full entry is not swallowed by a pending question", () => {
  let ctx = emptyContext();
  ctx = pushTurn(ctx, "Ramesh ko udhaar diya", ruleParse("Ramesh ko udhaar diya", { today: TODAY }));
  const text = "Suresh ko 300 udhaar diya";
  const { intent } = resolveTurn(text, ruleParse(text, { today: TODAY }), ctx);
  assert.equal(intent.party, "Suresh");
  assert.equal(intent.amount, 300);
});
