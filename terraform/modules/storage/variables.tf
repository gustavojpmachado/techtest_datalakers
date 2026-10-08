variable "project_id" { type = string }
variable "location"   { type = string }  # ex.: southamerica-east1
variable "env"        { type = string }  # dev | prd

variable "bucket_name" {
  description = "Nome globalmente único do bucket Raw"
  type        = string
}

variable "ingestion_sa_email" {
  description = "Service account que roda a ingestão (lê, grava e move arquivos)"
  type        = string
}

variable "processed_nearline_days"  { type = number, default = 90 }
variable "processed_coldline_days"  { type = number, default = 365 }
variable "rejected_retention_days"  { type = number, default = 180 }

variable "labels" {
  type    = map(string)
  default = {}
}