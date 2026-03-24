{{
  config(
    description='Quarterly grain fact table with GDP metrics and averaged monthly indicators plus recession signals',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'},
      {'columns': ['year', 'quarter'], 'type': 'btree'}
    ],
    unique_id='period_date_key'
  )
}}

with gdp_base as (
  select
    period_date_key,
    gdp_billions_usd,
    qoq_growth_pct,
    yoy_growth_pct,
    is_qoq_negative_growth,
    is_yoy_negative_growth
  from {{ ref('int_gdp_with_yoy_change') }}
),

quarterly_averages as (
  -- Average monthly indicators to quarterly level
  select
    date_trunc('quarter', m.period_date_key::date)::date as period_date_key,
    extract(year from date_trunc('quarter', m.period_date_key::date)) as year,
    extract(quarter from date_trunc('quarter', m.period_date_key::date)) as quarter,
    avg(m.cpi_index) as avg_cpi_index,
    avg(m.yoy_inflation_rate_pct) as avg_yoy_inflation_rate_pct,
    avg(m.unemployment_rate_pct) as avg_unemployment_rate_pct,
    avg(m.unemployment_yoy_change_pct) as avg_unemployment_yoy_change_pct,
    avg(m.fedfunds_rate_pct) as avg_fedfunds_rate_pct,
    avg(m.sentiment_index) as avg_sentiment_index,
    avg(m.housing_starts_thousands) as avg_housing_starts_thousands
  from {{ ref('fct_economic_indicators_monthly') }} m
  group by 1, 2, 3
),

recession_signals as (
  select
    period_date_key,
    recession_risk_level,
    recession_intensity_score,
    consecutive_negative_quarters
  from {{ ref('int_recession_indicators') }}
),

combined as (
  select
    coalesce(g.period_date_key, qa.period_date_key) as period_date_key,
    coalesce(g.period_date_key, qa.period_date_key) as period_date_quarter,
    coalesce(extract(year from g.period_date_key), qa.year) as year,
    coalesce(extract(quarter from g.period_date_key), qa.quarter) as quarter,
    g.gdp_billions_usd,
    g.qoq_growth_pct,
    g.yoy_growth_pct,
    g.is_qoq_negative_growth,
    g.is_yoy_negative_growth,
    qa.avg_cpi_index,
    qa.avg_yoy_inflation_rate_pct,
    qa.avg_unemployment_rate_pct,
    qa.avg_unemployment_yoy_change_pct,
    qa.avg_fedfunds_rate_pct,
    qa.avg_sentiment_index,
    qa.avg_housing_starts_thousands,
    rs.recession_risk_level,
    rs.recession_intensity_score,
    rs.consecutive_negative_quarters,
    current_timestamp as dbt_loaded_at
  from gdp_base g
  full outer join quarterly_averages qa on g.period_date_key = qa.period_date_key
  left join recession_signals rs on g.period_date_key = rs.period_date_key
)

select
  period_date_key,
  period_date_quarter,
  year,
  quarter,
  concat(year, '-Q', quarter) as year_quarter,
  gdp_billions_usd,
  qoq_growth_pct,
  yoy_growth_pct,
  is_qoq_negative_growth,
  is_yoy_negative_growth,
  avg_cpi_index,
  avg_yoy_inflation_rate_pct,
  avg_unemployment_rate_pct,
  avg_unemployment_yoy_change_pct,
  avg_fedfunds_rate_pct,
  avg_sentiment_index,
  avg_housing_starts_thousands,
  recession_risk_level,
  recession_intensity_score,
  consecutive_negative_quarters,
  dbt_loaded_at
from combined
order by period_date_key desc
