"""Probe how proto-forms are actually encoded, and check relation mirroring."""
import collections
import io
import sys

TSV = r"C:\Projects\etymology-tree-viz\data\etymwn\etymwn.tsv"

def main():
    star_by_lang = collections.Counter()   # nodes whose word starts with '*' (reconstructed)
    samples = collections.defaultdict(list)
    proto_examples = []
    mirror_check = {}
    seen = 0

    with io.open(TSV, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            src, rel, tgt = parts
            for node in (src, tgt):
                i = node.find(":")
                if i <= 0:
                    continue
                lg, word = node[:i], node[i+1:]
                if word.startswith("*"):
                    star_by_lang[lg] += 1
                    if len(samples[lg]) < 5:
                        samples[lg].append(node)
                if lg.startswith("p_") and len(proto_examples) < 25:
                    proto_examples.append(line.rstrip("\n"))
            # sample the mirror relations for a specific word
            if src == "eng:father" or tgt == "eng:father":
                mirror_check.setdefault(rel, []).append(line.rstrip("\n"))
            seen += 1

    print("-- reconstructed forms (word begins with '*') by language --")
    tot = 0
    for lg, c in star_by_lang.most_common(40):
        tot += c
        print("  {:<10} {:>9,}   e.g. {}".format(lg, c, ", ".join(samples[lg][:3])))
    print("  TOTAL starred node-mentions: {:,} across {} languages".format(
        sum(star_by_lang.values()), len(star_by_lang)))

    print("\n-- p_ prefixed proto edges (all/first 25) --")
    for l in proto_examples:
        print("  " + l)

    print("\n-- every edge touching eng:father --")
    for rel, lines in sorted(mirror_check.items()):
        print("  [{}] {}".format(rel, len(lines)))
        for l in lines[:40]:
            print("      " + l)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
