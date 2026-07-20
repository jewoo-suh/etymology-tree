# Etymology Tree

**[Open it →](https://jewoo-suh.github.io/etymology-tree/)**

Type a word in any language, trace it back through its ancestors to a
reconstructed proto-form, and see the whole tree of everything else that grew
from the same root.

**1,250,000 words · 4,473 languages · 815,000 definitions.** Search is
accent-folding, so plain ASCII finds accented forms: `pater` finds *patḗr*,
*patēr* and *pater*; `вода` finds *вода́*.

```
sugar
  *ḱorkeh₂        Proto-Indo-European
  *śárkaraH       Proto-Indo-Aryan
  शर्करा            Sanskrit
  سُكَّر            Arabic          (borrowed)
  çucre           Old French
  sugre           Middle English
  sugar           English
```

Whisky and water share a root. Grammar and carve share one too — `*gerbʰ-`,
"to scratch", because writing was scratching marks into a surface.

## Builds

| | words | definitions | size | for |
|---|---|---|---|---|
| `index.html` | 1,250,000 | 815,421 | 45 MB | this site |
| full | 2,851,910 | 1,975,299 | 106 MB | [Releases](../../releases) — offline use |
| compact | 830,000 | proto-forms only | 16 MB | embedding where size is capped |

```sh
python build/extract.py                              # one pass over the 2.65 GB dump
python build/extract_etym.py                         # second pass: etymology templates
python build/etym_edges.py && python build/merge_graph.py
python build/export_graph.py [--glossall --target N | --full]
python build/bundle.py [--web | --full]
```

`data/` is not committed; the pipeline regenerates it from
[kaikki.org](https://kaikki.org).

## What it is built from

Wiktionary, via [wiktextract](https://github.com/tatuylonen/wiktextract), using
**both** places ancestry is recorded. Descendants sections point downward and
carry inheritance. `etymology_templates` point upward on each word's own page
and carry borrowing — without them, *grammar* dead-ends at Latin *grammatica*,
and most of English's learned vocabulary has no history at all.

The merged graph is 2.85M nodes and 3.86M edges across 4,473 languages, and it
is a **DAG, not a tree**: 150,000+ nodes have more than one parent, from spelling
variants converging and words with several etymons.

## Things the data teaches you the hard way

**Fan from the topmost word, not the topmost root.** English *father* reaches
PIE `*ph₂tḗr` (156 descendants, all clean), which derives from `*peh₂-` (439,
including *bread*, *fodder* and *to feed*). One hop too far and the tool looks
broken. Roots carry a trailing hyphen; words do not.

**Suffixes are not ancestors.** Once word-formation edges were added, every word
became a child of its ending, and endings have their own descent to PIE — so
*sugar* traced through `*-ō → *-anaz → -inn`, and *heart* through `*-utaz` to
*heorot*, which is a deer. Affixes are excluded from lineage.

**Borrowing is not descent.** Japanese 学校 is loaned from Chinese, not inherited
from it. Loan edges are tracked separately and drawn dashed.

**Shortest path is the wrong path.** Wiktionary pages routinely cite a distant
ancestor directly, so the quick route from `*ph₂tḗr` to *father* is two hops and
drops Old English and Proto-Germanic. Chains follow the longest route; trees drop
shortcut edges by transitive reduction.

See [RECON-FINDINGS.md](RECON-FINDINGS.md) for how the data was assessed, and
[PROJECT-BRIEF.md](PROJECT-BRIEF.md) for the original scope.

## Known limits

**Homographs merge, and this can produce chains that are confidently wrong.**
Nodes are keyed by language plus spelling, so every sense of a spelling shares
one node. Usually that is harmless. Sometimes it is not:

> `Korea → 高麗 → kool → … → *ǵwelH-`

Each edge there is real. Korea does come from 高麗 (Goryeo), and Taiwanese
高麗菜 "cabbage" genuinely is borrowed from Dutch *kool*. But they are different
senses of the same spelling, and merging them walks the chain out of a country
and into a vegetable. The true line is 고구려 → 고려 → Cauli → Corea → Korea.

Treat a chain as a claim about **spellings**, not about meanings. Where a step
looks absurd, it usually is, and the detail rail lists every recorded parent so
you can see which one the chain took. Fixing this properly means keying nodes on
Wiktionary's `etymology_number`, which every template reference would then have
to disambiguate.

**Chains prefer depth over completeness.** *ontology* is shown as
`*h₁sónts → *ehónts → ὤν → ontology`. Every step is recorded, but Latin
*ontologia* — where the word was actually coined, around 1600 — is skipped,
because it has no recorded ancestry of its own and the climb prefers the route
that reaches a reconstructed form. It is listed under "Comes from" in the rail.

**Only lemmas.** A plural never finds its singular.

Surname, place-name and inflected-form entries are stripped (185,064 of them)
unless a real word descends from them.

## Licence

Data derived from Wiktionary via wiktextract, **CC BY-SA 3.0** — share-alike, so
any derived dataset carries the same terms. See [LICENCE-DATA.md](LICENCE-DATA.md).
Build scripts and page code are MIT.
