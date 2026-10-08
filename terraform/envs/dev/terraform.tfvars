project_id         = "mrhealth-dw-dev"
env                = "dev"
ingestion_sa_email = "sa-ingestion@mrhealth-dw-dev.iam.gserviceaccount.com"
dbt_sa_email       = "sa-dbt@mrhealth-dw-dev.iam.gserviceaccount.com"
report_readers     = ["group:operacoes@mrhealth.com.br"]
labels             = { project = "mrhealth-dw", owner = "dados" }