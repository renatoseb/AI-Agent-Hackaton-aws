"""Canonical flattened schema columns for curated parquet across all country plugins.

We keep this minimal subset (tier-1). Additional future tiers (jurisdiction, narrative, confidence)
can extend this list while maintaining backward compatibility.

Each entry: (column_name, logical_type)
logical_type is informational only for now.
"""
from __future__ import annotations

CANONICAL_COLUMNS = [
    ("recall_id", "string"),
    ("classification", "string"),
    ("reason", "string"),
    ("product_name", "string"),
    ("brand", "string"),
    ("gtin_upc_ean", "string"),
    ("lot_numbers", "array<string>"),
    ("manufacturer", "string"),
    ("distribution", "array<string>"),
    ("event_date", "date"),
    ("publication_date", "date"),
    ("status", "string"),
    ("category", "string"),
    ("source_country", "string"),
    ("source_agency", "string"),
    ("plugin_id", "string"),
]

CANONICAL_COLUMN_NAMES = [c[0] for c in CANONICAL_COLUMNS]