{{
  config(
    description='Staging layer for Real GDP data from FRED (GDPC1). Quarterly data cleaned and standardized.',
    meta={
      'owner': 'analytics',
      'frequency': 'quarterly'
    }
  )
}}

with raw_gdp as (
  select
    observation_date,
    series_id,
    value,
    ingested_at
  from {{ source('fred_raw', 'raw_gdp') }}
  where value is not null
)

select
  observation_date as period_date,
  cast(observation_date as date) as period_date_key,
  series_id as series_code,
  cast(value as numeric(18, 2)) as gdp_billions_usd,
  'FRED' as data_source,
  'Economic Output' as indicator_type,
  'GDPC1' as indicator_name,
  ingested_at as loaded_at,
  row_number() over (order by observation_date desc) = 1 as is_latest,
  current_timestamp as dbt_loaded_at
from raw_gdp
