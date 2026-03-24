{{
  config(
    description='Dimension table for economic time periods with calendar dimensions and NBER recession dates',
    materialized='table',
    indexes=[
      {'columns': ['period_date'], 'type': 'btree'},
      {'columns': ['year', 'month'], 'type': 'btree'},
      {'columns': ['is_nber_recession_period'], 'type': 'btree'}
    ]
  )
}}

with date_spine as (
  -- Generate monthly calendar spine
  select
    (date_trunc('month', d)::date) as period_date
  from (
    select generate_series(
      '2000-01-01'::date,
      current_date,
      '1 month'::interval
    ) as d
  ) dates
),

with_dimensions as (
  select
    period_date,
    extract(year from period_date) as year,
    extract(quarter from period_date) as quarter,
    extract(month from period_date) as month,
    to_char(period_date, 'Month') as month_name,
    to_char(period_date, 'Mon') as month_short,
    concat(extract(year from period_date)::int, '-Q', extract(quarter from period_date)::int) as year_quarter,
    concat(extract(year from period_date)::int, '-', lpad(extract(month from period_date)::text, 2, '0')) as year_month,
    extract(week from period_date) as week_of_year,
    extract(day from period_date) as day_of_month,
    extract(isodow from period_date) as day_of_week,
    case
      when extract(quarter from period_date) = 1 then 'Q1'
      when extract(quarter from period_date) = 2 then 'Q2'
      when extract(quarter from period_date) = 3 then 'Q3'
      else 'Q4'
    end as quarter_name
  from date_spine
),

with_nber_dates as (
  -- NBER official recession dates (as of 2024)
  -- Sourced from National Bureau of Economic Research
  select
    d.*,
    case
      when (d.year = 2001 and d.month >= 3) or (d.year = 2001 and d.month <= 11) then true
      when (d.year = 2007 and d.month >= 12) or (d.year = 2009 and d.month <= 6) then true
      when (d.year = 2020 and d.month >= 3) or (d.year = 2020 and d.month <= 4) then true
      else false
    end as is_nber_recession_period,
    case
      when (d.year = 2001 and d.month >= 3) or (d.year = 2001 and d.month <= 11) then '2001 Recession'
      when (d.year = 2007 and d.month >= 12) or (d.year = 2009 and d.month <= 6) then '2007-2009 Financial Crisis'
      when (d.year = 2020 and d.month >= 3) or (d.year = 2020 and d.month <= 4) then '2020 COVID Recession'
      else null
    end as recession_name,
    current_timestamp as dbt_loaded_at
  from with_dimensions d
)

select
  period_date,
  year,
  quarter,
  month,
  month_name,
  month_short,
  year_quarter,
  year_month,
  week_of_year,
  day_of_month,
  day_of_week,
  quarter_name,
  is_nber_recession_period,
  recession_name,
  dbt_loaded_at
from with_nber_dates
order by period_date
