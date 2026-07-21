"""Build the deployed shell: template + inline META + d3, nothing else.

The page boots instantly on META alone (codes, names, counts, search-bucket
bounds, starter words). Search fetches ~20 KB buckets as you type; opening a
word fetches only the range shards its tree touches, a few hundred KB. All
shard files have stable names and ride a ?v=<content-hash> query for cache
busting. Single-file builds from bundle.py are untouched."""
import glob
import io
import json
import os

WEB = r"C:\Projects\etymology-tree-viz\web"
ROOT = r"C:\Projects\etymology-tree-viz"

tpl = io.open(os.path.join(WEB, "template.html"), encoding="utf-8").read()
lib = io.open(os.path.join(WEB, "vendor", "d3-hierarchy.min.js"),
              encoding="utf-8").read()
meta = io.open(os.path.join(ROOT, "shards", "meta.json"),
               encoding="utf-8").read().replace("</script", "<\\/script")

for old in (glob.glob(os.path.join(ROOT, "graph-*.json.gz")) +
            glob.glob(os.path.join(ROOT, "gloss-*.json.gz"))):
    os.remove(old)

DATA = '<script id="data" type="application/json">/*__GRAPH__*/</script>'
assert DATA in tpl, "data placeholder missing"
out = (tpl
       .replace(DATA, "<script>window.__SHARDMETA__ = " + meta + ";</script>", 1)
       .replace("/*__D3__*/", lib, 1))

io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print("wrote index.html ({:.0f} KB shell, meta v{})".format(
    os.path.getsize(os.path.join(ROOT, "index.html")) / 1024,
    json.loads(io.open(os.path.join(ROOT, "shards", "meta.json"),
                       encoding="utf-8").read())["v"]))
