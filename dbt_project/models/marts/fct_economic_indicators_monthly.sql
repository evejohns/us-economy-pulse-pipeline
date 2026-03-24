{{
  config(
    description='Monthly grain fact table with all monthly indicators, YoY changes, rolling averages, and data quality flags',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'},
      {'columns': ['year', 'month'], 'type': 'btree'}
    ],
    unique_id='period_date_key'
  )
}}

with cpi_base as (
  select
    period_date_key,
    cpi_index,
    yoy_inflation_rate_pct,
    inflation_severity_category,
    mom_change_pct as cpi_mom_change_pct
  from {{ ref('int_cpi_inflation_rates') }}
),

unemployment_base as (
  select
    period_date_key,
    unemployment_rate_pct,
    yoy_change_pct as unemployment_yoy_change_pct,
    trend_direction as unemployment_trend,
    is_labor_market_healthy
  from {{ ref('int_labor_market_metrics') }}
),

fedfunds_base as (
  select
    period_date_key,
    fedfunds_rate_pct,
    rate_direction as fedfunds_direction
  from {{ ref('int_financial_conditions') }}
  where fedfunds_rate_pct is not null
),

sentiment_base as (
  select
    period_date_key,
    sentiment_index,
    sentiment_outlook
  from {{ ref('int_financial_conditions') }}
  where sentiment_index is not null
),

housing_base as (
  select
    period_date_key,
    housing_starts_thousands
  from {{ ref('stg_housing_starts') }}
),

combined as (
  select
    coalesce(
      c.period_date_key,
      u.period_date_key,
      f.period_date_key,
      s.period_date_key,
      h.period_date_key
    ) as period_date_key,
    extract(year from coalesce(c.period_date_key, u.period_date_key, f.period_date_key, s.period_date_key, h.period_date_key)) as year,
    extract(month from coalesce(c.period_date_key, u.period_date_key, f.period_date_key, s.period_date_key, h.period_date_key)) as month,
    -- CPI / Inflation metrics
    c.cpi_index,
    c.yoy_inflation_rate_pct,
    c.inflation_severity_category,
    c.cpi_mom_change_pct,
    -- Unemployment metrics
    u.unemployment_rate_pct,
    u.unemployment_yoy_change_pct,
    u.unemployment_trend,
    u.is_labor_market_healthy,
    -- Federal Funds Rate
    f.fedfunds_rate_pct,
    f.fedfunds_direction,
    -- Sentiment
    s.sentiment_index,
    s.sentiment_outlook,
    -- Housing
    h.housing_starts_thousands,
    -- Data quality flags
    case when c.period_date_key is not null then 1 else 0 end +
    case when u.period_date_key is not null then 1 else 0 end +
    case when f.period_date_key is not null then 1 else 0 end +
    case when s.period_date_key is not null then 1 else 0 end +
    case when h.period_date_key is not null then 1 else 0 end as data_completeness_score,
    current_timestamp as dbt_loaded_at
  from cpi_base c
  full outer join unemployment_base u on c.period_date_key = u.period_date_key
  full outer join fedfunds_base f on c.period_date_key = f.period_date_key
  full outer join sentiment_base s on c.period_date_key = s.period_date_key
  full outer join housing_base h on c.period_date_key = h.period_date_key
)

select distinct on (period_date_key)
  period_date_key,
  year,
  month,
  concat(year, '-', lpad(month::text, 2, '0')) as year_month,
  cpi_index,
  yoy_inflation_rate_pct,
  inflation_severity_category,
  cpi_mom_change_pct,
  unemployment_rate_pct,
  unemployment_yoy_change_pct,
  unemployment_trend,
  is_labor_market_healthy,
  fedfunds_rate_pct,
  fedfunds_direction,
  sentiment_index,
  sentiment_outlook,
  housing_starts_thousands,
  data_completeness_score,
  case when data_completeness_score >= 4 then true else false end as is_data_complete,
  dbt_loaded_at
from combined
order by period_date_key desc
