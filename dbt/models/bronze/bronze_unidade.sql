{{ config(materialized='table') }}

select
    safe_cast(Id_Unidade as int64) as id_unidade,
    trim(Nome_Unidade)             as nome_unidade,
    safe_cast(Id_Estado as int64)  as id_estado,
    _snapshot_date,
    _ingestion_ts
from {{ source('raw_postgres', 'unidade') }}
where _snapshot_date = (select max(_snapshot_date) from {{ source('raw_postgres', 'unidade') }})