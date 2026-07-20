# Data licensing

Decided 2026-07-20.

## The derived graph is CC BY-SA 3.0

The etymology graph in `data/graph/` is derived from Wiktionary via
[wiktextract / kaikki.org](https://kaikki.org). Wiktionary content is licensed
**CC BY-SA 3.0** (with GFDL dual-licensing on older revisions). Share-alike is
copyleft and propagates: any dataset we derive from it carries the same terms.

We are adopting that deliberately rather than working around it.

**What this obliges us to do:**

- Attribute Wiktionary and the wiktextract project wherever the data is published.
- Publish the derived dataset under CC BY-SA 3.0 (or a compatible later version).
- Not relicense the data under permissive or proprietary terms, ourselves included.

**What it does not restrict:** the application code. Site code, build scripts and
visualisation logic are a separate work and may carry any licence we choose.
Only the *data* is share-alike.

## Attribution text to ship

> Etymology data derived from [Wiktionary](https://www.wiktionary.org/) via
> [wiktextract](https://github.com/tatuylonen/wiktextract) by Tatu Ylönen,
> available at [kaikki.org](https://kaikki.org).
> Licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).

## Sources evaluated and rejected

- **droher/etymology-db** — 4.2M pre-built edges, declared Apache-2.0. Rejected:
  it is itself Wiktionary-derived, so the permissive relicensing appears unsound.
  Adopting it would mean inheriting somebody else's licence risk for no benefit,
  since it is a 2023 snapshot with no descendant-tree depth.
- **EtymDB 2.1** — CC BY-SA 4.0, but unmaintained since 2022 and nodes are
  unnormalised surface strings (16,546 PIE nodes collapse to 12,685 distinct).
- **Lexibank** — licence trap: the three richest reconstruction datasets are the
  most restricted (`peirosst` CC-BY-NC, `luangthongkumkaren` CC-BY-NC-**ND**,
  which forbids derivative visualisations outright, `zhangrgyalrong` unspecified).
- **STEDT** — no licence published anywhere, and no bulk download exists. Avoid.
- **CHISE/IDS** — no LICENSE file; GPLv2 only asserted downstream. Licence risk.

## Compatible additions

- **Wikidata lexemes** — CC0. Safe to layer as stable identifiers.
- **tshet-uinh-data** (Middle Chinese) — CC0. Safe for the planned CJK spine.
- **KANJIDIC2** (EDRDG) — CC BY-SA 4.0. Compatible with our share-alike stance.
  Use KANJIDIC2, not legacy KANJIDIC, which carries extra conditions.
