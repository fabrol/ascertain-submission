-- LLM Cache table setup script
-- This script creates the llm_cache table for storing processed document summaries
-- Depends on the documents table being created first (01-init.sql)

-- Create the LLM cache table
CREATE TABLE IF NOT EXISTS llm_cache (
    id SERIAL PRIMARY KEY,
    note_hash VARCHAR(64) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    version VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create an index on note_hash for faster lookups
CREATE INDEX IF NOT EXISTS idx_llm_cache_note_hash ON llm_cache (note_hash); 