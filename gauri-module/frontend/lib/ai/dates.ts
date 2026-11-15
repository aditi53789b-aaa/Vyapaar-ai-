/** Tiny date helpers on ISO "YYYY-MM-DD" strings (UTC math, so no DST/timezone drift). */

const pad = (n: number) => String(n).padStart(2, "0");

/** Today's date in the *device's local* timezone (an IST shop at 1 AM is still "today"). */
export function todayISO(now: Date = new Date()): string {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function toMs(iso: string): number {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

export function fromMs(ms: number): string {
  const d = new Date(ms);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
}

export function addDays(iso: string, n: number): string {
  return fromMs(toMs(iso) + n * 86_400_000);
}

/** Whole days from a to b (b - a). */
export function daysBetween(a: string, b: string): number {
  return Math.round((toMs(b) - toMs(a)) / 86_400_000);
}

export const monthOf = (iso: string) => iso.slice(0, 7);
