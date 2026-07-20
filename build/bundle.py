"""Inline trees.json into the template to produce a self-contained page."""
import io
import json
import os

WEB = r"C:\Projects\etymology-tree-viz\web"

tpl = io.open(os.path.join(WEB, "template.html"), encoding="utf-8").read()
import sys
TAG = "full" if "--full" in sys.argv else "web" if "--web" in sys.argv else None
data = io.open(os.path.join(WEB, "graph-{}.json".format(TAG) if TAG else "graph.json"),
               encoding="utf-8").read()

# Artifacts run under a CSP that blocks every external host, so the layout
# library is vendored at build time and inlined rather than fetched at runtime.
lib = io.open(os.path.join(WEB, "vendor", "d3-hierarchy.min.js"), encoding="utf-8").read()

# guard against breaking out of the <script> block
data = data.replace("</script", "<\\/script")
assert "/*__GRAPH__*/" in tpl, "graph placeholder missing"
assert "/*__D3__*/" in tpl, "library placeholder missing"
out = tpl.replace("/*__D3__*/", lib).replace("/*__GRAPH__*/", data)

dest = os.path.join(WEB, "index-{}.html".format(TAG) if TAG else "index.html")
io.open(dest, "w", encoding="utf-8").write(out)
print("wrote {}  ({:.0f} KB)".format(dest, os.path.getsize(dest) / 1024))
