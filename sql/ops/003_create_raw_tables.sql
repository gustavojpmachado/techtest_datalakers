create table if not exists raw_csv.pedido (
  Id_Unidade string, Id_Pedido string, Tipo_Pedido string, Data_Pedido string,
  Vlr_Pedido string, Endereco_Entrega string, Taxa_Entrega string, Status string,
  _ingestion_ts timestamp, _source_file string, _file_hash string,
  _file_version int64, _id_unidade string, _batch_id string
) partition by date(_ingestion_ts);

create table if not exists raw_csv.item_pedido (
  Id_Pedido string, Id_Item_Pedido string, Id_Produto string, Qtd string,
  Vlr_Item string, Observacao string,
  _ingestion_ts timestamp, _source_file string, _file_hash string,
  _file_version int64, _id_unidade string, _batch_id string
) partition by date(_ingestion_ts);

create table if not exists raw_postgres.produto (
  Id_Produto string, Nome_Produto string,
  _snapshot_date date, _ingestion_ts timestamp, _batch_id string
) partition by _snapshot_date;

create table if not exists raw_postgres.unidade (
  Id_Unidade string, Nome_Unidade string, Id_Estado string,
  _snapshot_date date, _ingestion_ts timestamp, _batch_id string
) partition by _snapshot_date;

create table if not exists raw_postgres.estado (
  Id_Estado string, Id_Pais string, Nome_Estado string,
  _snapshot_date date, _ingestion_ts timestamp, _batch_id string
) partition by _snapshot_date;

create table if not exists raw_postgres.pais (
  Id_Pais string, Nome_Pais string,
  _snapshot_date date, _ingestion_ts timestamp, _batch_id string
) partition by _snapshot_date;