output "dataset_ids" {
  value = { for k, d in google_bigquery_dataset.layers : k => d.dataset_id }
}