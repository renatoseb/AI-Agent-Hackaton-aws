"""Generic ingestion orchestrator using registered plugins.

Example:
  python -m src.dataset.orchestrator --plugin us_fda_enforcement --since 2025-09-01 --until 2025-10-02 --output data_output
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
import pandas as pd

from .common.base import get_plugin, PLUGIN_REGISTRY  # noqa: F401
from .common.state import load_watermark, save_watermark
from .common.storage import write_json_lines, write_parquet
from .common.schema import CANONICAL_COLUMN_NAMES

# Ensure plugin modules are imported so they self-register
from . import fda_plugin  # type: ignore  # registers us_fda_enforcement

log = logging.getLogger("orchestrator")


def main():
    parser = argparse.ArgumentParser(description="Generic recall ingestion orchestrator")
    parser.add_argument("--plugin", required=True, help="Plugin id (e.g. us_fda_enforcement)")
    parser.add_argument("--output", required=True, help="Output root (local or s3://bucket/prefix)")
    parser.add_argument("--since", help="Start date YYYY-MM-DD (if omitted uses watermark or until)")
    parser.add_argument("--until", help="End date YYYY-MM-DD (default today)")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    plugin = get_plugin(args.plugin)

    output_root = args.output.rstrip("/")
    state_root = f"{output_root}/.state"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    until = args.until or today
    since = args.since or load_watermark(state_root, plugin.id) or until

    log.info("Running plugin=%s since=%s until=%s", plugin.id, since, until)

    raw_iter = list(plugin.fetch_raw(since, until))
    log.info("Fetched raw records=%d", len(raw_iter))

    # Partition by until date (same simplification used earlier)
    dt = datetime.strptime(until, "%Y-%m-%d")
    year, month = dt.year, dt.month
    raw_path = f"{output_root}/raw/{plugin.id}/year={year}/month={month:02d}/data.jsonl"
    write_json_lines(raw_iter, raw_path)

    normalized_iter = list(plugin.normalize_batch(raw_iter))
    # Flatten minimal columns
    rows = []
    for r in normalized_iter:
        recall = r.get("recall", {})
        product = r.get("product", {})
        trace = r.get("traceability", {})
        timeline = r.get("timeline", {})
        source = r.get("source", {})
        row = {
            "recall_id": recall.get("recall_id"),
            "classification": recall.get("classification"),
            "reason": recall.get("reason"),
            "product_name": product.get("name"),
            "brand": product.get("brand"),
            "gtin_upc_ean": product.get("gtin_upc_ean"),
            "lot_numbers": trace.get("lot_numbers"),
            "manufacturer": trace.get("manufacturer"),
            "distribution": trace.get("countries_affected"),
            "event_date": timeline.get("event_date"),
            "publication_date": timeline.get("publication_date"),
            "status": recall.get("status"),
            "category": recall.get("category"),
            "source_country": source.get("country"),
            "source_agency": source.get("agency"),
            "plugin_id": plugin.id,
        }
        # Guarantee all canonical columns present (fill missing with None)
        for col in CANONICAL_COLUMN_NAMES:
            row.setdefault(col, None)
        rows.append(row)
    df = pd.DataFrame(rows, columns=CANONICAL_COLUMN_NAMES) if rows else pd.DataFrame(columns=CANONICAL_COLUMN_NAMES)
    if not df.empty:
        df["year"] = year
        df["month"] = month
        curated_path = f"{output_root}/curated/{plugin.id}/year={year}/month={month:02d}/data.parquet"
        write_parquet(df, curated_path)
        log.info("Wrote curated rows=%d to %s", len(df), curated_path)
    else:
        log.warning("No normalized rows produced for plugin=%s", plugin.id)

    save_watermark(state_root, plugin.id, until)
    log.info("Done.")


if __name__ == "__main__":
    main()