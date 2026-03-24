{{
  config(
    description='Financial conditions metrics: Federal Funds Rate and Consumer Sentiment with trend analysis',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'}
    ]
  )
}}

with stg_fedfunds as (
  select *
  from {{ ref('stg_federal_funds_rate') }}
),

stg_sentiment as (
  select *
  from {{ ref('stg_consumer_sentiment') }}
),

fedfunds_with_trends as (
  select
    period_date,
    period_date_key,
    series_code,
    fedfunds_rate_pct,
    (fedfunds_rate_pct - lag(fedfunds_rate_pct) over (order by period_date_key)) as rate_change_bps,
    case
      when fedfunds_rate_pct > lag(fedfunds_rate_pct) over (order by period_date_key) then 'Rising'
      when fedfunds_rate_pct < lag(fedfunds_rate_pct) over (order by period_date_key) then 'Falling'
      else 'Flat'
    end as rate_direction,
    dbt_loaded_at,
    current_timestamp as dbt_transformed_at
  from stg_fedfunds
),

sentiment_with_metrics as (
  select
    period_date,
    period_date_key,
    series_code,
    sentiment_index,
    {{ calculate_yoy_change('sentiment_index', 'period_date_key', 12) }} as yoy_change_pct,
    case
      when sentiment_index > 100 then 'Optimistic'
      when sentiment_index < 100 then 'Pessimistic'
      else 'Neutral'
    end as sentiment_outlook,
    dbt_loaded_at
  from stg_sentiment
)

select
  coalesce(f.period_date, s.period_date) as period_date,
  coalesce(f.period_date_key, s.period_date_key) as period_date_key,
  f.fedfunds_rate_pct,
  f.rate_change_bps,
  f.rate_direction,
  s.sentiment_index,
  s.yoy_change_pct as sentiment_yoy_change_pct,
  s.sentiment_outlook,
  -- Financial stress indicator: rising rates + pessimistic sentiment
  case
    when f.rate_direction = 'Rising' and s.sentiment_outlook = 'Pessimistic' then true
    else false
  end as is_financial_stress_elevated,
  coalesce(f.dbt_loaded_at, s.dbt_loaded_at) as dbt_loaded_at,
  coalesce(f.dbt_transformed_at, s.dbt_loaded_at) as dbt_transformed_at
from fedfunds_with_trends f
full outer join sentiment_with_metrics s
  on f.period_date_key = s.period_date_key
