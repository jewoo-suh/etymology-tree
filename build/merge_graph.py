"""Merge the two ancestry sources into one typed graph.

Descendants sections give inheritance downward; etymology_templates give
ancestry upward including borrowings. Neither alone is the etymology of a
language: the first misses every loanword, the second misses the long
descendant chains that make cognates visible.
"""
import collections
import io
import json
import os
import sys

G = r"C:\Projects\etymology-tree-viz\data\graph"
EX = r"C:\Projects\etymology-tree-viz\data\extract"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with io.open(os.path.join(G, "nodes.json"), encoding="utf-8") as fh:
        nodes = json.load(fh)
    with io.open(os.path.join(G, "edges.json"), encoding="utf-8") as fh:
        desc_edges = json.load(fh)
    borrowed = set()
    bp = os.path.join(G, "borrowed.json")
    if os.path.exists(bp):
        with io.open(bp, encoding="utf-8") as fh:
            borrowed = set(tuple(e) for e in json.load(fh))
    with io.open(os.path.join(G, "etym-edges.json"), encoding="utf-8") as fh:
        etym = json.load(fh)

    print("from descendants : {:,} nodes, {:,} edges".format(len(nodes), len(desc_edges)))
    print("from templates   : {:,} edges".format(len(etym)))

    code_name = {}
    for v in nodes.values():
        c, nm = v.get("lang_code"), v.get("lang")
        if c and nm and c not in code_name:
            code_name[c] = nm

    rank = {"inh": 5, "bor": 4, "cal": 4, "der": 3, "form": 2, "root": 0}
    merged = {}
    for p, c in desc_edges:
        merged[(p, c)] = "bor" if (p, c) in borrowed else "inh"

    added_nodes = 0
    for p, c, k in etym:
        for side in (p, c):
            if side not in nodes:
                i = side.find(":")
                if i <= 0:
                    continue
                code, word = side[:i], side[i + 1:]
                nodes[side] = {"lang_code": code, "lang": code_name.get(code, ""),
                               "word": word, "gloss": "", "entry": False}
                added_nodes += 1
        if p not in nodes or c not in nodes:
            continue
        cur = merged.get((p, c))
        if cur is None or rank[k] > rank[cur]:
            merged[(p, c)] = k

    print("\nnew nodes from templates: {:,}".format(added_nodes))
    print("merged: {:,} nodes, {:,} edges".format(len(nodes), len(merged)))

    kinds = collections.Counter(merged.values())
    print("\n-- relations --")
    for k, n in kinds.most_common():
        print("  {:<6} {:>9,}".format(k, n))

    # fill glosses for anything still missing one, from the whole-dump sidecar
    need = {k for k, v in nodes.items() if not v.get("gloss")}
    hit = 0
    gp = os.path.join(EX, "glosses.jsonl")
    if os.path.exists(gp):
        with io.open(gp, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                key = "{}:{}".format(r["c"], r["w"])
                if key in need:
                    nodes[key]["gloss"] = r["g"]
                    need.discard(key)
                    hit += 1
    print("\nglosses filled: {:,}".format(hit))

    with io.open(os.path.join(G, "nodes2.json"), "w", encoding="utf-8") as fh:
        json.dump(nodes, fh, ensure_ascii=False)
    with io.open(os.path.join(G, "edges2.json"), "w", encoding="utf-8") as fh:
        json.dump([[p, c, k] for (p, c), k in sorted(merged.items())],
                  fh, ensure_ascii=False)

    up = collections.Counter()
    for (p, c) in merged:
        up[c] += 1
    orphans = sum(1 for k in nodes if not up.get(k))
    print("nodes with no parent: {:,} ({:.0%})".format(orphans, orphans / len(nodes)))
    print("\nwrote nodes2.json / edges2.json")


if __name__ == "__main__":
    main()
