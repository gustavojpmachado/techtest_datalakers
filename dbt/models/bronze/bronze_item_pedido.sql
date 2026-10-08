{{ config(
    materialized         = 'incremental',
    incremental_strategy = 'merge',
    unique_key           = ['id_unidade', 'id_pedido', 'id_item_pedido'],
    cluster_by           = ['id_unidade', 'id_pedido']
) }}

with src as (
    select * from {{ source('raw_csv', 'item_pedido') }}
    {% if is_incremental() %}
    where _ingestion_ts > (select max(_ingestion_ts) from {{ this }})
    {% endif %}
),

renamed as (
    select
        safe_cast(_id_unidade as int64)        as id_unidade,   -- vem do caminho do arquivo
        safe_cast(Id_Pedido as int64)          as id_pedido,
        safe_cast(Id_Item_Pedido as int64)     as id_item_pedido,
        safe_cast(Id_Produto as int64)         as id_produto,
        safe_cast(Qtd as int64)                as qtd,
        {{ parse_decimal_br('Vlr_Item') }}     as vlr_item,
        nullif(trim(Observacao), '')           as observacao,
        _file_version,
        _source_file,
        _ingestion_ts
    from src
)

{{ dedup_latest_version('renamed', ['id_unidade', 'id_pedido', 'id_item_pedido']) }}