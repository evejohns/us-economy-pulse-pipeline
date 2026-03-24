{{
  config(
    description='Monthly grain fact table focused on inflation analysis with rates, severity, and Fed response indicators',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'},
      {'columns': ['year', 'month'], 'type': 'btree'},
      {'columns': ['inflation_severity_category'], 'type': 'btree'}
    ]
  )
}}

with inflation_data as (
  select
    m.period_date_key,
    m.year,
    m.month,
    m.cpi_index,
    m.yoy_inflation_rate_pct,
    m.inflation_severity_category,
    m.cpi_mom_change_pct,
    m.fedfunds_rate_pct,
    m.fedfunds_direction,
    -- Calculate Fed response to inflation
    case
      when m.fedfunds_direction = 'Rising' and m.yoy_inflation_rate_pct > 3.0 then 'Tightening Response'
      when m.fedfunds_direction = 'Falling' and m.yoy_inflation_rate_pct > 3.0 then 'Accommodative Despite Inflation'
      when m.fedfunds_direction = 'Rising' and m.yoy_inflation_rate_pct < 2.0 then 'Restrictive'
      when m.fedfunds_direction = 'Flat' then 'Neutral'
      else 'Accommodative'
    end as fed_policy_stance_to_inflation,
    -- Inflation momentum (computed here so it can be referenced below)
    lag(m.yoy_inflation_rate_pct) over (order by m.period_date_key) as prev_yoy_inflation_rate_pct,
    case
      when m.yoy_inflation_rate_pct > lag(m.yoy_inflation_rate_pct) over (order by m.period_date_key) then 'Accelerating'
      when m.yoy_inflation_rate_pct < lag(m.yoy_inflation_rate_pct) over (order by m.period_date_key) then 'Decelerating'
      else 'Stable'
    end as inflation_momentum,
    current_timestamp as dbt_loaded_at
  from {{ ref('fct_economic_indicators_monthly') }} m
)

select
  period_date_key,
  year,
  month,
  concat(year, '-', lpad(month::text, 2, '0')) as year_month,
  cpi_index,
  yoy_inflation_rate_pct,
  round((yoy_inflation_rate_pct - prev_yoy_inflation_rate_pct)::numeric, 2) as mom_inflation_change_pct,
  inflation_severity_category,
  cpi_mom_change_pct,
  fedfunds_rate_pct,
  fedfunds_direction,
  fed_policy_stance_to_inflation,
  inflation_momentum,
  -- Policy effectiveness assessment
  case
    when fed_policy_stance_to_inflation = 'Tightening Response' and inflation_momentum = 'Decelerating' then 'Effective'
    when fed_policy_stance_to_inflation = 'Tightening Response' and inflation_momentum = 'Accelerating' then 'Insufficient'
    when fed_policy_stance_to_inflation in ('Accommodative', 'Accommodative Despite Inflation') and inflation_momentum = 'Accelerating' then 'Permissive'
    else 'Neutral'
  end as fed_policy_effectiveness,
  dbt_loaded_at
from inflation_data
order by period_date_key desc
