"""Normalization logic to map openFDA enforcement records to RecallCanonical subset."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List


CLASSIFICATION_ALLOWED = {"I", "II", "III"}

LOT_REGEXES = [
    re.compile(r"\bLOT[:\s-]*([A-Z0-9-]{3,})", re.IGNORECASE),
    re.compile(r"\bLote[:\s-]*([A-Z0-9-]{3,})", re.IGNORECASE),
    re.compile(r"\bBatch[:\s-]*([A-Z0-9-]{3,})", re.IGNORECASE),
]

DISTRIBUTION_CANONICAL = {
    "nationwide": ["US"],
    "national": ["US"],
    "puerto rico": ["PR"],
    "u.s. virgin islands": ["VI"],
    "virgin islands": ["VI"],
}

US_STATE_MAP = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}


def normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    for fmt in ["%Y-%m-%d", "%Y/%m/%d"]:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_lot_numbers(code_info: str | None) -> List[str]:
    if not code_info:
        return []
    lots = set()
    for rx in LOT_REGEXES:
        for m in rx.finditer(code_info):
            lots.add(m.group(1).upper())
    return sorted(lots)


def _extract_states(text: str) -> List[str]:
    found = set()
    for name, code in US_STATE_MAP.items():
        if re.search(rf"\b{name}\b", text):
            found.add(code)
    if "puerto rico" in text:
        found.add("PR")
    if "virgin islands" in text:
        found.add("VI")
    return sorted(found)


def parse_distribution(distribution_pattern: str | None) -> List[str]:
    if not distribution_pattern:
        return []
    text = unicodedata.normalize("NFKD", distribution_pattern).lower()
    for key, vals in DISTRIBUTION_CANONICAL.items():
        if key in text:
            states = _extract_states(text)
            return sorted(set(vals + states))
    states = _extract_states(text)
    return states or []


def split_product_description(desc: str | None):
    if not desc:
        return None, None
    parts = re.split(r"\s*-\s*", desc, maxsplit=1)
    if len(parts) == 2 and len(parts[0].split()) <= 4:
        return parts[0][:80].strip(), parts[1][:512].strip()
    comma = desc.split(",", 1)
    if len(comma) == 2 and len(comma[0].split()) <= 4:
        return comma[0][:80].strip(), desc[:512].strip()
    return None, desc[:512].strip()


def normalize_record(category: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    recall_number = raw.get("recall_number") or raw.get("event_id")
    classification = str(raw.get("classification", ""))
    classification = classification.strip().upper() if classification else ""
    classification = classification.split()[1]
    if classification not in CLASSIFICATION_ALLOWED:
        classification = "unknown"
    reason = raw.get("reason_for_recall") or raw.get("reason")
    product_description = raw.get("product_description")
    brand, normalized_name = split_product_description(product_description)
    code_info = raw.get("code_info")
    lot_numbers = extract_lot_numbers(code_info)
    distribution_pattern = raw.get("distribution_pattern")
    countries = parse_distribution(distribution_pattern)
    report_date = normalize_date(raw.get("report_date"))
    initiation_date = normalize_date(raw.get("recall_initiation_date"))
    status = (raw.get("status") or "").lower() or "unknown"

    openfda = raw.get("openfda", {}) or {}
    print("openfda", openfda)
    gtin = None
    if isinstance(openfda, dict):
        upc = openfda.get("upc")
        if upc and isinstance(upc, list) and upc:
            gtin = upc[0]
        ndc = openfda.get("package_ndc")
        if not gtin and ndc and isinstance(ndc, list) and ndc:
            gtin = ndc[0]

    record = {
        "source": {
            "country": "US",
            "agency": "FDA",
            "url": raw.get("web_url") or raw.get("more_code_info") or "",
        },
        "recall": {
            "recall_id": recall_number,
            "category": category,
            "classification": classification,
            "reason": reason,
            "status": status,
        },
        "product": {
            "name": normalized_name,
            "brand": brand,
            "gtin_upc_ean": gtin,
        },
        "traceability": {
            "lot_numbers": lot_numbers,
            "countries_affected": countries,
            "manufacturer": raw.get("recalling_firm"),
        },
        "timeline": {
            "event_date": initiation_date,
            "publication_date": report_date,
        },
    }
    return record