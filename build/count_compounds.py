"""How much vocabulary is missing because word-formation templates were skipped?

Compounds and affixed words have no ancestor in another language -- they are
built inside their own language -- so the ancestry-only rule leaves them out
entirely. German Antibabypille is Anti- + Baby + Pille and nothing else.
"""
import collections, gzip, io, json, os, sys, time

SRC = r"C:\Projects\etymology-tree-viz\data\raw-wiktextract-data.jsonl.gz"
FORMATION = {"af", "affix", "compound", "com", "suffix", "suf", "prefix", "pre",
             "confix", "con", "blend", "univerbation", "surf"}
ANCESTRY = {"inh", "inherited", "der", "derived", "uder", "bor", "borrowed",
            "lbor", "learned borrowing", "slbor", "obor", "calque", "cal",
            "partial calque", "psm", "semantic loan", "sl", "root", "etymon"}

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    n = only_form = both = neither = 0
    langs = collections.Counter()
    t0 = time.time()
    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            n += 1
            if '"etymology_templates"' not in line:
                continue
            e = json.loads(line)
            if not e.get("lang_code") or not e.get("word"):
                continue
            names = set(t.get("name") for t in (e.get("etymology_templates") or []))
            f, a = bool(names & FORMATION), bool(names & ANCESTRY)
            if f and not a:
                only_form += 1
                langs[e["lang_code"]] += 1
            elif f and a:
                both += 1
            elif not f and not a:
                neither += 1
            if n % 3000000 == 0:
                print("  {:>10,} lines  {:.0f}s".format(n, time.time() - t0), flush=True)
    print("\nlines read {:,}  in {:.0f}s".format(n, time.time() - t0))
    print("entries whose ONLY etymology is word-formation: {:,}".format(only_form))
    print("  (these are the ones currently missing entirely)")
    print("entries with both formation and ancestry       : {:,}".format(both))
    print("\ntop languages among the missing:")
    for c, v in langs.most_common(12):
        print("   {:<8} {:>8,}".format(c, v))

if __name__ == "__main__":
    main()
