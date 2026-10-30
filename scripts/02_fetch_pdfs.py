"""Download the TBMM minutes PDFs for every vote in data/processed/votes.csv.

Needs outbound access to www5.tbmm.gov.tr. Already-downloaded files are skipped.
    python3 02_fetch_pdfs.py [--only-land]
"""
import sys
import time
import urllib.request

import pandas as pd

from common import PDF_DIR, PROCESSED


def main():
    votes = pd.read_csv(PROCESSED / "votes.csv")
    if "--only-land" in sys.argv:
        votes = votes[votes.topic_group == "land"]
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    urls = votes.drop_duplicates("session_id")[["session_id", "pdf_url"]]
    failed = []
    for sid, url in urls.itertuples(index=False):
        out = PDF_DIR / f"{sid}.pdf"
        if out.exists() and out.stat().st_size > 10_000:
            continue
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    out.write_bytes(r.read())
                print("ok  ", sid)
                break
            except Exception as e:  # noqa: BLE001 - report and retry
                wait = 2 ** (attempt + 1)
                print(f"fail {sid} ({e}); retry in {wait}s")
                time.sleep(wait)
        else:
            failed.append(sid)
        time.sleep(1)
    print(f"{len(urls) - len(failed)}/{len(urls)} PDFs present; failed: {failed}")


if __name__ == "__main__":
    main()
