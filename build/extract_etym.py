"""Second pass over the raw dump: harvest etymology_templates.

The first pass took Descendants sections, which record inheritance downward and
say nothing about borrowing. A borrowed word's ancestry lives on its own page --
Latin grammatica carries `root {la, ine-pro, *gerbʰ-}` and a calque template
pointing at Greek -- so building only from Descendants left every learned
Latinate and Greek word stranded with no parents.

wiktextract has already parsed these into structured args, so no prose parsing
is needed.
"""
import gzip
import io
import json
import os
import sys
import time

SRC = r"C:\Projects\etymology-tree-viz\data\raw-wiktextract-data.jsonl.gz"
OUT = r"C:\Projects\etymology-tree-viz\data\extract"

# templates that assert "this word came from that word"
WANTED = {
    "inh", "inherited", "der", "derived", "bor", "borrowed", "lbor",
    "learned borrowing", "slbor", "semi-learned borrowing", "obor",
    "orthographic borrowing", "calque", "cal", "partial calque", "psm",
    "semantic loan", "sl", "root", "etymon", "uder",
    # {{ety}} is Wiktionary's "etymology tree" template and carries the relation
    # in its second argument (:af, :inh, :bor, :der). Missing it left Latin
    # munitio with no ancestry at all, though the page states plainly that it is
    # mūniō + -tiō -- and the same for a great many Latin and Greek entries.
    "ety",
    # Word-formation: a word built inside its own language rather than handed
    # down from another. Skipping these left out 1,069,776 entries -- German
    # Antibabypille, and most of modern English, Finnish and Hungarian, which
    # build vocabulary by compounding rather than by borrowing it.
    "af", "affix", "compound", "com", "suffix", "suf", "prefix", "pre",
    "confix", "con", "blend", "univerbation",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    dest = os.path.join(OUT, "etym-templates.jsonl")
    fh_out = io.open(dest, "w", encoding="utf-8")

    n = kept = 0
    t0 = time.time()
    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            n += 1
            if '"etymology_templates"' not in line:
                continue
            e = json.loads(line)
            code, word = e.get("lang_code"), e.get("word")
            if not code or not word:
                continue
            tmpl = [t for t in (e.get("etymology_templates") or [])
                    if t.get("name") in WANTED]
            if not tmpl:
                continue
            fh_out.write(json.dumps(
                {"c": code, "w": word,
                 "t": [{"n": t.get("name"), "a": t.get("args", {})} for t in tmpl]},
                ensure_ascii=False) + "\n")
            kept += 1
            if n % 2000000 == 0:
                print("  {:>10,} lines   {:>8,} kept   {:.0f}s".format(
                    n, kept, time.time() - t0), flush=True)

    fh_out.close()
    print("\ndone in {:.0f}s".format(time.time() - t0))
    print("  lines read {:,}".format(n))
    print("  entries with usable templates {:,}".format(kept))
    print("  {:.1f} MB".format(os.path.getsize(dest) / 1048576))


if __name__ == "__main__":
    main()
