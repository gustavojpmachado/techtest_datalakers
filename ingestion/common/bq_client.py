from google.cloud import bigquery
from ingestion.config import get_settings


def get_client() -> bigquery.Client:
    s = get_settings()
    return bigquery.Client(project=s.project_id, location=s.bq_location)