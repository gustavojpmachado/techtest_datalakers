{{ config(
    materialized = 'table',
    partition_by = {'field': 'data_pedido', 'data_type': 'date'},
    cluster_by   = ['id_unidade', 'id_produto']
) }}

with diario as (
    select
        data_pedido, id_unidade, id_produto, nome_produto,
        sum(qtd_itens) as qtd_vendida
    from {{ ref('silver_vendas_dia_unidade_produto') }}
    where status = 'FINALIZADO'
    group by 1, 2, 3, 4
)

select
    *,
    sum(qtd_vendida) over (
        partition by id_unidade, id_produto
        order by unix_date(data_pedido)
        range between 6 preceding and current row) / 7   as media_diaria_7d,
    sum(qtd_vendida) over (
        partition by id_unidade, id_produto
        order by unix_date(data_pedido)
        range between 27 preceding and current row) / 28 as media_diaria_28d
from diario