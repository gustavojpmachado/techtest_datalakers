{{ config(materialized='table') }}

with datas as (
    select d as data_ref
    from unnest(generate_date_array(
        date_sub(current_date('America/Sao_Paulo'), interval 14 day),
        date_sub(current_date('America/Sao_Paulo'), interval 1 day))) d
),

esperadas as (
    select id_unidade from {{ ref('unidades_esperadas') }} where ativa
),

enviados as (
    select
        id_unidade,
        data_ref,
        countif(tipo = 'pedido'      and status = 'LOADED') > 0 as enviou_pedido,
        countif(tipo = 'item_pedido' and status = 'LOADED') > 0 as enviou_item_pedido
    from {{ source('ops', 'ingestion_log') }}
    group by 1, 2
)

select
    d.data_ref,
    e.id_unidade,
    u.nome_unidade,
    coalesce(s.enviou_pedido, false)      as enviou_pedido,
    coalesce(s.enviou_item_pedido, false) as enviou_item_pedido,
    case
        when s.enviou_pedido and s.enviou_item_pedido then 'OK'
        when s.enviou_pedido or  s.enviou_item_pedido then 'PARCIAL'
        else 'FALTANDO'
    end as situacao
from datas d
cross join esperadas e
left join enviados s on s.data_ref = d.data_ref and s.id_unidade = e.id_unidade
left join {{ ref('silver_unidade') }} u on u.id_unidade = e.id_unidade