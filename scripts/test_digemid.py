import logging, json, os
from datetime import datetime

from src.dataset.digemid_plugin import (
    fetch_archive_pages,
    fetch_detail,
    DigemidAlertsPlugin,
    parse_date_tokens,
)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def main():
    print("=== DIGEMID Diagnostic ===")
    pages = fetch_archive_pages(1)
    print(f"Archive listings count (page1): {len(pages)}")
    if not pages:
        print("No listings found; aborting")
        return
    first = pages[0]
    print("First listing URL:", first.url)
    # Fetch details for first 3 only
    details = []
    for idx, p in enumerate(pages[:3]):
        d = fetch_detail(p.url)
        details.append(d)
        print(f"-- Detail {idx+1} URL: {p.url}")
        print("   publication_date=", d.get("publication_date"), "tokens_raw=", parse_date_tokens(d.get("raw_text",""))[:3])
    detail = details[0]
    print("First detail keys:", list(detail.keys()))
    print("First detail text sample:\n", detail.get("raw_text","")[:400].replace('\n',' '))

    # Run plugin normalization for a small date window
    plugin = DigemidAlertsPlugin()
    since = datetime.utcnow().strftime('%Y-01-01')  # broad window
    until = datetime.utcnow().strftime('%Y-%m-%d')
    # Try fetching at most 5 raw records via plugin but short-circuit after 5
    raws = []
    for r in plugin.fetch_raw(since, until):
        raws.append(r)
        if len(raws) >= 5:
            break
    print(f"Plugin raw sample count (first 5 max): {len(raws)} (window {since}..{until})")
    if raws:
        sample = raws[0]
        print("Sample meta: inferred=", sample.get('_date_inferred'), 'effective_date=', sample.get('_effective_date'))
        norms = list(plugin.normalize_batch([sample]))
        n = norms[0]
        print("Normalized recall:", n['recall'])
        print("Normalized timeline:", n['timeline'])

    # Dump diagnostic JSON
    os.makedirs('digemid_debug', exist_ok=True)
    with open('digemid_debug/first_detail.json','w', encoding='utf-8') as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)
    print("Saved digemid_debug/first_detail.json")

if __name__ == '__main__':
    main()
