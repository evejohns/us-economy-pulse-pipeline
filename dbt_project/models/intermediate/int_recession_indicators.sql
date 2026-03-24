{{
  config(
    description='Comprehensive recession analysis joining GDP, unemployment, inflation, and sentiment with recession risk scoring',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'}
    ]
  )
}}

with gdp_data as (
  select
    period_date_key,
    gdp_billions_usd,
    qoq_growth_pct,
    yoy_growth_pct,
    is_qoq_negative_growth,
    is_yoy_negative_growth
  from {{ ref('int_gdp_with_yoy_change') }}
),

unemployment_data as (
  select
    period_date_key,
    unemployment_rate_pct,
    yoy_change_pct as unemployment_yoy_change_pct,
    is_labor_market_healthy
  from {{ ref('int_labor_market_metrics') }}
),

inflation_data as (
  select
    period_date_key,
    yoy_inflation_rate_pct,
    inflation_severity_category
  from {{ ref('int_cpi_inflation_rates') }}
),

sentiment_data as (
  select
    period_date_key,
    sentiment_index,
    sentiment_outlook
  from {{ ref('int_financial_conditions') }}
),

combined as (
  select
    g.period_date_key,
    g.gdp_billions_usd,
    g.qoq_growth_pct,
    g.yoy_growth_pct,
    g.is_qoq_negative_growth,
    u.unemployment_rate_pct,
    u.unemployment_yoy_change_pct,
    i.yoy_inflation_rate_pct,
    i.inflation_severity_category,
    s.sentiment_index,
    s.sentiment_outlook,
    -- Count consecutive negative GDP quarters (lag and look back)
    count(case when g.is_qoq_negative_growth then 1 end)
      over (order by g.period_date_key rows between 3 preceding and current row) as consecutive_negative_quarters,
    current_timestamp as dbt_transformed_at
  from gdp_data g
  left join unemployment_data u on g.period_date_key = u.period_date_key
  left join inflation_data i on g.period_date_key = i.period_date_key
  left join sentiment_data s on g.period_date_key = s.period_date_key
)

select
  period_date_key,
  gdp_billions_usd,
  qoq_growth_pct,
  yoy_growth_pct,
  unemployment_rate_pct,
  unemployment_yoy_change_pct,
  yoy_inflation_rate_pct,
  inflation_severity_category,
  sentiment_index,
  sentiment_outlook,
  consecutive_negative_quarters,
  -- Recession Risk Level: indicator of probability/imminence of recession
  case
    when consecutive_negative_quarters >= {{ var('consecutive_negative_quarters_threshold', 2) }} then 'High'
    when is_qoq_negative_growth and unemployment_yoy_change_pct > 0.5 then 'High'
    when (is_qoq_negative_growth or yoy_growth_pct < 2.0) and sentiment_outlook = 'Pessimistic' then 'Moderate'
    when yoy_growth_pct between 2.0 and 2.5 and unemployment_yoy_change_pct > 0 then 'Emerging'
    else 'Low'
  end as recession_risk_level,
  -- Recession Intensity Score (0-10): composite score of economic distress
  round(
    case
      when is_qoq_negative_growth then 3 else 0 end +
      case when yoy_growth_pct < 0 then 5 else case when yoy_growth_pct < 2 then 2 else 0 end end +
      case when unemployment_rate_pct > 5.5 then 2 else case when unemployment_rate_pct > 4.5 then 1 else 0 end end +
      case when unemployment_yoy_change_pct > 1 then 2 else case when unemployment_yoy_change_pct > 0.5 then 1 else 0 end end +
      case when inflation_severity_category in ('High', 'Severe') then 1 else 0 end +
      case when sentiment_outlook = 'Pessimistic' then 1 else 0 end,
    2
  ) as recession_intensity_score,
  dbt_transformed_at
from combined
