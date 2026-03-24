{{
  config(
    description='Monthly grain fact table focused on employment analysis with unemployment trends, housing indicators, and labor market health',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'},
      {'columns': ['year', 'month'], 'type': 'btree'},
      {'columns': ['unemployment_trend'], 'type': 'btree'}
    ]
  )
}}

with employment_data as (
  select
    m.period_date_key,
    m.year,
    m.month,
    m.unemployment_rate_pct,
    m.unemployment_yoy_change_pct,
    m.unemployment_trend,
    m.is_labor_market_healthy,
    m.housing_starts_thousands,
    -- Calculate labor market health score (0-10 scale)
    (
      case when m.unemployment_rate_pct < 4.0 then 3 else 0 end +
      case when m.unemployment_rate_pct between 4.0 and 5.0 then 2 else 0 end +
      case when m.unemployment_trend = 'Declining' then 2 else case when m.unemployment_trend = 'Flat' then 1 else 0 end end +
      case when m.unemployment_yoy_change_pct < 0 then 2 else case when m.unemployment_yoy_change_pct < 0.5 then 1 else 0 end end +
      case when m.housing_starts_thousands > 1500 then 2 else case when m.housing_starts_thousands > 1200 then 1 else 0 end end
    ) as labor_market_health_score,
    -- Housing as leading indicator
    lag(m.housing_starts_thousands, 6) over (order by m.period_date_key) as housing_starts_6m_ago,
    current_timestamp as dbt_loaded_at
  from {{ ref('fct_economic_indicators_monthly') }} m
)

select
  period_date_key,
  year,
  month,
  concat(year, '-', lpad(month::text, 2, '0')) as year_month,
  unemployment_rate_pct,
  unemployment_yoy_change_pct,
  unemployment_trend,
  is_labor_market_healthy,
  housing_starts_thousands,
  -- Housing leading indicator assessment
  round(((housing_starts_thousands - housing_starts_6m_ago) / housing_starts_6m_ago) * 100, 2) as housing_starts_6m_change_pct,
  case
    when housing_starts_thousands > housing_starts_6m_ago then 'Positive'
    when housing_starts_thousands < housing_starts_6m_ago then 'Negative'
    else 'Flat'
  end as housing_leading_indicator,
  labor_market_health_score,
  case
    when labor_market_health_score >= 8 then 'Excellent'
    when labor_market_health_score >= 6 then 'Good'
    when labor_market_health_score >= 4 then 'Fair'
    else 'Weak'
  end as labor_market_condition,
  -- Combined assessment
  case
    when is_labor_market_healthy and housing_starts_thousands > 1500 then 'Robust Employment'
    when is_labor_market_healthy and housing_starts_thousands between 1000 and 1500 then 'Solid Employment'
    when unemployment_rate_pct < 4.5 and unemployment_trend in ('Declining', 'Flat') then 'Tightening Labor Market'
    when unemployment_yoy_change_pct > 0.5 then 'Deteriorating Labor Market'
    else 'Moderate Employment'
  end as employment_assessment,
  dbt_loaded_at
from employment_data
order by period_date_key desc
