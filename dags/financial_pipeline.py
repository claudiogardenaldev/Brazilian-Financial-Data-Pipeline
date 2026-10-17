"""DAG: coleta incremental diária das séries do Banco Central.

O dbt é executado separadamente com o perfil 'transformation' do Compose.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="bcb_financial_indicators",
    start_date=datetime(2024, 1, 1),
    schedule="0 10 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["portfolio", "bcb", "financial-data"],
) as dag:
    ingest = BashOperator(
        task_id="extract_validate_upsert",
        bash_command="python -m financial_pipeline.cli --lookback-days 60",
    )
