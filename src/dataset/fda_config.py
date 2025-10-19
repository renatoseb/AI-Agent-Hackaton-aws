"""Configuration constants for FDA (openFDA) enforcement recall ingestion."""
from __future__ import annotations

import os
from dataclasses import dataclass


OPENFDA_BASE_URL = os.getenv("OPENFDA_BASE_URL", "https://api.fda.gov")

# Enforcement categories we currently support. The openFDA path pattern is:
#   /{category}/enforcement.json
# Where category is one of: food, drug, device
ENFORCEMENT_CATEGORIES = [
    "food",
    "drug",
    "device",
]

MAX_RECORDS_PER_QUERY = 10_000  # Absolute maximum the API will return for a query
DEFAULT_PAGE_SIZE = int(os.getenv("OPENFDA_PAGE_SIZE", "1000"))  # We'll use 1000 to balance requests

DATE_FIELDS = ["report_date", "recall_initiation_date"]

RAW_PREFIX = "raw/fda"  # appended with category/year=YYYY/month=MM
CURATED_PREFIX = "curated/fda"  # appended with year=YYYY/month=MM


@dataclass
class IngestionParams:
    category: str
    since: str  # ISO date (YYYY-MM-DD)
    until: str  # ISO date (YYYY-MM-DD)
    incremental_field: str = "report_date"  # or recall_initiation_date
    page_size: int = DEFAULT_PAGE_SIZE

    def validate(self):
        if self.category not in ENFORCEMENT_CATEGORIES:
            raise ValueError(f"Unsupported category {self.category}")
        if self.page_size > MAX_RECORDS_PER_QUERY:
            raise ValueError("Page size cannot exceed 10,000")
        return self


STATE_DIR_NAME = ".state"
STATE_FILE_TEMPLATE = "fda_{category}.json"


def state_file_name(category: str) -> str:
    return STATE_FILE_TEMPLATE.format(category=category)