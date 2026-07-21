"""Build the deployed site: a small shell, a core graph asset, and a
definitions asset that streams in after boot.

Definitions are a third of the raw payload and none are needed to draw a
tree, so the shell fetches the core (words, edges, kinds) with a progress
bar, boots as soon as it lands, and applies the glosses whenever their
file arrives. Both assets carry a content hash, so revisits are served
from the browser cache and a rebuilt graph gets fresh names. Single-file
pages from bundle.py stay for offline use."""
import glob
import gzip
import hashlib
import io
import json
import os

WEB = r"C:\Projects\etymology-tree-viz\web"
ROOT = r"C:\Projects\etymology-tree-viz"

tpl = io.open(os.path.join(WEB, "template.html"), encoding="utf-8").read()
lib = io.open(os.path.join(WEB, "vendor", "d3-hierarchy.min.js"),
              encoding="utf-8").read()
G = json.load(io.open(os.path.join(WEB, "graph-web.json"), encoding="utf-8"))

gloss = {"gids": G.pop("gids", ""), "gtexts": G.pop("gtexts", "")}


def pack(obj, stem):
    gz = gzip.compress(json.dumps(obj, ensure_ascii=False,
                                  separators=(",", ":")).encode("utf-8"),
                       compresslevel=9, mtime=0)
    name = "{}-{}.json.gz".format(stem, hashlib.sha1(gz).hexdigest()[:10])
    io.open(os.path.join(ROOT, name), "wb").write(gz)
    return name, len(gz)


for old in glob.glob(os.path.join(ROOT, "graph-*.json.gz")) + \
        glob.glob(os.path.join(ROOT, "gloss-*.json.gz")):
    os.remove(old)
core_name, core_len = pack(G, "graph-core")
gloss_name, gloss_len = pack(gloss, "gloss")

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
  function pull(url, expect, onpc) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
      var total = +r.headers.get("Content-Length") || expect;
      var reader = r.body.getReader(), got = 0, parts = [];
      function pump() {
        return reader.read().then(function (s) {
          if (s.done) return null;
          parts.push(s.value);
          got += s.value.length;
          if (onpc) onpc(got, total);
          return pump();
        });
      }
      return pump().then(function () {
        var ds = new Blob(parts).stream()
          .pipeThrough(new DecompressionStream("gzip"));
        return new Response(ds).text();
      }).then(function (t) { return JSON.parse(t); });
    });
  }
  // definitions ride behind; the page must not wait for them
  var glossReady = pull("__GLOSS__", __GLOSSLEN__, null);
  pull("__CORE__", __CORELEN__, function (got, total) {
    var pc = total ? Math.min(99, Math.round(got * 100 / total)) : 50;
    document.getElementById("bootbar").style.width = pc + "%";
    document.getElementById("boottxt").textContent =
      (got / 1048576).toFixed(1) + " MB of " +
      (total / 1048576).toFixed(1) + " MB";
  }).then(function (core) {
    document.getElementById("bootbar").style.width = "100%";
    document.getElementById("boottxt").textContent =
      "building the graph\\u2026";
    return new Promise(function (res) {
      setTimeout(function () { res(core); }, 30);
    });
  }).then(function (core) {
    window.__GRAPH__ = core;
    window.__boot();
    window.__GRAPH__ = null;
    wrap.remove();
    glossReady.then(function (gd) {
      if (window.__applyGloss) window.__applyGloss(gd);
    }).catch(function () { /* definitions are an extra, not a blocker */ });
  }).catch(function (e) {
    fail("Failed to load the graph (" + e.message + "). Refresh to " +
         "retry, or use the offline build from the GitHub release.");
  });
})();
</script>"""

LOADER = (LOADER
          .replace("__CORE__", core_name)
          .replace("__CORELEN__", str(core_len))
          .replace("__GLOSS__", gloss_name)
          .replace("__GLOSSLEN__", str(gloss_len))
          .replace("__MB__", "{:.0f}".format(core_len / 1048576)))

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
print("wrote index.html ({:.0f} KB)".format(
    os.path.getsize(os.path.join(ROOT, "index.html")) / 1024))
print("  core  {} ({:.1f} MB gz)".format(core_name, core_len / 1048576))
print("  gloss {} ({:.1f} MB gz)".format(gloss_name, gloss_len / 1048576))
