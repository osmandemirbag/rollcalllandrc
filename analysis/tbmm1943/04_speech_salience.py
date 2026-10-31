"""Salience of land reform in parliamentary speech, 1943-80, from the GNACT page text.

Share of minutes pages (TBMM 1943-60; Millet Meclisi and Cumhuriyet Senatosu 1961-80) that mention
land reform or land distribution, by the legislative year's start (Millet Meclisi: by term). GNACT's OCR misreads and in places invents text,
so these are page counts of robust phrases, not quotations; quotations come from the TBMM PDFs.
Output: analysis/output/speech_land_salience.csv
"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
TERMS = {
    "land_reform": r"toprak\s+reform|tar[ıi]m\s+reform|zirai\s+reform|toprak\s+da[ğg][ıi]t|topraklan[dd][ıi]r",
    "landlord": r"toprak\s+a[ğg]a|a[ğg]al[ıi]k\s+d[üu]zen|b[üu]y[üu]k\s+arazi\s+sahip",
    "landless": r"topraks[ıi]z|az\s+topraklı",
    # Pressure from below entering debate: land occupations and seizures by peasants.
    "occupation": r"toprak\s+i[şs]gal|arazi\s+i[şs]gal|i[şs]gal\s+edilen\s+(toprak|arazi|çiftlik)|çiftlik\s+i[şs]gal|i[şs]galci\s+köylü",
    # Public land: Treasury land and commons as a reserve for distribution.
    "public_land": r"hazine\s+(arazi|toprak)|devlet\s+arazi|mera(lar)?\b|kamu\s+arazi",
}


def main():
    t = pq.read_table(ROOT / "data/gnact/pages_1943_1980.parquet",
                      columns=["legislative_body", "term", "year", "text"]).to_pandas()
    # Start year of each legislative year: TBMM term + year within it; the Senate's 'term' counts
    # legislative years from 1961; the Millet Meclisi has only its five terms (1961, 65, 69, 73, 77).
    tb = {7: 1943, 8: 1946, 9: 1950, 10: 1954, 11: 1957}
    t["start"] = [tb[int(r.term)] + int(r.year) - 1 if r.legislative_body == "TBMM" else
                  1960 + int(r.term) if r.legislative_body == "CS" else [1961, 1965, 1969, 1973, 1977][int(r.term) - 1]
                  for r in t.itertuples()]
    t["text"] = t.text.fillna("").str.lower()
    out = t[["legislative_body", "start"]].copy()
    for k, rx in TERMS.items():
        out[k] = t.text.str.contains(rx, regex=True)
    g = out.groupby(["legislative_body", "start"]).agg(pages=("land_reform", "size"),
                                                      **{k: (k, "mean") for k in TERMS}).reset_index()
    g.to_csv(ROOT / "analysis/output/speech_land_salience.csv", index=False)
    print(g.round(4).to_string())


if __name__ == "__main__":
    main()
