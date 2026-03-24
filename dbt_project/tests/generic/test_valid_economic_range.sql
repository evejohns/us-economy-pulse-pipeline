-- Validate that values fall within expected economic ranges.
-- Flags records where values are outside the specified min/max bounds.
{% test test_valid_economic_range(model, column_name, min_value, max_value) %}

  select *
  from {{ model }}
  where {{ column_name }} is not null
    and ({{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }})

{% endtest %}
