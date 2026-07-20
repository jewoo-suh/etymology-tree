"""Corrected probe: node format is 'lang: word' (space after colon)."""
import collections
import io
import sys

TSV = r"C:\Projects\etymology-tree-viz\data\etymwn\etymwn.tsv"


def split_node(node):
    i = node.find(":")
    if i <= 0:
        return "??", node
    return node[:i].strip(), node[i + 1:].strip()


def main():
    star_by_lang = collections.Counter()
    samples = collections.defaultdict(list)
    father = []
    water = []
    starred_nodes = set()

    with io.open(TSV, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            src, rel, tgt = parts
            for node in (src, tgt):
                lg, word = split_node(node)
                if word.startswith("*"):
                    star_by_lang[lg] += 1
                    starred_nodes.add(node)
                    if len(samples[lg]) < 4:
                        samples[lg].append(word)
            if split_node(src) == ("eng", "father") or split_node(tgt) == ("eng", "father"):
                father.append(line.rstrip("\n"))
            if split_node(src) == ("eng", "water") or split_node(tgt) == ("eng", "water"):
                water.append(line.rstrip("\n"))

    print("-- reconstructed ('*') forms by language --")
    for lg, c in star_by_lang.most_common(30):
        print("  {:<10} {:>9,}   e.g. {}".format(lg, c, ", ".join(samples[lg][:3])))
    print("  TOTAL starred mentions: {:,}  distinct starred nodes: {:,}  languages: {}".format(
        sum(star_by_lang.values()), len(starred_nodes), len(star_by_lang)))

    print("\n-- edges touching eng: father ({}) --".format(len(father)))
    for l in father:
        print("  " + l)

    print("\n-- edges touching eng: water ({}) --".format(len(water)))
    for l in water[:60]:
        print("  " + l)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
