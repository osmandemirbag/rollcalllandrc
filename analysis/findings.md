# What the land and agriculture roll calls show: findings ranked by credibility

Every finding below rests on a comparison that holds most things fixed:
- the same deputies before and after something changes, or
- different deputies on the same vote.

Each finding states its design and its main threat.

**Sample.** Assembly roll calls, 1961–80. Excused absences are excluded: ministers, members on
leave and presiding officers, from the `status_note` column. Derived not-voting rows are also
excluded.

**Scripts:** `analysis/04_quality_and_designs.py` and `05_more_designs.py`.
**Tables:** `analysis/output/d*.csv` and `e*.csv`.

Credibility scale:
- **A**: within-unit design, large effect, robust.
- **B**: within-unit or same-vote design, with a plausible confounder.
- **C**: suggestive.

---

## A. Strong

### 1. Being in government, not ideology, decides how a deputy votes on agricultural budgets (A)

**Design:** the same deputy before and after a change of cabinet, with deputy and vote fixed
effects.

| Outcome | Effect of being in government | Deputies whose status changed |
|---|---|---|
| Yes on land-reform agency budgets | **+0.96** | 603 |
| Yes on all agency budgets | +0.56 | 1,139 |
| Turnout on agency budgets | +0.13 | 1,256 |

**Main threat:** a change in a budget's content at the same moment as the cabinet change. That
is unlikely for the same agency's annual budget.

### 2. Leaving the governing party turns a loyal deputy into an opponent overnight (A)

**Design:** the 21 AP deputies who left in December 1970 to found the Democratic Party (DP),
compared before and after with the 205 who stayed (deputy and vote fixed effects, contested
agency budgets).

| | Before December 1970 | After |
|---|---|---|
| AP deputies who left for DP | 100% yes | **13% yes** |
| AP deputies who stayed | 99.6% yes | 95.7% yes |

**Effect: −0.79** (standard error 0.07).

**What it adds:** the same people, voting on the same kind of budget, reverse their vote as soon
as they change party. Budget votes reflect party role, not personal views on the budget.

### 3. On land taxes, personal preferences show *before* the party switch (A)

**Design:** the same AP deputies' votes on the June 1970 Emlâk Vergisi (property tax), six
months *before* the split.

| Group | Yes | No |
|---|---|---|
| Future DP founders (n = 35) | 9% | 31% |
| AP deputies who stayed (n = 206) | 55% | 1% |

**Finding 2 and finding 3 together:**
- The future DP founders voted with AP on every budget until the day they left.
- But they had already broken with AP on taxing land.
- So taxing landed property was something deputies would defy their own government over.
  Budgets were not.
- This is the clearest individual-level trace of landed interest in the data. It also shows
  that party splits sorted deputies by their views on land; the views came first.

### 4. A party's stance toward the cabinet decides its vote, not its coalition partner's ideology (A)

**Design:** the MSP governed first with the centre-left CHP (1974), then with the right-wing AP
(1975–77).

| Year | Cabinet | MSP's relation to cabinet | MSP vote on land-reform agency budget |
|---|---|---|---|
| 1974 | Ecevit I (with CHP) | in cabinet | 45 yes – 0 no |
| 1975 | Irmak (technocratic) | supporting from outside | 31 – 0 |
| 1976–77 | Nationalist Front (with AP) | in cabinet | 33 – 0, 37 – 0, 29 – 0 |
| 1978–79 | Ecevit III | opposing | 0 – 11, 0 – 4 |
| 1980 | Demirel VI | supporting from outside | 15 – 0 |

Of the same 31 MSP deputies, 29 voted yes in 1974 alongside CHP and again in 1976 alongside AP.

**What it rules out:** that MSP had a fixed position on land reform, or that it followed its
partner's ideology.

### 5. The 1971 military memorandum suspended party conflict for a year, but not on land taxes (A−)

**Design:** within one parliament (1969–73), so the same deputies are compared before and after
the military's ultimatum of 12 March 1971, adjusting for policy type.

| Period | Votes | Average gap between AP and CHP yes-shares |
|---|---|---|
| Demirel (Oct 1969 – Mar 1971) | 45 | 0.42 |
| **Erim I–II (Mar 1971 – Apr 1972)** | 31 | **0.03** (−0.40 adjusted, p < 0.001) |
| After Ecevit takes over CHP (May 1972 – Oct 1973) | 14 | 0.29 |

**Did conflict vanish because CHP held cabinet posts?** No. It was lowest under Erim II, when
CHP was *outside* the cabinet (0.03).

**What happened to each policy type:**

| Policy | Gap before | Gap under Erim | Gap after May 1972 |
|---|---|---|---|
| Land tax | 0.88 | 0.11 | **0.65** |
| Agency budgets | 0.48 | 0.03 | 0.27 |
| Agricultural institutions and regulation | 0.71 | 0.00 | — |

Land taxation was the first issue on which conflict came back, in June 1972. CHP voted 12% and
44% yes, against AP's 89–98%.

In 1973 CHP opposed the land reform law by staying away: 2 of its 105 deputies voted. Because
of that, the gap among votes cast looks close to zero.

**Main threat:** the end of the consensus coincides with Ecevit's takeover of CHP (May 1972) and
the approach of the 1973 election. The start of the consensus is the memorandum itself.

---

## B. Credible but with caveats

### 6. Governments block farm benefits by staying away, not by voting against them (B)

**Design:** deputies on the same vote, government versus opposition, with party fixed effects,
on the 18 benefit votes that failed quorum.

- Government deputies' turnout: **−0.10** (p < 0.001).
- Excluding ministers and members on leave: −0.09.
- The 1976–77 small-farmer debt relief bill failed quorum 12 times before passing in January
  1977, five months before the June 1977 election.
- On benefits, almost no one votes no: 4% of votes cast.

**Main threat:** being in government brings other duties, and there are only 18 such votes.

### 7. Breaking with the party on recorded votes signals that a deputy will leave it (B, predictive)

**Design:** dissent in a deputy's first year in office, compared with whether they switch party
later.

| Group | Later switched party |
|---|---|
| Never defected in first year (1,264 deputies) | 13% |
| **Defected at least once (161 deputies)** | **49%** |

The difference adjusted for term and party is +0.17 (p = 0.001).

**How to read it:** this is a prediction, not a causal effect. It shows that recorded dissent
measures real disagreement, and that Turkish parties of the period lost dissenters rather than
disciplining them.

---

## C. Suggestive

### 8. Concentrated crop benefits draw their own deputies to vote, but only weakly (C)

**Design:** deputies from producing provinces voting on their crop's law, compared with their
turnout on other votes and with other deputies (deputy and vote fixed effects).

| Crop law | Producing provinces | Extra turnout | t |
|---|---|---|---|
| Tea board (1971–72) | Rize, Trabzon, Artvin | +0.05 | 0.9 |
| Tobacco law (1969) | 5 largest producers | **+0.21** | 3.3 |
| Tobacco law (1969) | broader list of 18 provinces | +0.07 | 1.3 |

The result depends on how producing provinces are defined. I report both definitions because
I tested both. Read it as suggestive only.

### 9. Close races bring deputies to the chamber, not away from it (C)

**Design:** deputies from provinces where AP and CHP were close (below the median gap), in the
9 months before an election, compared on the same vote with deputies from safe provinces.

- Turnout **+0.02** (t = 2.1).
- The direction contradicts the idea that deputies skip votes to campaign.
- The effect is small, and the competitiveness measure (the AP–CHP vote gap in the province)
  is a rough proxy.

---

## Reliable nulls

- **No regional or rural voting bloc.**
  - Scaling each term's votes gives one dominant dimension, government versus opposition
    (37–76% of the variance).
  - Inside parties, the second dimension has no link to how rural the province is or to the
    East/Southeast (|r| ≤ 0.10).
  - Within-party effects of rural share, East/Southeast, an agriculture degree or local birth
    are all close to zero.
- **No eastern-landlord defection on land reform.** Eastern AP deputies voted like other AP
  deputies in both 1965 and 1973 (p = 1.0 and 0.28).

## What none of this can show

- Effects of these votes on farmers or farm incomes. Most decisive policies, such as support
  prices, credit ceilings and the 1972 pre-measures law, were never recorded votes.
- Anything requiring Senate parties, which are not in the data.
- The effect of government status on land-tax votes. No deputy's status changed between the
  land-tax votes.

---

## Extension to 1943–60 and to speeches (added October 2026)

### What was built

- **Vote index 1943–60.** `analysis/tbmm1943/01_index_votes.py` searches the GNACT page text
  (Hugging Face `boun-tabilab/turkish_parliamentary_data`) for result headers in both the old
  and the new vocabulary ("reylerin neticesi", "Müstenkif", "Reye iştirak etmiyenler", "Oya
  katılmayanlar"). It finds 1,872 open votes in TBMM terms 7–11.
  - Output: `data/interim/tbmm_1943_60_votes.csv`.
  - Each vote's GNACT page is the page of the official TBMM PDF.
- **Name lists, 1945.** `analysis/tbmm1943/02_parse_lists.py` reuses the 1960s parser with
  three changes for the old print style:
  - initial-style names ("A. MENDERES") are read as names, not as headers;
  - the old section words are recognised ("Kabul etmiyenler", "Müstenkif");
  - the restart-in-the-alphabet rule is switched off.
- **Parse quality, after repair.** Of 57 votes from April 1945 to January 1946, 54 are usable:
  no list holds more names than its printed tally. 85% of the parsed names match a deputy of the
  1943 roster on province plus fuzzy surname.
  - Repairs: OCR-garbled headers ("[0]](h ıvatılnrHjanjarl", "Oya katûm%yaıUar") are
    recognised; a list filed under a section whose tally is zero is moved to the section left
    short; a tally that GNACT misread (17 for 167) is taken from the PDF when GNACT's tallies do
    not add up to the house.
  - Excluded: three votes whose lists run into the next vote. On one usable vote
    (tbmm07019081) a page has no text layer, so about 170 "yes" names are missing.
  - The parse check is in `data/interim/tbmm_1945_namelists_check.csv`.

### 1945: did the future DP founders single out the land law? No.

**The record**
- **29 May 1945, seven-month budget (a confidence vote), 368–5.** The five "no" votes were
  A. Menderes, F. Köprülü, R. Koraltan, C. Bayar and E. Sazak (tbmm07017065, PDF p. 41).
- **11 June 1945, Çiftçiyi Topraklandırma Kanunu, 345–0.** Menderes, Köprülü, Koraltan,
  Bayar and Sazak are all in the not-voting list, with no leave mark (tbmm07018072, PDF pp. 22–24).

**The test**
- **Units:** the 1943 deputies who were not excused.
- **Votes:** the 33 votes that parsed cleanly.
- **Estimate:** each deputy's absence on the land law minus their own absence on the other
  votes, compared with the same difference for other deputies.
- **Inference:** randomization over which vote is treated as the land law.

**Result**
- **All 54 votes.** For the 14 deputies who later sat for the DP, the difference-in-differences
  (DiD) is +0.25. The land law ranks 2nd of 54 votes, p = 0.07 over votes.
- **The withdrawal.** The five dissenters were absent on 41% of the votes before the budget
  vote and on 91% of the 38 other votes after it.
- **Votes after 29 May only.** The land law is not distinctive: for the five, DiD +0.21
  (p = 0.18 over 39 votes); for all 14 later-DP deputies, +0.15 (p = 0.15).
- **The exception.** In December 1945 Menderes, Köprülü and Koraltan came back to vote "no" on
  the 1946 budget (tbmm07020020).

**Reading**
- **What it shows.** The founders' absence from the land law was part of a general withdrawal
  that began the day after their "no" on the budget. On that withdrawal they broke cover only to
  vote against budgets.
- **What it does not show.** The land-law absence is not evidence of landlord opposition to that
  law in particular. The common story in the literature, that the DP founders split with the
  CHP over the land law, is not supported by their votes, though it may still hold for their
  speeches (to be checked in the 1945 debate in the PDFs).
- **Government mobilization.** Other deputies were unusually present for the land law: 17%
  absent against 29% on the other votes after the budget.

### Speech salience, 1943–80

`analysis/output/speech_land_salience.csv` gives the share of minutes pages that mention land
reform or land distribution. Terms used: toprak reformu, tarım reformu, toprak dağıtımı,
topraklandırma.

| Period | Share of pages |
|---|---|
| Legislative year 1944–45 (TBMM) | **3.9%** |
| 1950–51 (TBMM) | **1.6%**, the DP amendments to the 1945 law |
| Other TBMM years | 0.1–0.7% |
| Millet Meclisi 1961–65 | 1.4% |
| Millet Meclisi 1965–69 | 2.3% |
| Millet Meclisi 1969–73 | **4.2%** |
| Millet Meclisi 1973–77 | 2.2% |
| Millet Meclisi 1977–80 | 1.5% |
| Senate 1972–73 and 1974–75 | 4.4% |

Land reform talk rises when a government puts it on the agenda (1945, 1950, 1971–74), not
steadily with rural pressure. This fits the cabinet-driven pattern in the votes.

**Caveat:** GNACT's OCR sometimes invents text, so these are counts of robust phrases. Every
quotation must come from the TBMM PDFs.

### The 1945 debate in the speeches

`analysis/tbmm1943/05_land_debate_1945.py` splits the GNACT text of the debate into speaker turns.
- **Sessions:** the general debate of 14–21 May (B. 54–58) and the articles, 4–11 June (B. 67–70, 72).
- **Size:** 445 turns from 94 speakers; 87% of turns are matched to the 1943 roster.

**Who spoke.** The 14 future-DP deputies, about 3% of the house, spoke 16% of all words.
Menderes, Düşünsel, Sazak, Ülkümen, Koraltan and Oral each spoke 5,000–7,400 words.

**What they said** (each quote checked on the TBMM PDF page):
- **Menderes, 15 May (tbmm07017055 p. 22):** the bill's farmstead idea (ocak) is copied "almost
  verbatim" from the National Socialist Erbhof law.
- **Menderes, 4 June (tbmm07018067 p. 41):** he protests that the majority's motion on Article
  17, the expropriation of land worked by sharecroppers down to small holdings, was
  "passed hand to hand" for signatures and is being adopted without debate. He also asks not to be counted against the
  land law.
- **Oral (Seyhan), 4 June (p. 32):** "the provisions of Article 17 recognize no limit in land."
- **Sazak, 4 June (p. 46):** "if I denied that my tie to land affects my speech, I would be
  lying."
- **Sazak, 5 June (tbmm07018068 p. 41):** "where are these serfs, these captives?"
- **Koraltan, 14 May (tbmm07017054 p. 30):** "the economic measures of late are bad … if the
  government continues on this path I cannot trust it."
- **Koraltan, 5 June (tbmm07018069 p. 7):** a unanimous final vote "will be a clear answer" to
  those who say there is opposition in the Assembly. He then did not vote.

**A rough lexicon index** (property and producer terms against redistribution terms; speakers
with at least 500 words, government and commission excluded):
- Future-DP speakers 0.64, others 0.45. Permutation p = 0.17.
- CHP loyalists such as Bayur and Tugay used the same property language.

**Reading.** The opposition to the core article was voiced openly, and partly by CHP members.
Nobody recorded a "no" vote (345–0). The dissenters said what they thought in debate and stayed
away from the vote.

### Occupations from the TBMM Albümü

The parliament's open archive (acikerisim.tbmm.gov.tr, hdl 11543/2343) holds the TBMM Albümü
1920–2010.
- **Parsing:** volumes 1–2 (1920–80) have a text layer. `analysis/occupation/01_parse_album.py`
  reads 7,355 biographies. Matched to the elites rows by year, province and name, 97–100%
  match in every term (`data/processed/elites_occupation.csv`).
- **Farmer flag:** the biography lists farming, a farm, land or livestock as an occupation
  (çiftçi, çiftçilik, ziraatçı, çiftlik sahibi, arazi sahibi, hayvancılık). Examples:
  Menderes "Çiftçilik", Sazak "Ziraatçı", Oral "Çiftçiler Birliği Reisi".
- **Share of farmers:** 9–11% before 1946, 14–18% in 1946–69, 13–15% in the 1970s.
- **Agricultural schooling** is a separate flag.
- **Senators are not covered.** The Senate albums are scans without a text layer, and no OCR
  engine is available here.

**Results** (`analysis/occupation/03_farmer_votes.py`):

| Sample | Outcome | Farmer effect |
|---|---|---|
| Millet Meclisi 1961–80, contested land-reform and land-tax votes (16 roll calls, 246 farmer deputies) | yes | **+0.002 (SE 0.009)**: farmers vote like their party colleagues on the same roll call |
| Same, contested agency budgets | yes | +0.010 (0.008) |
| Same, land votes | taking part | −0.030 (0.015) |
| Same, farm-benefit votes | taking part | −0.040 (0.019) |
| 1945 land law (41 farmer deputies) | excess absence | +0.005 (p = 0.93) |
| 1945 debate | share of words spoken | **23%**, against 9% of the house |

**Reading.** Landed deputies shaped the debate but not the vote. Once their party's line was
set, they voted like everyone else. Where they differed, they were slightly more likely to be
away. This is the same "voice, then exit" pattern as the DP founders, and it supports the
party-and-cabinet account over a sectoral, landed-interest account of roll-call behaviour.

### Agrarian roll calls 1946–60

**Data.** `analysis/tbmm1943/06_farm_votes_1946_60.py` selects 143 named votes of 1946–60 on:
- land distribution and titling;
- the grain board (TMO), sugar and tobacco;
- forests, state farms (DÜÇ), the State Hydraulic Works (DSİ) and irrigation;
- seed loans, livestock and village water;
- the agencies' budgets and accounts.

`02_parse_lists.py farm` reads the lists:
- 135 votes are usable, with 60,080 deputy-votes; 25 votes are contested.
- 89.5% of names are matched to the 1946, 1950, 1954 and 1957 cohorts on province and full name.
- Hand fixes: tally corrections in `data/interim/tbmm_1946_60_tally_fixes.csv`. Five votes are
  excluded because GNACT's page does not exist in the TBMM PDF.
- Analysis: `07_analyse_1946_60.py`, output in `analysis/output/h1950s_results.json`.

**1. The 1950 turnover: the same deputies flip with the cabinet.**
- **Design.** 68 deputies sat both before and after the May 1950 election and kept their party:
  27 DP members (opposition, then government) and 41 CHP members (government, then opposition).
- **Outcome.** Yes on contested agrarian votes (mostly agency budgets).

| Group | Before May 1950 | After May 1950 |
|---|---|---|
| DP deputies | 5% yes | 100% yes |
| CHP deputies | 99% yes | 40% yes |

- **Result.** DiD = +1.54, the two flips added together (Fisher randomization over party labels:
  p < 0.001, 0 of 5,000).
- **Meaning.** The same people, voting on the same kinds of farm agencies, switch sides when the
  cabinet changes hands. This is the 1961–80 result (DID_M +0.41) in a sharper form.

**2. The 1955 DP → Hürriyet exit: a second "AP→DP".**
- **Design.** 36 DP deputies of 1954 who left in October 1955 and founded the Hürriyet Partisi,
  compared with 429 who stayed.
- **Agency budgets.** Both groups voted 100% yes before the split. After it, the dissidents voted
  48% yes and the stayers 100%. DiD −0.52, p < 0.001.
- **All agrarian votes.** DiD −0.16, p < 0.001.
- **Meaning.** This replicates the 1970 AP→DP exit (−0.83) fifteen years earlier, with a
  different party. Leaving the government party, not the farm content of the bill, changes the vote.

**3. Party lines.** Share voting yes on contested agrarian votes:

| Period | CHP | DP |
|---|---|---|
| 1946–50 | 98% (government) | 8.5% (opposition) |
| 1950–60 | 8% (opposition) | 99% (government) |

Hürriyet Partisi members, 1956–57: 23%.

**4. Farmers.** Within party on the same roll call, farmer deputies differ by −0.002 (SE 0.007;
235 farmer deputies). A tight null, as in 1961–80.

**5. Recorded dissent on the land laws.**
- **22 March 1950, the CHP's amendment to the 1945 land law: 261–15–6.**
  - All 15 "no" votes come from the CHP benches, with Adnan Adıvar an independent. They include
    Şevket Raşit Hatipoğlu, the Agriculture Minister who carried the 1945 law (tbmm08025070,
    PDF p. 87), Falih Rıfkı Atay, Ekrem Oran and Mümtaz Ökmen.
  - 25 of the 31 DP deputies in the lists did not vote.
  - The reform's own authors voted against diluting it, two months before the CHP lost power.
  - **The debate of 10–13 March 1950** (tbmm08025062–63; quotes checked on the PDF):
    - **The government's spokesman.** The Agriculture Minister presenting the dilution was Cavit
      Oral (Seyhan), the leading critic of Article 17 in 1945 (pp. 37–39).
    - **İbrahim Arvas (CHP, Van):** the delegates at the CHP's own party congress "all at once
      attacked articles 15, 16, 17 and 43" (p. 20).
    - **Sabit Sağıroğlu (CHP, Erzincan, a farmer in the album)** says sharecropping arrangements
      ended "all from the fear of Article 17" (p. 37).
    - **Hatipoğlu** answers that the law is "the only legacy of honour I can leave my children"
      (p. 25).
  - **Reading.** The landed critics of 1945 rewrote the law from inside the governing party, with
    one of them as minister. This is the CHP's own landed wing, not the DP.
- **The 1950 Tapulama (titling) law** passed 241–0.
- **The 1955 TMO and land-law amendments** passed 289–1 and 275–0. Under the DP, agrarian
  legislation passed with near-unanimity.
- **31 August 1956, the Forest Law: 261–13.**
  - 7 of the 8 CHP deputies who voted said no, İnönü among them.
  - The DP voted 233–2 for it.
  - Forest villagers were a core DP clientele, and the opposition voted against.
- **December 1948, the amendment of the Sugar and Glucose Consumption Tax (tbmm08014022):**
  14 DP and 14 Millet Partisi deputies voted no, including Bayar and Koraltan.

**Reading.** Two eras, two governing parties, three natural experiments, all with the same
answer:
- **The turnover:** the same deputies flip when the cabinet changes hands.
- **Exits from the government party:** in 1955 (DP→HP), as in 1970 (AP→DP), they turn deputies
  against the cabinet's farm budgets.
- **An exit that stays in opposition:** in 1967 (CHP→GP) it changes nothing.

Landed occupation never predicts a vote within party. Agrarian roll calls in Turkey, 1945–80,
are confidence votes on the cabinet. Landed interests act through debate, through absence, and
through party exit, not through recorded votes against their party.
