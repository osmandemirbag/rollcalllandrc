"""Index of recorded (open) votes in the single-chamber TBMM, 1943-60, from the GNACT page text.

A vote is a result header ('... verilen oyların sonucu / reylerin neticesi') followed within
900 characters by a yes tally and at least one other tally line, in any of the vocabularies the
minutes used (Reddedenler, Kabul etmiyenler, Müstenkif, Çekinser, Reye iştirak etmiyenler, Oya
katılmayanlar). Output: data/interim/tbmm_1943_60_votes.csv with the GNACT page, which is also the
page of the TBMM PDF (tbmm{term}{volume}{session}.pdf).
"""
import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
HDR = re.compile(r"(verilen|verilmiş olan)\s+(rey|oy)(ların|lerin)\s+(neticesi|sonucu)", re.I)
OTHER = re.compile(r"Reddedenler|Kabul etm|Müstenkif|Çekin|Reye iştirak|Oya katıl|Oylamaya katıl", re.I)


def num(label, s):
    m = re.search(r"(?:" + label + r")[^\d\n]{0,25}(\d{1,3})", s, re.I)
    return int(m.group(1)) if m else None


def main():
    t = pq.read_table(ROOT / "data/gnact/pages_1943_1980.parquet", filters=[("legislative_body", "=", "TBMM")],
                      columns=["document_id", "term", "volume", "session", "page_num", "text"]).to_pandas()
    rows = []
    for r in t.itertuples():
        s = r.text or ""
        for m in HDR.finditer(s):
            after = s[m.end():m.end() + 900]
            if not (re.search(r"Kabul edenler", after, re.I) and OTHER.search(after)):
                continue
            title = re.sub(r"\s+", " ", s[max(0, m.start() - 260):m.end()]).strip()
            title = re.sub(r"[*|#]+", " ", title)
            rows.append({"doc": r.document_id, "term": r.term, "volume": r.volume, "session": r.session,
                         "page": r.page_num, "title": re.sub(r"\s+", " ", title)[-320:],
                         "members": num("Üye sayısı|Aza adedi", after), "yes": num("Kabul edenler", after),
                         "no": num("Reddedenler|Kabul etm[iı]yenler|Kabul etmişenler", after),
                         "abstain": num("Müstenkif|Çekin", after),
                         "not_voting": num("Reye iştirak etm|Oya katıl|Oylamaya katıl", after)})
    d = pd.DataFrame(rows).drop_duplicates(["doc", "title"])
    d["session_id"] = d.doc.str.extract(r"(tbmm\d{8})")[0]
    d.to_csv(ROOT / "data/interim/tbmm_1943_60_votes.csv", index=False)
    print(len(d), d.groupby("term").size().to_dict())


if __name__ == "__main__":
    main()
