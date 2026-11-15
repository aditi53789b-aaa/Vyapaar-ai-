import { embed } from "ai";
import { openai } from "@ai-sdk/openai";
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
export const EMBED_MODEL = openai.embedding("text-embedding-3-small");

export interface SchemeChunk {
  scheme_id: string;
  scheme_name: string;
  section: string;
  content: string;
  source_url: string | null;
  similarity: number;
}

export async function embedText(text: string): Promise<number[]> {
  const { embedding } = await embed({ model: EMBED_MODEL, value: text });
  return embedding;
}

export const toPgVector = (v: number[]) => `[${v.join(",")}]`;

export async function retrieveSchemeChunks(query: string, k = 6, minSimilarity = 0.25): Promise<SchemeChunk[]> {
  const q = toPgVector(await embedText(query));
  const { rows } = await pool.query<SchemeChunk>(
    `SELECT scheme_id, scheme_name, section, content, source_url,
            1 - (embedding <=> $1::vector) AS similarity
       FROM scheme_chunks
      ORDER BY embedding <=> $1::vector
      LIMIT $2`,
    [q, k]
  );
  return rows.filter((r) => r.similarity >= minSimilarity);
}

export { pool };
