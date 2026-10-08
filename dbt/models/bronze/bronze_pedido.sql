{{ config(
    materialized         = 'incremental',
    incremental_strategy = 'merge',
    unique_key           = ['id_unidade', 'id_pedido'],
    partition_by         = {'field': 'data_pedido', 'data_type': 'date'},
    cluster_by           = ['id_unidade']
) }}

with src as (
    select * from {{ source('raw_csv', 'pedido') }}
    {% if is_incremental() %}
    where _ingestion_ts > (select max(_ingestion_ts) from {{ this }})
    {% endif %}
),

renamed as (
    select
        safe_cast(Id_Unidade as int64)             as id_unidade,
        safe_cast(Id_Pedido  as int64)             as id_pedido,
        {{ standardize_tipo_pedido('Tipo_Pedido') }} as tipo_pedido,
        {{ parse_date_br('Data_Pedido') }}         as data_pedido,
        {{ parse_decimal_br('Vlr_Pedido') }}       as vlr_pedido,
        nullif(trim(Endereco_Entrega), '')         as endereco_entrega,
        coalesce({{ parse_decimal_br('Taxa_Entrega') }}, 0) as taxa_entrega,
        {{ standardize_status('Status') }}         as status,
        _file_version,
        _source_file,
        _ingestion_ts
    from src
)

{{ dedup_latest_version('renamed', ['id_unidade', 'id_pedido']) }}