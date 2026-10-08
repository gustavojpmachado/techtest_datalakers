import os
import re
from dataclasses import dataclass
from functools import lru_cache

# Colunas esperadas em cada arquivo (nomes canônicos; espaços viram "_")
EXPECTED_COLUMNS = {
    "pedido": ["Id_Unidade", "Id_Pedido", "Tipo_Pedido", "Data_Pedido", "Vlr_Pedido",
               "Endereco_Entrega", "Taxa_Entrega", "Status"],
    "item_pedido": ["Id_Pedido", "Id_Item_Pedido", "Id_Produto", "Qtd", "Vlr_Item", "Observacao"],
}

# Tabelas do PostgreSQL da matriz
POSTGRES_TABLES = {
    "produto": ["Id_Produto", "Nome_Produto"],
    "unidade": ["Id_Unidade", "Nome_Unidade", "Id_Estado"],
    "estado":  ["Id_Estado", "Id_Pais", "Nome_Estado"],
    "pais":    ["Id_Pais", "Nome_Pais"],
}

# incoming/pedido/id_unidade=12/dt=2026-10-07/arquivo.csv
INCOMING_PATTERN = re.compile(
    r"^raw/id_unidade=(?P<unidade>\d+)/dt=(?P<dt>\d{4}-\d{2}-\d{2})/[^/]+\.csv$"
)


@dataclass(frozen=True)
class Settings:
    project_id: str
    raw_bucket: str
    bq_location: str
    pg_secret_name: str
    force_reprocess: str | None   # "12:2026-10-07" -> ignora o log só para essa unidade/data
    data_ref: str | None          # "2026-10-07"    -> processa só essa data (backfill)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        project_id=os.environ["PROJECT_ID"],
        raw_bucket=os.environ["RAW_BUCKET"],
        bq_location=os.getenv("BQ_LOCATION", "southamerica-east1"),
        pg_secret_name=os.getenv("PG_SECRET_NAME", "pg-matriz-readonly"),
        force_reprocess=os.getenv("FORCE_REPROCESS") or None,
        data_ref=os.getenv("DATA_REF") or None,
    )