resource "google_storage_bucket" "raw" {
  name                        = var.bucket_name
  project                     = var.project_id
  location                    = var.location
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false # nunca apagar a Raw por engano

  labels = merge(var.labels, { layer = "raw", env = var.env })

  # Protege contra sobrescrita/exclusão acidental
  versioning {
    enabled = true
  }

  # Versões antigas (substituídas) saem após 30 dias
  lifecycle_rule {
    condition {
      age        = 30
      with_state = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  # Arquivos processados ficam mais baratos com o tempo (não apagamos: são a base de reprocessamento)
  lifecycle_rule {
    condition {
      age            = var.processed_nearline_days
      matches_prefix = ["processed/"]
      with_state     = "LIVE"
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age            = var.processed_coldline_days
      matches_prefix = ["processed/"]
      with_state     = "LIVE"
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # Rejeitados: retenção limitada
  lifecycle_rule {
    condition {
      age            = var.rejected_retention_days
      matches_prefix = ["rejected/"]
    }
    action {
      type = "Delete"
    }
  }
}

# "Pastas" de nível superior (placeholders)
resource "google_storage_bucket_object" "prefixes" {
  for_each = toset(["raw/", "processed/", "rejected/"])

  bucket  = google_storage_bucket.raw.name
  name    = each.value
  content = " "
}

# A ingestão precisa ler, gravar e mover (copiar + apagar) objetos
resource "google_storage_bucket_iam_member" "ingestion_object_admin" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.ingestion_sa_email}"
}