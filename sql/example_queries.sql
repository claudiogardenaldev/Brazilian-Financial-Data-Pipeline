-- Dados de exemplo para BI após executar dbt build.
SELECT * FROM analytics.mart_monthly_financial_indicators ORDER BY month DESC LIMIT 12;

-- Histórico de execuções e falhas
SELECT series_code, status, executed_at, records_processed, detail
FROM finance.pipeline_runs ORDER BY executed_at DESC LIMIT 20;

-- Validação de idempotência (não há mais de uma linha por série/data)
SELECT series_code, observed_on, count(*) AS repetitions
FROM finance.observations
GROUP BY series_code, observed_on
HAVING count(*) > 1;
