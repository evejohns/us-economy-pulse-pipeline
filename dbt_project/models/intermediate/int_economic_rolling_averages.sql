{{
  config(
    description='Unified rolling averages (3M, 6M, 12M) for all monthly indicators using UNION approach',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key', 'indicator_type'], 'type': 'btree'}
    ]
  )
}}

-- CPI rolling averages
with cpi_rolling as (
  select
    period_date_key,
    'CPI' as indicator_type,
    {{ calculate_rolling_average('cpi_index', 'period_date_key', 3) }} as rolling_3m_avg,
    {{ calculate_rolling_average('cpi_index', 'period_date_key', 6) }} as rolling_6m_avg,
    {{ calculate_rolling_average('cpi_index', 'period_date_key', 12) }} as rolling_12m_avg,
    'Inflation' as metric_category,
    current_timestamp as dbt_loaded_at
  from {{ ref('stg_cpi') }}
),

-- Unemployment rolling averages
unemployment_rolling as (
  select
    period_date_key,
    'Unemployment Rate' as indicator_type,
    {{ calculate_rolling_average('unemployment_rate_pct', 'period_date_key', 3) }} as rolling_3m_avg,
    {{ calculate_rolling_average('unemployment_rate_pct', 'period_date_key', 6) }} as rolling_6m_avg,
    {{ calculate_rolling_average('unemployment_rate_pct', 'period_date_key', 12) }} as rolling_12m_avg,
    'Labor Market' as metric_category,
    current_timestamp as dbt_loaded_at
  from {{ ref('stg_unemployment_rate') }}
),

-- Federal Funds Rate rolling averages
fedfunds_rolling as (
  select
    period_date_key,
    'Federal Funds Rate' as indicator_type,
    {{ calculate_rolling_average('fedfunds_rate_pct', 'period_date_key', 3) }} as rolling_3m_avg,
    {{ calculate_rolling_average('fedfunds_rate_pct', 'period_date_key', 6) }} as rolling_6m_avg,
    {{ calculate_rolling_average('fedfunds_rate_pct', 'period_date_key', 12) }} as rolling_12m_avg,
    'Monetary Policy' as metric_category,
    current_timestamp as dbt_loaded_at
  from {{ ref('stg_federal_funds_rate') }}
),

-- Consumer Sentiment rolling averages
sentiment_rolling as (
  select
    period_date_key,
    'Consumer Sentiment' as indicator_type,
    {{ calculate_rolling_average('sentiment_index', 'period_date_key', 3) }} as rolling_3m_avg,
    {{ calculate_rolling_average('sentiment_index', 'period_date_key', 6) }} as rolling_6m_avg,
    {{ calculate_rolling_average('sentiment_index', 'period_date_key', 12) }} as rolling_12m_avg,
    'Consumer Confidence' as metric_category,
    current_timestamp as dbt_loaded_at
  from {{ ref('stg_consumer_sentiment') }}
),

-- Housing Starts rolling averages
housing_rolling as (
  select
    period_date_key,
    'Housing Starts' as indicator_type,
    {{ calculate_rolling_average('housing_starts_thousands', 'period_date_key', 3) }} as rolling_3m_avg,
    {{ calculate_rolling_average('housing_starts_thousands', 'period_date_key', 6) }} as rolling_6m_avg,
    {{ calculate_rolling_average('housing_starts_thousands', 'period_date_key', 12) }} as rolling_12m_avg,
    'Construction Activity' as metric_category,
    current_timestamp as dbt_loaded_at
  from {{ ref('stg_housing_starts') }}
)

-- Union all rolling averages
select
  period_date_key,
  indicator_type,
  rolling_3m_avg,
  rolling_6m_avg,
  rolling_12m_avg,
  metric_category,
  dbt_loaded_at
from cpi_rolling

union all

select * from unemployment_rolling

union all

select * from fedfunds_rolling

union all

select * from sentiment_rolling

union all

select * from housing_rolling
