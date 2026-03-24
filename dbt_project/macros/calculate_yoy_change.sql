-- Calculate year-over-year percentage change.
-- intervals: 12 for monthly data, 4 for quarterly data
{% macro calculate_yoy_change(value_col, date_col, intervals) %}
  (
    ({{ value_col }} - lag({{ value_col }}, {{ intervals }})
      over (order by {{ date_col }}))
    / lag({{ value_col }}, {{ intervals }})
      over (order by {{ date_col }})
  ) * 100
{% endmacro %}
