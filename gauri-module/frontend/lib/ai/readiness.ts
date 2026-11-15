/**
 * Deterministic credit-readiness signals computed from ledger metrics.
 * The LLM only EXPLAINS these numbers; it never invents them.
 */
export interface MerchantProfile {
  businessType?: string; // "kirana", "street_vendor", "tailor"...
  isStreetVendor?: boolean;
  hasUdyam?: boolean;
  hasBankAccount?: boolean;
  isNewBusiness?: boolean; // not yet operating (PMEGP)
  monthsOfRecords: number; // months with >=1 ledger entry
  avgMonthlyTurnover: number; // INR
  avgMonthlyExpenses: number; // INR
  activeDaysPerMonth: number; // days with entries, avg
  digitalPaymentShare: number; // 0..1 of sales via UPI/card
  overdueCreditShare: number; // 0..1 of receivables overdue > 30 days
}

export interface ReadinessReport {
  score: number; // 0..100
  band: "low" | "building" | "good" | "strong";
  strengths: string[];
  gaps: string[];
  nextSteps: string[];
}

export function assessReadiness(p: MerchantProfile): ReadinessReport {
  let score = 0;
  const strengths: string[] = [];
  const gaps: string[] = [];
  const nextSteps: string[] = [];

  // Record history (30)
  const hist = Math.min(p.monthsOfRecords / 12, 1) * 30;
  score += hist;
  (p.monthsOfRecords >= 6 ? strengths : gaps).push(
    p.monthsOfRecords >= 6 ? `${p.monthsOfRecords} months of ledger history` : `Only ${p.monthsOfRecords} month(s) of records; lenders like 6-12`
  );

  // Consistency (20)
  score += Math.min(p.activeDaysPerMonth / 20, 1) * 20;
  if (p.activeDaysPerMonth < 15) nextSteps.push("Log entries on more days so income looks consistent");
  else strengths.push("Regular daily record-keeping");

  // Profitability margin (20)
  const margin = p.avgMonthlyTurnover > 0 ? (p.avgMonthlyTurnover - p.avgMonthlyExpenses) / p.avgMonthlyTurnover : 0;
  score += Math.max(0, Math.min(margin / 0.2, 1)) * 20;
  (margin > 0.1 ? strengths : gaps).push(margin > 0.1 ? "Healthy profit margin" : "Thin or negative margin on recorded data");

  // Digital trail (15)
  score += Math.min(p.digitalPaymentShare / 0.5, 1) * 15;
  if (p.digitalPaymentShare < 0.3) nextSteps.push("Accept more UPI payments: bank-visible income helps loan approval");
  else strengths.push("Good share of digital payments");

  // Formalisation (10)
  if (p.hasUdyam) { score += 5; strengths.push("Udyam registered"); }
  else { gaps.push("No Udyam registration"); nextSteps.unshift("Register on Udyam (free) before applying for other schemes"); }
  if (p.hasBankAccount) score += 5;
  else { gaps.push("No business bank account"); nextSteps.unshift("Open/link a bank account for business receipts"); }

  // Receivables health (5)
  score += (1 - Math.min(p.overdueCreditShare, 1)) * 5;
  if (p.overdueCreditShare > 0.3) nextSteps.push("Collect overdue udhaar; heavy unpaid credit weakens cash flow");

  score = Math.round(score);
  const band = score >= 75 ? "strong" : score >= 55 ? "good" : score >= 35 ? "building" : "low";
  return { score, band, strengths, gaps, nextSteps };
}
