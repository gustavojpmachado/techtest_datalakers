locals {
  datasets = {
    raw_csv      = "Raw: CSVs das unidades como recebidos (tudo STRING + metadados)"
    raw_postgres = "Raw: tabelas do PostgreSQL da matriz como recebidas"
    bronze       = "Bronze: nomenclatura e tipagem corrigidas"
    silver       = "Silver: agregações e enriquecimentos necessários"
    gold         = "Gold: tabelas prontas para relatórios"
    ops          = "Controle: ingestion_log e quarantine"
  }

  layer_of = {
    raw_csv      = "raw"
    raw_postgres = "raw"
    bronze       = "bronze"
    silver       = "silver"
    gold         = "gold"
    ops          = "ops"
  }

  ingestion = "serviceAccount:${var.ingestion_sa_email}"
  dbt       = "serviceAccount:${var.dbt_sa_email}"

  # Matriz de permissões por dataset (mínimo necessário)
  access_list = concat(
    [
      { dataset = "raw_csv",      role = "roles/bigquery.dataEditor", member = local.ingestion },
      { dataset = "raw_postgres", role = "roles/bigquery.dataEditor", member = local.ingestion },
      { dataset = "ops",          role = "roles/bigquery.dataEditor", member = local.ingestion },

      { dataset = "raw_csv",      role = "roles/bigquery.dataViewer", member = local.dbt },
      { dataset = "raw_postgres", role = "roles/bigquery.dataViewer", member = local.dbt },
      { dataset = "ops",          role = "roles/bigquery.dataViewer", member = local.dbt },
      { dataset = "bronze",       role = "roles/bigquery.dataEditor", member = local.dbt },
      { dataset = "silver",       role = "roles/bigquery.dataEditor", member = local.dbt },
      { dataset = "gold",         role = "roles/bigquery.dataEditor", member = local.dbt },
    ],
    [for r in var.report_readers :
      { dataset = "gold", role = "roles/bigquery.dataViewer", member = r }
    ]
  )

  access = { for a in local.access_list : "${a.dataset}|${a.role}|${a.member}" => a }
}

resource "google_bigquery_dataset" "layers" {
  for_each = local.datasets

  project       = var.project_id
  dataset_id    = each.key
  friendly_name = each.key
  description   = each.value
  location      = var.location

  delete_contents_on_destroy = false # protege contra destroy acidental

  labels = merge(var.labels, {
    layer = local.layer_of[each.key]
    env   = var.env
  })
}

resource "google_bigquery_dataset_iam_member" "access" {
  for_each = local.access

  project    = var.project_id
  dataset_id = google_bigquery_dataset.layers[each.value.dataset].dataset_id
  role       = each.value.role
  member     = each.value.member
}

# Rodar jobs (load e queries) exige jobUser no projeto
resource "google_project_iam_member" "job_user" {
  for_each = toset([var.ingestion_sa_email, var.dbt_sa_email])

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${each.value}"
}