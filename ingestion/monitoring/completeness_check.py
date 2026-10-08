import sys

from ingestion.common.bq_client import get_client
from ingestion.common.logging_utils import setup_logging
from ingestion.config import get_settings
from ingestion.monitoring.notifier import notify


def main() -> int:
    setup_logging()
    s, client = get_settings(), get_client()
    sql = f"""
        select id_unidade, coalesce(nome_unidade, '?') as nome_unidade, situacao
        from `{s.project_id}.gold.gold_completude_unidades`
        where data_ref = date_sub(current_date('America/Sao_Paulo'), interval 1 day)
          and situacao != 'OK'
        order by id_unidade"""
    pendentes = list(client.query(sql).result())
    if pendentes:
        linhas = "\n".join(f"• {r.id_unidade} {r.nome_unidade}: {r.situacao}" for r in pendentes)
        notify(f":mailbox_with_no_mail: {len(pendentes)} unidade(s) sem envio completo de D-1:\n{linhas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())