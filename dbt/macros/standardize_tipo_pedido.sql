{% macro standardize_status(col) -%}
case upper(trim({{ col }}))
  when 'PENDENTE'   then 'PENDENTE'
  when 'FINALIZADO' then 'FINALIZADO'
  when 'CANCELADO'  then 'CANCELADO'
end   -- valor inesperado vira NULL e é pego pelos testes
{%- endmacro %}

{% macro standardize_tipo_pedido(col) -%}
case upper(trim({{ col }}))
  when 'LOJA ONLINE' then 'ONLINE'
  when 'LOJA FISICA' then 'FISICA'
  when 'LOJA FÍSICA' then 'FISICA'
end
{%- endmacro %}