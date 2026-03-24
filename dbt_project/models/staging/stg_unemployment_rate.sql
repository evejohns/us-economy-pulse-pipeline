{{
  config(
    description='Staging layer for Unemployment Rate data from FRED (UNRATE). Monthly data cleaned and standardized.',
    meta={
      'owner': 'analytics',
      'frequency': 'monthly'
    }
  )
}}

with raw_unemployment as (
  select
    observation_date,
    series_id,
    value,
    ingested_at
  from {{ source('fred_raw', 'raw_unemployment') }}
  where value is not null
)

select
  observation_date as period_date,
  cast(observation_date as date) as period_date_key,
  series_id as series_code,
  cast(value as numeric(6, 2)) as unemployment_rate_pct,
  'FRED' as data_source,
  'Labor Market' as indicator_type,
  'UNRATE' as indicator_name,
  ingested_at as loaded_at,
  row_number() over (order by observation_date desc) = 1 as is_latest,
  current_timestamp as dbt_loaded_at
from raw_unemployment
