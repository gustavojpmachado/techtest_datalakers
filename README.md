# Case Mr. Health: proposta de modernização do Data Warehouse

Stack: **GCP** (GCS + BigQuery) · **dbt** · **Git/GitHub** · orquestração via **GitHub Actions** agendada 1x ao dia · **arquitetura Medalion** (Raw / Bronze / Silver / Gold).

---

## 1. Mapeamento do processo atual (AS-IS)

Cada uma das ~50 unidades gera `pedido.csv` e `item_pedido.csv` à meia-noite (D-1). A equipe de Operações consolida tudo manualmente em planilhas e só então a visão de vendas chega à diretoria e aos gestores.

```mermaid
flowchart LR
A[Unidade gera CSV D-1] --> B[Envio à matriz]
B --> C[Equipe de Operações junta planilhas]
C --> D[Cruza com produto e unidade]
D --> E[Visão de vendas D-1]
E --> F[Operações analisa e age]
```

### Pontos problemáticos

| # | Ponto problemático | Impacto |
|---|---|---|
| 1 | Consolidação manual em planilhas | Erro humano, retrabalho, dependência de pessoas |
| 2 | Sem validação de schema, formato ou duplicidade | Datas, decimais e status inconsistentes |
| 3 | Sem controle de completude | Ninguém sabe se uma unidade deixou de enviar |
| 4 | Latência alta | O D-1 só existe após o trabalho manual |
| 5 | Produto/Unidade/Estado/País ficam no PostgreSQL | Cruzamento manual (PROCV) |
| 6 | `item_pedido` não possui `Id_Unidade` | Unidade só via join com `pedido` ou pelo nome do arquivo |
| 7 | Pedido "Pendente" muda de status depois | Versões conflitantes do mesmo pedido |
| 8 | Sem histórico, versionamento ou rastreabilidade | Sem auditoria nem base para modelos de estoque |
| 9 | Endereço de entrega em planilhas soltas | Risco de LGPD |
| 10 | Sem alertas ou recomendações | Gestão reativa |

---

## 2. Mapeamento do processo futuro (TO-BE)

```mermaid
flowchart LR
A[Unidade envia CSV] --> B[Raw: GCS]
GA[GitHub Actions 1x/dia] --> C[Script de ingestão: valida e checa idempotência]
B --> C
C -->|válido e novo| D[Raw: BigQuery]
C -->|inválido| Q[Quarentena e alerta]
C -->|já processado| X[Ignorado e logado]
P[(PostgreSQL matriz)] -->|VPN| C
D --> E[dbt: Bronze, Silver e Gold]
E --> F[Dashboard Looker Studio]
E --> G[Monitor de completude e alertas]
```

**Fluxo diário (workflow agendado):**

1. As unidades enviam os CSVs para o bucket GCS da camada Raw (SFTP gerenciado, URL assinada ou `gcloud storage cp`).
2. O workflow do GitHub Actions dispara 1x ao dia, após a janela de envio (ex.: 06:00 BRT).
3. O job autentica no GCP via Workload Identity Federation (sem chave de service account no repositório).
4. O script de ingestão lista os arquivos novos, valida nome, schema, unidade e data, checa idempotência e carrega as tabelas Raw no BigQuery, sem alterar o conteúdo. Arquivos inválidos vão para quarentena.
5. O mesmo job, executando em um runner dentro da VPC, extrai as 4 tabelas do PostgreSQL da matriz e grava na Raw.
6. O job roda `dbt build`: Bronze (nomes e tipos corrigidos), Silver (agregações) e Gold (tabelas para relatórios), com testes.
7. O monitor de completude confere se as 50 unidades enviaram e notifica Slack/e-mail sobre as faltantes e sobre falhas.
8. A área de Operações consome o dashboard e os alertas, sem montar planilha.

### Avaliação dos problemas

| Problema | Status | Como |
|---|---|---|
| 1, 4 | Resolvido | Automação ponta a ponta; D-1 disponível pela manhã |
| 2, 8 | Resolvido | Contrato de dados, testes dbt, Raw imutável, Git com commits assinados |
| 3 | Resolvido | Monitor de completude por unidade e dia |
| 5, 6 | Resolvido | Joins no dbt; `id_unidade` derivado do caminho do arquivo |
| 7 | Minimizado | Bronze incremental com MERGE em `(id_unidade, id_pedido)`, mantendo o último status |
| 9 | Minimizado | Policy tags/mascaramento no BigQuery e IAM por camada |
| 10 | Parcial | Alertas operacionais na fase 1; recomendação de estoque na fase 2 |

---

## 3. Diagrama de arquitetura (GCP)

```mermaid
flowchart LR
subgraph Fontes
U[50 unidades: CSV D-1]
PG[(PostgreSQL matriz)]
end
subgraph Rede
IP[IP privado com regras de segurança]
end
subgraph Orquestração
GIT[GitHub: commits assinados pela service account]
GA[GitHub Actions: cron diário]
PY[Script Python de ingestão]
DBT[dbt build]
end
subgraph Medalion
RAWF[Raw: arquivos no GCS]
RAWT[Raw: tabelas no BigQuery]
LOG[ops.ingestion_log]
BR[Bronze]
SI[Silver]
GO[Gold]
end
subgraph Consumo
LK[Looker Studio]
ML[BigQuery ML]
AL[Alertas Slack e e-mail]
end
U -->|SFTP ou URL assinada| RAWF
PG --> IP --> PY
GIT --> GA
GA --> PY
GA --> DBT
RAWF --> PY
PY <--> LOG
PY --> RAWT
RAWT --> BR --> SI --> GO
DBT -.-> BR
GO --> LK
GO --> ML
GO --> AL
```

### Justificativas

- **GCS + BigQuery:** lake para arquivos e warehouse serverless para SQL e dbt, sem infraestrutura para administrar.
- **GitHub Actions agendado:** o repositório já existe por causa do dbt e do Git, então não há ferramenta nova para operar nem custo fixo de orquestrador. O cron diário atende o SLA de D-1, com `workflow_dispatch` para execução manual e reprocessamento.
- **Conexão com o PostgreSQL:** O banco é acessado por IP privado dentro de um grupo de segurança, com usuário somente leitura e credenciais no Secret Manager. 
- **Autenticação no GCP:** Workload Identity Federation entre GitHub e GCP, restrita ao repositório e à branch `main`; segredos no Secret Manager.
- **Concorrência:** `concurrency` no workflow para impedir duas execuções simultâneas.
- **Trade-offs conhecidos:** o cron do Actions pode atrasar alguns minutos, e não há retry/backfill nativos. Por isso o pipeline precisa ser idempotente e ter alerta de falha. 
- **Transversal:** IAM por camada, Secret Manager, Cloud Logging/Monitoring e Terraform.

---

## 4. Camadas do datalake (arquitetura Medalion)

| Camada | Definição | Onde | Estrutura | Regras |
|---|---|---|---|---|
| **Raw** | Dado **como foi recebido** | GCS (arquivos) e BigQuery `raw_csv`, `raw_postgres` (tabelas) | Arquivos: `gs://raw/id_unidade=XX/dt=YYYY-MM-DD/arquivo.csv`. Tabelas espelho da origem (`pedido`, `item_pedido`, `produto`, `unidade`, `estado`, `pais`), nomes originais, tudo STRING, mais metadados `_ingestion_ts`, `_source_file`, `_file_hash`, `_file_version`, `_id_unidade`, `_batch_id` | Imutável e append-only, particionada por data de ingestão; nenhuma transformação; base de reprocessamento. Após o processamento o arquivo vai para `processed/` ou `rejected/` |
| **Bronze** | Dado com **nomenclatura e tipagem corrigidas** | BigQuery `bronze` (dbt) | `bronze_pedido`, `bronze_item_pedido`, `bronze_produto`, `bronze_unidade`, `bronze_estado`, `bronze_pais` | snake_case e nomes padronizados, tipos corretos (DATE, NUMERIC, INT64), padronização de status e tipo de pedido, mantém uma linha por chave de negócio (deduplicação e **MERGE incremental**); sem regras de negócio nem agregações |
| **Silver** | Dado com as **agregações necessárias** | BigQuery `silver` (dbt) | `silver_unidade` (unidade + estado + país), `silver_pedido_item` (pedido + itens + produto + unidade, no grão do item), `silver_vendas_dia_unidade_produto` (agregação base por dia, unidade e produto) | Joins entre entidades e agregações reutilizáveis; particionadas por `data_pedido` e clusterizadas por `id_unidade` |
| **Gold** | Tabelas com **valor agregado, prontas para relatórios** | BigQuery `gold` (dbt) | `gold_vendas_diarias` (unidade × dia × tipo de pedido), `gold_vendas_produto`, `gold_cancelamentos`, `gold_ticket_medio`, `gold_consumo_produto_unidade` (base para estoque), `gold_completude_unidades`, `gold_alertas` | Métricas de negócio prontas para BI, ML e alertas; nomes e granularidade pensados para o consumidor final |
| **Controle** | Apoio à ingestão | BigQuery `ops` | `ingestion_log`, `quarantine` | Registro de cada arquivo processado e dos registros rejeitados com o motivo |

**Qualidade (dbt):** `unique`, `not_null`, `relationships`, `accepted_values` (status, tipo) e teste singular (soma dos itens ≈ `vlr_pedido`).

---

## 5. Atividades do projeto (ordem de execução)

| # | Atividade | Descrição |
|---|---|---|
| 1 | Kickoff e levantamento | Workshop com os responsáveis de Operações e de TI: SLA, volumetria, KPIs, formato real dos CSVs, regras de status |
| 2 | Contrato de dados | Documentar schema, tipos, chaves e nomes de arquivo; definir como obter `id_unidade` em `item_pedido` |
| 3 | Setup GCP | Projeto, billing, IAM, service accounts, ambientes dev/prd, Secret Manager |
| 4 | IaC (Terraform) | Provisionar buckets, datasets, VPN, VM do runner e Workload Identity Federation |
| 5 | Repositório Git e governança | Estrutura do repo, branching, PR review, service account de Git com chave de assinatura, branch protection exigindo commits assinados |
| 6 | Canal de envio das unidades | Implantar SFTP ou URL assinada e orientar as unidades, incluindo a convenção de nomes |
| 7 | Bucket GCS da camada Raw | Estrutura por unidade/data, pastas `processed/` e `rejected/`, lifecycle |
| 8 | Datasets BigQuery | raw_csv, raw_postgres, bronze, silver, gold, ops, com permissões por camada |
| 9 | Tabelas de controle | `ops.ingestion_log` e `ops.quarantine` |
| 10 | Script de ingestão dos CSVs | Python: listar arquivos, validar schema/nome, calcular hash, checar idempotência, carregar na Raw sem transformar, mover o arquivo |
| 11 | Script de extração do PostgreSQL | Usuário read-only, acesso via VPN, cópia diária das 4 tabelas para a Raw com snapshot datado |
| 12 | Projeto dbt | Configuração, `sources` apontando para a Raw com freshness, targets dev/prd |
| 13 | Modelos Bronze | Renomeação, tipagem, padronização de domínios, deduplicação e MERGE incremental das 6 fontes |
| 14 | Modelos Silver | Enriquecimento de unidade (estado e país), pedido com itens e produto, agregação base por dia/unidade/produto |
| 15 | Modelos Gold | Tabelas de vendas, cancelamentos, ticket médio, consumo por unidade, completude e alertas |
| 16 | Testes de qualidade | Testes genéricos e singulares em cada camada; falha bloqueia a publicação |
| 17 | Workflow de produção (GitHub Actions) | Cron diário + `workflow_dispatch`, `concurrency`, autenticação via WIF, execução de ingestão, extração e `dbt build` |
| 18 | Workflow de CI | Em PR: lint + `dbt build` em dev + verificação de commits assinados; merge e deploy pela service account |
| 19 | Monitoramento e alertas | Completude por unidade, falha do workflow, freshness, saúde da VPN/runner e arquivos em quarentena, via Slack/e-mail |
| 20 | Segurança e LGPD | Policy tags/mascaramento de endereço, revisão de IAM, rotação de chaves |
| 21 | Testes de idempotência | Reenvio do mesmo arquivo, versão corrigida, reexecução do workflow e backfill |
| 22 | Carga histórica | Backfill das planilhas e arquivos existentes na Raw e reprocessamento das demais camadas |
| 23 | Dashboard | Painel D-1 no Looker Studio sobre a Gold, substituindo a planilha |
| 24 | Paralelo e UAT | Comparar planilha × DW por 1–2 semanas, com validação dos responsáveis de Operações |
| 25 | Documentação e treinamento | dbt docs, runbook, capacitação do time |
| 26 | Go-live e hypercare | Desligar o processo manual e acompanhar de perto |
| 27 | Fase 2: inteligência | Alertas de ruptura e anomalias; previsão de demanda e estoque (BigQuery ML ou Vertex AI) |

---

## 6. Backlog (melhorias futuras)

| # | Atividade | Descrição |
|---|---|---|
| 1 | Migrar base PostgreSQL para GCP | Trazer as tabelas existentes nessa base direto para o GCP, eliminando outro uma ferramenta externa e unificando tudo dentro da plataforma. |
| 2 | Automatizar o envio dos CSV’s | Para evitar a interferência humana, seria possível criar uma automação que enviaria, de forma automática, os CSV’s para o GCS. |

---

## Premissas

- A chave do pedido é composta (`id_unidade`, `id_pedido`).
- `item_pedido` não traz unidade; ela é derivada do caminho do arquivo.
- O status do pedido pode mudar entre envios diários.
- As unidades enviam os arquivos até antes da execução diária do workflow; arquivos tardios são processados na execução seguinte.
