"""Export per-word etymology trees for the prototype.

Implements the two rules the recon surfaced:

  1. Stop at the NEAREST meaningful shared ancestor. Walking one hop too high
     (*ph₂tḗr -> *peh₂-) tripled the descendant set and dragged in 'bread' and
     'fodder'. We detect that by watching for a jump in descendant count.
  2. Collapse spelling variants. 15 Middle English spellings of 'fader' are one
     node with variants attached, not 15 ancestors.
"""
import collections
import io
import json
import os
import sys

G = r"C:\Projects\etymology-tree-viz\data\graph"
OUT = r"C:\Projects\etymology-tree-viz\web"

# Deliberately multilingual entry points: the brief's whole premise is that any
# language is a valid starting place, not just English.
# NB ru:вода́ carries a stress mark and la:māter a macron -- stored forms have
# diacritics users will not type, so the real search index needs accent-folding.
QUERIES = [
    "en:father", "en:water", "en:mother", "en:heart", "en:name",
    "en:night", "en:star", "en:wheel", "en:milk",
    "de:Vater", "la:pater", "grc:πατήρ", "sa:पितृ", "ru:вода́",
    "fi:vesi", "lt:vanduo", "sq:natë", "hy:հայր", "ga:athair",
    "cy:mam", "is:hjarta", "fa:پدر", "hi:पिता", "tr:su",
    "ko:물", "ja:水", "zh:水", "ko:학교", "ja:学校",
]

# Descendant counts always grow as you walk up a generation, so a ratio test fires
# on every step. The real signal is orthographic: Wiktionary writes bare roots with
# a trailing hyphen (*peh₂-, *ḱewh₁-) and derived words without (*ph₂tḗr, *nókʷts).
# A root is a morpheme, not a word, and fanning from one is what dragged 'bread'
# into 'father'. So we climb the full chain but fan from the topmost real word.

DEPTH_CAP = 12    # guard against pathological depth only, not a size budget


def is_bare_root(word):
    w = (word or "").strip()
    return w.endswith("-") or w.endswith("−")


def load():
    with io.open(os.path.join(G, "nodes.json"), encoding="utf-8") as fh:
        nodes = json.load(fh)
    with io.open(os.path.join(G, "edges.json"), encoding="utf-8") as fh:
        edges = json.load(fh)
    up, down = collections.defaultdict(set), collections.defaultdict(set)
    for p, c in edges:
        up[c].add(p)
        down[p].add(c)
    borrowed = set()
    bp = os.path.join(G, "borrowed.json")
    if os.path.exists(bp):
        with io.open(bp, encoding="utf-8") as fh:
            borrowed = set(tuple(e) for e in json.load(fh))
    return nodes, up, down, borrowed


def descendants(down, start):
    seen, frontier = {start}, [start]
    while frontier:
        nxt = []
        for n in frontier:
            for c in down.get(n, ()):
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
        frontier = nxt
    seen.discard(start)
    return seen


def primary_chain(nodes, up, down, start):
    """Search the whole ancestor set, then walk back down to the query.

    Picking one representative parent per generation and hoping it continues is
    fragile: if the chosen spelling variant happens to have no recorded parent,
    the climb dies early. That silently truncated 'mother' at Old English modor
    when the fuller dataset gave it more variants to choose between. So instead
    breadth-first the entire ancestor set, choose the highest genuine proto-form,
    and reconstruct the path to it.
    """
    parent_of, depth = {}, {start: 0}
    queue = collections.deque([start])
    while queue:
        cur = queue.popleft()
        for p in sorted(up.get(cur, ())):
            if p in depth:
                continue
            depth[p] = depth[cur] + 1
            parent_of[p] = cur
            queue.append(p)

    cands = [k for k in depth if k != start]
    if not cands:
        return []

    def rank(k):
        n = nodes.get(k, {})
        proto = "-pro" in (n.get("lang_code") or "")
        return (proto and not is_bare_root(n.get("word", "")), depth[k])

    root = max(cands, key=rank)

    # walk parent_of back down to the query to recover the actual route
    route, cur = [], root
    while cur != start:
        route.append(cur)
        cur = parent_of[cur]
    route.reverse()

    chain = []
    for k in route:
        code = nodes.get(k, {}).get("lang_code", "?")
        word = nodes.get(k, {}).get("word", "")
        # other ancestors of the same generation and language are spelling variants
        sibs = sorted(x for x in depth
                      if x != k and depth[x] == depth[k]
                      and nodes.get(x, {}).get("lang_code") == code)
        chain.append({
            "key": k,
            "variants": [nodes.get(s, {}).get("word", "") for s in sibs][:12],
            "n_desc": len(descendants(down, k)),
            "root_form": is_bare_root(word),
        })
    return chain


def build_tree(nodes, down, root, route, borrowed, depth_cap=9):
    """Nested dict for rendering, marking query path and loaned edges.

    `route` runs top-down, root first. Matching on membership rather than position
    was wrong: flattening a DAG into a tree repeats the same word at many places,
    so every copy lit up as 'on the path' and the default view opened all of their
    ancestors at once -- 1,236 rows for a tree with a six-step lineage.
    """
    def rec(k, depth, seen, loan, parent_on):
        n = nodes.get(k, {})
        kids = sorted(down.get(k, ())) if depth < depth_cap else []
        # only a lineage descending unbroken from the root counts: matching on
        # depth alone still lit up every copy of the word sitting at that depth
        on = parent_on and depth < len(route) and route[depth] == k
        return {
            "key": k,
            "word": n.get("word", k),
            "lang": n.get("lang", ""),
            "code": n.get("lang_code", ""),
            "gloss": (n.get("gloss") or "")[:70],
            "path": on,
            "loan": loan,
            "children": [rec(c, depth + 1, seen | {k}, (k, c) in borrowed, on)
                         for c in kids if c not in seen],
        }
    return rec(root, 0, frozenset(), False, True)


def count_nodes(tree):
    n, stack = 0, [tree]
    while stack:
        t = stack.pop()
        n += 1
        stack.extend(t["children"])
    return n


def main():
    sys.setrecursionlimit(20000)
    nodes, up, down, borrowed = load()
    out = {}

    for q in QUERIES:
        if q not in nodes:
            print("  {:<14} MISSING".format(q))
            continue
        chain = primary_chain(nodes, up, down, q)
        if not chain:
            print("  {:<14} no ancestors".format(q))
            continue
        # fan from the topmost ancestor that is still a word, not a bare root
        words_only = [c for c in chain if not c["root_form"]]
        usable = words_only or chain[:1]
        root = usable[-1]["key"]
        # top-down route: root first, query last
        route = [c["key"] for c in reversed(chain)] + [q]
        # Never shrink the tree to fit a render budget: an earlier version did, and
        # silently cut en:star -- the user's own query -- out of its own tree. The
        # UI folds branches by default, so size is a display concern, not an export one.
        tree = build_tree(nodes, down, root, route, borrowed, DEPTH_CAP)

        # count what the user will actually see, and verify the query survived
        stack, seen_langs, total, found = [tree], set(), 0, False
        while stack:
            t = stack.pop()
            total += 1
            if t["code"]:
                seen_langs.add(t["code"])
            if t["key"] == q:
                found = True
            stack.extend(t["children"])
        if not found:
            print("  {:<14} REJECTED: query absent from its own tree".format(q))
            continue

        # the chain stops at the topmost real word, so the bare root we declined to
        # fan from sits just above it; surface it, because explaining the cut is
        # more useful than silently making it
        bare = sorted(k for k in up.get(root, ())
                      if is_bare_root(nodes.get(k, {}).get("word", "")))
        cut = None
        if bare:
            pick = max(bare, key=lambda k: len(descendants(down, k)))
            cut = {"key": pick, "n_desc": len(descendants(down, pick))}
        out[q] = {
            "query": q,
            "word": nodes[q].get("word", ""),
            "lang": nodes[q].get("lang", ""),
            "root": root,
            "chain": [{"key": c["key"],
                       "word": nodes.get(c["key"], {}).get("word", ""),
                       "lang": nodes.get(c["key"], {}).get("lang", ""),
                       "code": nodes.get(c["key"], {}).get("lang_code", ""),
                       "variants": c["variants"],
                       "rootForm": c["root_form"],
                       "fanRoot": c["key"] == root} for c in chain],
            "stoppedAt": ({"word": nodes.get(cut["key"], {}).get("word", ""),
                           "lang": nodes.get(cut["key"], {}).get("lang", ""),
                           "nDesc": cut["n_desc"]} if cut else None),
            "tree": tree,
            "nodes": total,
            "langs": len(seen_langs),
        }
        print("  {:<14} chain={:>2}  fan={:<20} tree={:>4}n /{:>3} langs{}".format(
            q, len(chain), root, total, len(seen_langs),
            "   held back from *{}".format(out[q]["stoppedAt"]["word"]) if cut else ""))

    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    dest = os.path.join(OUT, "trees.json")
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("\nwrote {} trees -> {} ({:.1f} KB)".format(
        len(out), dest, os.path.getsize(dest) / 1024))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
