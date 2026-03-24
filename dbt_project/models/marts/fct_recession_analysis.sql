{{
  config(
    description='Quarterly grain fact table focused on recession analysis with risk levels, intensity scores, and contributing factors',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'},
      {'columns': ['year', 'quarter'], 'type': 'btree'},
      {'columns': ['recession_risk_level'], 'type': 'btree'}
    ]
  )
}}

with recession_data as (
  select
    extract(year from ri.period_date_key) as year,
    extract(quarter from ri.period_date_key) as quarter,
    ri.period_date_key,
    ri.gdp_billions_usd,
    ri.qoq_growth_pct,
    ri.yoy_growth_pct,
    ri.unemployment_rate_pct,
    ri.unemployment_yoy_change_pct,
    ri.yoy_inflation_rate_pct,
    ri.sentiment_index,
    ri.recession_risk_level,
    ri.recession_intensity_score,
    ri.consecutive_negative_quarters,
    -- Identify contributing factors
    case when ri.qoq_growth_pct < 0 then 'Negative GDP Growth' else null end as factor_1,
    case when ri.unemployment_yoy_change_pct > 1.0 then 'Rapid Job Losses' else null end as factor_2,
    case when ri.yoy_inflation_rate_pct > 5.0 then 'High Inflation' else null end as factor_3,
    case when ri.sentiment_index < 100 then 'Weak Consumer Sentiment' else null end as factor_4,
    current_timestamp as dbt_loaded_at
  from {{ ref('int_recession_indicators') }} ri
)

select
  period_date_key,
  year,
  quarter,
  concat(year, '-Q', quarter) as year_quarter,
  gdp_billions_usd,
  qoq_growth_pct,
  yoy_growth_pct,
  unemployment_rate_pct,
  unemployment_yoy_change_pct,
  yoy_inflation_rate_pct,
  sentiment_index,
  recession_risk_level,
  recession_intensity_score,
  consecutive_negative_quarters,
  -- Aggregate contributing factors
  concat_ws(', ', factor_1, factor_2, factor_3, factor_4) as recession_contributing_factors,
  -- Count number of contributing factors
  (case when factor_1 is not null then 1 else 0 end +
   case when factor_2 is not null then 1 else 0 end +
   case when factor_3 is not null then 1 else 0 end +
   case when factor_4 is not null then 1 else 0 end) as num_contributing_factors,
  -- Risk assessment summary
  case
    when recession_risk_level = 'High' then 'Imminent recession risk with multiple distress signals'
    when recession_risk_level = 'Moderate' then 'Elevated recession risk, continued monitoring warranted'
    when recession_risk_level = 'Emerging' then 'Early warning signs present, situation developing'
    else 'Low recession risk, economy functioning normally'
  end as risk_assessment_summary,
  dbt_loaded_at
from recession_data
order by period_date_key desc
