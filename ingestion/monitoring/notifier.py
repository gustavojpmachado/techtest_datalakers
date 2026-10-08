import logging
import os

import requests

log = logging.getLogger(__name__)


def notify(text: str) -> None:
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        log.warning("SLACK_WEBHOOK_URL não definido; alerta apenas no log: %s", text)
        return
    try:
        requests.post(url, json={"text": text}, timeout=10).raise_for_status()
    except Exception:
        log.exception("falha ao enviar alerta")   # alerta nunca derruba o pipeline