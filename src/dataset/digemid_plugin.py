"""DIGEMID (Peru) alerts scraping plugin.

Strategy:
- Paginated archive pages under /publicaciones/alertas-modificaciones/alertas/page/{n}/ up to oldest.
- Each archive page lists posts as H2 with anchor text like "ALERTA DIGEMID Nº 113-2025" followed by short product snippet and date token (e.g. 02Oct without year; year inferred from URL segment or alert number pattern).
- For reliability we parse static HTML via requests + BeautifulSoup (site currently server-side rendered WordPress style). Avoid brittle class name dependency: target semantic tags (h2>a) whose href contains '/alerta-digemid-no-'.
- Detail page: Title H1/H2, body paragraphs/lists sometimes with bullet (•) product lines, possible PDF link (Descargar) containing full circular; we attempt to collect:
    * recall_id: normalized from alert number (e.g. DIGEMID-113-2025)
    * classification: N/A (None) unless keywords ("RETIRO", "ALERTA", "FALSIFICADO") map to generic values (we map FALSIFICADO->"Counterfeit", RETIRO->"Withdrawal")
    * reason: first heading/paragraph after title (uppercase sentence) limited length
    * product_name: first product bullet or capitalized product token in title if available
    * brand: None (DIGEMID alerts often list only INN/ingredient); can be extended by PDF parsing later
    * lot_numbers: regex for lote / Lote / LOTE <code>; not present in snippet; PDF parse future
    * manufacturer: attempt pattern (LABORATORIO|LAB.) <name> in text
    * distribution: ["PE"] constant (country affected Peru); future: parse if specific regions
    * event_date/publication_date: page date (converted) as both for now
    * status: None (could derive from words like RETIRO VOLUNTARIO => voluntary)
    * category: from taxonomy: e.g. 'Alertas', 'Productos Falsificados', 'Control de Calidad'; we use list of categories extracted from breadcrumb/taxonomy links that appear with Post; choose most specific (exclude broad parent). For now pick first taxonomy after 'Alertas y Modificaciones' that differs from 'Alertas'.

Incremental:
- No official API; implement incremental by stopping pagination when encountering an alert_id already ingested (persist last recall_id in watermark) OR using publication date cutoff since/until.
- We'll parse date on listing (ddMon) plus infer year from detail URL (segment /2025/). Convert to YYYY-MM-DD using month lookup.

Watermark semantics:
- Use publication_date string (YYYY-MM-DD). We'll iterate pages until date < since.

Robustness:
- Respect politeness delay (configurable) though not implemented yet (TODO) if scaling.
- Retry with simple backoff on HTTP errors.

Future Enhancements:
- PDF parsing for lot numbers, manufacturer, reason details.
- NLP / LLM enrichment when body sparse.
"""
from __future__ import annotations

import re
import time
import random
from dataclasses import dataclass
from typing import Iterable, Dict, Any, List, Optional, Set
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import json

from .common.base import DataSourcePlugin, register

log = logging.getLogger("digemid")

BASE_ARCHIVE = "https://www.digemid.minsa.gob.pe/webDigemid/publicaciones/alertas-modificaciones/alertas/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}
MONTH_MAP = {"Ene":1, "Feb":2, "Mar":3, "Abr":4, "May":5, "Jun":6, "Jul":7, "Ago":8, "Sep":9, "Oct":10, "Nov":11, "Dic":12,
             "Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}

ALERT_ANCHOR_PATTERN = re.compile(r"/alerta-digemid-no-\d{1,3}-\d{4}/")
ALERT_ID_EXTRACT = re.compile(r"ALERTA\s+DIGEMID\s+N[º°]\s+(\d{1,3})-(\d{4})", re.IGNORECASE)
DATE_TOKEN_PATTERN = re.compile(r"(\d{1,2})([A-Za-z]{3})")
# Broader date token including Spanish & English abbreviations without separator, e.g. 02Oct, 2Sep, 15Ene
DATE_TOKEN_ABBR = re.compile(r"\b(\d{1,2})(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", re.IGNORECASE)
CLASSIFICATION_KEYWORDS = [
    (re.compile(r"FALSIFICAD", re.IGNORECASE), "Counterfeit"),
    (re.compile(r"RETIRO", re.IGNORECASE), "Withdrawal"),
]
MANUFACTURER_PATTERN = re.compile(r"LAB(?:ORATORIO)?\s+([A-ZÁÉÍÓÚÑ0-9&.,\- ]{3,})")
LOT_PATTERN = re.compile(r"LOTE\s+([A-Z0-9\-]+)")
# Common taxonomy/category tokens observed on site to refine category vs generic 'Alert'
CATEGORY_PATTERNS = [
    (re.compile(r"PRODUCTOS?\s+FALSIFICADOS", re.IGNORECASE), "Counterfeit Product"),
    (re.compile(r"CONTROL\s+DE\s+CALIDAD", re.IGNORECASE), "Quality Control"),
    (re.compile(r"RETIRO\s+VOLUNTARIO", re.IGNORECASE), "Voluntary Withdrawal"),
    (re.compile(r"RETIRO\s+DEL\s+MERCADO", re.IGNORECASE), "Market Withdrawal"),
    (re.compile(r"DISPOSITIVO[S]?\s+M[ÉE]DICO[S]?", re.IGNORECASE), "Medical Device"),
]
@dataclass
class AlertListing:
    url: str
    title: str


def _http_get(url: str, *, max_retries: int = 3, sleep_base: float = 0.6):
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code >= 500:
                raise RuntimeError(f"Server {resp.status_code}")
            return resp
        except Exception as e:
            if attempt == max_retries:
                raise
            wait = sleep_base * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            log.warning("Retry %s/%s GET %s due to %s; sleeping %.2fs", attempt, max_retries, url, e.__class__.__name__, wait)
            time.sleep(wait)


def fetch_archive_pages(max_pages: int = 2, max_listings: int | None = None) -> List[AlertListing]:
    """Fetch archive pages (limited) collecting alert listing anchors.

    max_pages kept small for diagnostic / incremental use. Increase when stabilized.
    max_listings can early-stop once enough listings gathered.
    """
    listings: List[AlertListing] = []
    seen: Set[str] = set()
    page = 1
    while page <= max_pages:
        url = BASE_ARCHIVE if page == 1 else urljoin(BASE_ARCHIVE, f"page/{page}/")
        log.info("Fetching archive page %d: %s", page, url)
        resp = _http_get(url)
        if resp.status_code != 200:
            log.warning("Archive page %s returned %s", url, resp.status_code)
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.find_all('a', href=ALERT_ANCHOR_PATTERN)
        log.info("Archive page %d anchors found=%d", page, len(anchors))
        for a in anchors:
            href = a.get('href')
            if not href or href in seen:
                continue
            seen.add(href)
            h2 = a.find_parent(['h2','h1'])
            title_text = (h2.get_text(strip=True) if h2 else a.get_text(strip=True)) or a.get_text(strip=True)
            listings.append(AlertListing(url=href, title=title_text))
        log.info("Accumulated listings=%d after page=%d", len(listings), page)
        # Heuristic stop: if fewer than 5 new anchors found we assume near end
        if page > 1 and len(anchors) < 5:
            break
        if max_listings and len(listings) >= max_listings:
            break
        page += 1
        time.sleep(0.4 + random.uniform(0, 0.2))
    return listings


def parse_date_tokens(text: str) -> List[str]:
    tokens = []
    for m in DATE_TOKEN_ABBR.finditer(text):
        day = int(m.group(1))
        mon_abbr = m.group(2)[:3].title()
        month = MONTH_MAP.get(mon_abbr, None)
        if not month:
            continue
        # Try to find year nearby (search window 40 chars after match)
        start = m.end()
        window = text[start:start+60]
        year_match = re.search(r"20\d{2}", window)
        if not year_match:
            # fallback search backwards 40 chars
            back_window = text[max(0, m.start()-60):m.start()]
            year_match = re.search(r"20\d{2}", back_window)
        if year_match:
            year = int(year_match.group(0))
        else:
            from datetime import datetime as _dt
            year = _dt.utcnow().year
        tokens.append(f"{year:04d}-{month:02d}-{day:02d}")
    return tokens


def pick_publication_date(text: str) -> Optional[str]:
    dates = parse_date_tokens(text)
    if not dates:
        return None
    # Return most recent (max) assuming page contains at least one relevant date
    return max(dates)


def fetch_detail(url: str) -> Dict[str, Any]:
    log.info("Fetching detail %s", url)
    resp = _http_get(url)
    if resp.status_code != 200:
        log.warning("Detail page %s status %s", url, resp.status_code)
        return {"_error": resp.status_code, "url": url}
    # Force correct encoding detection
    if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
        resp.encoding = resp.apparent_encoding or 'utf-8'
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # 1) Structured date extraction attempts
    iso_date = None
    # a) <time datetime="YYYY-MM-DD...">
    for t in soup.find_all('time'):
        dt_attr = t.get('datetime') or t.get('content')
        if not dt_attr:
            continue
        m_iso = re.search(r"(20\d{2}-\d{2}-\d{2})", dt_attr)
        if m_iso:
            iso_date = m_iso.group(1)
            break
    # b) <meta property="article:published_time" content="...">
    if not iso_date:
        for meta in soup.find_all('meta'):
            prop = (meta.get('property') or '').lower()
            name = (meta.get('name') or '').lower()
            if prop in ('article:published_time','og:updated_time') or name in ('date','dc.date','dc.date.issued'):
                content = meta.get('content') or ''
                m_iso = re.search(r"(20\d{2}-\d{2}-\d{2})", content)
                if m_iso:
                    iso_date = m_iso.group(1)
                    break
    # c) JSON-LD scripts
    if not iso_date:
        for script in soup.find_all('script'):
            mime = (script.get('type') or '').lower()
            if 'ld+json' in mime and script.string:
                try:
                    data = json.loads(script.string.strip())
                except Exception:
                    continue
                candidates = []
                def walk(obj):
                    if isinstance(obj, dict):
                        for k,v in obj.items():
                            lk = k.lower()
                            if lk in ('datepublished','datecreated','uploadDate'.lower()):
                                if isinstance(v,str):
                                    m_ = re.search(r"(20\d{2}-\d{2}-\d{2})", v)
                                    if m_:
                                        candidates.append(m_.group(1))
                            walk(v)
                    elif isinstance(obj, list):
                        for e in obj:
                            walk(e)
                walk(data)
                if candidates:
                    iso_date = sorted(candidates)[0]
                    break

    body_text = soup.get_text("\n", strip=True)
    share_idx = body_text.find("Compartir publicación")
    if share_idx != -1:
        main = body_text[:share_idx]
    else:
        main = body_text
    # Search tail, then full text, then raw HTML for date tokens
    tail = main[-600:]
    pub_date = iso_date or pick_publication_date(tail) or pick_publication_date(main) or pick_publication_date(html)

    # Optional: dump first N detail pages for debugging if no date
    if pub_date is None:
        # Derive simple file-safe id
        m_id = ALERT_ID_EXTRACT.search(main)
        short_id = m_id.group(1)+"-"+m_id.group(2) if m_id else str(abs(hash(url)))
        try:
            import os
            dbg_dir = 'digemid_debug'
            if not os.path.exists(dbg_dir):
                os.makedirs(dbg_dir, exist_ok=True)
            path = os.path.join(dbg_dir, f"detail_{short_id}.html")
            if not os.path.exists(path):  # don't rewrite repeatedly
                with open(path,'w',encoding='utf-8') as f:
                    f.write(html)
        except Exception:
            pass
    return {"url": url, "raw_text": main, "raw_html_head": html[:1500], "publication_date": pub_date}


def parse_recall_id(title: str) -> Optional[str]:
    m = ALERT_ID_EXTRACT.search(title)
    if m:
        return f"DIGEMID-{m.group(1)}-{m.group(2)}"
    return None


def classify(content: str) -> Optional[str]:
    for pattern, label in CLASSIFICATION_KEYWORDS:
        if pattern.search(content):
            return label
    return None


def extract_reason(content: str) -> Optional[str]:
    # Take first uppercase line longer than 15 chars
    for line in content.splitlines():
        t = line.strip()
        if len(t) > 15 and t.upper() == t and any(ch.isalpha() for ch in t):
            return t[:500]
    return None


def extract_products(content: str) -> List[str]:
    products = []
    for line in content.splitlines():
        line = line.strip(" •\t")
        if 0 < len(line) < 80 and line.isupper() and any(c.isalpha() for c in line) and not line.startswith("ALERTA DIGEMID"):
            products.append(line)
    return products[:5]


def extract_category(content: str) -> Optional[str]:
    for patt, label in CATEGORY_PATTERNS:
        if patt.search(content):
            return label
    return None


def extract_lots(content: str) -> List[str]:
    return list({m.group(1) for m in LOT_PATTERN.finditer(content)})


def extract_manufacturer(content: str) -> Optional[str]:
    m = MANUFACTURER_PATTERN.search(content)
    if m:
        return m.group(1).strip()
    return None

@register
class DigemidAlertsPlugin(DataSourcePlugin):
    id = "pe_digemid_alerts"
    country = "PE"
    agency = "DIGEMID"
    incremental_field = "publication_date"
    supports_incremental = True

    def fetch_raw(self, since: str, until: str):
        log.info("DIGEMID fetch_raw window %s..%s", since, until)
        listings = fetch_archive_pages(max_pages=2, max_listings=30)
        from datetime import datetime, timedelta
        try:
            until_dt = datetime.strptime(until, "%Y-%m-%d")
        except ValueError:
            from datetime import datetime as _dt
            until_dt = _dt.utcnow()
        for idx, lst in enumerate(listings):
            detail = fetch_detail(lst.url)
            pub_date = detail.get("publication_date")
            if not pub_date:
                # Fallback: sequential descending days from 'until' to preserve ordering
                fallback_date = (until_dt - timedelta(days=idx)).strftime("%Y-%m-%d")
            else:
                fallback_date = pub_date
            effective_date = fallback_date
            # Only skip if we have a real parsed pub_date outside window; fallback dates always included
            if pub_date and (effective_date < since or effective_date > until):
                continue
            raw = {
                "listing": lst.__dict__,
                "detail": detail,
                "_effective_date": effective_date,
                "_date_inferred": pub_date is None,
                "_fallback_strategy": None if pub_date else "sequential_desc_from_until",
            }
            log.info("Yield recall listing url=%s effective=%s inferred=%s", lst.url, effective_date, pub_date is None)
            yield raw

    def normalize_batch(self, raws: Iterable[Dict[str, Any]]):
        for raw in raws:
            listing = raw.get("listing", {})
            detail = raw.get("detail", {})
            title = listing.get("title", "")
            raw_text = detail.get("raw_text", "")
            recall_id = parse_recall_id(title) or parse_recall_id(raw_text) or listing.get("url")
            products = extract_products(raw_text)
            product_name = products[0] if products else None
            classification = classify(raw_text) or "Information"  # default generic
            reason = extract_reason(raw_text)
            lots = extract_lots(raw_text)
            manufacturer = extract_manufacturer(raw_text)
            pub_date = detail.get("publication_date") or raw.get("_effective_date")
            category = extract_category(raw_text) or "Alert"
            normalized = {
                "recall": {
                    "recall_id": recall_id,
                    "classification": classification,
                    "reason": reason,
                    "status": None,
                    "category": category,  # refined if detected
                },
                "product": {
                    "name": product_name,
                    "brand": None,
                    "gtin_upc_ean": None,
                },
                "traceability": {
                    "lot_numbers": lots or None,
                    "manufacturer": manufacturer,
                    "countries_affected": ["PE"],
                },
                "timeline": {
                    "event_date": pub_date,
                    "publication_date": pub_date,
                },
                "source": {
                    "country": "PE",
                    "agency": "DIGEMID",
                    "raw_url": listing.get("url"),
                    "date_inferred": raw.get("_date_inferred"),
                },
                "_raw": raw,
            }
            yield normalized
