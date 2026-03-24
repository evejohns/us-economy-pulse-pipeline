{{
  config(
    description='GDP data with calculated growth metrics (QoQ and YoY changes, growth flags)',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'}
    ]
  )
}}

with stg_gdp as (
  select *
  from {{ ref('stg_gdp') }}
),

gdp_with_changes as (
  select
    period_date,
    period_date_key,
    series_code,
    gdp_billions_usd,
    -- Quarter-over-quarter change (4 quarters = 1 year, so lag by 1 for QoQ)
    lag(gdp_billions_usd) over (order by period_date_key) as prev_quarter_gdp,
    ((gdp_billions_usd - lag(gdp_billions_usd) over (order by period_date_key))
      / lag(gdp_billions_usd) over (order by period_date_key)) * 100 as qoq_growth_pct,
    -- Year-over-year change (4 quarters = 1 year, so lag by 4)
    {{ calculate_yoy_change('gdp_billions_usd', 'period_date_key', 4) }} as yoy_growth_pct,
    data_source,
    indicator_type,
    indicator_name,
    loaded_at,
    is_latest,
    dbt_loaded_at,
    current_timestamp as dbt_transformed_at
  from stg_gdp
)

select
  period_date,
  period_date_key,
  series_code,
  gdp_billions_usd,
  qoq_growth_pct,
  yoy_growth_pct,
  case
    when qoq_growth_pct < 0 then true
    else false
  end as is_qoq_negative_growth,
  case
    when yoy_growth_pct < 0 then true
    else false
  end as is_yoy_negative_growth,
  data_source,
  indicator_type,
  indicator_name,
  loaded_at,
  is_latest,
  dbt_loaded_at,
  dbt_transformed_at
from gdp_with_changes
