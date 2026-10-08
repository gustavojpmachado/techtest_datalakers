variable "project_id" { type = string }
variable "location"   { type = string } # deve ser igual ao do bucket GCS
variable "env"        { type = string }

variable "ingestion_sa_email" { type = string } # carrega Raw e escreve em ops
variable "dbt_sa_email"       { type = string } # lê Raw, escreve Bronze/Silver/Gold

variable "report_readers" {
  description = "Grupos/usuários/SAs que consomem a Gold (ex.: group:operacoes@empresa.com)"
  type        = list(string)
  default     = []
}

variable "labels" {
  type    = map(string)
  default = {}
}