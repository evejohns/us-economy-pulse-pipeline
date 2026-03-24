{{
  config(
    description='Staging layer for Consumer Price Index data from FRED (CPIAUCSL). Monthly data cleaned and standardized.',
    meta={
      'owner': 'analytics',
      'frequency': 'monthly'
    }
  )
}}

with raw_cpi as (
  select
    observation_date,
    series_id,
    value,
    ingested_at
  from {{ source('fred_raw', 'raw_cpi') }}
  where value is not null
)

select
  observation_date as period_date,
  cast(observation_date as date) as period_date_key,
  series_id as series_code,
  cast(value as numeric(18, 4)) as cpi_index,
  'FRED' as data_source,
  'Inflation' as indicator_type,
  'CPIAUCSL' as indicator_name,
  ingested_at as loaded_at,
  row_number() over (order by observation_date desc) = 1 as is_latest,
  current_timestamp as dbt_loaded_at
from raw_cpi
