import logging
import os
import sys
import uuid
from collections import Counter

from ingestion.common.bq_client import get_client
from ingestion.common.gcs_client import get_bucket
from ingestion.common.logging_utils import setup_logging
from ingestion.config import get_settings
from ingestion.csv_ingestion import file_mover
from ingestion.csv_ingestion.file_discovery import IncomingFile, discover
from ingestion.csv_ingestion.hashing import sha256_hex
from ingestion.csv_ingestion.idempotency import Action, IngestionLog, decide
from ingestion.csv_ingestion.loader import load_raw
from ingestion.csv_ingestion.quarantine import quarantine_file
from ingestion.csv_ingestion.validator import validate
from ingestion.monitoring.notifier import notify

logger = logging.getLogger("ingestion.csv")


def _is_forced(f: IncomingFile, force: str | None) -> bool:
    if not force:
        return False
    unidade, dt = force.split(":")
    return f.id_unidade == int(unidade) and f.data_ref.isoformat() == dt


def process_file(f, client, settings, bucket, ing_log, batch_id) -> str:
    data = bucket.blob(f.blob_name).download_as_bytes()
    file_hash = sha256_hex(data)
    forced = _is_forced(f, settings.force_reprocess)

    # 1) Porta de entrada: idempotência por arquivo
    plan = decide(
        hash_already_loaded=ing_log.hash_already_loaded(f, file_hash),
        max_loaded_version=ing_log.max_loaded_version(f),
        force=forced,
    )
    if plan.action == Action.SKIP_DUPLICATE:
        ing_log.record("SKIPPED_DUPLICATE", batch_id, f, file_hash=file_hash)
        file_mover.to_duplicates(bucket, f)
        return "SKIPPED_DUPLICATE"

    # 2) Validação (estrutural; o conteúdo continua como recebido)
    result = validate(data, f)
    if not result.ok:
        ing_log.record("REJECTED", batch_id, f, file_hash=file_hash, error="; ".join(result.errors)[:1000])
        quarantine_file(client, settings, bucket, f.blob_name, "VALIDACAO_FALHOU",
                        result.errors, batch_id, f, file_hash)
        return "REJECTED"

    # 3) Carga atômica na Raw
    ing_log.record("STARTED", batch_id, f, file_hash=file_hash, file_version=plan.file_version)
    n = load_raw(client, settings, f, result.rows, file_hash, plan.file_version, batch_id, bucket.name)
    ing_log.record("LOADED", batch_id, f, file_hash=file_hash, file_version=plan.file_version, row_count=n)

    # 4) Só move depois de registrar LOADED (se falhar aqui, o próximo run o trata como duplicado)
    file_mover.to_processed(bucket, f, plan.file_version, file_hash)
    return "LOADED"


def main() -> int:
    setup_logging()
    settings = get_settings()
    client, bucket = get_client(), get_bucket()
    ing_log = IngestionLog(client, settings)
    batch_id = uuid.uuid4().hex

    files, invalid_names = discover(bucket, settings)
    logger.info("batch=%s arquivos=%d fora_do_padrao=%d", batch_id, len(files), len(invalid_names))

    counts: Counter = Counter()

    for name in invalid_names:
        quarantine_file(client, settings, bucket, name, "NOME_FORA_DO_PADRAO", [name], batch_id)
        ing_log.record("REJECTED", batch_id, file_path=name, error="nome fora do padrão")
        counts["REJECTED"] += 1

    for f in files:
        try:
            status = process_file(f, client, settings, bucket, ing_log, batch_id)
        except Exception as exc:       # um arquivo com problema não derruba os demais
            logger.exception("erro em %s", f.blob_name)
            status = "ERROR"
            try:
                ing_log.record("ERROR", batch_id, f, error=str(exc)[:1000])
            except Exception:
                logger.exception("não foi possível registrar o erro no log")
        counts[status] += 1

    summary = (f"Ingestão CSV batch {batch_id[:8]}: "
               + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) if counts else "nenhum arquivo novo")
    logger.info(summary)

    if path := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"### Ingestão CSV\n{summary}\n")

    if counts["REJECTED"] or counts["ERROR"]:
        notify(f":warning: {summary}")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())