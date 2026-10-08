{% macro parse_date_br(col) -%}
coalesce(
  safe.parse_date('%d/%m/%Y', substr(trim({{ col }}), 1, 10)),
  safe.parse_date('%Y-%m-%d', substr(trim({{ col }}), 1, 10))
)
{%- endmacro %}