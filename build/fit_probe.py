"""What slice of the graph fits in the 16 MB single-file budget?

The proto-seeded slice silently excluded every word whose ancestry stops at an
attested language -- 'grammar' halts at Latin grammatica -- which is most of the
learned Latinate and Greek vocabulary. Measure the alternatives properly.
"""
import collections
import io
import json
import os
import sys

G = r"C:\Projects\etymology-tree-viz\data\graph"
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def b36(n):
    if n == 0:
        return "0"
    s = ""
    while n:
        s = DIGITS[n % 36] + s
        n //= 36
    return s


def frontcode(strings):
    """Sorted forms share long prefixes (enm:gramer / gramere / grammer), so
    store a shared-prefix length plus the tail instead of the whole word."""
    out, prev = [], ""
    for s in strings:
        n = 0
        m = min(len(prev), len(s), 35)
        while n < m and prev[n] == s[n]:
            n += 1
        out.append(DIGITS[n] + s[n:])
        prev = s
    return "\n".join(out)


def cost(nodes, keep, edges, gloss_max, front=False):
    ids = {}
    order = sorted(keep)
    for i, k in enumerate(order):
        ids[k] = i
    raw = [nodes[k].get("word", "").replace("\n", " ") for k in order]
    words = frontcode(raw) if front else "\n".join(raw)
    gl = "\n".join((nodes[k].get("gloss") or "")[:gloss_max].replace("\n", " ")
                   for k in order) if gloss_max else ""
    adj = collections.defaultdict(list)
    ne = 0
    for p, c in edges:
        if p in ids and c in ids:
            adj[ids[p]].append(ids[c])
            ne += 1
    chunks = []
    for p in sorted(adj):
        chunks.append(b36(p) + ">" + ",".join(b36(c) for c in sorted(adj[p])))
    adjs = ";".join(chunks)
    total = (len(words.encode("utf-8")) + len(gl.encode("utf-8")) +
             len(adjs.encode("utf-8")) + 400000)   # rough allowance for the rest
    return len(order), ne, total / 1e6


def main():
    with io.open(os.path.join(G, "nodes.json"), encoding="utf-8") as fh:
        nodes = json.load(fh)
    with io.open(os.path.join(G, "edges.json"), encoding="utf-8") as fh:
        edges = json.load(fh)

    up = collections.defaultdict(set)
    down = collections.defaultdict(set)
    for p, c in edges:
        up[c].add(p)
        down[p].add(c)

    connected = set()
    for p, c in edges:
        connected.add(p)
        connected.add(c)

    print("total nodes        : {:,}".format(len(nodes)))
    print("with any edge      : {:,}".format(len(connected)))
    print("isolated           : {:,}\n".format(len(nodes) - len(connected)))

    n, e, mb = cost(nodes, set(nodes), edges, 34)
    print("  {:<26} {:>9,} nodes  {:>6.1f} MB  over".format("whole graph", n, mb))
    n, e, mb = cost(nodes, set(nodes), edges, 0)
    print("  {:<26} {:>9,} nodes  {:>6.1f} MB  over\n".format("whole graph, no glosses", n, mb))

    # Slice by language instead. Keep the best-covered languages, then close
    # upward so every kept word still has its complete chain of ancestors --
    # a word whose lineage is truncated is worse than a word that is absent.
    bylang = collections.Counter(v.get("lang_code", "?") for v in nodes.values())
    ranked = [c for c, _ in bylang.most_common()]

    def ancestor_close(seed):
        keep = set(seed)
        frontier = list(seed)
        while frontier:
            nxt = []
            for x in frontier:
                for p in up.get(x, ()):
                    if p not in keep:
                        keep.add(p)
                        nxt.append(p)
            frontier = nxt
        return keep

    probe_words = ["en:grammar", "en:nation", "en:justice", "en:library",
                   "en:father", "ru:вода́", "hi:पिता", "ja:水"]
    n, e, mb = cost(nodes, set(nodes), edges, 0, front=True)
    print("  {:<26} {:>9,} nodes  {:>6.1f} MB  (front-coded, no glosses)\n".format(
        "whole graph", n, mb))

    # Hybrid: wide language coverage, but glosses only where they will actually
    # be read -- reconstructed forms (what does *ph₂tḗr mean?) and the languages
    # people search in. A gloss on an obscure dialect leaf costs the same bytes
    # and is seen far less often.
    for topn in (160, 260, 400):
        langs = set(ranked[:topn])
        seed = {k for k, v in nodes.items() if v.get("lang_code") in langs}
        keep = ancestor_close(seed)
        base_n, base_e, base_mb = cost(nodes, keep, edges, 0, front=True)
        hit = sum(1 for w in probe_words if w in keep)
        print("  top {:<4} {:>9,} nodes {:>9,} edges  base {:>5.1f} MB  probes {}/{}".format(
            topn, base_n, base_e, base_mb, hit, len(probe_words)))
        for gtop in (12, 25, 45):
            glangs = set(ranked[:gtop])
            gbytes = 0
            gcount = 0
            for k in keep:
                v = nodes[k]
                c = v.get("lang_code", "")
                if c in glangs or "-pro" in c:
                    g = (v.get("gloss") or "")[:30]
                    if g:
                        gbytes += len(g.encode("utf-8")) + 1
                        gcount += 1
            tot = base_mb + gbytes / 1e6
            print("      + glosses for protos and top {:<3} : {:>7,} glossed  "
                  "{:>5.1f} MB  {}".format(gtop, gcount, tot,
                                           "FITS" if tot < 15.3 else "over"))
        print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
