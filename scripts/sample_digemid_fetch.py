import logging
from datetime import datetime
from itertools import islice

from src.dataset.digemid_plugin import DigemidAlertsPlugin, parse_recall_id  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

def main():
    plugin = DigemidAlertsPlugin()
    since = '2025-09-01'
    until = datetime.utcnow().strftime('%Y-%m-%d')
    print(f"Window: {since}..{until}")

    raws = list(islice(plugin.fetch_raw(since, until), 5))
    print(f"Records fetched (limited to 5): {len(raws)}")
    if not raws:
        print('No records returned.')
        return

    print("Index | EffectiveDate | Inferred | RecallID | URL")
    for idx, r in enumerate(raws, 1):
        listing = r.get('listing', {})
        detail = r.get('detail', {})
        title = listing.get('title') or ''
        rid = parse_recall_id(title) or parse_recall_id(detail.get('raw_text','')) or 'N/A'
        eff = r.get('_effective_date')
        inf = r.get('_date_inferred')
        url = (listing.get('url') or '')[:60]
        print(f"{idx:>5} | {eff} | {str(inf):>8} | {rid:<16} | {url}")

    any_real = any(not r.get('_date_inferred') for r in raws)
    print(f"Any real publication date parsed? {any_real}")

    # Check debug directory
    import os
    if os.path.isdir('digemid_debug'):
        samples = os.listdir('digemid_debug')[:5]
        print(f"digemid_debug/ exists, sample files: {samples}")
    else:
        print("digemid_debug/ not created (no missing-date dumps or not triggered yet).")

if __name__ == '__main__':
    main()
