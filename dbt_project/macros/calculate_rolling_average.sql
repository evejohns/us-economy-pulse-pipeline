-- Calculate a rolling average over a specified window size.
-- window_size: number of periods to include (e.g. 3, 6, 12)
{% macro calculate_rolling_average(value_col, date_col, window_size) %}
  avg({{ value_col }})
    over (
      order by {{ date_col }}
      rows between {{ window_size - 1 }} preceding and current row
    )
{% endmacro %}
