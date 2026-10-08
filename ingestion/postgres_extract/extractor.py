import json

import psycopg2
from psycopg2 import sql

from ingestion.common.secrets import get_secret
from ingestion.config import POSTGRES_TABLES, get_settings


def connect():
    cfg = json.loads(get_secret(get_settings().pg_secret_name))
    conn = psycopg2.connect(
        host=cfg["host"],              # IP privado, alcançado pela VPN
        port=cfg.get("port", 5432),
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode="require",
        connect_timeout=15,
    )
    conn.set_session(readonly=True, autocommit=True)   # usuário e sessão somente leitura
    return conn


def extract_table(conn, table: str) -> list[dict]:
    expected = POSTGRES_TABLES[table]
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table)))
        names = [d.name for d in cur.description]
        canon = {c.lower(): c for c in expected}
        missing = set(canon) - {n.lower() for n in names}
        if missing:
            raise ValueError(f"{table}: colunas ausentes no PostgreSQL: {sorted(missing)}")
        keys = [canon.get(n.lower()) for n in names]
        return [
            {k: (None if v is None else str(v)) for k, v in zip(keys, row) if k}
            for row in cur.fetchall()
        ]