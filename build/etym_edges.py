"""Turn etymology_templates into parent edges.

The entry's own word is the CHILD; the term named in the template is the PARENT.
Relation type is kept, because the kinds are not interchangeable:

  inh   inherited      - passed down the family line
  bor   borrowed       - crossed over from another language
  der   derived        - from, without asserting inheritance
  cal   calqued        - translated piece by piece
  root  ultimate root  - NOT the immediate parent, the far end of the chain

`root` matters most and misleads most. Latin grammatica records PIE *gerbʰ- as
its root, but the real path runs through Greek. Treating that as an ordinary
parent edge would collapse a five-step history into one hop, so it is tagged and
the climb only falls back to it when nothing better exists.
"""
import collections
import io
import json
import os
import sys

SRC = r"C:\Projects\etymology-tree-viz\data\extract\etym-templates.jsonl"
OUT = r"C:\Projects\etymology-tree-viz\data\graph"

KIND = {
    "inh": "inh", "inherited": "inh",
    "der": "der", "derived": "der", "uder": "der",
    "bor": "bor", "borrowed": "bor",
    "lbor": "bor", "learned borrowing": "bor",
    "slbor": "bor", "semi-learned borrowing": "bor",
    "obor": "bor", "orthographic borrowing": "bor",
    "calque": "cal", "cal": "cal", "partial calque": "cal",
    "psm": "cal", "semantic loan": "cal", "sl": "cal",
    "root": "root",
    # word-formation: parts of the same language, not an ancestor in another
    "af": "form", "affix": "form", "compound": "form", "com": "form",
    "suffix": "form", "suf": "form", "prefix": "form", "pre": "form",
    "confix": "form", "con": "form", "blend": "form", "univerbation": "form",
}
# These list the pieces a word was built from, all in the word's own language,
# starting at argument 2 and running on: {{compound|de|Anti-|Baby|Pille}}.
FORMATION = {"af", "affix", "compound", "com", "suffix", "suf", "prefix",
             "pre", "confix", "con", "blend", "univerbation"}
# `doublet`, `clipping`, `back-formation` and `short for` are deliberately NOT
# here. They are sibling relations, not ancestry: glamour is a doublet of
# grammar, not its parent. Treating them as parents made the shortest path from
# 'grammar' run *glaumaz -> gleam -> glam -> glamour -> grammar, and sent
# 'father' through Irish athair and Manx ayr.

# only the calque family legitimately carries its term in arg 4 (arg 3 empty)
CALQUE = {"calque", "cal", "partial calque", "psm", "semantic loan", "sl"}


def clean_term(t):
    """Reject the debris that leaks out of template arguments: bare hyphens,
    parenthetical asides ('*lewbʰ- (cut off)'), and empty placeholders."""
    if not t:
        return ""
    t = t.split("<")[0].strip()
    if "(" in t or ")" in t:
        return ""
    t = t.lstrip("*").strip()
    if t in ("", "-", "--", "?"):
        return ""
    return t


def is_affix(term):
    """A grammatical ending or prefix, written with a hanging hyphen: -ing, -ly,
    un-, anti-. Note that PIE roots are also written with a trailing hyphen
    (*gerbʰ-), but those arrive through ancestry templates, never through
    word-formation, so a trailing hyphen here always means a prefix."""
    return term.startswith("-") or term.startswith("−") or \
        term.endswith("-") or term.endswith("−")


def parse_parts(args, own_lang):
    """Word-formation: every numbered argument from 2 on is a component, all in
    the word's own language. Returns a list of (lang, term).

    Affixes are dropped. They are components, but they are not where a word came
    from, and treating them as ancestors was ruinous: every -ing word became a
    child of -ing, which has its own descent to Proto-Indo-European, so the
    climb preferred it. 'sugar' traced through *-ō -> *-anaz -> -inn -> -en, and
    'blackboard' through *-eh₂ rather than through black. They also dominated
    the edge count, which crowded major languages out of the export entirely.
    """
    out = []
    i = 2
    while True:
        v = args.get(str(i))
        if v is None:
            break
        t = clean_term(v)
        if t and not is_affix(t):
            out.append((own_lang, t))
        i += 1
        if i > 9:
            break
    return out


def parse(name, args, own_lang):
    """Return (parent_lang, parent_term) or None."""
    if name == "etymon":
        # args like {"1": "la", "2": ":inh", "3": "itc-pro:*gnātiō<id:family>"}
        spec = args.get("3") or ""
        spec = spec.split("<")[0]
        if ":" not in spec:
            return None
        lg, term = spec.split(":", 1)
        return lg.strip(), clean_term(term)
    lg = (args.get("2") or "").strip()
    term = clean_term(args.get("3"))
    if not term and name in CALQUE:
        term = clean_term(args.get("4"))
    if not lg or not term:
        return None
    return lg, term


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    edges = {}
    kinds = collections.Counter()
    seen_tmpl = collections.Counter()
    n = 0

    with io.open(SRC, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            n += 1
            child = "{}:{}".format(rec["c"], rec["w"].lstrip("*").strip())
            for t in rec["t"]:
                name = t["n"]
                kind = KIND.get(name)
                if not kind:
                    continue
                seen_tmpl[name] += 1
                args = t.get("a") or {}
                if name in FORMATION:
                    got = parse_parts(args, rec["c"])
                else:
                    one = parse(name, args, rec["c"])
                    got = [one] if one else []
                # keep the most informative relation if several assert the pair
                rank = {"inh": 5, "bor": 4, "cal": 4, "der": 3, "form": 2, "root": 0}
                for lg, term in got:
                    if not lg or not term:
                        continue
                    parent = "{}:{}".format(lg, term)
                    if parent == child:
                        continue
                    key = (parent, child)
                    if key not in edges or rank[kind] > rank[edges[key]]:
                        edges[key] = kind

    for k in edges.values():
        kinds[k] += 1

    print("entries read       : {:,}".format(n))
    print("distinct edges     : {:,}\n".format(len(edges)))
    print("-- by relation --")
    for k, c in kinds.most_common():
        print("  {:<6} {:>9,}".format(k, c))
    print("\n-- top templates seen --")
    for t, c in seen_tmpl.most_common(12):
        print("  {:<22} {:>9,}".format(t, c))

    dest = os.path.join(OUT, "etym-edges.json")
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump([[p, c, k] for (p, c), k in sorted(edges.items())],
                  fh, ensure_ascii=False)
    print("\nwrote {} ({:.1f} MB)".format(dest, os.path.getsize(dest) / 1048576))


if __name__ == "__main__":
    main()
