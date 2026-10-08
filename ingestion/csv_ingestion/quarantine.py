import json
from datetime import datetime, timezone

from ingestion.config import Settings
from ingestion.csv_ingestion import file_mover
from ingestion.csv_ingestion.file_discovery import IncomingFile


def quarantine_file(client, settings: Settings, bucket, blob_name: str, reason: str,
                    details: list[str] | None, batch_id: str,
                    f: IncomingFile | None = None, file_hash: str | None = None) -> None:
    row = {
        "file_path": blob_name,
        "file_hash": file_hash,
        "id_unidade": f.id_unidade if f else None,
        "tipo": f.tipo if f else None,
        "data_ref": f.data_ref.isoformat() if f else None,
        "reason": reason,
        "details": json.dumps(details or [], ensure_ascii=False)[:5000],
        "batch_id": batch_id,
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
    }
    errors = client.insert_rows_json(f"{settings.project_id}.ops.quarantine", [row])
    if errors:
        raise RuntimeError(f"falha ao gravar quarantine: {errors}")
    file_mover.to_rejected(bucket, blob_name)