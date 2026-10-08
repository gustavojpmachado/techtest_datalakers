create table if not exists ops.quarantine (
  file_path      string not null,
  file_hash      string,
  id_unidade     int64,
  tipo           string,
  data_ref       date,
  reason         string not null,
  details        string,
  batch_id       string,
  quarantined_at timestamp not null
)
partition by date(quarantined_at);