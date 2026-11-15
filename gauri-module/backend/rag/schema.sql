-- pgvector setup for the Credit Readiness Copilot.
-- Run once against the same PostgreSQL instance Aditi manages.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS scheme_chunks (
    id           BIGSERIAL PRIMARY KEY,
    scheme_id    TEXT        NOT NULL,           -- e.g. 'mudra', 'pm_svanidhi'
    scheme_name  TEXT        NOT NULL,
    section      TEXT        NOT NULL,           -- 'eligibility' | 'benefits' | 'documents' | 'how_to_apply'
    content      TEXT        NOT NULL,
    source_url   TEXT,
    language     TEXT        NOT NULL DEFAULT 'en',
    embedding    vector(1536) NOT NULL,          -- text-embedding-3-small
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (scheme_id, section, language)
);

-- Cosine-distance HNSW index (fast ANN search; fine for small corpora too)
CREATE INDEX IF NOT EXISTS scheme_chunks_embedding_idx
    ON scheme_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS scheme_chunks_scheme_idx ON scheme_chunks (scheme_id);

-- Example retrieval query ($1 = query embedding, $2 = k):
--   SELECT scheme_name, section, content, source_url,
--          1 - (embedding <=> $1::vector) AS similarity
--   FROM scheme_chunks ORDER BY embedding <=> $1::vector LIMIT $2;
