{{ config(
    materialized         = 'incremental',
    incremental_strategy = 'insert_overwrite',
    partition_by         = {'field': 'data_pedido', 'data_type': 'date'},
    cluster_by           = ['id_unidade', 'id_produto']
) }}

select
    i.id_unidade,
    p.nome_unidade,
    p.nome_estado,
    i.id_pedido,
    i.id_item_pedido,
    p.data_pedido,
    p.tipo_pedido,
    p.status,
    i.id_produto,
    pr.nome_produto,
    i.qtd,
    i.vlr_item            as vlr_unitario,
    i.qtd * i.vlr_item    as vlr_total_item,
    i.observacao
from {{ ref('bronze_item_pedido') }} i
join {{ ref('silver_pedido') }} p
  on p.id_unidade = i.id_unidade and p.id_pedido = i.id_pedido
left join {{ ref('bronze_produto') }} pr on pr.id_produto = i.id_produto
{% if is_incremental() %}
where p.data_pedido >= date_sub(current_date('America/Sao_Paulo'), interval {{ var('lookback_days', 7) }} day)
{% endif %}