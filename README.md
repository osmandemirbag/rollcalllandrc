# TBMM land and agricultural roll calls, 1961–1980, merged with the Turkish Political Elites Dataset

This repo has every recorded (open, by-name) vote on land and agricultural matters in the
Millet Meclisi (MM) and the Cumhuriyet Senatosu (CS), October 1961 to September 1980. For each
vote it records **each member's vote**, read from the printed name lists in the official TBMM
minutes. Deputies are linked to the Turkish Political Elites Dataset.

## Outputs (`data/processed/`)

| file | content |
|---|---|
| `TBMM_land_agri_rollcalls_1961-1980.xlsx` | **Main workbook.** Sheets: codebook, votes (with quality flags), member_votes, matrix_assembly, matrix_senate, unmatched. |
| `rollcall_long.csv.gz` | 177k rows, one per member × vote. Holds the vote, choice, person, the name as printed with its PDF page, match method, row status and elite covariates. |
| `rollcall_wide_elites.csv` | All elites rows for the 1961–1977 Assembly cohorts, with **all 318 original columns**, plus one `v_<vote_id>` column per Assembly roll call (313 votes). |
| `rollcall_wide_senate.csv` | One row per senator (`senate_person_id`, linked to `elite_row` when the senator also served as a deputy), with one column per Senate roll call (241 votes). |
| `votes_quality.csv` | One row per roll call: metadata, printed counts, listed counts, `quality` and `names_off_vs_tally`. |

The matrix codes follow Voteview:
- `1` yes
- `6` no
- `7` abstain
- `9` not voting
- `0` not a member at the time
- blank: a member at the time but on no printed list

## Coverage and accuracy

| | votes | lists match the printed tally exactly | within 2 names | off by more than 10 |
|---|---|---|---|---|
| land (hand-checked set) | 73 | 57 | 69 | 0 |
| agriculture | 169 | 114 | 134 | 10 |
| rural/peripheral (forestry, DSİ, village affairs, cooperatives law) | 312 | 203 | 260 | 26 |
| **all** | **554** | **374** | **463** | 36 |

Linking:
- 99.5% of Assembly names are linked to an elites row.
- 99.8% of Senate names are linked to a senator id.

`quality` / `names_off_vs_tally` in the votes sheet say how far each vote's lists are from the
printed tallies. Filter on them for analysis that needs exact votes. Some of the remaining gaps
come from the printed tally blocks themselves, which are sometimes wrong in the original minutes
(see `data/interim/verified_votes.csv`).

## How the lists were read (`scripts/`)

1. `01_build_vote_index.py`: builds the vote index, made of the 73 land votes plus agricultural
   votes selected by topic rules from the 6,446 open votes.
2. `02_fetch_pdfs.py`: downloads the 340 TBMM minutes PDFs.
3. `03_parse_namelists.py` (with `layout.py`): reads the multi-column lists from the PDF word
   positions:
   - finds section headers, including garbled or missing ones
   - splits province headers
   - joins hyphenated names
   - reads the PDF's own tally block and checks every list against it, using the identities
     votes cast = yes + no + abstain and members − vacancies = all lists
4. `04_match_elites.py`: matches names to people.
   - Deputies are matched to the elites roster of the term; senators to a roster built from the lists.
   - OCR-garbled names are rescued among the members sitting at the time.
   - Then each vote is reconciled: OCR fragments are dropped, and missing members are added
     by elimination when that is unambiguous.
5. `05_build_dataset.py`: writes the final tables. When an Assembly vote failed for lack of
   quorum, the minutes often omit the not-voting list. In that case, not voting is derived from
   the sitting members (`row_status` = `derived ...`).

Hand corrections go in `data/interim/namelists_manual/<vote_id>.csv`. Votes checked against the
page images are recorded in `data/interim/verified_votes.csv`.

```bash
cd scripts
python3 01_build_vote_index.py
python3 02_fetch_pdfs.py
python3 03_parse_namelists.py
python3 04_match_elites.py
python3 05_build_dataset.py
```

Requirements:
- Python packages: pandas, openpyxl, numpy, rapidfuzz
- poppler-utils (`pdftotext`)
- network access to `www5.tbmm.gov.tr`

## Caveats
- The names come from the OCR text layer of the TBMM PDFs. `list_name` keeps the printed
  (OCR) spelling, and `person_name` is the matched canonical name.
- Some match methods deserve a look:
  - `surname+province (low confidence)`
  - `rescued (garbled name of a sitting member)`
  - `added (by elimination)`
- `elite_party` is the career string from the elites data (for example `CHP/BAĞIMSIZ/GP`).
  `elite_party_at_election` is its first element. Party at the vote date is not in the sources.
- The elites dataset covers deputies only. Senators have `senate_person_id`, and `elite_row`
  only when they also served as deputies.

## Sources
- TBMM Tutanak Dergisi (PDF links in the votes sheet).
- GNACT OCR corpus (Boğaziçi TABILab, CC BY-NC-SA 4.0), used for vote detection.
- The Turkish Political Elites Dataset.
