"""Download the GNACT page-level corpus of the Turkish parliamentary minutes and extract 1943-1980.

Source: Hugging Face dataset boun-tabilab/turkish_parliamentary_data (20 parquet files, about 2.5 GB).
Output: data/gnact_raw/pages-000NN-of-00020.parquet (downloaded) and data/gnact/pages_1943_1980.parquet,
        the TBMM terms 7-11 (1943-60) and all Millet Meclisi (MM) and Senate (CS) pages (1961-80).
The corpus is used to locate named votes (01_index_votes.py) and to segment debates
(5_analysis_1945_60); every list and quotation used in the article is read from the official PDFs.
"""
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
URL = "https://huggingface.co/datasets/boun-tabilab/turkish_parliamentary_data/resolve/main/pages/{}"
RAW, OUT = ROOT / "data/gnact_raw", ROOT / "data/gnact"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(20):
        name = f"pages-{i:05d}-of-00020.parquet"
        if not (RAW / name).exists():
            subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(RAW / name), URL.format(name)], check=True)
    parts = []
    for f in sorted(RAW.glob("*.parquet")):
        t = pq.read_table(f, columns=["document_id", "legislative_body", "term", "year", "session", "volume", "page_num", "text"])
        lb, term = t["legislative_body"], t["term"]
        keep = pc.or_(pc.and_(pc.equal(lb, "TBMM"), pc.and_(pc.greater_equal(term, 7), pc.less_equal(term, 11))),
                      pc.is_in(lb, value_set=pa.array(["MM", "CS"])))
        parts.append(t.filter(keep))
    t = pa.concat_tables(parts)
    pq.write_table(t, OUT / "pages_1943_1980.parquet", compression="zstd")
    print(t.num_rows, "pages")


if __name__ == "__main__":
    main()
