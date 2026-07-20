"""How much of the graph can we actually ship in one self-contained page?

Counts distinct words reachable from every PIE root, so we can pick a slice
that is big enough to be a real corpus and small enough to inline.
"""
import collections
import io
import json
import os
import sys

G = r"C:\Projects\etymology-tree-viz\data\graph"


def main():
    sys.setrecursionlimit(20000)
    with io.open(os.path.join(G, "nodes.json"), encoding="utf-8") as fh:
        nodes = json.load(fh)
    with io.open(os.path.join(G, "edges.json"), encoding="utf-8") as fh:
        edges = json.load(fh)
    down = collections.defaultdict(set)
    up = collections.defaultdict(set)
    for p, c in edges:
        down[p].add(c)
        up[c].add(p)

    roots = [k for k, v in nodes.items()
             if v.get("lang_code") == "ine-pro" and not v.get("word", "").endswith("-")]
    bare = [k for k, v in nodes.items()
            if v.get("lang_code") == "ine-pro" and v.get("word", "").endswith("-")]
    print("PIE word-forms (fannable): {:,}".format(len(roots)))
    print("PIE bare roots (excluded): {:,}".format(len(bare)))

    def reach(start):
        seen, frontier = {start}, [start]
        while frontier:
            nxt = []
            for n in frontier:
                for c in down.get(n, ()):
                    if c not in seen:
                        seen.add(c)
                        nxt.append(c)
            frontier = nxt
        return seen

    covered = set()
    sizes = []
    for r in roots:
        s = reach(r)
        sizes.append(len(s))
        covered |= s
    sizes.sort(reverse=True)

    print("\ndistinct nodes reachable from all PIE word-forms: {:,}".format(len(covered)))
    print("  largest single tree : {:,}".format(sizes[0] if sizes else 0))
    print("  median tree         : {:,}".format(sizes[len(sizes) // 2] if sizes else 0))
    print("  sum of all trees    : {:,}  (overlap {:.1f}x)".format(
        sum(sizes), sum(sizes) / max(1, len(covered))))

    langs = collections.Counter(nodes[k].get("lang_code", "?") for k in covered if k in nodes)
    print("  languages covered   : {:,}".format(len(langs)))

    # a search index needs only word + language + gloss per node
    idx = [{"k": k,
            "w": nodes[k].get("word", ""),
            "l": nodes[k].get("lang", ""),
            "c": nodes[k].get("lang_code", ""),
            "g": (nodes[k].get("gloss") or "")[:60]}
           for k in covered if k in nodes]
    raw = json.dumps(idx, ensure_ascii=False, separators=(",", ":"))
    print("\nsearch index over that slice: {:,} entries, {:.1f} MB raw".format(
        len(idx), len(raw.encode("utf-8")) / 1048576))

    noGloss = json.dumps([[e["k"], e["w"], e["c"]] for e in idx],
                         ensure_ascii=False, separators=(",", ":"))
    print("  without glosses            : {:.1f} MB".format(
        len(noGloss.encode("utf-8")) / 1048576))

    # whole graph, for comparison
    allIdx = json.dumps([[k, v.get("word", ""), v.get("lang_code", "")]
                         for k, v in nodes.items()],
                        ensure_ascii=False, separators=(",", ":"))
    print("  entire 1.17M-node graph    : {:.1f} MB".format(
        len(allIdx.encode("utf-8")) / 1048576))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
