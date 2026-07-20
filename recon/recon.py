"""Data recon on etymwn-20130208. Answers the five questions in PROJECT-BRIEF.md.

Single streaming pass to collect counts, then an in-memory adjacency build for traversal.
"""
import collections
import io
import json
import os
import sys

TSV = r"C:\Projects\etymology-tree-viz\data\etymwn\etymwn.tsv"
OUT = r"C:\Projects\etymology-tree-viz\recon"

FOCUS = ["eng", "lat", "fra", "kor", "cmn", "jpn", "deu", "spa", "grc", "san", "ara"]


def parse(line):
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 3:
        return None
    src, rel, tgt = parts
    return src, rel, tgt


def lang(node):
    i = node.find(":")
    return node[:i] if i > 0 else "??"


def main():
    rel_counts = collections.Counter()
    lang_src = collections.Counter()   # nodes appearing as source, per language
    lang_edges = collections.Counter() # edges touching a language (either end)
    nodes = set()
    edges = 0
    proto_langs = collections.Counter()

    with io.open(TSV, encoding="utf-8") as fh:
        for line in fh:
            p = parse(line)
            if not p:
                continue
            src, rel, tgt = p
            edges += 1
            rel_counts[rel] += 1
            nodes.add(src)
            nodes.add(tgt)
            ls, lt = lang(src), lang(tgt)
            lang_src[ls] += 1
            lang_edges[ls] += 1
            if lt != ls:
                lang_edges[lt] += 1
            for l in (ls, lt):
                if l.startswith("p_"):
                    proto_langs[l] += 1

    node_lang = collections.Counter(lang(n) for n in nodes)

    report = {
        "totals": {"edges": edges, "nodes": len(nodes)},
        "relations": rel_counts.most_common(),
        "top_languages_by_nodes": node_lang.most_common(30),
        "focus_languages": {
            l: {"nodes": node_lang.get(l, 0), "edges_touching": lang_edges.get(l, 0)}
            for l in FOCUS
        },
        "proto_languages": proto_langs.most_common(),
        "distinct_languages": len(node_lang),
    }

    with io.open(os.path.join(OUT, "recon-counts.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print("edges: {:,}  nodes: {:,}  languages: {}".format(
        edges, len(nodes), len(node_lang)))
    print("\n-- relations --")
    for r, c in rel_counts.most_common():
        print("  {:<32} {:>10,}".format(r, c))
    print("\n-- focus languages (nodes / edges touching) --")
    for l in FOCUS:
        print("  {:<5} {:>9,} {:>12,}".format(
            l, node_lang.get(l, 0), lang_edges.get(l, 0)))
    print("\n-- proto languages --")
    for l, c in proto_langs.most_common(25):
        print("  {:<14} {:>10,}".format(l, c))
    print("\n-- top 30 languages by node count --")
    for l, c in node_lang.most_common(30):
        print("  {:<8} {:>10,}".format(l, c))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
