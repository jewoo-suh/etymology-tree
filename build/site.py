"""Build the deployed site: a small shell that downloads the graph core once
(with a progress bar), boots the moment it lands so every word is instant, and
streams the definitions in behind.

Why load-once rather than per-word: this is a static site (GitHub Pages, no
backend), so it cannot compute one word's subtree server-side the way a
database-backed site does. Shipping the whole structural core once (~17 MB gz)
and holding it in memory is the standard client-side data-app pattern -- after
it lands, drawing any word's tree touches only memory, no network. The earlier
range-shard scheme made first paint instant but re-downloaded scattered data on
every word (tens of MB each); loading once is strictly cheaper overall.

Core = words + adjacency + kinds + flags (everything needed to draw any tree).
Gloss = the definitions, a third of the payload and needed only for the side
panel, so it streams after boot. Both carry a content hash for cache-busting.
The single-file builds from bundle.py stay self-contained for offline use.
"""
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


# clear stale assets (shards from the old scheme, previous core/gloss)
import shutil
for old in (glob.glob(os.path.join(ROOT, "graph-*.json.gz"))
            + glob.glob(os.path.join(ROOT, "gloss-*.json.gz"))):
    os.remove(old)
if os.path.isdir(os.path.join(ROOT, "shards")):
    shutil.rmtree(os.path.join(ROOT, "shards"))

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
  wrap.innerHTML = '<div>Loading the etymology graph (about __MB__ MB, once)' +
    '\\u2026</div>' +
    '<div style="width:min(420px,70vw);height:6px;border-radius:3px;' +
    'background:rgba(128,128,128,.25);overflow:hidden">' +
    '<div id="bootbar" style="width:0%;height:100%;' +
    'background:var(--accent,#e8b34b);transition:width .15s"></div></div>' +
    '<div id="boottxt" style="font-size:12px;opacity:.7"></div>';
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
  var glossReady = pull("__GLOSS__", __GLOSSLEN__, null);  // rides behind
  pull("__CORE__", __CORELEN__, function (got, total) {
    var pc = total ? Math.min(99, Math.round(got * 100 / total)) : 50;
    document.getElementById("bootbar").style.width = pc + "%";
    document.getElementById("boottxt").textContent =
      (got / 1048576).toFixed(1) + " of " + (total / 1048576).toFixed(1) +
      " MB";
  }).then(function (core) {
    document.getElementById("bootbar").style.width = "100%";
    document.getElementById("boottxt").textContent = "building\\u2026";
    return new Promise(function (res) { setTimeout(function () { res(core); }, 30); });
  }).then(function (core) {
    window.__GRAPH__ = core;
    window.__runapp();          // every word now instant, all in memory
    window.__GRAPH__ = null;
    wrap.remove();
    glossReady.then(function (gd) {
      if (window.__applyGloss) window.__applyGloss(gd);
    }).catch(function () { /* definitions are an extra, never a blocker */ });
  }).catch(function (e) {
    fail("Failed to load the graph (" + e.message + "). Refresh to retry, " +
         "or use the offline build from the GitHub release.");
  });
})();
</script>"""

LOADER = (LOADER
          .replace("__CORE__", core_name).replace("__CORELEN__", str(core_len))
          .replace("__GLOSS__", gloss_name).replace("__GLOSSLEN__", str(gloss_len))
          .replace("__MB__", "{:.0f}".format(core_len / 1048576)))

DATA = '<script id="data" type="application/json">/*__GRAPH__*/</script>'
assert DATA in tpl, "data placeholder missing"
assert "/*__D3__*/" in tpl, "d3 placeholder missing"
out = tpl.replace(DATA, LOADER, 1).replace("/*__D3__*/", lib, 1)

io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print("wrote index.html ({:.0f} KB shell)".format(
    os.path.getsize(os.path.join(ROOT, "index.html")) / 1024))
print("  core  {} ({:.1f} MB gz)".format(core_name, core_len / 1048576))
print("  gloss {} ({:.1f} MB gz)".format(gloss_name, gloss_len / 1048576))
