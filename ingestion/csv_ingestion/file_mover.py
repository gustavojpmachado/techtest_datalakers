from datetime import datetime, timezone

from ingestion.csv_ingestion.file_discovery import IncomingFile


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def _rename(bucket, src: str, dst: str) -> None:
    bucket.rename_blob(bucket.blob(src), dst)   # copia + apaga


def to_processed(bucket, f: IncomingFile, file_version: int, file_hash: str) -> str:
    rel = f.blob_name.removeprefix("incoming/")
    folder, name = rel.rsplit("/", 1)
    dst = f"processed/{folder}/v{file_version}_{file_hash[:8]}_{name}"
    _rename(bucket, f.blob_name, dst)
    return dst


def to_duplicates(bucket, f: IncomingFile) -> str:
    rel = f.blob_name.removeprefix("incoming/").replace("/", "__")
    dst = f"processed/duplicates/{_ts()}_{rel}"
    _rename(bucket, f.blob_name, dst)
    return dst


def to_rejected(bucket, blob_name: str) -> str:
    rel = blob_name.removeprefix("incoming/")
    dst = f"rejected/{_ts()}/{rel}"
    _rename(bucket, blob_name, dst)
    return dst