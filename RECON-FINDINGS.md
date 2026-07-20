# Data Recon — etymwn-20130208

_Run 2026-07-20. Answers the five questions in PROJECT-BRIEF.md. Scripts in `recon/`._

## Headline

**etymwn cannot serve as the backbone for the product as briefed.** Two of the three
core features fail on this data. The 2013-snapshot caveat in the brief understates the
problem: the issue is not staleness, it is that the ancestry layer is largely absent.

## 1. Edge types and frequencies

| Relation | Count |
|---|---|
| `rel:has_derived_form` | 2,264,744 |
| `rel:is_derived_from` | 2,264,744 |
| `rel:etymologically_related` | 538,558 |
| `rel:etymological_origin_of` | 473,433 |
| `rel:etymology` | 473,433 |
| `rel:variant:orthography` | 16,516 |
| `rel:derived` | 2 |
| `rel:etymologically` | 1 |

Relations are stored as **mirrored pairs** (`has_derived_form`/`is_derived_from`,
`etymology`/`etymological_origin_of` have identical counts). Unique edges ≈ 3M, not 6M.

**75% of all edges are intra-language derivational morphology**, not ancestry
(`father` → `fatherless`, `water` → `rainwater`).

## 2. Totals

- 6,031,431 edge rows / ~3M unique
- 2,888,541 nodes
- 397 languages (not the 2,500+ the brief cites)

## 3. Coverage per language

| Lang | Nodes | Edges touching |
|---|---|---|
| lat | 641,234 | 1,331,147 |
| eng | 445,157 | 1,019,293 |
| fra | 272,019 | 564,952 |
| spa | 241,008 | 487,559 |
| deu | 86,673 | 183,401 |
| jpn | 13,126 | 26,454 |
| grc | 7,541 | 20,432 |
| cmn | 4,949 | 7,746 |
| **kor** | **2,857** | **6,195** |
| san | 1,440 | 5,330 |

Also notable: Italian (454k) and **Esperanto (108k)** outrank German. The corpus is
skewed by whatever Wiktionary had good derivational coverage for in 2013.

## 4. Proto-forms — effectively absent

This is the decisive finding. The brief states proto-forms are "first-class nodes".
They are not.

- Total `p_`-prefixed node mentions in the entire 313MB file: **282**
  (`p_sla` 248, `p_gem` 24, `p_ine` 6, `p_gmw` 4)
- Nodes whose form begins with `*`: **14 mentions, 5 distinct**, and they are junk
  (`*`, `*hospiticidal`)

There is no PIE layer. There is no usable Proto-Germanic layer.

Format gotcha found while checking this: nodes are `lang: word` with **a space after
the colon**. Naive `split(":")` leaves a leading space on every word and silently
matches nothing.

## 5. End-to-end traversal — fails

Following `rel:etymology` upward:

| Word | Chain | Depth |
|---|---|---|
| eng: father | → enm: fader → ang: fæder | 2, stops |
| eng: water | → enm: water → ang: wæter | 2, stops |
| eng: mother | → enm: moder → ang: modor | 2, stops |
| deu: Vater | → gmh: vater → goh: fater | 2, stops |
| fra: père | → lat: pater, fro: pedre | 1, stops |
| **lat: pater** | **(none)** | **0** |
| kor: 물 / 사람 / 학교 | (none) | 0 |
| jpn: 水, cmn: 水 | (none) | 0 |

The brief's own headline example — _father_ → `*fadēr` → `*ph₂tḗr` — does not exist
in this data. Chains terminate at the oldest attested form, 1-2 hops up.

Of the 473,433 `rel:etymology` edges, only **99,956 are cross-language**. The
remaining 373,477 are same-language derivation mislabelled as etymology.

## Consequence: cognates do NOT come free

The brief's "key technical insight" is that cognates are a shared-ancestor traversal
requiring no modelling. That is true in principle and **false on this data**:
_father_ terminates at `ang: fæder` and `lat: pater` has no parents at all, so the two
never meet. No shared node, no LCA, no cognate. The insight is sound; the graph needed
to exercise it is missing its top layer.

CJK is not "thin", it is **zero** for every word tested.

## Recommendation

Reclassify the sources. wiktextract/kaikki is **not enrichment, it is the backbone**;
etymwn is at best a seed for derivational morphology within well-covered European
languages.

This also relocates the LLM. The brief scoped it for generating readable per-hop
explanations. The prior question is that the hops themselves must be **extracted** from
Wiktionary etymology prose, because the structured layer that would have supplied them
does not exist. That is the load-bearing LLM job, and it should be settled before any
stack choice.

---

# Resolution — kaikki measured (same day)

The open question above is answered, and the answer is better than the recommendation
anticipated.

## Etymology prose does not need parsing

The brief assumed etymology sections are prose and that extracting edges from them is
an LLM job. That is true of the `etymology_text` field and **irrelevant**, because
wiktextract separately extracts Wiktionary's **Descendants** sections into nested,
typed JSON:

```json
{"lang": "Proto-Germanic", "lang_code": "gem-pro", "word": "*fadēr",
 "descendants": [{"lang": "Old English", "lang_code": "ang", "word": "fæder"}]}
```

Coverage of the proto layer that etymwn lacked entirely:

| Extract | Entries | Carrying `descendants` |
|---|---|---|
| Proto-Indo-European | 1,905 | 96% |
| Proto-Germanic | 5,717 | 97% |

The upstream Reconstruction namespace holds **50,650 pages across 283 proto-languages**.

**The LLM moves back to writing explanations.** Ancestry is assembly, not inference.

## Trees are local and must be joined

No single entry holds a full chain. PIE `*ph₂tḗr` lists Proto-Germanic `*fadēr` and
stops; `*fadēr`'s own 523-node subtree lives in the Proto-Germanic extract. The graph
is built by joining extracts on `(lang_code, word)`.

Two join gotchas, both hit in practice:

- The `word` field strips the leading asterisk whilst descendant references keep it.
  Normalise with `lstrip("*")` or nothing matches.
- Stored forms carry diacritics users will not type: `ru:вода́` has a stress mark,
  Latin has macrons, Greek has breathings. **Search needs accent-folding.**

## Assembled graph, from 12 proto extracts

| | |
|---|---|
| nodes | 369,778 |
| edges | 502,619 |
| languages | 833 |
| multi-parent nodes | 70,772 |
| borrowing-flagged edges | 32,444 |

**It is a DAG, not a tree.** 70,772 nodes have more than one parent. Any layout that
assumes a tree will be structurally wrong.

## The cognate trap, and the fix

Following ancestry one hop too far destroys the result:

| Root | Descendants | Contains |
|---|---|---|
| `*ph₂tḗr` | 156 | *pater*, *athair*, *पितृ*, *Vater* — clean |
| `*peh₂-` | 439 | the above **plus** *panis* (bread), *pāscō* (to feed), *Futter* (fodder) |

357 of 368 "cognates" for *father* came from `*peh₂-`. Search *father*, get *bread*.

A descendant-count ratio test does **not** detect this, because counts always grow when
you climb a generation. The working signal is orthographic: Wiktionary writes bare roots
with a trailing hyphen (`*peh₂-`, `*ḱewh₁-`, `*ḱerd-`) and derived words without
(`*ph₂tḗr`, `*nókʷts`, `*kʷékʷlos`). A root is a morpheme, not a word.

**Rule adopted:** climb the full chain for display, but fan cognates only from the
topmost ancestor that is still a word. Verified across 18 queries.

## Sources ruled out

Checked and rejected for ancestry: **IE-CoR** (25,918 forms, *zero* proto-languages,
undirected cognate classes only), **Lexibank** (mostly undirected; richest reconstruction
datasets are NC/ND-licensed), **Wikidata lexemes** (63 PIE lexemes), **Unihan**
(readings, not ancestry), **STEDT** (no licence, no bulk download), **EtymDB 2.1**
(unmaintained, unnormalised node strings), **droher/etymology-db** (Apache-2.0 claim
looks unsound on Wiktionary-derived data).

CJK is separately solvable: tshet-uinh-data (Middle Chinese, CC0) → KANJIDIC2 →
Baxter-Sagart, as a directed Sinoxenic spine. See [LICENCE-DATA.md](LICENCE-DATA.md).

## Status

Working prototype at `web/index.html`, 18 words across 8 languages. Full 23GB dump
extracted to widen coverage beyond the 12 proto extracts used so far.
