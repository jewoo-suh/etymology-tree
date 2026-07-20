# Etymology Tree

**[Open it →](https://jewoo-suh.github.io/etymology-tree/)**

Type a word in any language, trace it back through its ancestors to a
reconstructed proto-form, and see the whole tree of everything else that grew
from the same root.

**2,000,000 words · 4,502 languages · 1,375,000 definitions.** Search is
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
| `index.html` | 2,000,000 | 1,375,461 | 77 MB | this site |
| full | 3,103,066 | 2,279,472 | 128 MB | [Releases](../../releases) — offline use |
| compact | 795,000 | proto-forms only | 16 MB | embedding where size is capped |

```sh
python build/extract2.py                             # one pass over the 2.65 GB dump
python build/graph2.py                               # sense-keyed merged graph
python build/export_graph.py [--glossall --target N | --full]
python build/bundle.py [--web | --full]
```

(`extract.py`, `extract_etym.py`, `etym_edges.py` and `merge_graph.py` are the
earlier spelling-keyed pipeline, kept for history.)

`data/` is not committed; the pipeline regenerates it from
[kaikki.org](https://kaikki.org).

## What it is built from

Wiktionary, via [wiktextract](https://github.com/tatuylonen/wiktextract), using
**both** places ancestry is recorded. Descendants sections point downward and
carry inheritance. `etymology_templates` point upward on each word's own page
and carry borrowing — without them, *grammar* dead-ends at Latin *grammatica*,
and most of English's learned vocabulary has no history at all.

The merged graph is 3.1M nodes and 4.6M edges across 4,502 languages, and it
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

**Every cross-reference is resolved with evidence, and demoted without it.**
A reference by spelling must earn its landing: a unique sense, a sense-id, or
gloss overlap with the context around the edge. A landing with no evidence is
demoted to a last-resort edge the chain will not walk, an untrusted node never
anchors the subtree below it, and a diacritic redirect must prove its target
means the same thing — Old English *daġ* ("day") no longer folds into *dag*
("dough"), it stays an honest phantom. This is what keeps *star* off the stair,
*sun* out of sin, *eye* out of the egg, *hound* out of the hand, and *moon* out
of lamentation: every one of those was a confident chain once, welded together
by a shared spelling.

**Homographs are split by etymology, and cross-references are resolved, not
known.** Nodes are keyed on Wiktionary's `etymology_number`, so *school* the
institution and *school* of fish are separate nodes with separate chains
(101,639 spellings split this way). But a reference in running data points at a
spelling, not a sense, so each one is resolved: a unique sense wins outright; a
sense-id or gloss hint wins where present; otherwise the primary etymology is
assumed. A formation part that would be resolved by bare guesswork is dropped
instead — that guess is what once made *Korea* descend from *Core*, the birth
name of Persephone. The residue: an unhinted reference to a homograph can still
land on the wrong sense when Wiktionary's first etymology is not the intended
one, and senses Wiktionary itself lumps together stay lumped.

*Korea* now shows the honest answer — `고려 → Korea`, with 高麗 and Dutch *Core*
among its listed parents — rather than a confident march to a Proto-Germanic
cabbage. The Marco-Polo leg (Cauli → Corea) is not in Wiktionary's structured
data, so it is not shown.

**Chains prefer depth over completeness.** *ontology* is shown as
`*h₁sónts → *ehónts → ὤν → ontology`. Every step is recorded, but Latin
*ontologia* — where the word was actually coined, around 1600 — is skipped,
because it has no recorded ancestry of its own and the climb prefers the route
that reaches a reconstructed form. It is listed under "Comes from" in the rail.

**Only lemmas.** A plural never finds its singular.

Surname, place-name and inflected-form entries are stripped (217,451 of them)
unless a real word descends from them.

## Licence

Data derived from Wiktionary via wiktextract, **CC BY-SA 3.0** — share-alike, so
any derived dataset carries the same terms. See [LICENCE-DATA.md](LICENCE-DATA.md).
Build scripts and page code are MIT.
