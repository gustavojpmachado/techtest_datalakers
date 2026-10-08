{{ config(
    materialized = 'table',
    partition_by = {'field': 'data_pedido', 'data_type': 'date'},
    cluster_by   = ['id_unidade']
) }}

select
    data_pedido,
    id_unidade,
    nome_unidade,
    nome_estado,
    tipo_pedido,
    count(*)                                              as qtd_pedidos,
    countif(status = 'FINALIZADO')                        as qtd_finalizados,
    countif(status = 'CANCELADO')                         as qtd_cancelados,
    countif(status = 'PENDENTE')                          as qtd_pendentes,
    sum(if(status = 'FINALIZADO', vlr_pedido, 0))         as faturamento,
    sum(if(status = 'FINALIZADO', taxa_entrega, 0))       as total_taxa_entrega,
    safe_divide(
        sum(if(status = 'FINALIZADO', vlr_pedido, 0)),
        countif(status = 'FINALIZADO'))                   as ticket_medio,
    safe_divide(countif(status = 'CANCELADO'), count(*))  as taxa_cancelamento
from {{ ref('silver_pedido') }}
group by 1, 2, 3, 4, 5