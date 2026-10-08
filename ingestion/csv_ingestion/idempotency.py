from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from google.cloud import bigquery

from ingestion.config import Settings
from ingestion.csv_ingestion.file_discovery import IncomingFile


class Action(str, Enum):
    LOAD = "LOAD"
    SKIP_DUPLICATE = "SKIP_DUPLICATE"


@dataclass(frozen=True)
class Plan:
    action: Action
    file_version: int | None = None


def decide(hash_already_loaded: bool, max_loaded_version: int | None, force: bool) -> Plan:
    """Regra pura (fácil de testar):
    - mesmo hash já carregado          -> ignora (a menos que force)
    - mesma unidade/tipo/data, outro hash -> nova versão (max + 1)
    - primeiro envio                    -> versão 1
    """
    if hash_already_loaded and not force:
        return Plan(Action.SKIP_DUPLICATE)
    return Plan(Action.LOAD, (max_loaded_version or 0) + 1)


class IngestionLog:
    def __init__(self, client: bigquery.Client, settings: Settings):
        self.client = client
        self.table = f"{settings.project_id}.ops.ingestion_log"

    def _scalar(self, sql: str, params: list):
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
        return list(job.result())[0][0]

    def hash_already_loaded(self, f: IncomingFile, file_hash: str) -> bool:
        sql = f"""select count(*) from `{self.table}`
                  where file_hash=@h and id_unidade=@u and tipo=@t and status='LOADED'"""
        return self._scalar(sql, [
            bigquery.ScalarQueryParameter("h", "STRING", file_hash),
            bigquery.ScalarQueryParameter("u", "INT64", f.id_unidade),
            bigquery.ScalarQueryParameter("t", "STRING", f.tipo),
        ]) > 0

    def max_loaded_version(self, f: IncomingFile) -> int | None:
        sql = f"""select max(file_version) from `{self.table}`
                  where id_unidade=@u and tipo=@t and data_ref=@d and status='LOADED'"""
        return self._scalar(sql, [
            bigquery.ScalarQueryParameter("u", "INT64", f.id_unidade),
            bigquery.ScalarQueryParameter("t", "STRING", f.tipo),
            bigquery.ScalarQueryParameter("d", "DATE", f.data_ref),
        ])

    def record(self, status: str, batch_id: str, f: IncomingFile | None = None, *,
               file_path: str | None = None, file_hash: str | None = None,
               file_version: int | None = None, row_count: int | None = None,
               error: str | None = None) -> None:
        row = {
            "file_path": file_path or (f.blob_name if f else None),
            "file_hash": file_hash,
            "id_unidade": f.id_unidade if f else None,
            "tipo": f.tipo if f else None,
            "data_ref": f.data_ref.isoformat() if f else None,
            "file_version": file_version,
            "row_count": row_count,
            "status": status,
            "batch_id": batch_id,
            "error": error,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(self.table, [row])
        if errors:
            raise RuntimeError(f"falha ao gravar ingestion_log: {errors}")