{{
  config(
    description='CPI data with calculated inflation rates and severity categories',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'}
    ]
  )
}}

with stg_cpi as (
  select *
  from {{ ref('stg_cpi') }}
),

cpi_with_mom as (
  select
    *,
    ((cpi_index - lag(cpi_index) over (order by period_date_key))
      / nullif(lag(cpi_index) over (order by period_date_key), 0)) * 100 as mom_change_pct
  from stg_cpi
),

cpi_with_rates as (
  select
    period_date,
    period_date_key,
    series_code,
    cpi_index,
    -- Year-over-year inflation rate
    {{ calculate_yoy_change('cpi_index', 'period_date_key', 12) }} as yoy_inflation_rate_pct,
    mom_change_pct,
    -- 3-month rolling inflation rate (avg of mom changes)
    {{ calculate_rolling_average('mom_change_pct', 'period_date_key', 3) }} as rolling_3m_inflation_pct,
    data_source,
    indicator_type,
    indicator_name,
    loaded_at,
    is_latest,
    dbt_loaded_at,
    current_timestamp as dbt_transformed_at
  from cpi_with_mom
)

select
  period_date,
  period_date_key,
  series_code,
  cpi_index,
  yoy_inflation_rate_pct,
  mom_change_pct,
  rolling_3m_inflation_pct,
  -- Categorize inflation severity
  case
    when yoy_inflation_rate_pct <= {{ var('inflation_mild_threshold', 2.5) }} then 'Mild'
    when yoy_inflation_rate_pct <= {{ var('inflation_moderate_threshold', 4.0) }} then 'Moderate'
    when yoy_inflation_rate_pct <= {{ var('inflation_high_threshold', 5.0) }} then 'High'
    else 'Severe'
  end as inflation_severity_category,
  data_source,
  indicator_type,
  indicator_name,
  loaded_at,
  is_latest,
  dbt_loaded_at,
  dbt_transformed_at
from cpi_with_rates
