from google.cloud import storage
from ingestion.config import get_settings


def get_bucket() -> storage.Bucket:
    s = get_settings()
    return storage.Client(project=s.project_id).bucket(s.raw_bucket)