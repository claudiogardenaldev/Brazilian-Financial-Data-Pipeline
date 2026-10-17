-- Executado automaticamente pelo contêiner PostgreSQL apenas no primeiro start do volume.
CREATE DATABASE airflow;
CREATE SCHEMA IF NOT EXISTS finance;
CREATE TABLE IF NOT EXISTS finance.observations (
    series_code INTEGER NOT NULL,
    observed_on DATE NOT NULL,
    value NUMERIC(20, 8) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (series_code, observed_on),
    CONSTRAINT observations_positive CHECK (series_code NOT IN (1,1178) OR value > 0)
);
CREATE INDEX IF NOT EXISTS idx_observations_date ON finance.observations (observed_on);
CREATE TABLE IF NOT EXISTS finance.pipeline_runs (
    run_id UUID PRIMARY KEY,
    series_code INTEGER NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN ('success','failed')),
    records_processed INTEGER NOT NULL DEFAULT 0,
    detail TEXT
);
