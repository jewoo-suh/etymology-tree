"""Assemble a single etymology DAG from kaikki per-language extracts.

Each kaikki entry carries a nested `descendants` tree. Those trees are local: they
stop at intermediate proto-forms rather than recursing. We therefore:

  1. flatten every tree into (parent -> child) edges
  2. key every node as "<lang_code>:<word>" with the leading '*' stripped, so a
     reference to Proto-Germanic *fadēr unifies with the *fadēr entry's own tree
  3. dedup edges (raw trees repeat whole subtrees under each spelling variant)
  4. build the reverse index, because the source data only points downward and
     users search upward

Output: nodes.json, edges.json, and stats printed to stdout.
"""
import collections
import glob
import io
import json
import os
import sys

DATA = r"C:\Projects\etymology-tree-viz\data\kaikki"
OUT = r"C:\Projects\etymology-tree-viz\data\graph"


def norm(word):
    """Reference form '*fadēr' and entry form 'fadēr' must unify."""
    return (word or "").lstrip("*").strip()


def key(code, word):
    return "{}:{}".format(code, norm(word))


class Graph(object):
    def __init__(self):
        self.edges = set()             # (parent_key, child_key)
        self.label = {}                # key -> {lang, lang_code, word}
        self.gloss = {}                # key -> first gloss, when we have an entry
        self.has_entry = set()         # keys that are a real entry, not just a reference
        self.borrowed = set()          # edges flagged as borrowing rather than inheritance

    def note(self, code, word, lang=None):
        k = key(code, word)
        if k not in self.label:
            self.label[k] = {"lang_code": code, "lang": lang or "", "word": norm(word)}
        elif lang and not self.label[k]["lang"]:
            self.label[k]["lang"] = lang
        return k

    def walk(self, parent_key, nodes):
        for n in nodes:
            code, word = n.get("lang_code"), n.get("word")
            if not code or not word:
                # malformed row (kaikki emits word=None occasionally); keep descending
                if n.get("descendants"):
                    self.walk(parent_key, n["descendants"])
                continue
            k = self.note(code, word, n.get("lang"))
            if k != parent_key:
                self.edges.add((parent_key, k))
                tags = " ".join(n.get("raw_tags") or []) + " " + " ".join(n.get("tags") or [])
                if "borrow" in tags.lower() or "loan" in tags.lower():
                    self.borrowed.add((parent_key, k))
            if n.get("descendants"):
                self.walk(k, n["descendants"])


def main():
    sys.setrecursionlimit(20000)
    g = Graph()
    # default: the per-language kaikki files. Pass a path to use the filtered
    # whole-dump extract instead (build/extract.py output).
    if len(sys.argv) > 1:
        files = [sys.argv[1]]
    else:
        files = sorted(glob.glob(os.path.join(DATA, "*.jsonl")))
    print("assembling from {} source(s)".format(len(files)))

    for path in files:
        n_entries = 0
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                code, word = e.get("lang_code"), e.get("word")
                if not code or not word:
                    continue
                k = g.note(code, word, e.get("lang"))
                g.has_entry.add(k)
                senses = e.get("senses") or []
                if senses and k not in g.gloss:
                    gl = senses[0].get("glosses") or []
                    if gl:
                        g.gloss[k] = gl[0]
                if e.get("descendants"):
                    g.walk(k, e["descendants"])
                n_entries += 1
        print("  {:<28} {:>7,} entries".format(os.path.basename(path), n_entries))

    # The filtered whole-dump extract carries no senses, so glosses live in a
    # sidecar. Stream it and keep only keys the graph actually contains, rather
    # than holding ten million gloss records in memory.
    gl_path = os.path.join(os.path.dirname(files[0]), "glosses.jsonl")
    if len(files) == 1 and os.path.exists(gl_path):
        hit = 0
        with io.open(gl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                k = key(r["c"], r["w"])
                if k in g.label and k not in g.gloss:
                    g.gloss[k] = r["g"]
                    hit += 1
        print("  glosses matched  {:,}".format(hit))

    # reverse index: child -> parents. This is the direction users search in.
    up = collections.defaultdict(set)
    down = collections.defaultdict(set)
    for p, c in g.edges:
        up[c].add(p)
        down[p].add(c)

    roots = [k for k in g.label if not up.get(k)]
    leaves = [k for k in g.label if not down.get(k)]
    multi = [k for k in up if len(up[k]) > 1]

    print("\n-- graph --")
    print("  nodes            {:,}".format(len(g.label)))
    print("  edges            {:,}".format(len(g.edges)))
    print("  with own entry   {:,}  ({:.0%})".format(
        len(g.has_entry), len(g.has_entry) / len(g.label)))
    print("  reference-only   {:,}".format(len(g.label) - len(g.has_entry)))
    print("  roots            {:,}".format(len(roots)))
    print("  leaves           {:,}".format(len(leaves)))
    print("  multi-parent     {:,}  <- proves DAG, not tree".format(len(multi)))
    print("  borrow-flagged   {:,}".format(len(g.borrowed)))

    langs = collections.Counter(v["lang_code"] for v in g.label.values())
    print("  languages        {:,}".format(len(langs)))
    print("\n-- top 15 languages by node count --")
    for c, n in langs.most_common(15):
        name = next((v["lang"] for v in g.label.values()
                     if v["lang_code"] == c and v["lang"]), "")
        print("  {:<14} {:<24} {:>7,}".format(c, name, n))

    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with io.open(os.path.join(OUT, "nodes.json"), "w", encoding="utf-8") as fh:
        json.dump({k: {**v, "gloss": g.gloss.get(k, ""), "entry": k in g.has_entry}
                   for k, v in g.label.items()}, fh, ensure_ascii=False)
    with io.open(os.path.join(OUT, "edges.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(g.edges), fh, ensure_ascii=False)
    # Borrowing is not descent. Sino-Japanese 学校 is loaned from Chinese, not
    # inherited from it, and drawing the two the same way misrepresents the history.
    with io.open(os.path.join(OUT, "borrowed.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(g.borrowed), fh, ensure_ascii=False)
    print("\nwrote nodes.json / edges.json to {}".format(OUT))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
