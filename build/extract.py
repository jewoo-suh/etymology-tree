"""One streaming pass over the 23GB raw wiktextract dump.

Keeps only what the graph needs:
  * every entry carrying a `descendants` tree (these are the ancestry edges)
  * a slim gloss record for every other entry, so attested words can be labelled
    and searched even when they are only referenced from someone else's tree

Writing two files avoids ever holding the dump in memory.
"""
import gzip
import io
import json
import os
import sys
import time

SRC = r"C:\Projects\etymology-tree-viz\data\raw-wiktextract-data.jsonl.gz"
OUT = r"C:\Projects\etymology-tree-viz\data\extract"

KEEP = ("word", "lang", "lang_code", "descendants", "etymology_text")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    f_desc = io.open(os.path.join(OUT, "with-descendants.jsonl"), "w", encoding="utf-8")
    f_gloss = io.open(os.path.join(OUT, "glosses.jsonl"), "w", encoding="utf-8")

    n = n_desc = n_gloss = bad = 0
    t0 = time.time()
    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            n += 1
            try:
                e = json.loads(line)
            except ValueError:
                bad += 1
                continue
            code, word = e.get("lang_code"), e.get("word")
            if not code or not word:
                continue

            if e.get("descendants"):
                rec = {k: e[k] for k in KEEP if k in e}
                f_desc.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_desc += 1

            senses = e.get("senses") or []
            gloss = ""
            for s in senses:
                gl = s.get("glosses") or []
                if gl:
                    gloss = gl[0]
                    break
            if gloss:
                f_gloss.write(json.dumps(
                    {"c": code, "w": word, "g": gloss[:90]}, ensure_ascii=False) + "\n")
                n_gloss += 1

            if n % 1000000 == 0:
                print("  {:>9,} lines   {:>7,} with descendants   {:.0f}s".format(
                    n, n_desc, time.time() - t0), flush=True)

    f_desc.close()
    f_gloss.close()
    print("\ndone in {:.0f}s".format(time.time() - t0))
    print("  lines read        {:,}".format(n))
    print("  with descendants  {:,}".format(n_desc))
    print("  gloss records     {:,}".format(n_gloss))
    print("  unparseable       {:,}".format(bad))
    for name in ("with-descendants.jsonl", "glosses.jsonl"):
        p = os.path.join(OUT, name)
        print("  {:<26} {:>8.1f} MB".format(name, os.path.getsize(p) / 1048576))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
