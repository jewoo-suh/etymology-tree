"""Pull complete raw wiktextract entries for specific words.

Used to answer: does Wiktionary record where Latin grammatica came from, and if
so, in a field we are not reading?
"""
import gzip
import io
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

SRC = r"C:\Projects\etymology-tree-viz\data\raw-wiktextract-data.jsonl.gz"

WANT = {
    ("la", "grammatica"), ("grc", "γραμματική"), ("grc", "γράμμα"),
    ("grc", "γράφω"), ("en", "grammar"), ("la", "natio"), ("la", "iustitia"),
}

found = {}
with gzip.open(SRC, "rt", encoding="utf-8") as fh:
    for line in fh:
        # cheap prefilter before paying for json.loads on 10.7M lines
        if '"word":' not in line:
            continue
        hit = False
        for _, w in WANT:
            if '"' + w + '"' in line:
                hit = True
                break
        if not hit:
            continue
        e = json.loads(line)
        key = (e.get("lang_code"), e.get("word"))
        if key in WANT and key not in found:
            found[key] = e
            print("found {} ({}/{})".format(key, len(found), len(WANT)), flush=True)
            if len(found) == len(WANT):
                break

sys.stdout.reconfigure(encoding="utf-8")
print("\n" + "=" * 70)
for key, e in found.items():
    print("\n### {}:{}".format(key[0], key[1]))
    print("  fields: {}".format(sorted(e.keys())))
    print("  has descendants: {}".format(bool(e.get("descendants"))))
    et = e.get("etymology_text") or ""
    print("  etymology_text: {}".format(et[:260]))
    tmpl = e.get("etymology_templates") or []
    print("  etymology_templates: {}".format(len(tmpl)))
    for t in tmpl[:8]:
        print("     {} {}".format(t.get("name"), json.dumps(t.get("args", {}), ensure_ascii=False)[:150]))

with io.open(r"C:\Projects\etymology-tree-viz\recon\entries.json", "w", encoding="utf-8") as fh:
    json.dump({":".join(k): v for k, v in found.items()}, fh, ensure_ascii=False, indent=1)
print("\nwrote recon/entries.json")
