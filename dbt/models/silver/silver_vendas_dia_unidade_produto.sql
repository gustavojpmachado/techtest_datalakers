{{ config(
    materialized         = 'incremental',
    incremental_strategy = 'insert_overwrite',
    partition_by         = {'field': 'data_pedido', 'data_type': 'date'},
    cluster_by           = ['id_unidade', 'id_produto']
) }}

select
    data_pedido,
    id_unidade,
    id_produto,
    nome_produto,
    tipo_pedido,
    status,
    count(distinct id_pedido) as qtd_pedidos,
    sum(qtd)                  as qtd_itens,
    sum(vlr_total_item)       as vlr_itens
from {{ ref('silver_pedido_item') }}
{% if is_incremental() %}
where data_pedido >= date_sub(current_date('America/Sao_Paulo'), interval {{ var('lookback_days', 7) }} day)
{% endif %}
group by 1, 2, 3, 4, 5, 6