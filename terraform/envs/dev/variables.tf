variable "project_id"         { type = string }
variable "region"             { type = string, default = "southamerica-east1" }
variable "env"                { type = string }
variable "ingestion_sa_email" { type = string }
variable "dbt_sa_email"       { type = string }
variable "report_readers"     { type = list(string), default = [] }
variable "labels"             { type = map(string), default = {} }