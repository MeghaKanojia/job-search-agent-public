-- Phase 1 schema, mirrors backend/app/models/*.py exactly.
-- Run this once against your Neon database to create tables.
-- (A real Alembic migration chain can replace this once the schema stabilizes --
--  not worth the setup overhead for a single initial migration.)

-- Neon supports this extension natively -- needed for the RAG skill-retrieval
-- pipeline (pipeline/rag.py) to store and vector-search skill embeddings.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE keyword_filters (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(50) NOT NULL DEFAULT 'professional',
    keyword VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE skill_profile_items (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    proficiency_level VARCHAR(50),
    years_experience FLOAT,
    evidence_bullet TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- 384-dim to match fastembed's BAAI/bge-small-en-v1.5 (pipeline/rag.py).
    -- NULL until backfill_skill_embeddings() runs; retrieval falls back to
    -- the full skill list when embeddings aren't populated yet.
    embedding vector(384)
);
CREATE INDEX idx_skill_profile_items_embedding ON skill_profile_items
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

CREATE TABLE education (
    id SERIAL PRIMARY KEY,
    institution VARCHAR(255) NOT NULL,
    degree VARCHAR(255) NOT NULL,
    field_of_study VARCHAR(255),
    location VARCHAR(255),
    start_date DATE,
    end_date DATE,
    grade VARCHAR(100),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE work_experience (
    id SERIAL PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    role_title VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tech_stack VARCHAR(500),
    project_url TEXT,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Covers certifications AND notable awards -- the source CV groups them under
-- one "Certifications & Awards" section; splitting into two tables wasn't
-- worth it for what's otherwise identical shape (a name, an issuer, a date).
CREATE TABLE certifications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    issuing_organization VARCHAR(255),
    issue_date DATE,
    credential_url TEXT,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE raw_ingest_events (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,
    batch_id VARCHAR(64)
);

CREATE TABLE job_postings (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_job_id VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255),
    location VARCHAR(255),
    url TEXT NOT NULL,
    description_raw TEXT,
    description_clean TEXT,
    salary_text VARCHAR(255),
    posted_at TIMESTAMP,
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    keyword_match_score FLOAT,
    matched_keywords JSONB,
    relevance_reasoning TEXT,
    dedup_hash VARCHAR(64) NOT NULL UNIQUE
);
CREATE INDEX idx_job_postings_dedup_hash ON job_postings (dedup_hash);

CREATE TYPE application_status AS ENUM (
    'new', 'staged_for_review', 'approved_ready_to_submit', 'applied',
    'viewed', 'interview', 'offer', 'rejected', 'withdrawn'
);

CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    job_posting_id INTEGER NOT NULL REFERENCES job_postings(id),
    company VARCHAR(255),
    role_title VARCHAR(500),
    source_portal VARCHAR(50),
    jd_link TEXT,
    key_skills_matched JSONB,
    status application_status NOT NULL DEFAULT 'new',
    applied_at TIMESTAMP,
    last_status_change_at TIMESTAMP NOT NULL DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TYPE document_type AS ENUM ('resume', 'cover_letter');

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    doc_type document_type NOT NULL,
    file_bytes BYTEA NOT NULL,
    content_text TEXT,
    version_number INTEGER NOT NULL DEFAULT 1,
    generated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE status_update_proposals (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    proposed_status VARCHAR(50) NOT NULL,
    evidence_snippet TEXT,
    gmail_message_id VARCHAR(255),
    confidence FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_status VARCHAR(50)
);

CREATE TABLE status_history (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Encrypted-at-rest only. Never insert plaintext into encrypted_blob/*_token columns --
-- always encrypt with app/core/security.py first. Encryption key lives outside this DB.
CREATE TABLE credentials (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(100) NOT NULL,
    encrypted_blob BYTEA NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(100) NOT NULL UNIQUE,
    encrypted_access_token BYTEA NOT NULL,
    encrypted_refresh_token BYTEA NOT NULL,
    scope VARCHAR(500),
    expires_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE pipeline_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
