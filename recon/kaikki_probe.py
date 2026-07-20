"""Inspect kaikki PIE / Proto-Germanic extracts for descendant-tree structure."""
import collections
import io
import json
import sys

PIE = r"C:\Projects\etymology-tree-viz\data\kaikki\ProtoIndoEuropean.jsonl"
PGM = r"C:\Projects\etymology-tree-viz\data\kaikki\ProtoGermanic.jsonl"


def load(path):
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main():
    pie = load(PIE)
    print("PIE entries: {}".format(len(pie)))

    keys = collections.Counter()
    for e in pie:
        keys.update(e.keys())
    print("\n-- top-level keys across PIE entries --")
    for k, c in keys.most_common():
        print("  {:<24} {:>6}  ({:.0%})".format(k, c, c / len(pie)))

    # find the father root
    target = None
    for e in pie:
        if "ph₂tḗr" in e.get("word", ""):
            target = e
            break
    if target:
        print("\n-- entry: {} --".format(target.get("word")))
        print("  keys: {}".format(sorted(target.keys())))
        for field in ("descendants", "derived", "related", "etymology_text"):
            v = target.get(field)
            if v is None:
                continue
            print("\n  [{}] type={} len={}".format(
                field, type(v).__name__, len(v) if hasattr(v, "__len__") else "-"))
            print("   " + json.dumps(v, ensure_ascii=False)[:2500])

    # how many PIE entries carry a descendants field, and how big
    withdesc = [e for e in pie if e.get("descendants")]
    print("\n\nPIE entries with 'descendants': {}/{} ({:.0%})".format(
        len(withdesc), len(pie), len(withdesc) / len(pie)))
    sizes = sorted((len(e["descendants"]) for e in withdesc), reverse=True)
    if sizes:
        print("  descendants-list size: max={} median={} total={}".format(
            sizes[0], sizes[len(sizes) // 2], sum(sizes)))

    pgm = load(PGM)
    wd = [e for e in pgm if e.get("descendants")]
    print("\nProto-Germanic entries: {}   with 'descendants': {} ({:.0%})".format(
        len(pgm), len(wd), len(wd) / len(pgm)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
