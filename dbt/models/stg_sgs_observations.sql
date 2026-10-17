{{ config(materialized='view') }}

select
    series_code,
    observed_on,
    value,
    fetched_at
from finance.observations
