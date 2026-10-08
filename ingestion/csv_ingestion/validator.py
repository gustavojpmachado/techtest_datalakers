import csv
import io
import re
from dataclasses import dataclass, field

from ingestion.config import EXPECTED_COLUMNS
from ingestion.csv_ingestion.file_discovery import IncomingFile

MAX_ERRORS = 20


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _normalize(h: str) -> str:
    return re.sub(r"\s+", "_", h.strip().lstrip("\ufeff"))


def validate(data: bytes, f: IncomingFile) -> ValidationResult:
    text = _decode(data)
    if not text.strip():
        return ValidationResult(False, ["arquivo vazio"])

    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;|\t").delimiter
    except csv.Error:
        delimiter = ";"

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = [_normalize(h) for h in next(reader)]

    expected = EXPECTED_COLUMNS[f.tipo]
    canon = {c.lower(): c for c in expected}          # tolera diferença de maiúsculas/minúsculas
    header = [canon.get(h.lower(), h) for h in header]

    errors: list[str] = []
    missing, extra = set(expected) - set(header), set(header) - set(expected)
    if missing:
        errors.append(f"colunas ausentes: {sorted(missing)}")
    if extra:
        errors.append(f"colunas inesperadas: {sorted(extra)}")
    if errors:
        return ValidationResult(False, errors)

    rows = []
    for line_no, row in enumerate(reader, start=2):
        if not any(c.strip() for c in row):
            continue
        if len(row) != len(header):
            errors.append(f"linha {line_no}: {len(row)} colunas (esperado {len(header)})")
        else:
            rows.append(dict(zip(header, row)))   # valores como recebidos (Raw não transforma)
        if len(errors) >= MAX_ERRORS:
            break

    if f.tipo == "pedido" and not errors:
        ids = {r["Id_Unidade"].strip() for r in rows}
        if ids and ids != {str(f.id_unidade)}:
            errors.append(f"Id_Unidade do conteúdo {sorted(ids)} diverge do caminho ({f.id_unidade})")

    return ValidationResult(not errors, errors, rows if not errors else [])