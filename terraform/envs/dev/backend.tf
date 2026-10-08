terraform {
  backend "gcs" {
    bucket = "mrhealth-tfstate-dev"   # bucket de state criado manualmente (bootstrap)
    prefix = "dw/state"
  }
}