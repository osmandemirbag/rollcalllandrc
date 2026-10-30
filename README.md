# TBMM land and agricultural roll calls, 1961–1980, merged with the Turkish Political Elites Dataset

This repo has every recorded (open, by-name) vote on land and agricultural matters in the
Millet Meclisi (MM) and the Cumhuriyet Senatosu (CS), October 1961 to September 1980. It also
links each voter to the Turkish Political Elites Dataset.

## Outputs (`data/processed/`)

| file | content |
|---|---|
| `votes.csv` | **554 roll calls** (313 MM, 241 CS): the 73 hand-checked land votes plus 481 agricultural votes found by topic rules. Includes date, category, `topic_group`, printed tallies, `outcome_class`, and the PDF link and page. |
| `rollcall_long.csv` | One row per member × vote. Holds the vote choice, the name as printed, the matched elites row (`elite_row` = row index of the elites CSV), `match_score` / `match_method`, and key elite covariates. |
| `rollcall_wide_elites.csv` | All elites rows for the 1961–1977 Assembly cohorts, with **all original columns**, plus one `v_<vote_id>` column per Assembly roll call. |
| `TBMM_land_agri_rollcalls_1961-1980.xlsx` | The same tables in one workbook, with a codebook, the list checks and unmatched names. |

The wide codes follow Voteview:
- `1` yes
- `6` no
- `7` abstain
- `9` not voting
- `0` not a member in that term
- blank: a member in that term but not on the printed lists

### Topic groups
- **land**: the 73 hand-checked votes covering land reform law and motions, the Toprak ve Tarım
  Reformu Müsteşarlığı budgets, land and property tax, Tapulama, İskân and the AOÇ sale.
- **agriculture**: Ziraat Bankası and Tarım Kredi Kooperatifleri (including small-farmer debt
  relief), crops and commodity boards (tobacco, tea, poppy), livestock, Devlet Üretme Çiftlikleri
  and seed/fertiliser, the Ministry of Agriculture, and farmers (disaster relief, agricultural
  income tax, ILO minimum wage in agriculture).
- **rural/peripheral**: forestry, DSİ water and irrigation, village affairs and the general
  Cooperatives Law. Drop this group for a narrow agricultural set.

`outcome_class` = `no quorum / majority not reached` marks repeated votes on the same bill
that failed for lack of quorum. These are common, for example the 1976–77 Küçük Çiftçilerin
Borçları bill.

## Status

| step | status |
|---|---|
| Vote index (land + agriculture) | done, 554 votes |
| Per-member lists | **1 of 554 done**: 11 Feb 1965 land-reform committee motion (438 names, 437 matched to elites) |
| Remaining 553 lists | need the TBMM PDFs: `www5.tbmm.gov.tr` was not reachable from the build environment |

The scripts for the remaining lists are written, but they have not yet been run on real PDFs.

## Rebuild / finish the collection

```bash
cd scripts
python3 01_build_vote_index.py   # votes.csv
python3 02_fetch_pdfs.py         # downloads TBMM PDFs to data/pdfs (needs www5.tbmm.gov.tr)
python3 03_parse_namelists.py    # name lists -> data/interim/namelists, counts vs printed tallies
python3 04_match_elites.py       # fuzzy match to the elites dataset
python3 05_build_dataset.py      # final long / wide / xlsx
```

`03_parse_namelists.py` checks every parsed list against the printed tallies and writes the
results to `data/interim/namelist_checks.csv`. A list that fails the check can be corrected by
hand in `data/interim/namelists/<vote_id>.csv`. Set `source` to anything other than
`pdftotext parser` and later runs will not overwrite the file. If a PDF has no text layer, it
needs OCR (`tesseract -l tur`).

## Caveats
- Vote titles, tallies and dates come from OCR. When the printed year was garbled, it was
  rebuilt from the session id (`date_source`).
- The agricultural votes were selected from OCR titles. The keyword hits that the rules rejected
  are in `data/interim/agri_candidates_rejected.csv` for review.
- `elite_party` is the career string from the elites data (for example `CHP/BAĞIMSIZ/GP`).
  `elite_party_at_election` is its first element. Party at the vote date is not in either source.
- The elites dataset covers deputies only. Senators are linked only when they also served as
  deputies.

## Sources
- TBMM Tutanak Dergisi.
- GNACT OCR corpus (Boğaziçi TABILab, CC BY-NC-SA 4.0).
- The Turkish Political Elites Dataset.
