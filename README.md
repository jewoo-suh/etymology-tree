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

- **Homographs merge.** Nodes are keyed by language plus spelling, so *school*
  the institution and *school* of fish share one node. Fixing it means keying on
  Wiktionary's `etymology_number`.
- **Only lemmas.** A plural never finds its singular.
- Surname, place-name and inflected-form entries are stripped (183,744 of them)
  unless a real word descends from them.

## Licence

Data derived from Wiktionary via wiktextract, **CC BY-SA 3.0** — share-alike, so
any derived dataset carries the same terms. See [LICENCE-DATA.md](LICENCE-DATA.md).
Build scripts and page code are MIT.
