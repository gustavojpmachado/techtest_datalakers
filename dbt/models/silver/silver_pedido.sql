{{ config(
    materialized         = 'incremental',
    incremental_strategy = 'insert_overwrite',
    partition_by         = {'field': 'data_pedido', 'data_type': 'date'},
    cluster_by           = ['id_unidade']
) }}

with itens as (
    select
        id_unidade,
        id_pedido,
        sum(qtd)             as qtd_itens,
        sum(qtd * vlr_item)  as vlr_itens
    from {{ ref('bronze_item_pedido') }}
    group by 1, 2
)

select
    p.id_unidade,
    u.nome_unidade,
    u.nome_estado,
    p.id_pedido,
    p.tipo_pedido,
    p.data_pedido,
    p.status,
    p.vlr_pedido,
    p.taxa_entrega,
    coalesce(i.qtd_itens, 0)  as qtd_itens,
    coalesce(i.vlr_itens, 0)  as vlr_itens,
    abs(p.vlr_pedido - p.taxa_entrega - coalesce(i.vlr_itens, 0)) > 0.01 as flag_divergencia_valor
from {{ ref('bronze_pedido') }} p
left join itens i using (id_unidade, id_pedido)
left join {{ ref('silver_unidade') }} u on u.id_unidade = p.id_unidade
{% if is_incremental() %}
where p.data_pedido >= date_sub(current_date('America/Sao_Paulo'), interval {{ var('lookback_days', 7) }} day)
{% endif %}