# Etymology Tree Viz — Project Brief

_Handoff document. Written 2026-07-20, summarising the scoping conversation that led here._

## The idea

An interactive, **multilingual** etymology graph. A user types a word in their own language and can:

1. Trace it **upward** through its ancestors to reconstructed proto-forms (e.g. English _father_ → Proto-Germanic _\*fadēr_ → PIE _\*ph₂tḗr_).
2. See **sideways** which words in other languages share those ancestors (cognates: Latin _pater_, Sanskrit _pitṛ́_, Greek _patḗr_).
3. See **downward** what descended from a given form.

Explicitly not English-only. The point is that any language is a valid entry point.

## Why now

The data is public, static, and small. The heavy lifting is graph plumbing, disambiguation, and generating readable explanations per hop — token-heavy, compute-light. That profile suits an agentic build.

## Prior art (all stalled)

| Project | What it is | Status |
|---|---|---|
| [Etytree](https://esterpantaleo.github.io/etytree-demo/) (Pantaleo, 2017, Wikimedia IEG grant) | Closest to this idea. Ancestors / descendants / cognates, d3.js frontend, SPARQL over Virtuoso. [Paper](https://wikiworkshop.org/2017/papers/p1635-pantaleo.pdf) | Public demo has only "a few words searchable". Main wmflabs tool dormant since ~2017. |
| [Etymap](https://github.com/zifeo/Etymap) (EPFL student project) | Interactive viz built directly on etymwn | Abandoned |
| [etymological-dictionary](https://github.com/nikita-moor/etymological-dictionary) | Offline etymological dictionary from Wiktionary | Data only, no visualisation |

**Conclusion:** the idea is good, nobody finished it, and the underlying data has improved substantially since 2017 (wiktextract, Wikidata lexemes). This is a real gap, not a crowded space.

## Data sources

### Primary backbone

- **Etymological Wordnet** (Gerard de Melo, 2013). ~6M etymology edges across 2,500+ languages, mined from English Wiktionary.
  - Landing pages: [etym.org](http://etym.org/), [Berkeley](https://www1.icsi.berkeley.edu/~demelo/etymwn/)
  - Download: [archive.org/details/etymwn-20130208](https://archive.org/details/etymwn-20130208) — `etymwn-20130208.zip`, 26.5MB, CC-BY-SA 3.0
  - Format: TSV, 3 columns. Col 1 and 3 are `iso639-3:word`, col 2 is the relation.
  - Relations include: `rel:etymology`, `rel:etymological_origin_of`, `rel:derived`, `rel:has_derived_form`, `rel:variant`, `rel:etymologically_related`
  - Reconstructed proto-forms (PIE, Proto-Germanic, etc.) are first-class nodes.
  - **Caveat: it is a 2013 snapshot.** Wiktionary has moved on considerably.

### Enrichment

- **[kaikki.org](https://kaikki.org)** / **wiktextract** (Tatu Ylönen) — machine-readable JSON of all Wiktionary: glosses, IPA, POS, and etymology sections. Current, far richer than etymwn. Etymology sections are **prose**, so extracting structured edges from them is an LLM parsing job. This is where the token budget goes, and it's how we'd supersede the 2013 snapshot.
- **Wikidata lexemes** — structured, growing, currently sparse.

### Cross-linguistic / comparative (for filling gaps)

- **Glottolog** — genealogical classification of ~8,500 languoids
- **Lexibank** — 100+ standardised wordlists, cognate-coded, CLDF format
- **ASJP** — 40-item wordlists for ~10,000 languages, uniform transcription
- **Grambank** — 195 grammatical features, 2,400+ languages
- **WALS**, **PHOIBLE** — typological features, phoneme inventories
- **IE-CoR** — Indo-European cognate database behind recent Bayesian phylogeny work
- **StarLing / Tower of Babel** — Starostin's etymological databases (messier, deeper)
- **Index Diachronica** — crowd-sourced compendium of attested sound changes

## Key technical insight

**Cognates come free from the graph.** Two words are cognate iff they share a common ancestor node. That's a lowest-common-ancestor traversal, not a computation. No modelling required.

## Known problem: CJK coverage

etymwn is deep for Indo-European and thin for Korean, Chinese, Japanese, plus Bantu and Austronesian. Expect the KR/CN/JP experience to be poor out of the box.

Discussed but not decided: **build our own KR/CN/JP etymology net.** This is a genuinely different problem from IE etymology:

- Sino-Korean and Sino-Japanese vocabulary is largely *borrowing* from Middle Chinese, not shared descent. The graph edges are loan edges, and the interesting structure is the shared Chinese character (hanja/kanji/hanzi) plus the Middle Chinese reading it was borrowed from.
- Native Korean and Japanese strata are separate and contested (the Altaic/Transeurasian debate is unresolved — do not assume a Koreanic-Japonic common ancestor).
- Useful sources to investigate: Wiktionary CJK entries, Baxter-Sagart Old Chinese reconstruction, Unihan database, Middle Chinese rime tables.

## Immediate next step (was in progress when this doc was written)

**Data recon before any architecture decisions.** Download etymwn, inspect it, and measure:

1. What the actual edge types and their frequencies are
2. Total node / edge counts
3. Coverage per language, specifically `kor`, `cmn`, `jpn`, vs `eng`, `lat`, `fra`
4. Whether proto-forms are consistently linked or patchy
5. Whether one word (`father`, `water`, a Korean word) traverses end-to-end sensibly

This measurement decides the architecture. Do not pick a stack before seeing the numbers.

## Open architecture questions (deliberately unanswered)

- **Static vs server.** 6M edges is fine server-side, too heavy for a fully client-side page. Options: precompute subgraphs per word into static JSON; or a small API over SQLite/DuckDB; or a graph DB.
- **Frontend.** Cytoscape.js or d3 force layout. Ancestors upward, cognate siblings fanned out. Needs to handle any script in the input box.
- **Where does the LLM sit?** Offline batch (pre-generate explanations for every edge, bake into the data) vs at request time. Offline is cheaper per user and the obvious fit for the token-heavy brief.
- **Superseding the 2013 snapshot.** Do we ship on etymwn first and swap in wiktextract-derived edges later, or parse wiktextract from the start?

## Working preferences

- British English spelling throughout.
- No em dashes.
