"""Query the assembled DAG: ancestors, descendants, and cognates for a word."""
import collections
import io
import json
import os
import sys

OUT = r"C:\Projects\etymology-tree-viz\data\graph"


def load():
    with io.open(os.path.join(OUT, "nodes.json"), encoding="utf-8") as fh:
        nodes = json.load(fh)
    with io.open(os.path.join(OUT, "edges.json"), encoding="utf-8") as fh:
        edges = json.load(fh)
    up, down = collections.defaultdict(set), collections.defaultdict(set)
    for p, c in edges:
        up[c].add(p)
        down[p].add(c)
    return nodes, up, down


def label(nodes, k):
    n = nodes.get(k)
    if not n:
        return k
    return "{} [{}] {}".format(n["lang"] or "?", n["lang_code"], n["word"])


def ancestors(up, start, maxd=20):
    """Return {key: depth} for everything above `start`."""
    seen, frontier, out = {start}, [start], {}
    for d in range(1, maxd + 1):
        nxt = []
        for n in frontier:
            for p in up.get(n, ()):
                if p in seen:
                    continue
                seen.add(p)
                out[p] = d
                nxt.append(p)
        frontier = nxt
        if not frontier:
            break
    return out


def descendants(down, start, maxd=20):
    seen, frontier, out = {start}, [start], {}
    for d in range(1, maxd + 1):
        nxt = []
        for n in frontier:
            for c in down.get(n, ()):
                if c in seen:
                    continue
                seen.add(c)
                out[c] = d
                nxt.append(c)
        frontier = nxt
        if not frontier:
            break
    return out


def main():
    nodes, up, down = load()
    targets = sys.argv[1:] or ["en:father"]

    for t in targets:
        print("\n" + "=" * 68)
        if t not in nodes:
            print("{}  NOT FOUND".format(t))
            continue
        print("QUERY  {}".format(label(nodes, t)))

        anc = ancestors(up, t)
        print("\n  ancestors ({}):".format(len(anc)))
        for k, d in sorted(anc.items(), key=lambda kv: kv[1]):
            print("    {}{}".format("  " * d, label(nodes, k)))

        # cognates: share an ancestor, but are not on our own ancestor/descendant line
        own = set(anc) | set(descendants(down, t)) | {t}
        cog = collections.defaultdict(list)
        for a in anc:
            for k in descendants(down, a):
                if k in own:
                    continue
                n = nodes.get(k, {})
                if n.get("lang_code", "").endswith("-pro"):
                    continue
                cog[anc[a]].append(k)

        print("\n  cognates via shared ancestor:")
        for depth in sorted(cog):
            uniq = sorted(set(cog[depth]))
            print("    via ancestor at depth {}: {} words".format(depth, len(uniq)))
        allcog = sorted({k for v in cog.values() for k in v})
        print("    total distinct cognates: {}".format(len(allcog)))
        show = [k for k in allcog if k.split(":")[0] in
                ("la", "grc", "sa", "ru", "de", "fr", "es", "it", "hi", "fa", "lt", "ga", "cy")]
        print("\n    sample in major languages:")
        for k in show[:25]:
            print("      {}".format(label(nodes, k)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
