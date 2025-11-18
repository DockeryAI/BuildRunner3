-- Initial database schema for BuildRunner persistence layer
-- Migration: 001_initial.sql

-- Cost tracking table
CREATE TABLE cost_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task_id TEXT,
    model_name TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    session_id TEXT
);

-- Indices for common queries
CREATE INDEX idx_cost_timestamp ON cost_entries(timestamp);
CREATE INDEX idx_cost_task_id ON cost_entries(task_id);
CREATE INDEX idx_cost_session_id ON cost_entries(session_id);
