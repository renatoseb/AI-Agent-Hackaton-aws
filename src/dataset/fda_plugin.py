"""FDA plugin wrapper that adapts existing FDA ingestion logic to the generic orchestrator."""
from __future__ import annotations

from .common.base import DataSourcePlugin, register
from .openfda_client import OpenFDAClient
from .normalize import normalize_record
from .fda_config import ENFORCEMENT_CATEGORIES


@register
class FDAEnforcementPlugin(DataSourcePlugin):
    id = "us_fda_enforcement"
    country = "US"
    agency = "FDA"
    incremental_field = "report_date"

    def __init__(self):
        self.client = OpenFDAClient()
        self.categories = ENFORCEMENT_CATEGORIES

    def fetch_raw(self, since: str, until: str):
        # Convert to yyyymmdd accepted by openFDA query builder using the existing helper
        from .openfda_client import OpenFDAClient as C
        for cat in self.categories:
            query = self.client.build_date_range_query(self.incremental_field, since.replace('-', ''), until.replace('-', ''))
            for r in self.client.fetch_enforcement(cat, query):
                r["_category"] = cat
                yield r

    def normalize_batch(self, raws):
        for r in raws:
            cat = r.get("_category", "unknown")
            yield normalize_record(cat, r)