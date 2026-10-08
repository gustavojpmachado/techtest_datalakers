from datetime import date, datetime, timezone

from google.cloud import bigquery

from ingestion.config import Settings


def load_snapshot(client: bigquery.Client, settings: Settings, table: str,
                  rows: list[dict], snapshot_date: date, batch_id: str) -> int:
    if not rows:
        # Proteção: nunca sobrescrever o snapshot do dia com um extract vazio
        raise ValueError(f"{table}: extração retornou 0 linhas; snapshot não foi substituído")

    now = datetime.now(timezone.utc).isoformat()
    records = [{**r, "_snapshot_date": snapshot_date.isoformat(), "_ingestion_ts": now, "_batch_id": batch_id}
               for r in rows]

    base = f"{settings.project_id}.raw_postgres.{table}"
    cfg = bigquery.LoadJobConfig(
        schema=client.get_table(base).schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # substitui só a partição do dia
    )
    # "$AAAAMMDD" = decorador de partição: reexecutar no mesmo dia troca o snapshot, sem duplicar
    job = client.load_table_from_json(records, f"{base}${snapshot_date:%Y%m%d}", job_config=cfg)
    job.result()
    return len(records)