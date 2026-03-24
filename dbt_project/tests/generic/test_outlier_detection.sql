-- Detect statistical outliers using z-score method.
-- std_dev_threshold: e.g. 3 means flag if value is >3 standard deviations from mean
{% test test_outlier_detection(model, column_name, std_dev_threshold) %}

  with stats as (
    select
      avg({{ column_name }}::numeric) as mean_value,
      stddev_pop({{ column_name }}::numeric) as std_value
    from {{ model }}
    where {{ column_name }} is not null
  ),

  flagged as (
    select
      m.*,
      abs((m.{{ column_name }}::numeric - s.mean_value) / nullif(s.std_value, 0)) as z_score
    from {{ model }} m
    cross join stats s
    where m.{{ column_name }} is not null
  )

  select *
  from flagged
  where z_score > {{ std_dev_threshold }}

{% endtest %}
