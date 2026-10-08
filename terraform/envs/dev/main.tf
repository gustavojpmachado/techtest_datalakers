terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# APIs necessárias
resource "google_project_service" "apis" {
  for_each = toset([
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "iamcredentials.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "storage" {
  source = "../../modules/storage"

  project_id         = var.project_id
  location           = var.region
  env                = var.env
  bucket_name        = "${var.project_id}-mrhealth-raw-${var.env}"
  ingestion_sa_email = var.ingestion_sa_email
  labels             = var.labels

  depends_on = [google_project_service.apis]
}

module "bigquery" {
  source = "../../modules/bigquery"

  project_id         = var.project_id
  location           = var.region
  env                = var.env
  ingestion_sa_email = var.ingestion_sa_email
  dbt_sa_email       = var.dbt_sa_email
  report_readers     = var.report_readers
  labels             = var.labels

  depends_on = [google_project_service.apis]
}