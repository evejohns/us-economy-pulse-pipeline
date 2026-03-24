{{
  config(
    description='Labor market metrics with YoY changes, rolling averages, and trend indicators',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'}
    ]
  )
}}

with stg_unemployment as (
  select *
  from {{ ref('stg_unemployment_rate') }}
),

unemployment_with_metrics as (
  select
    period_date,
    period_date_key,
    series_code,
    unemployment_rate_pct,
    -- Year-over-year change in unemployment rate
    {{ calculate_yoy_change('unemployment_rate_pct', 'period_date_key', 12) }} as yoy_change_pct,
    -- Month-over-month change
    (unemployment_rate_pct - lag(unemployment_rate_pct) over (order by period_date_key)) as mom_change_pct,
    -- 3-month rolling average
    {{ calculate_rolling_average('unemployment_rate_pct', 'period_date_key', 3) }} as rolling_3m_avg_pct,
    -- Determine trend direction
    case
      when unemployment_rate_pct > lag(unemployment_rate_pct) over (order by period_date_key) then 'Rising'
      when unemployment_rate_pct < lag(unemployment_rate_pct) over (order by period_date_key) then 'Declining'
      else 'Flat'
    end as trend_direction,
    data_source,
    indicator_type,
    indicator_name,
    loaded_at,
    is_latest,
    dbt_loaded_at,
    current_timestamp as dbt_transformed_at
  from stg_unemployment
)

select
  period_date,
  period_date_key,
  series_code,
  unemployment_rate_pct,
  yoy_change_pct,
  mom_change_pct,
  rolling_3m_avg_pct,
  trend_direction,
  -- Health flag: labor market considered healthy if unemployment is low and declining
  case
    when unemployment_rate_pct < 5.0 and trend_direction in ('Declining', 'Flat') then true
    else false
  end as is_labor_market_healthy,
  data_source,
  indicator_type,
  indicator_name,
  loaded_at,
  is_latest,
  dbt_loaded_at,
  dbt_transformed_at
from unemployment_with_metrics
