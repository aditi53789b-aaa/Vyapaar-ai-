/**
 * Deterministic Hinglish/Hindi ledger-entry parser. No network, no API key.
 * Used (a) offline, (b) when the LLM is unavailable, (c) as a fast first pass.
 * Confidence is capped at 0.85 so a human always sees the confirmation card for weak parses.
 */
import type { Intent, PaymentMode, TransactionIntent, TransactionItem } from "./types";
import { extractNumbers, tokenize, type NumberSpan, type Token } from "./numbers";
import { addDays, todayISO } from "./dates";
import { sanityCheck } from "./sanity";

const set = (s: string) => new Set(s.split(/\s+/).filter(Boolean));

const CREDIT = set("udhaar udhar udhari udhaari baaki baki khata khaata उधार उधारी बाकी खाता");
const GAVE = set("diya diye di dediya dediye dedia दिया दिए दी");
const TOOK = set("liya liye li lia लिया लिए ली");
const SELL = set("becha bech bechi bechna bika bikra bikri sale sold बेचा बेच बिक्री बिका");
const BUY = set("kharida kharide kharidi kharid khareed purchase bought maal stock खरीदा खरीद माल");
const EXPENSE = set(
  "kiraya kiraye rent bijli electricity bill salary tankhwah tankha kharcha kharch expense petrol transport bhada chai किराया बिजली तनख्वाह खर्चा खर्च"
);
const MONEY_IN = set("jama wapas vapas chukaya chukaye chuka mila mile aaya aaye जमा वापस चुकाया मिला मिले आया");
const MONEY_OUT = set("chukaya chukaye bhara bhare bhugtan payment bheja bheje bhej भरा");
const SUPPLIER = set("supplier wholesaler dukandar mahajan distributor vendor सप्लायर");
const QUERY = set("kitna kitne kitni batao bataiye dikhao dikha balance कितना कितने बताओ");
const CURRENCY = set("rupaye rupay rupaya rupiya rupees rupee rs inr ₹ रुपये रुपए रुपया");
const MARKERS = set("ko se ne को से ने");
const POSSESSIVE = set("ka ki ke का की के");
const HONORIFIC = set("bhai bhaiya ji didi seth sethji uncle aunty mama chacha bhabhi भाई जी दीदी सेठ");
const TODAY = set("aaj today आज");
const YESTERDAY = set("kal yesterday कल");
const DAY_BEFORE = set("parso parson परसों परसो");

const UNIT_ALIASES: Record<string, string[]> = {
  kg: ["kilo", "kg", "kilogram", "kilos", "किलो"],
  g: ["gram", "grams", "gm", "gms", "ग्राम"],
  litre: ["litre", "liter", "ltr", "litres", "लीटर"],
  packet: ["packet", "packets", "pkt", "पैकेट"],
  dozen: ["dozen", "darjan", "दर्जन"],
  piece: ["piece", "pieces", "pcs", "nag"],
  bag: ["bori", "bag", "bags", "बोरी"],
};
const UNIT_OF = new Map<string, string>();
for (const [canon, aliases] of Object.entries(UNIT_ALIASES)) aliases.forEach((a) => UNIT_OF.set(a, canon));

const PAYMENT_WORDS: [Set<string>, PaymentMode][] = [
  [set("upi gpay googlepay phonepe paytm bhim qr scanner"), "upi"],
  [set("card"), "card"],
  [set("cash nakad naqad nagad नकद"), "cash"],
];
const PAYMENT_ALL = new Set<string>(PAYMENT_WORDS.flatMap(([s]) => [...s]));

const PRONOUNS = set("usko unko isko unhe usse unse wahi wohi same usi");
export const hasPronoun = (toks: Token[]) => toks.some((t) => PRONOUNS.has(t.n));

/** words that can never be a person's name */
const NOT_NAME = new Set<string>([
  ...CREDIT, ...GAVE, ...TOOK, ...SELL, ...BUY, ...EXPENSE, ...MONEY_IN, ...MONEY_OUT, ...SUPPLIER, ...QUERY,
  ...CURRENCY, ...MARKERS, ...POSSESSIVE, ...TODAY, ...YESTERDAY, ...DAY_BEFORE, ...PAYMENT_ALL, ...PRONOUNS,
  ...set("maine mujhe mujhko usne unhone mein me par aur phir bhi yeh woh wo hai hain tha the kar kiya kiye ek do"),
  ...UNIT_OF.keys(),
]);

const isWord = (t: Token) => /^[\p{L}\p{M}]+$/u.test(t.raw);

function titleCase(words: string[]): string {
  return words.map((w) => (/^[a-z]/i.test(w) ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w)).join(" ");
}

interface PartyHit {
  name: string;
  marker: string;
}

function findParty(toks: Token[], inNumber: Set<number>): PartyHit | null {
  const candidateAt = (j: number): string | null => {
    if (j < 0 || inNumber.has(j)) return null;
    const t = toks[j];
    if (!isWord(t)) return null;
    if (HONORIFIC.has(t.n) && j > 0 && !inNumber.has(j - 1) && isWord(toks[j - 1]) && !NOT_NAME.has(toks[j - 1].n)) {
      return titleCase([toks[j - 1].raw, t.raw]);
    }
    if (NOT_NAME.has(t.n) || HONORIFIC.has(t.n)) return null;
    return titleCase([t.raw]);
  };

  for (let i = 0; i < toks.length; i++) {
    if (MARKERS.has(toks[i].n)) {
      const name = candidateAt(i - 1);
      if (name) return { name, marker: toks[i].n };
    }
    // "<name> ka udhaar/baaki"
    if (POSSESSIVE.has(toks[i].n) && i + 1 < toks.length && CREDIT.has(toks[i + 1].n)) {
      const name = candidateAt(i - 1);
      if (name) return { name, marker: "ka" };
    }
  }
  return null;
}

function parseItems(toks: Token[], spans: NumberSpan[]): { items: TransactionItem[]; qtySpans: Set<number> } {
  const items: TransactionItem[] = [];
  const qtySpans = new Set<number>();
  spans.forEach((s, si) => {
    const unitTok = toks[s.to + 1];
    const unit = unitTok ? UNIT_OF.get(unitTok.n) : undefined;
    if (!unit) return;
    qtySpans.add(si);
    const nameWords: string[] = [];
    for (let j = s.to + 2; j < toks.length && nameWords.length < 3; j++) {
      const t = toks[j];
      if (!isWord(t) || NOT_NAME.has(t.n) || CURRENCY.has(t.n) || spans.some((x) => j >= x.from && j <= x.to)) break;
      nameWords.push(t.raw);
    }
    if (nameWords.length) items.push({ name: nameWords.join(" "), quantity: s.value, unit, unit_price: null });
  });
  return { items, qtySpans };
}

export function ruleParse(text: string, opts: { today?: string } = {}): TransactionIntent {
  const today = opts.today ?? todayISO();
  const toks = tokenize(text);
  const words = toks.map((t) => t.n);
  const has = (s: Set<string>) => words.some((w) => s.has(w));
  const spans = extractNumbers(toks);

  const inNumber = new Set<number>();
  spans.forEach((s) => {
    for (let i = s.from; i <= s.to; i++) inNumber.add(i);
  });

  // ---- amount & items ----
  const { items, qtySpans } = parseItems(toks, spans);
  const candidates = spans
    .map((s, idx) => ({ s, idx }))
    .filter(({ s, idx }) => {
      if (qtySpans.has(idx)) return false;
      const withCurrency = CURRENCY.has(toks[s.to + 1]?.n ?? "") || CURRENCY.has(toks[s.from - 1]?.n ?? "");
      const hasDigit = toks.slice(s.from, s.to + 1).some((t) => /^\d/.test(t.n));
      const singleSmallWord = s.from === s.to && !hasDigit && s.value < 100;
      return !(singleSmallWord && !withCurrency); // "de do" must not become amount=2
    });
  const withCur = candidates.find(
    ({ s }) => CURRENCY.has(toks[s.to + 1]?.n ?? "") || CURRENCY.has(toks[s.from - 1]?.n ?? "")
  );
  const best = withCur ?? [...candidates].sort((a, b) => b.s.value - a.s.value)[0];
  const amount = best ? best.s.value : null;

  // ---- party ----
  const partyHit = findParty(toks, inNumber);

  // ---- intent ----
  const credit = has(CREDIT);
  const gave = has(GAVE);
  const took = has(TOOK);
  let intent: Intent = "unknown";

  if (amount == null && (has(QUERY) || /[?？]/.test(text))) intent = "query";
  else if (partyHit?.marker === "ne" && (has(MONEY_IN) || gave) && !has(SELL) && !has(BUY)) intent = "payment_received";
  else if (credit && (took || (partyHit?.marker === "se" && !gave && !has(SELL)))) intent = "credit_received";
  else if (credit) intent = "credit_given";
  else if (has(EXPENSE) && !has(SELL)) intent = "expense";
  else if (has(BUY)) intent = "purchase";
  else if (has(SELL)) intent = "sale";
  else if (partyHit && has(MONEY_OUT) && (has(SUPPLIER) || partyHit.marker === "ko")) intent = "payment_made";
  else if (has(MONEY_IN) && (partyHit || hasPronoun(toks))) intent = "payment_received";

  // ---- payment mode ----
  let payment_mode: PaymentMode = "unknown";
  for (const [ws, mode] of PAYMENT_WORDS) if (has(ws)) payment_mode = mode;
  if (intent === "credit_given" || intent === "credit_received") payment_mode = "credit";

  // ---- date ----
  let date: string | null = today;
  let notes: string | null = null;
  if (has(DAY_BEFORE)) date = addDays(today, -2);
  else if (has(YESTERDAY)) {
    date = addDays(today, -1);
    notes = "'kal' assumed to mean yesterday";
  } else if (!has(TODAY)) date = today;

  // ---- confidence ----
  let confidence = 0.5;
  if (amount != null) confidence += 0.15;
  if (intent !== "unknown") confidence += 0.15;
  if (partyHit) confidence += 0.05;
  if (items.length) confidence += 0.05;
  confidence = Math.min(confidence, 0.85);

  return sanityCheck({
    intent,
    amount,
    party: intent === "query" && !partyHit ? null : partyHit?.name ?? null,
    items,
    payment_mode,
    date,
    notes,
    confidence,
    needs_confirmation: false,
  });
}
