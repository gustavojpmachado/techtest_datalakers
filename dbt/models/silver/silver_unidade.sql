{{ config(materialized='table') }}

select
    u.id_unidade,
    u.nome_unidade,
    e.id_estado,
    e.nome_estado,
    p.id_pais,
    p.nome_pais
from {{ ref('bronze_unidade') }} u
left join {{ ref('bronze_estado') }} e on e.id_estado = u.id_estado
left join {{ ref('bronze_pais') }}   p on p.id_pais   = e.id_pais