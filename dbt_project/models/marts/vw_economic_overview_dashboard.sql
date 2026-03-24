{{
  config(
    description='Wide denormalized view combining latest economic metrics for dashboard display',
    materialized='view'
  )
}}

with latest_monthly as (
  select
    m.*,
    row_number() over (order by m.period_date_key desc) as rn
  from {{ ref('fct_economic_indicators_monthly') }} m
),

latest_quarterly as (
  select
    q.*,
    row_number() over (order by q.period_date_key desc) as rn
  from {{ ref('fct_economic_indicators_quarterly') }} q
),

latest_recession as (
  select
    r.*,
    row_number() over (order by r.period_date_key desc) as rn
  from {{ ref('fct_recession_analysis') }} r
),

period_dim as (
  select
    p.*,
    row_number() over (order by p.period_date desc) as rn
  from {{ ref('dim_economic_periods') }} p
)

select
  -- Monthly record info
  lm.period_date_key as latest_month,
  lm.year_month,
  -- Economic indicators
  lm.cpi_index,
  lm.yoy_inflation_rate_pct,
  lm.inflation_severity_category,
  lm.unemployment_rate_pct,
  lm.unemployment_yoy_change_pct,
  lm.unemployment_trend,
  lm.fedfunds_rate_pct,
  lm.fedfunds_direction,
  lm.sentiment_index,
  lm.sentiment_outlook,
  lm.housing_starts_thousands,
  -- Labor market health
  lm.is_labor_market_healthy,
  -- Quarterly GDP data
  lq.gdp_billions_usd,
  lq.qoq_growth_pct,
  lq.yoy_growth_pct,
  -- Recession analysis
  lr.recession_risk_level,
  lr.recession_intensity_score,
  lr.recession_contributing_factors,
  lr.num_contributing_factors,
  lr.risk_assessment_summary,
  -- Period dimensions
  pd.year,
  pd.month,
  pd.quarter,
  pd.is_nber_recession_period,
  pd.recession_name,
  -- Data quality
  lm.data_completeness_score,
  lm.is_data_complete,
  -- Timestamps
  lm.dbt_loaded_at
from latest_monthly lm
left join latest_quarterly lq on lq.rn = 1
left join latest_recession lr on lr.rn = 1
left join period_dim pd on pd.rn = 1
where lm.rn = 1
