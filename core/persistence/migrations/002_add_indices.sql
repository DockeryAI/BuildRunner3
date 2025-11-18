-- Add additional indices for performance optimization
-- Migration: 002_add_indices.sql

-- Add composite index for common cost queries
CREATE INDEX IF NOT EXISTS idx_cost_model_timestamp
ON cost_entries(model_name, timestamp);

-- Add index for metrics queries by period type and timestamp
CREATE INDEX IF NOT EXISTS idx_metrics_period_timestamp
ON metrics_hourly(period_type, timestamp);

-- ROLLBACK:
-- DROP INDEX IF EXISTS idx_cost_model_timestamp;
-- DROP INDEX IF EXISTS idx_metrics_period_timestamp;
