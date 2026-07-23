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

## Remaining confirmed defects (21) — for a future targeted pass

### A. id / gloss-hint homograph mis-pick (source carries a disambiguator we ignore)
The source names a specific sense via `<id:...>` or a gloss the target sense expresses
with a synonym, so neither the senseid map nor gloss-overlap catches it.
- grk-mar:пра́ма   *per- should be `<id:fare>` "to cross/traverse", not "to beat"
- cy:dyniawed      root should be *dʰeh₁(y)- "to suckle", not *dʰeh₁- "to do"
- scn:gaḍḍina      *gelH- should use `id:head`, shown as "naked"
- nb:fåtallig      Old Norse tal should use `id:number`, shown as "speech, parley"
- frm:cevich       cervix should root in *ḱerh₂- "head", shown as *weyk- "to sift"
- hy:բաժակաճառ     root should be *bʰag- "to share/apportion", not *bʰegʷ- "to flee"
- kk:жаттау        فا:یاد deeper origin is *yeh₂- "to go", not *h₂m̥bʰí "around"
- fi:arabiantiira  parent should be toponym Arabia, shown as "Arabic (language)"

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
