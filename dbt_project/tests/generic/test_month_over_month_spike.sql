-- Flag records where month-over-month percentage change exceeds threshold.
-- threshold_pct: e.g. 10 means flag if change > 10%
{% test test_month_over_month_spike(model, column_name, threshold_pct) %}

  with spine as (
    select
      row_number() over (order by period_date_key) as rn,
      period_date_key,
      {{ column_name }},
      lag({{ column_name }}) over (order by period_date_key) as prev_value
    from {{ model }}
    where {{ column_name }} is not null
  )

  select *
  from spine
  where prev_value is not null
    and abs(
      (({{ column_name }} - prev_value) / prev_value) * 100
    ) > {{ threshold_pct }}

{% endtest %}
