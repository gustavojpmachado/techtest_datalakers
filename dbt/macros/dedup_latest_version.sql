{% macro dedup_latest_version(relation, keys) -%}
select * from {{ relation }}
qualify row_number() over (
  partition by {{ keys | join(', ') }}
  order by _file_version desc, _ingestion_ts desc
) = 1
{%- endmacro %}