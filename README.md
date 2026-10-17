<div align="center">

# 🇧🇷 Brazilian Financial Data Pipeline

**Engenharia de Dados · ETL/ELT · Dados econômicos · Analytics**

Um pipeline incremental para coletar indicadores oficiais do Banco Central, armazenar no PostgreSQL e transformá-los em uma base analítica mensal.

![Python](https://img.shields.io/badge/PYTHON-111827?style=for-the-badge&logo=python&logoColor=3776AB)
![PostgreSQL](https://img.shields.io/badge/POSTGRESQL-111827?style=for-the-badge&logo=postgresql&logoColor=4169E1)
![Docker](https://img.shields.io/badge/DOCKER-111827?style=for-the-badge&logo=docker&logoColor=2496ED)
![Airflow](https://img.shields.io/badge/AIRFLOW-111827?style=for-the-badge&logo=apacheairflow&logoColor=017CEE)
![dbt](https://img.shields.io/badge/dbt-111827?style=for-the-badge&logo=dbt&logoColor=FF694B)

[**Código Python**](./src/financial_pipeline) · [**Modelos dbt**](./dbt/models) · [**Testes automatizados**](./tests)

</div>

---

## 01 / O problema

Dados macroeconômicos frequentemente precisam ser consultados em diferentes frequências, convertidos, validados e reunidos para análises financeiras. Este projeto demonstra uma solução reprodutível para:

- **Coletar** séries temporais da API SGS do Banco Central;
- **Validar** formato, datas, duplicidades e valores;
- **Persistir** observações no PostgreSQL com carga incremental e `UPSERT`;
- **Orquestrar** a coleta diária usando Apache Airflow;
- **Transformar** observações em um modelo analítico mensal com dbt;
- **Disponibilizar** uma tabela pronta para consumo em ferramentas como Power BI.

É um projeto de portfólio **com código executável**. Não representa um serviço financeiro de produção e **não inclui dashboard PBIX publicado**.

## 02 / Arquitetura

```text
         BANCO CENTRAL / API SGS
           1178 · 433 · 1
                 |
                 v
       Python + requests (Extract)
          retry · timeout · chunks
                 |
             JSON bruto             BRONZE
                 |
                 v
     Python (Validate & Normalize)
    date · Decimal · regras de dados
                 |
                 v
       PostgreSQL: finance.observations   SILVER
            PK(series, date)
            UPSERT idempotente
                 |
                 v
         dbt: models SQL             GOLD
       stg_sgs_observations
       mart_monthly_financial_indicators
                 |
                 v
       Power BI / SQL / Analytics

   Airflow (DAG diária) → Ingestão
   GitHub Actions       → Testes unitários
```

> **Importante:** a DAG do Airflow orquestra a **ingestão**. A etapa de transformação `dbt build` é executada separadamente, conforme abaixo. Não há integração automática Airflow → dbt nesta versão.

## 03 / Fontes de dados

| Série | Código SGS | Periodicidade | Unidade |
|:--|--:|:--|:--|
| SELIC anualizada (base 252) | `1178` | Diária | % ao ano |
| IPCA | `433` | Mensal | variação % mensal |
| Dólar comercial de venda | `1` | Diária | BRL/USD |

Dados oficiais obtidos no sistema [SGS do Banco Central do Brasil](https://dadosabertos.bcb.gov.br/).

**Regra da API:** consultas históricas de séries diárias são divididas em janelas de no máximo 3.650 dias, respeitando o limite de até dez anos por requisição.

## 04 / Como rodar localmente

**Pré-requisitos:** Docker com Docker Compose, Python 3.11+ e conexão com a internet.

### A. Suba o PostgreSQL

```bash
git clone https://github.com/claudiogardenaldev/Brazilian-Financial-Data-Pipeline.git
cd Brazilian-Financial-Data-Pipeline

docker compose up -d postgres
```

A inicialização cria o banco `finance`, o esquema `finance`, a tabela de observações e o histórico de execuções. As credenciais no Compose são **apenas para desenvolvimento local**.

### B. Execute a ingestão

**Linux / macOS:**

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src

python -m financial_pipeline.cli --start-date 2024-01-01
```

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"

python -m financial_pipeline.cli --start-date 2024-01-01
```

Para limitar a coleta a uma série ou escolher um intervalo:

```bash
python -m financial_pipeline.cli --series 433 --start-date 2025-01-01 --end-date 2025-12-31
```

Os JSONs recebidos são salvos em `data/raw/` (ignorado pelo Git). A aplicação registra a execução na tabela `finance.pipeline_runs`. Se uma etapa falhar, registra o erro e encerra sem marcar a coleta como bem-sucedida.

### C. Construa a camada analítica com dbt

```bash
docker compose --profile transformation run --build --rm dbt
```

O comando executa `dbt build`, com **modelos e testes de qualidade**. A tabela final estará em:

```sql
SELECT * 
FROM analytics.mart_monthly_financial_indicators
ORDER BY month DESC
LIMIT 12;
```

Campos gerados:

| Campo | Significado |
|:--|:--|
| `month` | Mês de referência |
| `selic_annual_pct` | Última taxa SELIC anualizada registrada no mês |
| `ipca_monthly_pct` | Variação do IPCA publicada para o mês |
| `usd_brl_avg` | Média das cotações diárias observadas no mês |

**Atenção às frequências:** SELIC (% a.a.), IPCA (% a.m.) e dólar (BRL/USD) têm unidades diferentes. Não são diretamente comparáveis nem devem ser somados. A média mensal do dólar é uma agregação analítica, não uma taxa oficial de fim de mês.

### D. Orquestração opcional com Airflow

```bash
docker compose --profile orchestration up -d --build
```

Acesse `http://localhost:8080`, com login de demonstração `admin` / `admin`, e ative a DAG **`bcb_financial_indicators`**.

A DAG está programada para **10:00 UTC diariamente**, sem execução retroativa automática (`catchup=False`). Ela usa um intervalo de revisita de 60 dias para capturar ajustes recentes das séries.

> O Airflow é opcional para a ingestão manual; é preciso ter recursos de memória suficientes para seus serviços. Altere todas as credenciais e segredos antes de qualquer implantação fora do ambiente local.

### E. Rode os testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

Os testes simulam respostas HTTP e verificam normalização, datas, duplicidades e comportamento incremental **sem chamar o Banco Central nem depender de um PostgreSQL ativo**. A automação está definida em [GitHub Actions](./.github/workflows/tests.yml).

## 05 / Decisões técnicas

| Decisão | Justificativa |
|:--|:--|
| `Decimal` na normalização | Evitar erros de arredondamento desnecessários na representação de valores |
| `(series_code, observed_on)` como PK | Garantir unicidade por série e data |
| `ON CONFLICT DO UPDATE` | Permitir reprocessamento e atualização de registros revisados |
| `lookback` de 45 dias | Reconsultar parte recente do histórico a cada execução manual |
| HTTP retry e timeout | Tratar falhas transitórias sem travar indefinidamente |
| Bronze em JSON local | Manter uma cópia do retorno original para auditoria/debug |
| dbt | Organizar transformação SQL e testes da camada Gold |

**Cuidado com atrasos de publicação:** a ausência de novos dados em fins de semana ou antes da divulgação do IPCA não é necessariamente uma falha da API.

## 06 / Estrutura do projeto

```text
Brazilian-Financial-Data-Pipeline/
├── .github/workflows/tests.yml
├── dags/financial_pipeline.py
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── stg_sgs_observations.sql
│       ├── mart_monthly_financial_indicators.sql
│       └── schema.yml
├── sql/
│   ├── init.sql
│   └── example_queries.sql
├── src/financial_pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── client.py
│   ├── repository.py
│   └── cli.py
├── tests/
│   ├── test_client.py
│   └── test_repository.py
├── Dockerfile.airflow
├── Dockerfile.dbt
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```


---

<div align="center">

Projeto de portfólio desenvolvido por **[Cláudio Gardenal](https://github.com/claudiogardenaldev)**

**Engenharia de Dados · Python · SQL · Airflow · dbt**

</div>
