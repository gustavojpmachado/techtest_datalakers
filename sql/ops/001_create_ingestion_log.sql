create table if not exists ops.ingestion_log (
  file_path     string    not null,
  file_hash     string,
  id_unidade    int64,
  tipo          string,        -- pedido | item_pedido
  data_ref      date,
  file_version  int64,
  row_count     int64,
  status        string    not null,  -- STARTED | LOADED | SKIPPED_DUPLICATE | REJECTED | ERROR
  batch_id      string,
  error         string,
  processed_at  timestamp not null
)
partition by date(processed_at)
cluster by id_unidade, tipo;