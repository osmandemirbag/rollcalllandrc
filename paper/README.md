# The Cabinet and the Countryside — manuscript

Build (TeX Live or Overleaf):

    pdflatex main && bibtex main && pdflatex main && pdflatex main

- `main.tex` — article (Tables 1–4, Figures 1–4); the online supplement is `appendix.tex` (Tables A1–A4, Figures A1–A4), input at the end.
- `references.bib` — bibliography (natbib, apalike).
- `figures/` — PDFs (and PNG previews) from `make_figures.py`.
- `tables/` — table bodies from `make_tables.py`.

Regenerate figures and tables from the analysis outputs:

    python3 paper/make_figures.py && python3 paper/make_tables.py

All numbers come from `analysis/output/` (see `analysis/10_synthesis_1945_80.py` and earlier scripts).
