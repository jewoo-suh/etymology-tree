"""Can we compose PIE -> proto -> attested by joining descendant trees across files?"""
import io
import json
import sys

PGM = r"C:\Projects\etymology-tree-viz\data\kaikki\ProtoGermanic.jsonl"


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def flatten(nodes, depth=0, out=None):
    if out is None:
        out = []
    for n in nodes:
        out.append((depth, n.get("lang_code"), n.get("lang"), n.get("word")))
        if n.get("descendants"):
            flatten(n["descendants"], depth + 1, out)
    return out


def main():
    pgm = load(PGM)
    target = None
    for e in pgm:
        if e.get("word", "").lstrip("*") == "fadēr":
            target = e
            break
    if not target:
        print("*fadēr not found")
        return

    flat = flatten(target.get("descendants", []))
    print("Proto-Germanic *fadēr -> {} descendant nodes, max depth {}".format(
        len(flat), max(d for d, *_ in flat)))
    for d, code, lang, word in flat:
        print("  {}{} [{}] {}".format("   " * d, lang, code, word))

    # does English 'father' appear?
    hits = [x for x in flat if x[1] == "en"]
    print("\nEnglish nodes reached: {}".format(hits))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
