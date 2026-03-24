{{
  config(
    description='Staging layer for Consumer Sentiment Index data from FRED (UMCSENT). Monthly data cleaned and standardized.',
    meta={
      'owner': 'analytics',
      'frequency': 'monthly'
    }
  )
}}

with raw_sentiment as (
  select
    observation_date,
    series_id,
    value,
    ingested_at
  from {{ source('fred_raw', 'raw_consumer_sentiment') }}
  where value is not null
)

select
  observation_date as period_date,
  cast(observation_date as date) as period_date_key,
  series_id as series_code,
  cast(value as numeric(8, 2)) as sentiment_index,
  'FRED' as data_source,
  'Consumer Confidence' as indicator_type,
  'UMCSENT' as indicator_name,
  ingested_at as loaded_at,
  row_number() over (order by observation_date desc) = 1 as is_latest,
  current_timestamp as dbt_loaded_at
from raw_sentiment
