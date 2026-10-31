"""Download volumes 1 (1920-50) and 2 (1950-80) of the TBMM Albümü 1920-2010 (TBMM, 2010).

Source: the Grand National Assembly's open archive, acikerisim.tbmm.gov.tr, handle 11543/2343
(item 030acf9a-7173-4b67-9c92-7c9547ebfd1f). About 500 MB. Output: data/albums/c1.pdf, c2.pdf.
"""
import subprocess
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
API = "https://acikerisim.tbmm.gov.tr/server/api/core/bitstreams/{}/content"
FILES = {"c1.pdf": "2244a204-a3fd-429c-b5e7-d7c93d131de7", "c2.pdf": "2285f4b7-10e7-4de7-9667-b95e4ef7ed99"}


def main():
    out = ROOT / "data/albums"
    out.mkdir(parents=True, exist_ok=True)
    for name, uuid in FILES.items():
        if not (out / name).exists():
            subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(out / name), API.format(uuid)], check=True)
        print(name, (out / name).stat().st_size)


if __name__ == "__main__":
    main()
