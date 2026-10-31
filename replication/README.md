# Replication materials: *The Cabinet and the Countryside: How Landed Interests Acted in the Turkish Parliament, 1945–1980*

This folder contains the data, code, and manuscript sources needed to reproduce every table, figure, and number reported in the article and its online supplement.

## Quick start

```bash
pip install -r requirements.txt
bash run_all.sh
```

`run_all.sh` regenerates all tables (`paper/tables/`) and figures (`paper/figures/`) from the data included here. It runs stage 4 (except `06` and `07`), stage 6, and stage 7 (see below) and needs no downloads. Then compile the manuscript:

```bash
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

To rebuild everything from the original sources, run `bash run_all.sh --full`. This downloads about 10 GB:

- the parliamentary minutes (PDFs);
- the speech corpus;
- the parliamentary albums.

It also takes several hours.

## Folder structure

```
replication/
├── README.md             this file
├── run_all.sh            runs the pipeline in order
├── requirements.txt      Python packages and system tools
├── .replication_root     marker file; every script finds this folder through it
├── code/
│   ├── lib/              shared helpers (paths, Turkish text folding, PDF layout reader)
│   ├── 1_rollcalls_1961_80/
│   ├── 2_rollcalls_1943_60/
│   ├── 3_deputies/
│   ├── 4_analysis_1961_80/
│   ├── 5_analysis_1945_60/
│   ├── 6_synthesis/
│   └── 7_manuscript/
├── data/
│   ├── raw/              inputs from outside sources (see "Data sources")
│   ├── interim/          parsed name lists, vote indexes, hand corrections
│   └── processed/        analysis datasets
├── output/               results of stages 4–6 (CSV and JSON), read by stage 7
└── paper/                main.tex, appendix.tex, references.bib, figures/, tables/
```

Scripts write only inside this folder. Folders created by the full rebuild (`data/pdfs/`, `data/pdfs_tbmm/`, `data/gnact_raw/`, `data/gnact/`, `data/albums/`) are not included because of their size.

## Pipeline

Stages run in numerical order, and scripts within a stage run in numerical order. Each script's docstring states its inputs, outputs, and design choices.

### Stage 1: Named votes in the National Assembly and Senate, 1961–80 (`code/1_rollcalls_1961_80/`)

| Script | What it does | Main output |
|---|---|---|
| `01_build_vote_index.py` | Selects land and agricultural roll calls from the index of all recorded votes with topic rules | `data/processed/votes.csv` |
| `02_fetch_pdfs.py` | Downloads the minutes (*Tutanak Dergisi*) containing each vote from tbmm.gov.tr | `data/pdfs/` (not included) |
| `03_parse_namelists.py` | Reads the name lists from the PDF layout (columns, province and section headings) and reconciles them with the printed tallies; applies hand corrections | `data/interim/namelists/*.csv`, `data/interim/namelist_checks.csv` |
| `04_match_elites.py` | Links names to the Turkish Political Elites Dataset (deputies) and builds a Senate roster | `data/interim/matches.csv`, `senate_persons.csv` |
| `05_build_dataset.py` | Assembles the long and wide roll-call datasets | `data/processed/rollcall_long.csv.gz`, `rollcall_wide_*.csv`, `votes_quality.csv`, `TBMM_land_agri_rollcalls_1961-1980.xlsx` |

Hand corrections are kept in plain files and applied by `03_parse_namelists.py`:

- `data/interim/namelist_patches.csv`: names to add, drop, or link, each with a note;
- `data/interim/verified_votes.csv`: votes checked against the page images;
- `data/interim/namelists_manual/`: two lists transcribed by hand.

### Stage 2: Named votes in the Grand National Assembly, 1943–60 (`code/2_rollcalls_1943_60/`)

| Script | What it does | Main output |
|---|---|---|
| `00_fetch_speech_corpus.py` | Downloads the GNACT page corpus and extracts 1943–80 | `data/gnact/pages_1943_1980.parquet` (not included) |
| `01_index_votes.py` | Finds every printed vote result (1,872 votes in terms 7–11) | `data/interim/tbmm_1943_60_votes.csv` |
| `02_select_and_fetch_farm_votes.py` | Selects the 143 agrarian votes of 1946–60, assigns policy types, downloads their PDFs | `data/interim/tbmm_1946_60_farm_votes.csv`, `data/pdfs_tbmm/` |
| `03_parse_lists.py` | Reads the lists, adapting the stage 1 parser to the older print style. Run without arguments for 1945 and with `farm` for 1946–60. | `data/interim/tbmm_1945_namelists*.csv`, `tbmm_1946_60_farm_namelists*.csv` |

Differences from the stage 1 lists that the parser handles:

- the 1945 lists print initials and surnames ("A. MENDERES");
- the section headings use older words (*Kabul etmiyenler*, *Oya katılmıyanlar*, *Reye iştirak etmiyenler*, *Müstenkifler*);
- some headings are garbled in the scans.

Tallies misread in the speech corpus and checked by hand on the page images are listed in `data/interim/tbmm_1946_60_tally_fixes.csv`.

### Stage 3: Deputies' occupations (`code/3_deputies/`)

| Script | What it does | Main output |
|---|---|---|
| `00_fetch_albums.py` | Downloads volumes 1–2 of the *TBMM Albümü 1920–2010* | `data/albums/` (not included) |
| `01_parse_album.py` | Reads 7,355 biographies (1920–80) and codes occupations | `data/processed/album_deputies.csv` |
| `02_match_elites.py` | Links biographies to the elites dataset by term, province, and name (97–100% per term) | `data/processed/elites_occupation.csv` |

### Stage 4: Coding and designs, National Assembly 1961–80 (`code/4_analysis_1961_80/`)

| Script | What it does | Main output |
|---|---|---|
| `01_code_votes.py` | Codes policy type and stage, cabinets, and each deputy's party and cabinet status at the date of the vote | `output/votes_coded.csv`, `output/member_votes.csv.gz` |
| `02_tests.py` | Descriptive tables: party lines, flips, participation, constituency, benefits | `output/t*.csv` |
| `04_quality_and_designs.py` | Data-quality audits; quorum gatekeeping; within-deputy government effect | `output/q*.csv`, `x*.csv`, `d*.csv` |
| `05_more_designs.py` | AP→DP exit, MSP partner switch, memorandum (uses `04_quality_and_designs.py`) | `output/e*.csv` |
| `06_rigorous.py` | Two-dimensional item-response ideal points; DID_M; randomization inference for the AP→DP exit; memorandum placebo in time | `output/ideal_points.csv`, `output/paper.json` |
| `07_flank_and_split.py` | TİP pivotality, quorum rule check, CHP→GP exit, quotation pages. Requires the PDFs, so it runs only in the full rebuild. | adds to `output/paper.json` |

`06` writes `output/paper.json` from scratch and `07` adds to it. Because `07` needs the PDFs, the quick run skips both and uses the included `paper.json`.
| `08_harvest_shocks.py` | Provincial harvest shocks and votes on farm benefits | `output/h1_harvest_shocks.csv` |

### Stage 5: 1945 and 1946–60 (`code/5_analysis_1945_60/`)

These scripts need the PDFs and the speech corpus, so they run only in the full rebuild. Their outputs are included.

| Script | What it does | Main output |
|---|---|---|
| `01_test_1945.py` | Matches the 1945 lists to the 1943 roster; tests whether later-DP deputies were selectively absent from the land law | `output/h1945_deputy_votes.csv`, `output/h1945_land_law.json` |
| `02_land_debate_1945.py` | Speaker turns in the 1945 land debate; speakers' shares; lexicon index | `output/h1945_debate_turns.csv`, `output/h1945_debate_speakers.csv` |
| `03_speech_salience.py` | Shares of pages mentioning land reform, the landless, land occupations, and public land, 1943–80 | `output/speech_land_salience.csv` |
| `04_analyse_1946_60.py` | Matches the 1946–60 lists to deputies. Designs: the 1950 turnover, the 1955 DP→HP exit, farmers within party, recorded dissent on land laws. | `output/h1950s_member_votes.csv.gz`, `output/h1950s_results.json` |

### Stage 6: Synthesis, 1945–80 (`code/6_synthesis/`)

| Script | What it does | Main output |
|---|---|---|
| `01_farmer_votes.py` | Farmer effects within party and roll call, 1961–80; farmers in the 1945 vote and debate | `output/occupation_farmer_effects.csv`, `output/occupation_1945.json` |
| `02_synthesis_1945_80.py` | Harmonized deputy-by-vote panel for 1945–80. Era statistics, the four party exits, and attendance on key land votes. | `data/processed/rollcall_1945_1980_long.csv.gz`, `output/synthesis.json` |
| `03_variance_and_composition.py` | Variance in vote choices explained by party and by province beyond party (net of chance); deputies' characteristics by party. Takes about 20 minutes. | `output/variance_decomposition.csv`, `output/characteristics_by_party.csv` |
| `04_repertoire.py` | Selective absence index, recorded opposition, and pivotality on the key land votes | `output/repertoire.csv` |

### Stage 7: Manuscript exhibits (`code/7_manuscript/`)

| Script | Output |
|---|---|
| `01_make_figures.py` | `paper/figures/*.pdf` (and `.png` previews) |
| `02_make_tables.py` | `paper/tables/*.tex` |

## Where each exhibit comes from

| Exhibit | File | Produced by | From |
|---|---|---|---|
| Table 1 Hypotheses | written in `main.tex` | — | — |
| Table 2 Record by term | `tables/t2_terms.tex` | `7/02_make_tables.py` | `data/processed/rollcall_1945_1980_long.csv.gz` |
| Table 3 Land and constituency within party | `tables/t4_social.tex` | `7/02` | `output/occupation_*`, `output/h1950s_results.json` |
| Table 4 Cabinet alignment within deputies | `tables/t3_designs.tex` | `7/02` | `output/paper.json`, `output/h1950s_results.json`, `output/synthesis.json` |
| Figure 1 Positions, 1965–69 and 1969–73 | `figures/fig1_split_maps.pdf` | `7/01_make_figures.py` | `output/ideal_points.csv` |
| Figure 2 Government premium; party and province | `figures/fig2_eras.pdf` | `7/01` | `output/synthesis.json`, `output/variance_decomposition.csv` |
| Figure 3 Party exits | `figures/fig3_exits.pdf` | `7/01` | `output/paper.json`, `output/h1950s_member_votes.csv.gz`, `output/synthesis.json` |
| Figure 4 Repertoire of opposition | `figures/fig4_land_attendance.pdf` | `7/01` | `output/repertoire.csv` |
| Table A1 Roll calls by policy type | `tables/ta1_coding.tex` | `7/02` | long panel |
| Table A2 Coverage; party composition | written in `appendix.tex`; `tables/t3_characteristics.tex` | `7/02` | `output/characteristics_by_party.csv` |
| Table A3 1945 debate | `tables/ta3_debate.tex` (Panel A); quotations in `appendix.tex` | `7/02` | `output/h1945_debate_speakers.csv` |
| Table A4 Land reform moments, TİP, robustness | written in `appendix.tex` | — | `output/paper.json`, `output/synthesis.json`, `output/h1945_land_law.json` |
| Figure A1 1945 withdrawal | `figures/figA1_1945_withdrawal.pdf` | `7/01` | `output/h1945_deputy_votes.csv` |
| Figure A2 Memorandum | `figures/figA2_memorandum.pdf` | `7/01` | `output/paper.json` |
| Figure A3 Speech | `figures/figA3_speech.pdf` | `7/01` | `output/speech_land_salience.csv` |
| Figure A4 Positions, other terms | `figures/figA4_split_maps_other.pdf` | `7/01` | `output/ideal_points.csv` |

Numbers in the text that do not appear in a table come from the same output files:

- **`output/synthesis.json`:** era statistics, the four exits, and key land votes by party.
- **`output/h1950s_results.json`:** the 1950 turnover and recorded dissent on land laws.
- **`output/t9_benefits.csv` and `output/d2_quorum_gatekeeping.csv`:** governmental populism.
- **`output/paper.json`:** DID_M, the memorandum, TİP, and the MSP.
- **`output/speech_land_salience.csv`:** speech measures.

Vote-level citations in the text, such as "08025070, p. 87", identify the minutes file (`tbmm08025070.pdf`) and the page of the official PDF. Files are at `https://www5.tbmm.gov.tr/tutanaklar/TUTANAK/TBMM/d08/c025/tbmm08025070.pdf`, or `.../MM/` and `.../CS/` for 1961–80.

## Main datasets

**`data/processed/rollcall_1945_1980_long.csv.gz`**: one row per deputy and roll call in the Assembly, 1945–80 (216,315 rows, 511 roll calls, 2,979 deputies).

| Column | Meaning |
|---|---|
| `era_src` | source block: `1945`, `1946-60`, `1961-80` |
| `chamber` | `TBMM` (to 1960) or `MM` (National Assembly) |
| `vote_id` | minutes file and PDF page of the list, e.g. `tbmm07018072_p022` |
| `date`, `title`, `policy_type` | date of the sitting, title of the measure, coded policy type |
| `contested` | the losing side holds at least 5% of votes cast (from the printed tallies) |
| `id`, `year` | deputy identifier and election year in the Turkish Political Elites Dataset |
| `name`, `province` | name as printed and province |
| `party_at_vote`, `government` | party on the date of the vote, and whether it held cabinet posts |
| `farmer` | the *TBMM Albümü* biography lists farming, a farm, land, or livestock as an occupation |
| `status_note` | excused (on leave, minister, presiding officer); excluded from the analyses |
| `choice`, `yes`, `voted` | `yes` / `no` / `abstain` / `not_voting`; yes among votes cast; took part |

**`data/processed/rollcall_long.csv.gz`** and **`rollcall_wide_*.csv`**: the 1961–80 record for both chambers, including the Senate. Wide files use Voteview-style codes: 1 yes, 6 no, 7 abstain, 8 invalid ballot, 9 not voting, 0 not a member.

## Data sources

| Source | Use | Location |
|---|---|---|
| TBMM *Tutanak Dergisi* (official minutes), www5.tbmm.gov.tr | name lists, tallies, quotations | downloaded by stages 1–2 |
| Turkish Political Elites Dataset | deputies, parties, provinces, province characteristics | `data/raw/The_Turkish_Political_Elites_Dataset.csv` |
| Index of recorded votes 1961–80 and the 1965 committee vote | vote selection | `data/raw/TBMM_land_roll_calls_1961-1980.xlsx`, `data/raw/TBMM_1965_land_reform_committee_vote_by_deputy.xlsx` |
| GNACT corpus, Hugging Face `boun-tabilab/turkish_parliamentary_data` | locating 1943–60 votes; debates; speech measures | downloaded by `2/00` |
| *TBMM Albümü 1920–2010* (TBMM 2010), acikerisim.tbmm.gov.tr, hdl 11543/2343 | occupations | downloaded by `3/00` |
| Provincial agricultural panel (yields, inputs, climate) | harvest shocks | `data/raw/agri/*.rds`, `provinces_p2.geojson` |

Please cite the original sources when using these data.

## Notes and limitations

- **Text recognition:** the speech corpus occasionally invents text. It is used only to locate votes, to segment speakers, and for phrase counts. Every name list and quotation used in the article was read from the official page images.
- **Usable votes:** a 1945 or 1946–60 vote is used when no section of its list holds more names than its printed tally. Names lost to unreadable print leave a missing value, not a miscoded vote.
  - **1945:** 54 of 57 votes are used.
  - **1946–60:** 135 of 143 are used. Five are excluded because the corpus page does not exist in the official file, and three because a list overflows its tally.
- **Senate:** senators' parties are not observed, so the Senate (1961–80) is collected but left out of the comparisons.
- **Randomization:** randomization inference uses fixed seeds, so results reproduce exactly.
- **Runtime:** `4/06_rigorous.py` (ideal points, bootstrap; full rebuild only) and `6/03_variance_and_composition.py` take tens of minutes; everything else takes seconds to a few minutes.
- **Verification:** with the included data, `bash run_all.sh` reproduces the included `output/` files and `paper/tables/` byte for byte. This was checked for the synthesis, repertoire, occupation, and coding outputs and for all table files.
