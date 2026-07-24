# QA sweep findings (2026-07-23, ultracode 450-word sweep)

450 random words, 67 agents (find + adversarial verify against source2.jsonl).
Result: **24 confirmed assembly defects**, 13 flagged-but-source-faithful (cleared), 0 unclear.

## Fixed this pass (s-mobile root collision)

`clean_term` stripped a leading `(s)` s-mobile parenthetical, collapsing citations of
`*(s)ker-` "to cut/turn", `*(s)pel-`, etc. onto the wrong plain homograph (`ker-` = "army").
Fix: preserve a leading `(C)` onset (it is part of the reconstruction's page title).

- en:intracrinal  `*(s)ker-` "to turn, bend" -> kriznis "hair" (was `*ker-` "army")
- ro:scriitură    `*(s)ker-` "to cut" -> *(s)kreybʰ- -> scribo (was "army")
- non:skraba      `*(s)ker-` "to cut" -> *skrappōną (was "army")
- csb:chôrna      `*(s)ker-` "to cut" -> *xorna "food" (was "army"; from earlier round)

## Also fixed (2026-07-24, medial optional-phoneme parens)

clean_term stripped a MEDIAL `(y)`/`(s)` too, collapsing *dʰeh₁(y)- "to suckle" onto
*dʰeh₁- "to do". Generalised the s-mobile keep to any short, space-free, embedded paren
in a reconstruction (so "word(s)" and CJK "词(儿)" still strip).
- cy:dyniawed      now roots in *dʰeh₁(y)- "to suckle" (was *dʰeh₁- "to do")

## Remaining confirmed defects (20) — for a future targeted pass

### A. id / gloss-hint homograph mis-pick — INVESTIGATED, mostly NOT cleanly fixable
The resolver already honours senseids and id-hint gloss tokens, so these are data /
synonym / ambiguity limits, not a single resolver bug:
- grk-mar:пра́ма   id `fare` does not match the target senseid `go forth` (synonym label, no lexical overlap)
- scn:gaḍḍina      source has NO id:head; *gelH- "naked" is Wiktionary's own uncertain derivation (over-flagged)
- nb:fåtallig      non:tal has ONLY the "talk, parley" sense in our data; the "number" sense is absent (data gap)
- frm:cevich       routes to *weyk- via the itc-pro *ker-weiks path, not the *ḱerh₂(s)weyk-s compound; needs compound-element selection
- hy:բաժակաճառ     citing template is a bare `uder` to Middle Iranian with no term; the *bʰegʷ- root is a merged node (no id to honour)
- kk:жаттау        competing roots: source lists BOTH inh *Habí (<- *h₂m̥bʰí) and der *yeh₂-; genuinely ambiguous
- fi:arabiantiira  capitalization homograph: cited lowercase "arabia" (language) vs the toponym page Arabia

### B. wrong-sense same-spelling landing
- af:kus           via fro:cost "financial cost"; should be OF coste <- costa "rib, side"
- en:dankishness   via non:døkkr "dark"; should be enm:danke "wet, damp"
- ruo:dåre         attached to Latin doleō "to hurt"; is Scandinavian dåre "fool"
- en:bagmoth       "moth" -> Hindi moth-bean; should be the insect moth (ang moþþe)

### C. false root promotion / spurious parent
- lmo-old:cjaun    *ō "vocative particle" promoted above *ḱwṓ "dog" (mispicked -ō formant)
- eo:barilpordo    barra via *bērō "bier"; should be *barō "bar, barrier"
- fi:kaitanokkalokki  kaita got a spurious gem-pro *gaidō parent above the Uralic root

### D. false-link splice (two unrelated trees joined)
- it:bocchino (both senses)  *weǵʰ- "way/road" branch spliced onto bucca via *bʰew-
- cmn:移鼠          Χριστός "Christ/anoint" spliced onto יֵשׁוּעַ "Jesus" (two names, not descent)

### E. root ordering
- ccp:Jahannam     Ge'ez shown as primary; Aramaic Gehinnom is the primary source of Arabic جهنم

### F. wrong language tag
- en:hydroxymethylome  μέθυ "wine" tagged de (German); should be grc (Greek)

### G. s-mobile homograph among (s)pel roots (partially shifted, still wrong)
- pl:pół-          *polъ "side/half" needs the "to split" (s)pel root, not "to say aloud"
