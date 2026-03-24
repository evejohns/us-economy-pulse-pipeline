{{
  config(
    description='Cross-correlations between key economic indicators using rolling 12-quarter windows',
    materialized='table',
    indexes=[
      {'columns': ['period_date_key'], 'type': 'btree'}
    ]
  )
}}

with normalized_data as (
  -- Normalize all quarterly data to same grain
  select
    g.period_date_key,
    g.gdp_billions_usd,
    u.unemployment_rate_pct,
    i.yoy_inflation_rate_pct,
    f.fedfunds_rate_pct,
    s.sentiment_index
  from {{ ref('int_gdp_with_yoy_change') }} g
  left join {{ ref('int_labor_market_metrics') }} u
    on g.period_date_key = (date_trunc('quarter', u.period_date_key::date))::date
  left join {{ ref('int_cpi_inflation_rates') }} i
    on g.period_date_key = (date_trunc('quarter', i.period_date_key::date))::date
  left join {{ ref('stg_federal_funds_rate') }} f
    on g.period_date_key = (date_trunc('quarter', f.period_date_key::date))::date
  left join {{ ref('stg_consumer_sentiment') }} s
    on g.period_date_key = (date_trunc('quarter', s.period_date_key::date))::date
),

rolling_correlations as (
  select
    period_date_key,
    -- GDP vs Unemployment (inverse correlation expected)
    round(
      corr(gdp_billions_usd, unemployment_rate_pct)
        over (order by period_date_key rows between 11 preceding and current row)::numeric,
      3
    ) as gdp_vs_unemployment_corr,
    -- Inflation vs Federal Funds Rate (positive correlation expected)
    round(
      corr(yoy_inflation_rate_pct, fedfunds_rate_pct)
        over (order by period_date_key rows between 11 preceding and current row)::numeric,
      3
    ) as inflation_vs_fedfunds_corr,
    -- GDP vs Consumer Sentiment (positive correlation expected)
    round(
      corr(gdp_billions_usd, sentiment_index)
        over (order by period_date_key rows between 11 preceding and current row)::numeric,
      3
    ) as gdp_vs_sentiment_corr,
    -- Unemployment vs Consumer Sentiment (inverse correlation expected)
    round(
      corr(unemployment_rate_pct, sentiment_index)
        over (order by period_date_key rows between 11 preceding and current row)::numeric,
      3
    ) as unemployment_vs_sentiment_corr,
    -- Inflation vs Consumer Sentiment (inverse correlation expected)
    round(
      corr(yoy_inflation_rate_pct, sentiment_index)
        over (order by period_date_key rows between 11 preceding and current row)::numeric,
      3
    ) as inflation_vs_sentiment_corr,
    current_timestamp as dbt_loaded_at
  from normalized_data
  where gdp_billions_usd is not null
)

select distinct on (period_date_key)
  period_date_key,
  gdp_vs_unemployment_corr,
  inflation_vs_fedfunds_corr,
  gdp_vs_sentiment_corr,
  unemployment_vs_sentiment_corr,
  inflation_vs_sentiment_corr,
  -- Relationship quality assessment
  case
    when gdp_vs_unemployment_corr < -0.5 then 'Strong Inverse'
    when gdp_vs_unemployment_corr between -0.5 and -0.2 then 'Moderate Inverse'
    when gdp_vs_unemployment_corr between -0.2 and 0.2 then 'Weak'
    else 'Positive'
  end as gdp_unemployment_relationship,
  case
    when inflation_vs_fedfunds_corr > 0.5 then 'Strong Positive'
    when inflation_vs_fedfunds_corr > 0.2 then 'Moderate Positive'
    else 'Weak'
  end as inflation_fedfunds_relationship,
  dbt_loaded_at
from rolling_correlations
