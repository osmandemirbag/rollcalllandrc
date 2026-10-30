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
