import { NextResponse } from "next/server";
import { ParseRequestSchema } from "@/lib/ai/schemas";
import { parseEntry } from "@/lib/ai/intent";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const body = ParseRequestSchema.safeParse(await req.json().catch(() => null));
  if (!body.success) {
    return NextResponse.json({ error: "Invalid request", details: body.error.flatten() }, { status: 400 });
  }
  try {
    const { text, language, today, history } = body.data;
    const result = await parseEntry(text, { turns: history ?? [] }, { language, today });
    return NextResponse.json(result); // { intent, question, engine, notes }
  } catch (e) {
    console.error("parse-intent failed", e);
    return NextResponse.json({ error: "Could not parse entry" }, { status: 502 });
  }
}
