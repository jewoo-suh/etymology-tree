"""Which language extracts must we download to resolve the graph?

Counts, per lang_code, how many nodes PIE + Proto-Germanic descendant trees point at,
and flags which of those are themselves proto-languages (i.e. need their own extract
to expand further).
"""
import collections
import io
import json
import sys

FILES = {
    "PIE": r"C:\Projects\etymology-tree-viz\data\kaikki\ProtoIndoEuropean.jsonl",
    "PGmc": r"C:\Projects\etymology-tree-viz\data\kaikki\ProtoGermanic.jsonl",
}


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def walk(nodes, seen, langname):
    for n in nodes:
        code, word = n.get("lang_code"), n.get("word")
        if code and word:
            seen[code].add(word)
            langname[code] = n.get("lang") or langname.get(code, "")
        if n.get("descendants"):
            walk(n["descendants"], seen, langname)


def main():
    sys.setrecursionlimit(10000)
    for label, path in FILES.items():
        entries = load(path)
        seen = collections.defaultdict(set)
        langname = {}
        for e in entries:
            if e.get("descendants"):
                walk(e["descendants"], seen, langname)

        total = sum(len(v) for v in seen.values())
        protos = {c: v for c, v in seen.items() if "-pro" in c}
        print("\n=== {} ===  {} entries -> {:,} distinct (lang, word) refs across {} languages"
              .format(label, len(entries), total, len(seen)))

        print("  -- proto-language targets (need their own extract) --")
        for c, v in sorted(protos.items(), key=lambda kv: -len(kv[1])):
            print("     {:<16} {:<26} {:>6} forms".format(c, langname.get(c, ""), len(v)))

        print("  -- top 15 attested-language targets --")
        att = {c: v for c, v in seen.items() if "-pro" not in c}
        for c, v in sorted(att.items(), key=lambda kv: -len(kv[1]))[:15]:
            print("     {:<16} {:<26} {:>6} forms".format(c, langname.get(c, ""), len(v)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
