import logging
import uuid
from datetime import datetime, timezone

from google.api_core.exceptions import Conflict
from google.cloud import bigquery

from ingestion.config import Settings
from ingestion.csv_ingestion.file_discovery import IncomingFile

log = logging.getLogger(__name__)


def make_job_id(f: IncomingFile, file_hash: str, file_version: int) -> str:
    # Determinístico: a mesma execução repetida gera o mesmo ID e o BigQuery rejeita o duplicado
    return f"load_{f.tipo}_{f.id_unidade}_{f.data_ref:%Y%m%d}_{file_hash[:12]}_v{file_version}"


def load_raw(client: bigquery.Client, settings: Settings, f: IncomingFile, rows: list[dict],
             file_hash: str, file_version: int, batch_id: str, bucket_name: str) -> int:
    if not rows:                       # unidade sem vendas: arquivo só com cabeçalho
        return 0

    now = datetime.now(timezone.utc).isoformat()
    records = [{
        **r,
        "_ingestion_ts": now,
        "_source_file": f"gs://{bucket_name}/{f.blob_name}",
        "_file_hash": file_hash,
        "_file_version": file_version,
        "_id_unidade": str(f.id_unidade),
        "_batch_id": batch_id,
    } for r in rows]

    table_id = f"{settings.project_id}.raw_csv.{f.tipo}"
    cfg = bigquery.LoadJobConfig(
        schema=client.get_table(table_id).schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,   # Raw é append-only
    )

    job_id = make_job_id(f, file_hash, file_version)
    try:
        job = client.load_table_from_json(records, table_id, job_id=job_id, job_config=cfg)
    except Conflict:
        job = client.get_job(job_id, location=settings.bq_location)
        if job.error_result:           # tentativa anterior falhou: um job_id falho não pode ser reutilizado
            log.warning("job %s anterior falhou; reenviando com novo sufixo", job_id)
            job = client.load_table_from_json(
                records, table_id, job_id=f"{job_id}_retry_{uuid.uuid4().hex[:6]}", job_config=cfg)
        else:
            log.info("job %s já existia e foi concluído (execução anterior)", job_id)

    job.result()                       # levanta exceção se falhar; carga é atômica (tudo ou nada)
    return len(records)