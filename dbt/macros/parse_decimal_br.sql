{% macro parse_decimal_br(col) -%}
safe_cast(
  case
    when {{ col }} like '%,%' then replace(replace(trim({{ col }}), '.', ''), ',', '.')
    else trim({{ col }})
  end as numeric)
{%- endmacro %}