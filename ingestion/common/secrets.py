from google.cloud import secretmanager
from ingestion.config import get_settings


def get_secret(name: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/{get_settings().project_id}/secrets/{name}/versions/{version}"
    return client.access_secret_version(request={"name": path}).payload.data.decode("utf-8")