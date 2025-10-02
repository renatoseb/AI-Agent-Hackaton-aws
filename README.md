# AI-Agent-Hackaton-aws

## RecallShield – Recall Ingestion & Normalization (FDA + Multi-Country)

This repository provides the foundation to ingest and normalize recall reports (starting with FDA food/drug/device) and an extensible plugin architecture for additional national authorities (COFEPRIS, ANMAT, ANVISA, etc.).

## 1. High-Level Architecture

Per data source (plugin) pipeline:
1. Fetch: retrieve (API / scraping / PDFs) filtered by incremental date window.
2. Raw persist: write raw JSONL partitioned by year/month.
3. Normalize: map to a canonical flattened subset with uniform columns.
4. Curated persist: write Parquet (partitioned by year, month) per plugin.
5. Watermark: update `.state/<plugin>.json` for incremental runs.

## 2. Main Components

| File | Description |
|------|-------------|
| `src/dataset/fda_config.py` | FDA-specific configuration (categories, limits). |
| `src/dataset/openfda_client.py` | Paginated + retry client for openFDA enforcement endpoints. |
| `src/dataset/normalize.py` | FDA normalizer to canonical subset. |
| `src/dataset/common/base.py` | Interfaces & plugin registry. |
| `src/dataset/common/storage.py` | Local/S3 IO (JSONL & Parquet) + state persistence. |
| `src/dataset/common/state.py` | Incremental watermark management. |
| `src/dataset/common/utils.py` | Shared helpers (dates, lot extraction). |
| `src/dataset/common/schema.py` | Canonical flattened column list. |
| `src/dataset/orchestrator.py` | Generic multi‑plugin CLI. |
| `src/dataset/fda_plugin.py` | `us_fda_enforcement` plugin adapter. |
| `src/dataset/fda_pipeline.py` | Legacy direct FDA pipeline (optional). |

## 3. Canonical Schema (Tier‑1 Subset)

Uniform columns (stable order):
```
recall_id, classification, reason, product_name, brand, gtin_upc_ean,
lot_numbers, manufacturer, distribution, event_date, publication_date,
status, category, source_country, source_agency, plugin_id,
year, month
```
Notes:
- `lot_numbers` & `distribution` are arrays.
- `year` and `month` also serve as partitions (S3 / Athena).
- Planned tier‑2 expansions: jurisdiction, narrative, confidence, doc_hash, extraction_method.

## 4. Data Layout

```
<output>/
  raw/<plugin_id>/year=YYYY/month=MM/data.jsonl
  curated/<plugin_id>/year=YYYY/month=MM/data.parquet
  .state/<plugin_id>.json
```

FDA example (`plugin_id=us_fda_enforcement`):
```
data_output/
  raw/us_fda_enforcement/year=2025/month=10/data.jsonl
  curated/us_fda_enforcement/year=2025/month=10/data.parquet
  .state/us_fda_enforcement.json
```

## 5. Incremental Strategy

- Base incremental field (FDA): `report_date` (can switch to `recall_initiation_date`).
- If you omit `--since`, the saved watermark (`last_until`) is used; otherwise your provided date.
- If no watermark and no `--since`, only the `--until` day is processed.

## 6. Orchestrator + Plugin Usage

Install dependencies (Windows PowerShell):
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

FDA run (explicit window):
```powershell
python -m src.dataset.orchestrator --plugin us_fda_enforcement --since 2025-09-01 --until 2025-10-02 --output data_output --log-level INFO
```

Incremental follow-up (omit --since):
```powershell
python -m src.dataset.orchestrator --plugin us_fda_enforcement --until 2025-10-05 --output data_output
```

Writing to S3 (needs AWS credentials):
```powershell
python -m src.dataset.orchestrator --plugin us_fda_enforcement --since 2025-09-01 --until 2025-10-02 --output s3://recallshield
```

## 7. Optional Legacy: Direct FDA Pipeline
`fda_pipeline.py` retained for quick troubleshooting:
```powershell
python -m src.dataset.fda_pipeline --output data_output --since 2025-09-01 --until 2025-10-02 --categories food drug device
```

## 8. TODO Athena / Glue (Current Canonical Schema)

Example table (only FDA plugin). Adjust LOCATION to your bucket/prefix:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS recalls_us_fda_enforcement (
  recall_id string,
  classification string,
  reason string,
  product_name string,
  brand string,
  gtin_upc_ean string,
  lot_numbers array<string>,
  manufacturer string,
  distribution array<string>,
  event_date date,
  publication_date date,
  status string,
  category string,
  source_country string,
  source_agency string,
  plugin_id string
)
PARTITIONED BY (year int, month int)
STORED AS PARQUET
LOCATION 's3://recallshield/curated/us_fda_enforcement/';
```

After new data arrives:
```sql
MSCK REPAIR TABLE recalls_us_fda_enforcement;
```

Query example:
```sql
SELECT recall_id, classification, product_name, publication_date
FROM recalls_us_fda_enforcement
WHERE classification = 'I'
  AND publication_date BETWEEN DATE '2025-09-01' AND DATE '2025-10-02';
```

## 9. Adding a New Country / Authority
1. Create folder `src/dataset/<country_authority>/` (e.g. `mx_cofepris`).
2. Implement a new plugin similar to `fda_plugin.py` with:
   - `id`, `country`, `agency`, `fetch_raw`, `normalize_batch`.
3. Reuse helpers (`common/utils.py`) and emit the same canonical keys.
4. Import the module in `orchestrator.py` (later: auto‑discovery).
5. Run orchestrator with `--plugin <id>`.

## 10. Next Steps
1. Create extraction from PERU, MX. 
---


