# AI index website — information architecture and design specification

- **Status:** proposed, for review before build
- **Date:** 2026-11-13
- **Edition covered:** SIDE 2026, Absolute dataset only
- **Supersedes:** the IA section of `docs/ai-index-website-plan.md` (that document's
  story/chart list is out of scope here)
- **Numbers in this document** are computed from the repo's own engine and are
  pre-publication. Nothing here may be quoted externally before SIDE sign-off.

## Scope

| In | Out (deferred, do not design) |
| --- | --- |
| 71 country profiles, 5 pillars, 16 sub-pillars, 58 indicators | Scrollytelling narrative |
| Rankings table, sortable, rank/score emphasis | Animated bump / ladder chart |
| 2025→2026 rank change for countries in both editions | Radar small multiples |
| Methodology + downloads | Hero animation |
| One indicator across 71 countries (P2, cut first) | Absolute/Relative comparison of any kind |

**Fixed facts the design must not fight.** The 2026 edition covers 71 countries and
all 71 receive a CHIPS score. There is no Relative dataset for this site, so no
toggle, no blend, no "absolute vs relative" chart. Counts verified against
`core/chips_hierarchy.py` for 2026: CONNECT 13 indicators, HARNESS 16, INNOVATE 15,
PROTECT 8, SUSTAINABILITY 6.

---

## 1. Site map

Four required pages, one section that lives on the Rankings page, and one page that
is P2. Priority order is build order.

| # | Page | URL | The one job | Why it is at this position |
| --- | --- | --- | --- | --- |
| 1 | **Rankings** | `/` | Answer "where does a country sit?" in one screen, then hand off. | The only page every visitor needs, and the door to all 71 profiles. No landing page: a hero delays the answer by a scroll. |
| 2 | **Country profile** | `/country/{iso3}` | Explain one country's position and what is behind it. | The deep end, reached from page 1. It carries the 58-indicator burden so page 1 does not. |
| 3 | **How the index works** | `/methodology` | Make the score auditable: what is measured, how it is scaled, how gaps are handled, how to cite it. | Trust is the second need, and only after a number is in hand. Every "why?" link lands here at an anchor. |
| 3a | *Change since 2025* | `/` (section below the table) | Show movement without implying a time series. | It needs the same 71 rows and the same sort controls; a separate page would duplicate the table for one extra column. |
| 4 | *One indicator, all countries* | `/indicator/{slug}` | Answer "who leads on mobile download speed?" | P2. The one question a profile cannot answer, reusing the rankings table. Cut it first if the build slips. |

**Navigation.** Three text links: Rankings · How the index works · About. A single
search field sits in the header on every page. No hamburger at desktop widths; no
nested menus.

**Not pages.** Glossary (a popover, available anywhere), pillar explainers and
downloads (sections of `/methodology`, addressed by anchor).

---

## 2. Progressive disclosure model

The problem is 58 numbers. The rule: **a user never faces more than seven unfamiliar
numbers at once**, and the number of items per level is bounded by the framework,
not by the layout.

| Level | Unit | Items on screen | How you get there | What is shown |
| --- | --- | --- | --- | --- |
| L0 | Country | 71 rows × **4 columns** | default | Rank, country, CHIPS score + bar, (optional) change vs 2025 |
| L1 | Pillar | **5** | click a row | Score, rank, weight, sub-pillar count, coverage state |
| L2 | Sub-pillar | **3–5** | expand a pillar card | Score, rank, weight inside the pillar, state |
| L3 | Indicator | **2–7** | expand a sub-pillar row | Score 0–100, world rank, share of the sub-pillar, state |

Three clicks reach any of the 58: Rankings → profile → pillar → sub-pillar. Two
clicks from a profile. Nothing is more than two clicks from the table.

**Why the depth is worth it.** In the 2026 scoring, India is 3rd of 71 overall —
2nd on CONNECT, 3rd on HARNESS and INNOVATE, 12th on PROTECT, and **66th on
SUSTAINABILITY**. The headline number is not wrong, but on its own it hides the only
interesting thing about the country. A single-screen "profile" with a radar chart
would show the same flattening; disclosure down to sub-pillars shows *which* of the
five areas is dragging, and down to indicators shows that it is smart-grid patents
(0.2 of 100), climate-related venture investment (0.0) and renewable share (13.0) —
not e-waste (65.8), which the eye would guess first.

### Why a table at L0 and accordions below it

71 items is a scanning task, not a storytelling task; a chart of 71 bars is a table
with worse sorting. Below L0, accordions beat sub-pages: the reader keeps the
country's headline score in view while reading a sub-pillar, there are no thin
unlinkable pages for 16 sub-pillars, and the back button stops being the main
navigation.

Accordion state goes into the URL (`/country/ind?open=harness`), so an expanded view
is shareable and survives a reload — the test an editor will apply: "send me the
number you're citing."

### The grouping, and the one exception

Pillar → sub-pillar → indicator is the framework's own tree, so the site adds no
invented structure. 2026 counts:

| Pillar (weight) | Sub-pillars (indicator counts) | Indicators |
| --- | --- | --- |
| CONNECT (25%) | Affordability 4 · Quality 2 · Access 4 · AI 3 | 13 |
| HARNESS (25%) | Apps and platform 6 · Data Intensity 2 · Fintech 2 · Real Economy 2 · AI 4 | 16 |
| INNOVATE (25%) | Investments and Startups 3 · Other Emerging Technology 7 · AI 5 | 15 |
| PROTECT (12.5%) | Preparedness 2 · Risk of Attack 3 · AI 3 | 8 |
| SUSTAINABILITY (12.5%) | Sustainability 6 | 6 |

**Exception:** SUSTAINABILITY has a single sub-pillar whose name repeats the pillar's.
It would be a 100%-weight, one-item level that teaches the reader nothing, so the
profile **skips L2 for that pillar** and goes straight from pillar card to its six
indicators. State this in the component, not in a footnote: the accordion for
SUSTAINABILITY opens onto indicators.

### Interaction rules

| Need | Mechanism | Where it lives |
| --- | --- | --- |
| Find a country | Typeahead over names + ISO3; first result is "Open {country} →", second result set filters the table | Header field; mirrors above the table |
| Narrow 71 rows | The same field filters in place; count updates ("14 of 71 countries") | Toolbar |
| Reorder | Column-header buttons: rank, score, country, change | Table header row |
| Rank vs score | Segmented control changes emphasis, not order | Toolbar, right of search |
| See pillars in the table | "Show pillars" checkbox adds 5 columns | Toolbar |
| Compare to 2025 | "Change vs 2025" checkbox adds one column | Toolbar |

Because score and rank are monotone (invariant 4), sorting by score and sorting by
rank are the same order. The Rank/Score control therefore changes *which number is
large in the row* and whether the bar encodes position or score. Say so in a caption
— a reader who expects two different orderings and finds one will assume a bug.

---

## 3. Plain-language guidance

Written for a reader who has never heard of CHIPS. These are final drafts, not
placeholders. Every one of them is reachable from the place it explains (popover,
"what this means" disclosure, or the methodology anchor) rather than only on a
methodology page nobody opens.

**What the score is** (above the table, first visit; behind the "What this means"
disclosure thereafter):

> Scores run from 0 to 100. Each indicator is put on that scale by comparing the 71
> countries: 0 is the lowest value anyone recorded on it this edition, 100 the
> highest. The index score is a weighted average of those, so in 2026 the scores
> actually run from 15.3 to 67.3. A 40 means the country sits below the top of the
> range the world covers — not at 40% of an ideal.

*(If the team publishes z-scores instead of min–max, this paragraph must be
replaced; see §9. It is the only piece of copy that hard-depends on the scaling
method.)*

**What the composite is:**

> CHIPS combines 58 indicators into five areas — CONNECT, HARNESS, INNOVATE,
> PROTECT and SUSTAINABILITY — and combines those five into one number. It is a
> summary, not a verdict: two countries can land on the same score for opposite
> reasons.

**What "rank 3 of 71" means:**

> Third means two countries scored higher this year. A rank is a position, not a
> grade: the gap between 3rd and 4th can be a hundredth of a point or ten. Read the
> score next to the rank, or the rank will flatter small differences.

**What a dropped sub-pillar means:**

> Some countries do not report every indicator. When more than half of a
> sub-pillar's indicators are missing, we do not guess at the gap: that sub-pillar is
> marked **not scored**, and its share of the index is spread across the parts that
> do have data. The score still reflects what is known — it just rests on less.

**What coverage means:**

> Coverage is the share of the index's weight that stands on a reported value.
> 100% means all 58 indicators had a number. In the 2026 edition, 12 of 71 countries
> are at 100%.

**What the 2025 change means:**

> This compares 2026 with the 2025 edition for the countries scored in both. The
> list of countries is not identical between editions, so a rank can move because
> others moved, not only because this country did.

**What the site is not:**

> These scores describe national conditions, not government performance, and they do
> not measure policy quality. A high score can come from private investment, from
> geography, or from a single large market.

**Vocabulary, fixed once.** Pillar (not "dimension"), sub-pillar (not "category"),
indicator (not "metric"), not scored (not "missing", never "n/a"), coverage (not
"completeness"). The glossary popover carries these twelve terms and nothing else.

---

## 4. Missing-data presentation

Missing data in 2026 is rare but structured, and it is concentrated: 26 of the
1,136 country×sub-pillar cells are empty (14 dropped by the >50% rule, 12 with no
data at all), and 21 of those 26 are in an AI sub-pillar. The design must therefore
be honest without making the index look broken.

**Principles.** Never print 0 for a gap. Never leave a cell blank. Never use red.
Never rely on grey alone — grey plus a hatch plus a word.

| Surface | What appears | Why |
| --- | --- | --- |
| Pillar cell in the rankings table | `—` (em dash), 12% grey cell, 2px dotted bottom border; tooltip "PROTECT · AI is not scored for Costa Rica — more than half of its indicators are missing" | An em dash is the conventional "no value"; a blank reads as a rendering fault. |
| Indicator row in a profile | `Not scored` in words, with the reason on the next line in 13px muted text | Words survive printing, zoom and screen readers. |
| Sub-pillar row inside a pillar card | Row stays in place, score replaced by `Not scored`, weight shown as "0% (redistributed)" | The reader must see that the sub-pillar exists and that its weight went somewhere. |
| Pillar card | Small grey chip `1 of 4 not scored` on the card, not a banner | Local, proportional, unalarmed. |
| Country profile header | Always one plain line, no icon: "Coverage 72% — 40 of 58 indicators, 3 of 16 sub-pillars not scored" | Coverage is a fact about every profile, so it belongs in the header, not in a conditional alert. |
| Country profile banner | Only when coverage < 80% (9 of 71 countries): the same line, plus one sentence and **What this means**: "Three areas are scored on partial data, so this rank rests on less than most." | A banner on 27 of 71 pages would be furniture. Nine is an exception worth flagging. No red, no warning triangle: low coverage is a documented property of the data, not an error. |
| Composite score | Score is always shown. Below 80% coverage a muted chip `Partial data` sits beside it, never an asterisk | Suppressing a score hides more than it protects. A chip is a caveat, not a warning label. |
| Chart | Fill = `#E3E6E9` with 45° hatch `#9AA3AC`, label "not scored" inside the mark when it fits | Hatch is visible in greyscale, at low contrast, and to a color-blind reader. |
| Download | NaN, with the reason in a `status` column | Analysts need the reason, not the rendering. |

**Never show.** "No data available", "n/a", "N/A", "–" (en dash, ambiguous with a
range), a zero, a greyed-out unlabeled cell, an asterisk, or a warning triangle.

**The empty state that cannot ship in 2026:** no country fails the ≥3-pillar rule,
so there is no "no score" row. Build the `Not ranked` state anyway (a row with rank
`—` and a one-line explanation) because the 2025 series has 21 of them and the
component will be reused in 2027.

---

## 5. Wireframes

### 5.1 Rankings (`/`)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ SIDE · CHIPS        Rankings   How the index works   About                     │
│                                                          [ Search countries… ] │
├────────────────────────────────────────────────────────────────────────────────┤
│ CHIPS 2026                                              Edition 2026 · 71 c.   │
│ A digital-economy score for 71 countries, from 58 indicators in five areas.    │
│ How the score works ↗                                                          │
│                                                                                │
│ ┌─ toolbar ────────────────────────────────────────────────────────────────┐   │
│ │ [ Filter 71 countries…            ]      Rank (Score)   □ Show pillars    │  │
│ │                                          □ Change vs 2025                 │  │
│ └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│ ┌─ table ──────────────────────────────────────────────────────────────────┐   │
│ │ # ▲  Country ▲           CHIPS score (0–100) ▲        Change vs 2025 ▲   │   │
│ │ ─────────────────────────────────────────────────────────────────────────│   │
│ │ 1    United States      ████████████████████████░░░░  67.3   no change   │   │
│ │ 2    China              █████████████████████░░░░░░░  58.8   ▲ 4          │  │
│ │ 3    India              ██████████████░░░░░░░░░░░░░░  40.4   no change   │   │
│ │ 4    United Kingdom     ███████████░░░░░░░░░░░░░░░░░  31.6   ▼ 2          │  │
│ │ …                                                                        │   │
│ │ 71   Algeria            █████░░░░░░░░░░░░░░░░░░░░░░░  15.3   ▲ 2          │  │
│ └──────────────────────────────────────────────────────────────────────────┘   │
│ 71 of 71 countries · scores 0–100 · 2026 Absolute edition · Download CSV ↗     │
│                                                                                │
│ ── Change since 2025 ────────────────────────────────────────────────────────  │
│ Rank movement for the N countries scored in both editions. Two columns only.   │
│ (same table component, filtered to movers, sorted by |change|)                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

Notes. The score bar's track is 0–100 with a 1px tick at the edition median
(19.7 on min–max, so the reader can see "above/below the middle country" without a
second chart). `Change vs 2025` is off by default: it is a second question, and
showing it on arrival invites misreading a two-edition delta as a trend. The change
values in the wireframe above are schematic — the eligible country set is still open
(§9.2), and the column caption must carry the live N.

### 5.2 Country profile, collapsed (`/country/ind`)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ SIDE · CHIPS   Rankings   How the index works   About                          │
├────────────────────────────────────────────────────────────────────────────────┤
│ ← All 71 countries                                                             │
│                                                                                │
│ India                                                          [flag]          │
│ Rank 3 of 71 · CHIPS 40.41            Change vs 2025: no change (rank 3)       │
│ ████████████████████████░░░░░░░░░░░░░░░░░░░░░  0 ─────── 100                   │
│                            ▲ world median 19.7                                 │
│ Coverage: full — 58 of 58 indicators · 5 of 5 pillars     What this means ▾    │
│                                                                                │
│ THE FIVE AREAS                                    weight shown under each      │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐ │
│ │ CONNECT      │ │ HARNESS      │ │ INNOVATE     │ │ PROTECT      │ │SUSTAIN.│ │
│ │ 55.6         │ │ 43.6         │ │ 20.8         │ │ 51.2         │ │ 32.1   │ │
│ │ rank 2 / 25% │ │ rank 3 / 25% │ │ rank 3 / 25% │ │ rank 12/12.5%│ │ r66/12%│ │
│ │ 4 sub-pillars│ │ 5 sub-pillars│ │ 3 sub-pillars│ │ 3 sub-pillars│ │ 6 ind. │ │
│ │ Show  ▾      │ │ Show  ▾      │ │ Show  ▾      │ │ Show  ▾      │ │ Show ▾ │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └────────┘ │
│                                                                                │
│ Read across: India is top-five on everything digital and 66th on               │
│ sustainability. The five areas disagree, which is the reason this page         │
│ does not stop at the headline.                                                 │
│                                                                                │
│ Download India's 58 indicator scores (CSV) ↗                                   │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Country profile, drilled into (`/country/ind?open=harness.ai`)

```
│ THE FIVE AREAS                                                                 │
│ ┌──────────────┐ ┌──────────────────────────────────────────────────────────┐  │
│ │ CONNECT  55.6│ │ HARNESS                            43.6 · rank 3 · 25%    │ │
│ └──────────────┘ │ 5 sub-pillars · 5 of 5 at full coverage         Hide ▲    │ │
│                  │ ──────────────────────────────────────────────────────── │  │
│                  │ Sub-pillar                    score  rank    weight     │   │
│                  │ Apps and platform              42.8   3/71    20%   ▸    │  │
│                  │ Data Intensity                 33.6   3/70    20%   ▸    │  │
│                  │ Fintech                        25.5   3/67    20%   ▸    │  │
│                  │ Real Economy                   70.1   2/71    20%   ▸    │  │
│                  │ AI                             46.0   2/71    20%   ▾    │  │
│                  │   ┌────────────────────────────────────────────────────┐ │  │
│                  │   │ Indicator                 score  rank   share      │ │  │
│                  │   │ Open Data score            41.9  56/71  25%        │ │  │
│                  │   │ Open-source model score     0.7  21/64  25%        │ │  │
│                  │   │ AI skill penetration      100.0   1/30  25%        │ │  │
│                  │   │ AI talent pillar           41.4   2/64  25%        │ │  │
│                  │   └────────────────────────────────────────────────────┘ │  │
│                  │ (dropped example, in place:)                             │  │
│                  │ PROTECT · AI        Not scored    —    0% (redistributed)│  │
│                  │                     more than half of its indicators are │  │
│                  │                     missing                       Why? ▸ │  │
│                  └──────────────────────────────────────────────────────────┘  │
```

Notes. One pillar is expanded at a time by default — opening a second closes the
first, because the point is comparison-free reading and a wall of open rows
recreates the problem. The reader can override with a "keep open" preference if
testing shows they want two side by side; do not build that in v1.

### 5.4 How the index works (`/methodology`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ SIDE · CHIPS   Rankings   How the index works   About                           │
├───────────────────────────┬─────────────────────────────────────────────────────┤
│ On this page              │ How the index works                                 │
│                           │                                                     │
│ 1 What CHIPS is           │ CHIPS is a composite of 58 indicators...            │
│ 2 The five areas          │ (4 short paragraphs, 1 idea each, 60 words max)     │
│ 3 The 58 indicators       │                                                     │
│ 4 From values to 0–100    │ ┌─ The five areas ────────────────────────────┐     │
│ 5 Missing data            │ │ CONNECT      25%   13 indicators  ▸          │    │
│ 6 Comparing editions      │ │ HARNESS      25%   16 indicators  ▸          │    │
│ 7 Download & cite         │ │ INNOVATE     25%   15 indicators  ▸          │    │
│                           │ │ PROTECT    12.5%    8 indicators  ▸          │    │
│ (sticky rail, current     │ │ SUSTAIN.   12.5%    6 indicators  ▸          │    │
│  section highlighted)     │ └──────────────────────────────────────────────┘    │
│                           │                                                     │
│                           │ ┌─ Missing data: a worked example ────────────┐     │
│                           │ │ Costa Rica, 2026: HARNESS · AI reports 1 of  │    │
│                           │ │ 4 indicators. Below the half-way rule, so... │    │
│                           │ │        [ the 4 indicator rows, 1 scored,      │   │
│                           │ │          3 marked Not scored ]                │   │
│                           │ └──────────────────────────────────────────────┘    │
│                           │                                                     │
│                           │ Download: [Rankings CSV] [All 58 × 71 CSV]          │
│                           │ [Framework JSON]   Cite: [copy citation]            │
└───────────────────────────┴─────────────────────────────────────────────────────┘
```

Notes. The 58-indicator list is a single table of five groups with counts, collapsed
by default. It exists so a skeptic can check membership; it is not a reading flow.
The sticky rail is the only place on the site with a table of contents, because it
is the only long page.

---

## 6. Design tokens

Institutional and paper-based: off-white paper, near-black ink, one deep navy for
structure, one blue for links and focus. Pillar hues are Okabe–Ito derived and
darkened to clear 3:1 against paper, and are still never the only carrier (§7).

### Color

| Token | Hex | Use | Contrast against background |
| --- | --- | --- | --- |
| `--paper` | `#FBFAF7` | Page background | — |
| `--surface` | `#FFFFFF` | Cards, table body | 1.04:1 vs paper (border needed, not fill) |
| `--ink` | `#14181C` | Primary text | **17.09:1** on paper |
| `--ink-muted` | `#55606C` | Secondary text, captions, units | **6.14:1** on paper |
| `--brand` | `#1B3A6B` | Wordmark, headings, rules | **10.79:1** on paper |
| `--accent` | `#0B5FA5` | Links, focus ring, selected state | **6.30:1** on paper · 6.57:1 on white |
| `--border` | `#808A94` | Input borders, control boundaries | **3.36:1** on paper (meets 1.4.11) |
| `--border-subtle` | `#D7DBDF` | Table rules, dividers | 1.33:1 (decorative only) |
| `--missing-fill` | `#E3E6E9` + 45° hatch `#9AA3AC` | Not-scored cells and marks | Text on it: **5.12:1** |
| `--positive` | `#1F6B3A` | Rank up | **6.24:1** on paper |
| `--negative` | `#9B2226` | Rank down | **7.59:1** on paper |

### Pillars (fills, for marks and tints)

| Pillar | Fill | On paper | Tint (chips) | Text on tint |
| --- | --- | --- | --- | --- |
| CONNECT | `#0072B2` | 4.97:1 | `#E6F0F7` | `#005A8C` — 6.40:1 |
| HARNESS | `#00805D` | 4.74:1 | `#E4F0EC` | `#00664B` — 5.99:1 |
| INNOVATE | `#B36B00` | 4.01:1 | `#F7EEDF` | `#7A5200` — 6.01:1 |
| PROTECT | `#B4453F` | 5.21:1 | `#F6E9E8` | `#8A2F2A` — 7.04:1 |
| SUSTAINABILITY | `#6A4C93` | 6.56:1 | `#EDE9F3` | `#4A3268` — 9.01:1 |

**Honest limitation:** five hues cannot be reliably distinguished by all color-blind
readers — practical CVD-safe grouping tops out around three or four. The mitigation
is structural, not cosmetic: every pillar mark is labeled with its name or a 2-letter
code (`CO HA IN PR SU`), pillars always appear in the same order, and any
single-pillar chart uses `--ink`, not the pillar hue. Hue is decoration for
orientation; the label carries the information.

**Missing is not a pillar color.** It is grey + hatch + the words "not scored", so it
never competes with a hue and never disappears in a printout.

### Type

Newsreader (display, OFL) and Inter (UI/body, OFL). No third face, no web-font
subsets beyond Latin + Latin-1 punctuation.

| Token | Face | Size / line | Weight | Use |
| --- | --- | --- | --- | --- |
| `display-xl` | Newsreader | 56 / 60 | 400 | The one number on a profile (40.41) |
| `display-l` | Newsreader | 40 / 46 | 400 | Page title |
| `display-m` | Newsreader | 28 / 34 | 500 | Country name, section heads |
| `body-l` | Inter | 18 / 28 | 400 | Lede paragraph under a title |
| `body` | Inter | 16 / 26 | 400 | Default |
| `body-s` | Inter | 14 / 22 | 400 | Captions, units, table body |
| `label` | Inter | 13 / 16 | 600, +0.02em | Toolbar labels, table headers |
| `micro` | Inter | 12 / 16 | 500 | Chips, footnotes |

Rules. Tabular figures (`font-variant-numeric: tabular-nums`) in every table and
every column of numbers. Newsreader is never used inside a table or a numeric
column — it has no tabular figures, so digits will not align, and the misalignment
reads as sloppiness in exactly the place the site is claiming precision. Scores in
running text use Inter, not Newsreader.

### Space, layout, radius

- Base unit 4px; scale `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96`.
- Max content width 1120px; reading measure 68ch; table gutter 24px.
- Breakpoints: 320 / 640 / 960 / 1200. At 640 and below, the rankings table drops to
  three columns (rank, country, score); pillar columns are hidden, not squeezed.
- Radius 2px on cards and inputs, 0 on table rows. Shadows: none. Separation is by
  1px `--border-subtle` rules — shadows add visual noise to a 71-row table.
- Focus ring: `2px solid #0B5FA5` with `2px` paper offset; never removed, never
  replaced by a color change alone.

---

## 7. Accessibility requirements (WCAG 2.2 AA)

| Requirement | Implementation |
| --- | --- |
| 1.3.1 Structure | Real `<table>` with `<caption>`, `<th scope="col">`, sortable headers as `<button>` inside `<th>` carrying `aria-sort`. No `div` grids. |
| 1.4.1 Use of color | Direction of change uses ▲/▼ **and** the sign **and** a visually-hidden "up 4 places". Pillar identity always carries a code. Missing uses hatch + words. |
| 1.4.3 / 1.4.11 Contrast | All text pairs in §6 are ≥4.5:1 (≥3:1 for the 56px display figure); all control boundaries ≥3:1. Pillar fills ≥3:1 against paper. |
| 1.4.4 / 1.4.10 Reflow | Usable at 320px and at 200% zoom with no horizontal scroll; table collapses to three columns. |
| 1.4.12 Text spacing | Line-height 1.5, paragraph 2em, letter 0.12em, word 0.16em without clipping; check it on the toolbar labels, the tightest text on the site. |
| 2.1.1 Keyboard | Everything operable: search, sort, toggles, accordions, downloads. Accordion headers are `<button aria-expanded>`. |
| 2.4.3 Focus order | Header → page title → toolbar → search → table → change section → footer. Accordions come after their card, not before. |
| 2.4.7 Focus visible | The 2px ring above, on paper and on dark tints. |
| 2.4.11 Focus not obscured | Sticky header is 56px; add `scroll-margin-top: 72px` to every anchor target so a focused row is never hidden under it. |
| 2.5.8 Target size | All interactive targets ≥24×24px; table row links padded to 44px height. |
| 3.3.2 Labels | The filter field is labeled "Filter countries"; the header field "Search countries". They are different jobs and must not share a label. |
| 3.3.7 Redundant entry | Country selection persists when moving between profile and rankings. |
| 4.1.3 Status messages | Sorting and filtering announce via `aria-live="polite"`: "Sorted by score, highest first, 71 countries." |
| Reduced motion | All transitions 0ms under `prefers-reduced-motion`; score bars are drawn filled, never animated from zero; no count-up numbers anywhere. |
| Charts | Every chart has a "View as table" disclosure immediately below it, containing the same values. The SVG gets `aria-hidden="true"` and a text summary above it ("Scores range 15.3 to 67.3; median 19.7"). No chart is the only route to a number. |
| Language | `<html lang="en">`, American spelling, no all-caps beyond 2-letter codes. |

**Keyboard path through the rankings table**, as a test case: Tab from the filter
field → "Rank" header → "Country" → "Score" → "Change" → first row's country link →
next row's link … → last row → "Download CSV". 71 links is a long run, so the filter
is the documented shortcut ("type three letters, press Enter") and the header search
opens a profile directly. Add a skip link: "Skip to the change since 2025 section."

---

## 8. Component inventory

| Component | What it does | Data it consumes |
| --- | --- | --- |
| `CountrySearch` | Typeahead over 71 names + ISO3; first result navigates to a profile, the rest filter the table | Country list, names, ISO3, current path |
| `RankingsTable` | 71 sortable rows; rank/score emphasis; optional pillar and change columns; coverage chip per row | `scores[]`: iso3, name, overall, rank, pillars, coverage, change |
| `ScoreBar` | 0–100 fill with a median tick and printed value; optionally encodes rank position | score, rank, N, median |
| `ChangeCell` | `▲ 4` / `▼ 2` / `no change` / `not scored`, with visually-hidden wording | rank 2025, rank 2026 |
| `PillarCard` | Pillar score, rank, weight, sub-pillar count, not-scored count, expand control | one pillar node: score, rank, weight, children, status |
| `SubPillarAccordion` | Row with score, rank, weight share, state; expands to its indicators; skipped when a pillar has one sub-pillar | sub-pillar node + its leaves |
| `IndicatorRow` | Indicator name, score 0–100, world rank, share of sub-pillar, state, link to indicator page | leaf: name, score, rank, weight, status |
| `CoverageBanner` | One-line coverage summary + "What this means" disclosure; renders only below 90% | coverage, indicators present/total, sub-pillars not scored |
| `MissingValue` | The `—` / "Not scored" primitive: cell style, tooltip, `aria-label`, hatch variant for charts | status code + reason string |
| `GlossaryPopover` | Twelve fixed definitions, triggered by a dotted-underline term | static glossary JSON |
| `MethodNote` | Footnotes strip under every table and chart: edition, method, N, rounding | edition, method, N |
| `TableDownload` | CSV/JSON download with edition and method in the filename | current view's rows |

Twelve components, of which `RankingsTable`, `PillarCard`, `SubPillarAccordion` and
`MissingValue` carry the whole design. If only four get built carefully, those four
are the site.

---

## 9. Decisions the team must make before build

1. **Which scaling method the site publishes.** Every score on the page and one
   paragraph of §3 depend on it. Recommendation: publish full-range min–max, because
   it is explainable in a sentence and its 0–100 has a literal meaning; z-score is
   the analyst default but produces numbers (India 66.03) that require a statistics
   lesson to interpret. Ordering is identical either way (invariant 4), so no
   ranking claim changes — but the site cannot ship two sets of numbers, and it must
   match whatever SIDE publishes in the spreadsheet. **This is the blocking item.**
2. **The eligible set for the 2025 change column.** The brief says 52 countries are
   in both editions; the engine gives 57 name-matched and 38 with a CHIPS score in
   both (2025 has 59 names, 21 of them unscored). Pick one rule (recommendation:
   *scored in both*, currently 38) and render N live in the caption instead of
   hard-coding it.
3. **Country naming.** The dataset says "United States of America"; the site should
   not. Recommendation: display "United States", keep the full name in the profile
   subtitle and the download, ISO3 everywhere in URLs.
4. **Pre-publication labeling.** This is a prototype of data that is not yet signed
   off. The site needs an explicit, visible status line and sign-off owner before
   the first demo, or a screenshot will end up on a slide as a published figure.

---

## 10. Amendment — scale toggle (2026-11-13)

Decided after review, superseding §9.1.

**The prototype publishes both scaling methods with a user toggle**, defaulting to
full-range min–max, with the choice in the URL (`?scale=z`) alongside the accordion
state. `meta.defaultMethod` drives the default; nothing is hard-coded.

**Correction to this specification.** §2 and §3 assumed the two methods differ only
in magnitude. They do not. Verified on the 2026 edition:

| Measure | Disagreement between methods |
|---|---|
| Overall ranks | **64 of 71 differ**, max 19 places (Saudi Arabia 55 → 36) |
| Pillar ranks | 312 of 355 differ, max 35 (SUSTAINABILITY) |
| Indicator ranks | 0 of 3714 differ |

Indicator order is preserved because each indicator is a monotone transform of one
column. The composite is a weighted **sum** of differently-shaped transforms, and
monotone transforms do not commute with sums, so the league table itself changes.
`AGENTS.md` invariant 4 previously claimed otherwise and has been corrected.

**Consequences for the design:**

1. Every "order does not change" claim is struck. The toggle changes scores **and**
   ranks.
2. When the non-default scale is active, each row carries a rank-movement indicator
   against the other scale (`▲ 19` / `▼ 12` / `—`), or an optional column. The
   movement is the most informative thing the toggle reveals; it must not require
   comparing two screenshots.
3. §3's "What the score is" needs the method-aware replacement below. The rest of
   the §3 copy stays verbatim.

> **Draft replacement for "What the score is":**
> Scores run from 0 to 100. Two ways of building that scale are shown here. The
> first compares each country with the lowest and highest value recorded this
> edition, so 0 is the bottom of the range and 100 the top. The second measures how
> far a country sits from the average, and compresses the extremes. Both use the
> same 58 indicators and the same weights — but the totals differ, and so does the
> ranking: Saudi Arabia sits 19 places apart between the two. The published index
> will use one method; the prototype shows both so the choice can be judged.

4. §7 accessibility applies unchanged: the toggle is a real radio group with a
   visible label, keyboard-operable, and the active method is announced in the same
   `aria-live` region as sorting and filtering.
5. Before any public launch, one method must be named official. Two league tables is
   a review affordance, not a publishing policy.

