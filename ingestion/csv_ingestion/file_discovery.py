from dataclasses import dataclass
from datetime import date

from ingestion.config import INCOMING_PATTERN, Settings


@dataclass(frozen=True)
class IncomingFile:
    blob_name: str
    tipo: str
    id_unidade: int
    data_ref: date

    @property
    def basename(self) -> str:
        return self.blob_name.rsplit("/", 1)[-1]


def discover(bucket, settings: Settings) -> tuple[list[IncomingFile], list[str]]:
    """Retorna (arquivos com nome válido, nomes fora do padrão)."""
    valid, invalid = [], []
    for blob in bucket.list_blobs(prefix="incoming/"):
        if blob.name.endswith("/") or blob.size == 0 and blob.name.count("/") <= 1:
            continue  # placeholders de "pasta"
        m = INCOMING_PATTERN.match(blob.name)
        if not m:
            invalid.append(blob.name)
            continue
        if settings.data_ref and m["dt"] != settings.data_ref:
            continue
        valid.append(IncomingFile(blob.name, m["tipo"], int(m["unidade"]), date.fromisoformat(m["dt"])))
    return sorted(valid, key=lambda f: (f.data_ref, f.id_unidade, f.tipo)), invalid