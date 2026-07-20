"""Question 4 + 5: are proto-forms linked, and does a word traverse end-to-end?

Builds an in-memory ancestry graph (rel:etymology only = 'X comes from Y'),
then walks upward from test words and computes cognates via shared ancestors.
"""
import collections
import io
import sys

TSV = r"C:\Projects\etymology-tree-viz\data\etymwn\etymwn.tsv"

TESTS = [
    ("eng", "father"), ("eng", "water"), ("eng", "mother"), ("eng", "night"),
    ("lat", "pater"), ("fra", "père"), ("deu", "Vater"),
    ("kor", "물"), ("kor", "사람"), ("kor", "학교"),
    ("jpn", "水"), ("cmn", "水"),
]


def split_node(node):
    i = node.find(":")
    if i <= 0:
        return "??", node
    return node[:i].strip(), node[i + 1:].strip()


def key(node):
    lg, w = split_node(node)
    return lg + ":" + w


def main():
    up = collections.defaultdict(set)     # child -> parents (rel:etymology)
    down = collections.defaultdict(set)   # parent -> children
    cross_lang_etym = 0
    intra_lang_etym = 0

    with io.open(TSV, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            src, rel, tgt = parts
            if rel != "rel:etymology":
                continue
            c, p = key(src), key(tgt)   # src comes from tgt
            up[c].add(p)
            down[p].add(c)
            if c.split(":")[0] != p.split(":")[0]:
                cross_lang_etym += 1
            else:
                intra_lang_etym += 1

    print("rel:etymology edges -> cross-language: {:,}   intra-language: {:,}".format(
        cross_lang_etym, intra_lang_etym))
    print("(intra-language 'etymology' edges are derivational morphology, not ancestry)\n")

    def ancestors(node, maxdepth=12):
        """Return list of (depth, node) reachable upward."""
        out, seen, frontier = [], {node}, [node]
        for d in range(1, maxdepth + 1):
            nxt = []
            for n in frontier:
                for p in up.get(n, ()):
                    if p in seen:
                        continue
                    seen.add(p)
                    out.append((d, p))
                    nxt.append(p)
            frontier = nxt
            if not frontier:
                break
        return out

    for lg, w in TESTS:
        node = lg + ":" + w
        anc = ancestors(node)
        cross = [a for d, a in anc if a.split(":")[0] != lg]
        depth = max([d for d, _ in anc], default=0)
        print("{:<14} ancestors={:<4} max_depth={}  cross-lang={}".format(
            node, len(anc), depth, len(cross)))
        for d, a in anc[:10]:
            print("      {}{}".format("  " * d, a))
        if not anc:
            print("      (no upward edges at all)")
        print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
