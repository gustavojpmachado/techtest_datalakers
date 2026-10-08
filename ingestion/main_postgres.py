import logging
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from ingestion.common.bq_client import get_client
from ingestion.common.logging_utils import setup_logging
from ingestion.config import POSTGRES_TABLES, get_settings
from ingestion.monitoring.notifier import notify
from ingestion.postgres_extract.extractor import connect, extract_table
from ingestion.postgres_extract.snapshot_loader import load_snapshot

logger = logging.getLogger("ingestion.postgres")


def main() -> int:
    setup_logging()
    settings, client = get_settings(), get_client()
    batch_id = uuid.uuid4().hex
    snapshot_date = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    failures = []
    conn = connect()
    try:
        for table in POSTGRES_TABLES:
            try:
                rows = extract_table(conn, table)
                n = load_snapshot(client, settings, table, rows, snapshot_date, batch_id)
                logger.info("%s: %d linhas (snapshot %s)", table, n, snapshot_date)
            except Exception as exc:
                logger.exception("falha em %s", table)
                failures.append(f"{table}: {exc}")
    finally:
        conn.close()

    if failures:
        notify(":x: Extração PostgreSQL falhou:\n" + "\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())