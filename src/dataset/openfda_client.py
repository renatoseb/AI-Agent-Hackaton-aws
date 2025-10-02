"""Simple client for openFDA enforcement endpoints with pagination & retry."""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, Generator

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .fda_config import OPENFDA_BASE_URL, MAX_RECORDS_PER_QUERY

log = logging.getLogger(__name__)


class OpenFDAClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.getenv("OPENFDA_API_KEY")
        self.session = session or requests.Session()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
    def _get(self, path: str, params: Dict) -> Dict:
        url = f"{OPENFDA_BASE_URL}{path}"
        headers = {}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        resp = self.session.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            if ra:
                time.sleep(int(ra))
            resp.raise_for_status()
        if not resp.ok:
            log.error("openFDA error %s: %s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
        return resp.json()

    def fetch_enforcement(
        self,
        category: str,
        query: str,
        limit: int = 1000,
    ) -> Generator[Dict, None, None]:
        path = f"/{category}/enforcement.json"
        retrieved = 0
        while retrieved < MAX_RECORDS_PER_QUERY:
            remaining = MAX_RECORDS_PER_QUERY - retrieved
            page_limit = min(limit, remaining)
            params = {
                "search": query,
                "limit": page_limit,
                "skip": retrieved,
            }
            data = self._get(path, params)
            results = data.get("results", [])
            if not results:
                break
            for r in results:
                yield r
            retrieved += len(results)
            if len(results) < page_limit:
                break

    @staticmethod
    def build_date_range_query(field: str, start_yyyymmdd: str, end_yyyymmdd: str) -> str:
        """Return a Lucene style date range query.

        IMPORTANT:
        openFDA documentation shows URLs like field:[20240101+TO+20240201]. The '+' characters
        in those examples are URL-encoded spaces (application/x-www-form-urlencoded). If we
        literally place '+' in the raw string, requests.urlencode will escape them as '%2B' and
        the backend will see plus symbols instead of whitespace, causing parse_exception errors.

        Therefore we build the query using actual spaces and allow urlencode to convert spaces
        to '+'.
        """
        return f"{field}:[{start_yyyymmdd} TO {end_yyyymmdd}]"

    def debug_query(self, category: str, query: str, skip: int, limit: int):  # helper for verbose troubleshooting
        log.debug("openFDA request category=%s skip=%d limit=%d query=%s", category, skip, limit, query)