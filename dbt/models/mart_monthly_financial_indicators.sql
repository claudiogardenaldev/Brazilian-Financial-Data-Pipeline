{{ config(materialized='table') }}

with observations as (
    select
        date_trunc('month', observed_on)::date as month,
        series_code,
        observed_on,
        value
    from {{ ref('stg_sgs_observations') }}
),
months as (
    select distinct month from observations
),
selic_last as (
    select month, value as selic_annual_pct
    from (
        select month, value,
               row_number() over (partition by month order by observed_on desc) as rn
        from observations where series_code = 1178
    ) ranked where rn = 1
),
ipca_last as (
    select month, value as ipca_monthly_pct
    from (
        select month, value,
               row_number() over (partition by month order by observed_on desc) as rn
        from observations where series_code = 433
    ) ranked where rn = 1
),
usd_monthly as (
    select month, avg(value) as usd_brl_avg
    from observations
    where series_code = 1
    group by month
)
select
    m.month,
    s.selic_annual_pct,
    i.ipca_monthly_pct,
    round(u.usd_brl_avg, 4) as usd_brl_avg
from months m
left join selic_last s using (month)
left join ipca_last i using (month)
left join usd_monthly u using (month)
order by m.month
