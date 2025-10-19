"""Command-line pipeline to ingest and normalize FDA (openFDA) enforcement recalls."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime

import pandas as pd

from .fda_config import (
    CURATED_PREFIX,
    ENFORCEMENT_CATEGORIES,
    IngestionParams,
    RAW_PREFIX,
    STATE_DIR_NAME,
    state_file_name,
)
from .openfda_client import OpenFDAClient
from .normalize import normalize_record
from .storage import read_state, write_state, write_json_lines, write_parquet

log = logging.getLogger("fda_pipeline")


def to_yyyymmdd(date_str: str) -> str:
    return date_str.replace("-", "")


def ingest_category(params: IngestionParams, output_root: str, client: OpenFDAClient):
    log.info("Ingesting category=%s since=%s until=%s", params.category, params.since, params.until)
    query = client.build_date_range_query(
        params.incremental_field,
        to_yyyymmdd(params.since),
        to_yyyymmdd(params.until),
    )
    raw_records = list(client.fetch_enforcement(params.category, query, limit=params.page_size))
    log.info("Fetched %d raw records", len(raw_records))
    until_dt = datetime.strptime(params.until, "%Y-%m-%d")
    year, month = until_dt.year, until_dt.month
    raw_path = f"{output_root.rstrip('/')}/{RAW_PREFIX}/{params.category}/year={year}/month={month:02d}/data.jsonl"
    write_json_lines(raw_records, raw_path)
    normalized = [normalize_record(params.category, r) for r in raw_records]
    flat_rows = []
    for rec in normalized:
        flat_rows.append(
            {
                "recall_id": rec["recall"]["recall_id"],
                "classification": rec["recall"]["classification"],
                "reason": rec["recall"].get("reason"),
                "product_name": rec["product"].get("name"),
                "brand": rec["product"].get("brand"),
                "gtin_upc_ean": rec["product"].get("gtin_upc_ean"),
                "lot_numbers": rec["traceability"].get("lot_numbers", []),
                "manufacturer": rec["traceability"].get("manufacturer"),
                "distribution": rec["traceability"].get("countries_affected", []),
                "event_date": rec["timeline"].get("event_date"),
                "publication_date": rec["timeline"].get("publication_date"),
                "status": rec["recall"].get("status"),
                "category": rec["recall"].get("category"),
            }
        )
    df = pd.DataFrame(flat_rows)
    if not df.empty:
        df["year"] = year
        df["month"] = month
        curated_path = f"{output_root.rstrip('/')}/{CURATED_PREFIX}/year={year}/month={month:02d}/{params.category}.parquet"
        write_parquet(df, curated_path)
        log.info("Wrote curated parquet rows=%d -> %s", len(df), curated_path)
    else:
        log.warning("No data to write for category=%s", params.category)
    return len(raw_records)


def resolve_incremental_dates(category: str, since: str | None, until: str | None, state_root: str) -> tuple[str, str]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    until_final = until or today
    state = read_state(state_root, state_file_name(category)) if state_root else None
    if state and not since:
        since_final = state.get("last_until")
    else:
        since_final = since or until_final
    return since_final, until_final


def update_state(category: str, until: str, state_root: str):
    if not state_root:
        return
    write_state(state_root, state_file_name(category), {"last_until": until})


def main():
    parser = argparse.ArgumentParser(description="Ingest & normalize FDA enforcement recalls")
    parser.add_argument("--output", required=True, help="Root output path (local folder or s3://bucket/path)")
    parser.add_argument("--categories", nargs="*", default=ENFORCEMENT_CATEGORIES, help="Categories to ingest")
    parser.add_argument("--since", help="ISO start date (YYYY-MM-DD). If omitted and state exists, continues after last run")
    parser.add_argument("--until", help="ISO final date (YYYY-MM-DD). Defaults to today")
    parser.add_argument("--incremental-field", default="report_date", choices=["report_date", "recall_initiation_date"], help="Field for incremental window")
    parser.add_argument("--page-size", type=int, default=1000, help="Page size per request (<=1000 recommended)")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    output_root = args.output.rstrip("/")
    state_root = f"{output_root}/.state" if args.output else None

    client = OpenFDAClient()

    total = 0
    for cat in args.categories:
        since_final, until_final = resolve_incremental_dates(cat, args.since, args.until, state_root)
        p = IngestionParams(category=cat, since=since_final, until=until_final, incremental_field=args.incremental_field, page_size=args.page_size).validate()
        count = ingest_category(p, output_root, client)
        total += count
        update_state(cat, until_final, state_root)

    log.info("Ingestion complete total_records=%d", total)


if __name__ == "__main__":
    main()