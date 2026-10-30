# The land and agriculture roll-call collection: quality, exploration and what is causally interpretable

Scripts: `analysis/04_quality_and_designs.py`. Tables: `analysis/output/q*.csv` (quality),
`x*.csv` (exploration), `d*.csv` (designs).

## 1. What we have

| | Assembly (MM) | Senate (CS) | total |
|---|---|---|---|
| roll calls | 322 | 245 | **567** |
| member-votes | 138k | 44k | **182k** |
| people | 2,269 deputy-terms in the elites data | 493 senators (roster built from the lists) | |

The collection is dominated by routine budget business:

| stage | roll calls |
|---|---|
| budgets and appropriation changes | 281 |
| final accounts | 114 |
| final passage of laws | 102 |
| article-by-article votes | 64 (mostly Senate Tapulama, Village Law) |
| motions | 6 |

Substantive agrarian policy is a small share of it:
- land reform law and motions: 3
- land reform agency budgets: 17
- land tax: 12
- titling, settlement and forest land: 50
- farm subsidies and benefits: 43

Coverage over time is uneven. The Senate's busiest year is 1963, with 61 roll calls, mostly the
Tapulama and Village Law articles. The Assembly peaks in 1971 with 41. After 1977 there are
only 3–5 per year in each chamber, because budgets were increasingly passed in omnibus votes.

**Not in the data:**
- Decisions taken by show of hands. That covers most laws, and all support prices and
  administrative subsidies.
- About 4% of open votes that the source index missed (estimated by the index's authors).

## 2. Quality, measured

### 2.1 Do the lists reproduce the printed tallies?

| | exact | within 2 names | median names off |
|---|---|---|---|
| Senate 1961–65 | 88% | 95% | 0 |
| Senate 1965–80 | 67–73% | 85–93% | 0 |
| Assembly 1961–65 | 74% | 86% | 0 |
| Assembly 1965–73 | 60–70% | 76–79% | 0 |
| Assembly 1973–80 | 66–75% | 80–83% | 0 |
| **all land votes (73)** | **100%** | 100% | 0 |
| **all votes (567)** | **72%** | **85%** | 0 |

- Errors are concentrated in a minority of votes: 37 votes are off by more than 10 names, and
  they carry most of the error. The `quality` / `names_off_vs_tally` flags identify them.
- For 9 votes the printed tally block itself is wrong, which I verified on the page images.
  Lists that add up exactly to the seats minus vacancies still miss the printed tally by 1–5.
  An "exact" share of 100% is therefore not attainable against the printed tallies.

### 2.2 Are names linked to the right person?

| how the name was linked | share of Assembly rows | share of Senate rows |
|---|---|---|
| name and province both match | 87.3% | 94.0% |
| name matches, OCR put it under another province | 2.5% | 4.1% |
| low-confidence, rescued or split lines | 1.6% | 0.6% |
| derived or inferred (no printed line) | 8.6% | 0.0% |
| new or garbled senator | — | 1.4% |
| unmatched | 0.2% | 0.2% |

**Hand audit of 75 sampled links**, drawn from every method and judged against the printed
names:
- 73 are correct.
- Both errors come from the low-confidence methods. One wrongly links "Nihat Erim" to Ömer
  Ergün. The other is a junk Senate id built from a vote-title fragment, which has now been
  removed.
- So the error rate is concentrated in the roughly 2% of rows linked by weak methods. No person
  appears twice in any vote.

### 2.3 Other known limits

- **Party at the time of the vote:** 21% of Assembly member-votes belong to deputies who
  switched party during the term.
  - For the major splits, dated switch points are used: CHP → GP (May 1967), AP → DP
    (Dec 1970), CHP → CGP (Nov 1972), DP → AP (1975), AP → CHP (Jan 1978).
  - Other switches are placed at mid-term. Results get stronger when switchers are dropped.
- **Derived "not voting" rows (11,622, 6.4%):** for 56 Assembly votes that failed quorum, the
  not-voting list was not printed. These rows are inferred from who was sitting at the time.
  They cannot distinguish absence from leave or ministerial duty.
- **Senate parties are unknown.** The elites data covers deputies only.
- **Absence types.** The lists mark ministers (B.), members on leave (İ.), presiding officers
  and the prime minister beside the name. This is now a `status_note` column, with 5,253
  entries, 98% of them in not-voting lists. Of the Assembly's not-voting entries:
  - 78% are plain absences
  - 17% are derived
  - 6% are excused

  Recall is limited by OCR, so some excused members are counted as plain absences.

## 3. What an inductive look shows

**Votes have one main dimension: government versus opposition.** Scaling each Assembly term's
yes/no votes on contested roll calls (a principal-components version of NOMINATE):

| term | contested votes | variance on dim 1 | dim 2 | dim 1 correlation with time spent in government | dim 2 within party: rural / East-SE |
|---|---|---|---|---|---|
| 1961–65 | 34 | 0.37 | 0.09 | 0.79 | −0.07 / −0.10 |
| 1965–69 | 44 | 0.42 | 0.07 | 0.86 | +0.09 / +0.09 |
| 1969–73 | 42 | 0.40 | 0.09 | 0.80 | +0.07 / +0.04 |
| 1973–77 | 20 | 0.67 | 0.13 | 0.61 | −0.02 / −0.04 |
| 1977–80 | 10 | 0.76 | 0.13 | 0.75 | +0.06 / −0.01 |

- There is no second, agrarian or regional dimension inside parties.
- In 1973–77 the first dimension is AP and its allies against CHP rather than "government",
  because both blocs governed during that term.

**Absence is the main activity.**
- Typical turnout is 41–55%, and 30–60% of roll calls failed for lack of quorum in most years.
- Quorum failure peaks in 1969 (63%), 1971 (54%) and 1977 (59%), the years of parliamentary
  crisis.
- AP–CHP party-line votes rise towards the end: 75–100% in 1978–80, when only contested budgets
  were still put to open votes.

**Farm votes look different from the rest.**
- Benefits are near-unanimous but frequently fail quorum.
- Land votes and budgets are polarised and well attended.
- The rest of this report's analysis builds on this split.

## 4. What is causally interpretable

| claim | design | estimate | can it be read causally? |
|---|---|---|---|
| **Government status causes deputies to support agency budgets** | same deputy, before and after a change of cabinet (deputy and vote fixed effects; 603 deputies change status on land reform budgets, 1,139 on all agency budgets) | +0.96 on land reform budgets; +0.56 on all agency budgets; turnout +0.13 to +0.15 | **Yes, under parallel trends.** Identified by cabinet changes within a term (1962–65 coalitions, 1971 technocratic cabinets, 1974–75, 1977–79). Main threat: the cabinet change could coincide with a change in the budget's content. That is small for the same agency's yearly budget, but cannot be ruled out. |
| **Support follows the party's stance toward the cabinet, not its partner's ideology** | MSP's change of partner: with CHP in 1974, with AP in 1975–77 | MSP yes 45–0 with CHP and 33–0 and 37–0 with AP. Of the same 31 deputies, 29 voted yes both times. Yes also when supporting a cabinet from outside (Irmak 1975, Demirel 1980); no against Ecevit in 1978–79. | **Yes, as a within-unit comparison.** It rules out "MSP likes or dislikes land reform" and "MSP follows its left or right partner". |
| **Party membership does not create land-tax preferences; preferences sort deputies into parties** | AP deputies before and after the Dec 1970 split, by which party they ended up in | Future DP members: 9% yes and 31% no on the 1970 land tax while still in AP; stayers 55% yes and 1% no | **Evidence of selection.** The dissent predates the switch. This is useful as a warning: party effects estimated cross-sectionally partly reflect sorting. |
| **Governments ration farm benefits by withholding quorum** | within roll call, government vs opposition deputies with party fixed effects, on benefit votes that failed quorum | −0.104 turnout (p < 0.001); −0.089 excluding ministers, members on leave and presiding officers | **Moderately.** It compares deputies on the same vote. But being in government is bundled with other duties, and party-by-period shocks cannot be fully separated with only 18 such votes. |
| Government status changes votes on land tax | — | not identifiable | **No.** No deputy's status changes between the land tax votes. |
| Left–right ideology drives land reform | cross-section, 2 Assembly votes | 1965 CHP 142–2 vs AP 2–127 | **Descriptive only.** Ideology, government role and the specific bill cannot be separated with 2 votes. |
| Rural constituencies or eastern landlords shape votes | cross-section within party | about zero | **Not causal.** Province traits are fixed and confounded. The precise zeros are informative descriptively: there is no visible constituency dissent on recorded votes. |
| Military senators favour reform | Senate member types | 0.86 vs 0.69 yes on agency budgets | **Descriptive.** Junta and quota senators were selected, not assigned, and are few. |
| Benefits pass before elections | timing | debt and disaster relief passed in Jan 1977, before the June 1977 election | **Anecdotal.** Too few events for inference. |
| Votes change agricultural outcomes | — | — | **Not possible with this data.** Most decisive choices were not recorded votes, and no outcome data is attached. |

**Main threats to every design:**
1. **Selection of what is recorded.** Open votes are compulsory for budgets and final accounts
   and taken on request otherwise, so the observed policy votes are the contested or
   symbolically important ones.
2. **Party measurement** for the 21% switcher share. Effects grow when switchers are dropped.
3. **OCR error** in the votes marked `count mismatch`. The land votes are all exact.
4. **Absence is ambiguous.** Use `status_note` to separate excused absence, and treat derived
   rows separately.

## 5. How to strengthen the collection

1. **Hand-verify the 37 votes that are off by more than 10 names**, using the page images and
   the patch mechanism. They hold most of the remaining count error.
2. **Date every party switch.** Resignations and new memberships are announced in the minutes
   (GNACT text), so party at the time of each vote could be exact.
3. **Add landholding or occupation detail** from deputies' biographies (TBMM albums). This is
   what a real test of the landed-elite theory needs.
4. **Bring in speeches** (GNACT) on the same bills, to measure preferences that recorded votes
   suppress through party discipline.
5. **Extend the period** to 1946–60 (DP era) and 1983–2002. Many more cabinet changes would
   give the within-deputy designs much more power, and land and agriculture laws continued to
   be voted.
