"""Build the deployed site as a small shell plus a gzipped graph asset.

The single-file pages (bundle.py) stay for offline use; the WEBSITE now
ships index.html (~0.3 MB) that fetches graph-web-<hash>.json.gz (~a
quarter of the raw JSON), shows a progress bar, and unpacks it in the
browser with DecompressionStream. The hash in the filename makes caching
safe: a rebuilt graph gets a new name, an unchanged one stays cached.
"""
import glob
import gzip
import hashlib
import io
import os

WEB = r"C:\Projects\etymology-tree-viz\web"
ROOT = r"C:\Projects\etymology-tree-viz"

tpl = io.open(os.path.join(WEB, "template.html"), encoding="utf-8").read()
lib = io.open(os.path.join(WEB, "vendor", "d3-hierarchy.min.js"),
              encoding="utf-8").read()
raw = io.open(os.path.join(WEB, "graph-web.json"), encoding="utf-8").read()

gz = gzip.compress(raw.encode("utf-8"), compresslevel=9, mtime=0)
h = hashlib.sha1(gz).hexdigest()[:10]
asset = "graph-web-{}.json.gz".format(h)

for old in glob.glob(os.path.join(ROOT, "graph-web-*.json.gz")):
    os.remove(old)
io.open(os.path.join(ROOT, asset), "wb").write(gz)

LOADER = """<script>
(function () {
  var wrap = document.createElement("div");
  wrap.id = "bootload";
  wrap.setAttribute("style", "position:fixed;inset:0;display:flex;" +
    "flex-direction:column;align-items:center;justify-content:center;" +
    "gap:14px;background:var(--canvas,#101014);color:var(--ink,#ddd);" +
    "font:15px/1.4 system-ui,sans-serif;z-index:99;text-align:center;" +
    "padding:0 16px;");
  wrap.innerHTML = '<div>Loading the etymology graph (__MB__ MB, cached ' +
    'after the first visit)\\u2026</div>' +
    '<div style="width:min(420px,70vw);height:6px;border-radius:3px;' +
    'background:rgba(128,128,128,.25);overflow:hidden">' +
    '<div id="bootbar" style="width:0%;height:100%;' +
    'background:var(--accent,#e8b34b);transition:width .15s"></div></div>' +
    '<div id="boottxt" style="font-size:12px;opacity:.7">0%</div>';
  document.body.appendChild(wrap);
  function fail(msg) { wrap.firstChild.textContent = msg; }
  if (!window.DecompressionStream) {
    fail("This browser cannot unpack the graph (it lacks " +
         "DecompressionStream). Any current Chrome, Edge, Firefox or " +
         "Safari will work; the offline build on the GitHub release " +
         "works everywhere.");
    return;
  }
  fetch("__ASSET__").then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    var total = +r.headers.get("Content-Length") || __GZBYTES__;
    var reader = r.body.getReader(), got = 0, parts = [];
    function pump() {
      return reader.read().then(function (s) {
        if (s.done) return null;
        parts.push(s.value);
        got += s.value.length;
        var pc = total ? Math.min(99, Math.round(got * 100 / total)) : 50;
        document.getElementById("bootbar").style.width = pc + "%";
        document.getElementById("boottxt").textContent =
          (got / 1048576).toFixed(1) + " MB of " +
          (total / 1048576).toFixed(1) + " MB";
        return pump();
      });
    }
    return pump().then(function () {
      document.getElementById("bootbar").style.width = "100%";
      document.getElementById("boottxt").textContent = "unpacking\\u2026";
      var ds = new Blob(parts).stream()
        .pipeThrough(new DecompressionStream("gzip"));
      return new Response(ds).text();
    });
  }).then(function (txt) {
    document.getElementById("boottxt").textContent =
      "building the graph\\u2026";
    return new Promise(function (res) {
      setTimeout(function () { res(txt); }, 30);
    });
  }).then(function (txt) {
    window.__GRAPH__ = JSON.parse(txt);
    txt = null;
    window.__boot();
    window.__GRAPH__ = null;
    wrap.remove();
  }).catch(function (e) {
    fail("Failed to load the graph (" + e.message + "). Refresh to " +
         "retry, or use the offline build from the GitHub release.");
  });
})();
</script>"""

LOADER = (LOADER
          .replace("__ASSET__", asset)
          .replace("__GZBYTES__", str(len(gz)))
          .replace("__MB__", "{:.0f}".format(len(gz) / 1048576)))

OLD_OPEN = ('<script id="data" type="application/json">/*__GRAPH__*/</script>\n'
            '<script>\n'
            '(function () {\n'
            '  "use strict";\n'
            '  var G = JSON.parse(document.getElementById("data").textContent);')
NEW_OPEN = (LOADER + '\n<script>\n'
            'window.__boot = function () {\n'
            '  "use strict";\n'
            '  var G = window.__GRAPH__;')
assert OLD_OPEN in tpl, "app opening anchor missing"
out = tpl.replace(OLD_OPEN, NEW_OPEN, 1).replace("/*__D3__*/", lib, 1)

tail = "})();\n</script>"
pos = out.rfind(tail)
assert pos > 0, "app closing anchor missing"
out = out[:pos] + "};\n</script>" + out[pos + len(tail):]

io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print("wrote index.html ({:.0f} KB) + {} ({:.1f} MB, raw {:.1f} MB)".format(
    os.path.getsize(os.path.join(ROOT, "index.html")) / 1024, asset,
    len(gz) / 1048576, len(raw.encode("utf-8")) / 1048576))
