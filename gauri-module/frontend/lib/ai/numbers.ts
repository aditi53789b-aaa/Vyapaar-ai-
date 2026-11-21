/**
 * Tokenizer + spoken-number extractor for Hindi / Hinglish / English (Roman and Devanagari).
 *
 *   "do hazaar paanch sau"  -> 2500      "dedh sau" -> 150      "saade teen sau" -> 350
 *   "sawa lakh"             -> 125000    "paune do sau" -> 175  "5 hazaar" -> 5000
 *   "five hundred" -> 500   "2k" -> 2000 "पाँच सौ" -> 500
 *
 * Coverage: Hindi 1-99 (common romanisations), 1-20 + tens in Devanagari, English words.
 * Anything exotic is left to the LLM parser; this module is the offline/deterministic layer.
 */

export interface Token {
  raw: string;
  /** normalised form used for matching */
  n: string;
  start: number;
  end: number;
}

export interface NumberSpan {
  value: number;
  /** inclusive token indices */
  from: number;
  to: number;
}

const DIGIT_SETS = ["०१२३४५६७८९", "੦੧੨੩੪੫੬੭੮੯", "௦௧௨௩௪௫௬௭௮௯", "૦૧૨૩૪૫૬૭૮૯", "০১২৩৪৫৬৭৮৯"];

/** 1:1 replacement, so character offsets stay valid. */
export function normalizeDigits(text: string): string {
  let out = "";
  for (const ch of text) {
    let r = ch;
    for (const set of DIGIT_SETS) {
      const i = set.indexOf(ch);
      if (i >= 0) {
        r = String(i);
        break;
      }
    }
    out += r;
  }
  return out;
}

export function normalizeWord(w: string): string {
  return w
    .toLowerCase()
    .normalize("NFC")
    .replace(/़/g, "") // nukta
    .replace(/ँ/g, "ं"); // chandrabindu -> anusvara
}

const TOKEN_RE = /\d+(?:,\d{2,3})*(?:\.\d+)?k?|[\p{L}\p{M}]+|₹/giu;

export function tokenize(text: string): Token[] {
  const src = normalizeDigits(text);
  const out: Token[] = [];
  for (const m of src.matchAll(TOKEN_RE)) {
    const raw = m[0];
    out.push({ raw, n: normalizeWord(raw), start: m.index ?? 0, end: (m.index ?? 0) + raw.length });
  }
  return out;
}

// ---- number words ---------------------------------------------------------------------------
const HINDI_1_99 =
  "ek do teen chaar paanch chhe saat aath nau das " +
  "gyarah barah terah chaudah pandrah solah satrah atharah unnis bees " +
  "ikkis baais teis chaubis pachchis chhabbis sattais atthais unattis tees " +
  "iktis battis taintis chauntis paintis chhattis saintis adtis untalis chalis " +
  "iktalis bayalis taintalis chauvalis paintalis chhiyalis saintalis adtalis unchas pachas " +
  "ikyavan baavan tirpan chauvan pachpan chhappan sattavan atthavan unsath saath " +
  "iksath baasath tirsath chausath painsath chhiyasath adsath arsath unhattar sattar " +
  "ikhattar bahattar tihattar chauhattar pachhattar chhihattar satattar athattar unyasi assi " +
  "ikyasi bayasi tirasi chaurasi pachasi chhiyasi sattasi atthasi navasi nabbe " +
  "ikyanve baanve tiranve chauranve pachanve chhiyanve sattanve atthanve ninyanve";

const NUM: Record<string, number> = {};
HINDI_1_99.split(" ").forEach((w, i) => (NUM[w] = i + 1));

// common alternate spellings
Object.assign(NUM, {
  char: 4, chaar: 4, panch: 5, pach: 5, chhah: 6, chah: 6, che: 6, chheh: 6, chhey: 6, aat: 8, nao: 9, nou: 9,
  gyaarah: 11, gyara: 11, baarah: 12, tera: 13, chaudha: 14, pandra: 15,
  sola: 16, satra: 17, athara: 18, unis: 19, bis: 20, ikis: 21, pachis: 25, pachees: 25, pachchees: 25,
  chhabbees: 26, tis: 30, chalees: 40, pachaas: 50, assee: 80, nabbay: 90,
  // Devanagari 1-20 + tens
  "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6, "छे": 6, "सात": 7, "आठ": 8,
  "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15, "पन्द्रह": 15,
  "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19, "बीस": 20, "तीस": 30, "चालीस": 40, "पचास": 50,
  "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90,
  // English
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11,
  twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
  twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
  // fractions that behave like plain values
  dedh: 1.5, derh: 1.5, "डेढ़": 1.5, "डेढ": 1.5, dhai: 2.5, dhaai: 2.5, adhai: 2.5, "ढाई": 2.5, sawa: 1.25, sava: 1.25, "सवा": 1.25,
});
const ENGLISH_TENS = new Set(["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]);
const ENGLISH_ONES = new Set(["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]);

const MULT: Record<string, number> = {
  sau: 100, "सौ": 100, hundred: 100,
  hazaar: 1_000, hazar: 1_000, hajar: 1_000, hajaar: 1_000, "हज़ार": 1_000, "हजार": 1_000, thousand: 1_000,
  lakh: 100_000, lac: 100_000, lakhs: 100_000, lacs: 100_000, "लाख": 100_000,
  crore: 10_000_000, karod: 10_000_000, "करोड": 10_000_000, "करोड़": 10_000_000,
};

/** "saade"=+0.5 on the next number, "paune"=-0.25 */
const PREFIX: Record<string, number> = { saade: 0.5, sade: 0.5, "साढ़े": 0.5, "साढे": 0.5, paune: -0.25, "पौने": -0.25 };

const round = (n: number) => Math.round(n * 100) / 100;

export function extractNumbers(tokens: Token[]): NumberSpan[] {
  const out: NumberSpan[] = [];
  let total = 0;
  let cur: number | null = null;
  let pend = 0;
  let from = -1;
  let to = -1;
  let last: "value" | "mult" | "prefix" | null = null;
  let lastWord = "";

  const reset = () => {
    total = 0; cur = null; pend = 0; from = -1; to = -1; last = null; lastWord = "";
  };
  const flush = () => {
    if (from >= 0 && (cur !== null || total > 0)) out.push({ value: round(total + (cur ?? 0)), from, to });
    reset();
  };

  tokens.forEach((t, i) => {
    const w = t.n;
    const isDigit = /^\d/.test(w);

    if (isDigit || (w in NUM && !(w in MULT))) {
      let v: number;
      if (isDigit) {
        v = parseFloat(w.replace(/,/g, ""));
        if (w.endsWith("k")) v *= 1000;
      } else v = NUM[w];

      const englishCombo = last === "value" && ENGLISH_TENS.has(lastWord) && ENGLISH_ONES.has(w);
      if (last === "value" && !englishCombo) flush();
      if (from < 0) from = i;
      cur = (cur ?? 0) + v + pend;
      pend = 0;
      last = "value";
      lastWord = w;
      to = i;
    } else if (w in PREFIX) {
      if (last === "value") flush();
      if (from < 0) from = i;
      pend = PREFIX[w];
      last = "prefix";
      to = i;
    } else if (w in MULT) {
      const m = MULT[w];
      if (from < 0) from = i;
      if (m === 100) {
        cur = (cur ?? 1) * 100;
      } else {
        total += (cur ?? 1) * m;
        cur = null;
      }
      pend = 0;
      last = "mult";
      lastWord = w;
      to = i;
    } else {
      flush();
    }
  });
  flush();
  return out;
}

/** Convenience: numbers in a raw string. */
export function numbersIn(text: string): number[] {
  return extractNumbers(tokenize(text)).map((s) => s.value);
}
