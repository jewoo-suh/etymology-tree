"""Size the root-explorer view: real dedup'd descendant counts per PIE root.

Answers: how big is a per-root payload, and does dedup actually bite?
"""
import io
import json
import statistics
import sys

PIE = r"C:\Projects\etymology-tree-viz\data\kaikki\ProtoIndoEuropean.jsonl"


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def walk(nodes, depth, raw, uniq, langs, maxd):
    for n in nodes:
        raw[0] += 1
        maxd[0] = max(maxd[0], depth)
        code = n.get("lang_code")
        word = n.get("word")
        if code and word:
            uniq.add((code, word))
            langs.add(code)
        kids = n.get("descendants")
        if kids:
            walk(kids, depth + 1, raw, uniq, langs, maxd)


def main():
    sys.setrecursionlimit(10000)
    pie = load(PIE)
    rows = []
    for e in pie:
        d = e.get("descendants")
        if not d:
            continue
        raw, uniq, langs, maxd = [0], set(), set(), [0]
        walk(d, 1, raw, uniq, langs, maxd)
        gloss = ""
        senses = e.get("senses") or []
        if senses:
            gl = senses[0].get("glosses") or []
            if gl:
                gloss = gl[0]
        rows.append({
            "word": e.get("word"),
            "gloss": gloss[:40],
            "raw": raw[0],
            "uniq": len(uniq),
            "langs": len(langs),
            "depth": maxd[0],
        })

    rows.sort(key=lambda r: -r["uniq"])
    raws = [r["raw"] for r in rows]
    uniqs = [r["uniq"] for r in rows]

    print("PIE roots with descendants: {}".format(len(rows)))
    print("raw nodes   total={:,}  median={}  max={:,}".format(
        sum(raws), int(statistics.median(raws)), max(raws)))
    print("dedup nodes total={:,}  median={}  max={:,}".format(
        sum(uniqs), int(statistics.median(uniqs)), max(uniqs)))
    print("dedup saving: {:.0%}".format(1 - sum(uniqs) / sum(raws)))
    print("max tree depth seen: {}".format(max(r["depth"] for r in rows)))

    print("\n-- 20 largest roots (what the explorer's top rows look like) --")
    print("  {:<16} {:<34} {:>7} {:>7} {:>6} {:>6}".format(
        "root", "gloss", "raw", "dedup", "langs", "depth"))
    for r in rows[:20]:
        print("  {:<16} {:<34} {:>7,} {:>7,} {:>6} {:>6}".format(
            r["word"], r["gloss"], r["raw"], r["uniq"], r["langs"], r["depth"]))

    over = [r for r in rows if r["uniq"] > 1000]
    print("\nroots with >1000 dedup'd nodes: {} ({:.1%})".format(
        len(over), len(over) / len(rows)))

    with io.open(r"C:\Projects\etymology-tree-viz\recon\pie-roots.json",
                 "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
