#!/usr/bin/env bash
# Replication of "The Cabinet and the Countryside".
#   bash run_all.sh            stages 4 (except 06-07), 6, 7: every table and figure from the included data (no downloads)
#   bash run_all.sh --full     stages 1-7: rebuild everything from the original sources (downloads about 10 GB)
set -euo pipefail
cd "$(dirname "$0")"
run() { echo "== $1"; python3 "$1"; }

if [[ "${1:-}" == "--full" ]]; then
  # 1. Named votes 1961-80: index, PDFs, name lists, links to deputies, datasets
  run code/1_rollcalls_1961_80/01_build_vote_index.py
  run code/1_rollcalls_1961_80/02_fetch_pdfs.py
  run code/1_rollcalls_1961_80/03_parse_namelists.py
  run code/1_rollcalls_1961_80/04_match_elites.py
  run code/1_rollcalls_1961_80/05_build_dataset.py
  # 2. Named votes 1943-60: speech corpus, vote index, farm votes and their PDFs, name lists
  run code/2_rollcalls_1943_60/00_fetch_speech_corpus.py
  run code/2_rollcalls_1943_60/01_index_votes.py
  run code/2_rollcalls_1943_60/02_select_and_fetch_farm_votes.py
  python3 code/2_rollcalls_1943_60/03_parse_lists.py            # 1945 lists (April 1945 - January 1946)
  python3 code/2_rollcalls_1943_60/03_parse_lists.py farm       # 1946-60 agrarian lists
  # 3. Deputies' occupations from the TBMM Albümü
  run code/3_deputies/00_fetch_albums.py
  run code/3_deputies/01_parse_album.py
  run code/3_deputies/02_match_elites.py
fi

# 4. Coding and designs, National Assembly 1961-80
run code/4_analysis_1961_80/01_code_votes.py
run code/4_analysis_1961_80/02_tests.py
run code/4_analysis_1961_80/04_quality_and_designs.py
run code/4_analysis_1961_80/05_more_designs.py
if [[ "${1:-}" == "--full" ]]; then
  # 06 writes output/paper.json and 07 adds to it (07 reads quotation pages from the PDFs);
  # the quick run keeps the included paper.json.
  run code/4_analysis_1961_80/06_rigorous.py
  run code/4_analysis_1961_80/07_flank_and_split.py
fi
run code/4_analysis_1961_80/08_harvest_shocks.py

# 5. 1945 and 1946-60 (needs the PDFs and the speech corpus)
if [[ "${1:-}" == "--full" ]]; then
  run code/5_analysis_1945_60/01_test_1945.py
  run code/5_analysis_1945_60/02_land_debate_1945.py
  run code/5_analysis_1945_60/03_speech_salience.py
  run code/5_analysis_1945_60/04_analyse_1946_60.py
fi

# 6. Synthesis 1945-80
run code/6_synthesis/01_farmer_votes.py
run code/6_synthesis/02_synthesis_1945_80.py
run code/6_synthesis/03_variance_and_composition.py
run code/6_synthesis/04_repertoire.py

# 7. Manuscript exhibits
run code/7_manuscript/01_make_figures.py
run code/7_manuscript/02_make_tables.py
echo "Done. Compile paper/: pdflatex main && bibtex main && pdflatex main && pdflatex main"
