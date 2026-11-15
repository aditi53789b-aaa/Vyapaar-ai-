/**
 * Loads backend/rag/schemes.json into pgvector.
 *   DATABASE_URL=... OPENAI_API_KEY=... npx tsx scripts/ingest-schemes.ts
 */
import fs from "node:fs";
import path from "node:path";
import { embedMany } from "ai";
import { pool, EMBED_MODEL, toPgVector } from "../lib/ai/rag";

async function main() {
  const file = path.resolve(__dirname, "../../backend/rag/schemes.json");
  const kb = JSON.parse(fs.readFileSync(file, "utf8"));

  const rows: { id: string; name: string; section: string; content: string; url: string }[] = [];
  for (const s of kb.schemes) {
    for (const [section, content] of Object.entries<string>(s.sections)) {
      rows.push({ id: s.id, name: s.name, section, content, url: s.source_url });
    }
  }

  // Prefix each chunk with scheme + section so retrieval matches on scheme names too.
  const { embeddings } = await embedMany({
    model: EMBED_MODEL,
    values: rows.map((r) => `${r.name} - ${r.section}: ${r.content}`),
  });

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    await pool.query(
      `INSERT INTO scheme_chunks (scheme_id, scheme_name, section, content, source_url, embedding)
       VALUES ($1,$2,$3,$4,$5,$6::vector)
       ON CONFLICT (scheme_id, section, language)
       DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding,
                     source_url = EXCLUDED.source_url, updated_at = now()`,
      [r.id, r.name, r.section, r.content, r.url, toPgVector(embeddings[i])]
    );
  }
  console.log(`Ingested ${rows.length} chunks`);
  await pool.end();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
