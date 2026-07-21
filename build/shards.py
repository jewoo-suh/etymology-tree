"""Cut the web graph into range shards + search buckets for on-demand loading.

The deployed site then fetches ~200 KB of meta up front and only the shards a
word's tree actually touches (a few hundred KB), instead of the whole graph.
Filenames are stable; meta.v (content hash) rides as a ?v= query for cache
busting, so rebuilds do not rename a thousand files.

Every shard is a lossless re-encoding: tools/shardcheck.js rebuilds the
monolith from the shards and compares field by field, so the route logic that
QA certifies on the monolith is certified for the shards too.
"""
import base64
import collections
import gzip
import hashlib
import io
import json
import os
import shutil
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_graph import frontcode  # the exact encoder the monolith uses

WEB = r"C:\Projects\etymology-tree-viz\web"
ROOT = r"C:\Projects\etymology-tree-viz"
OUT = os.path.join(ROOT, "shards")
K = 4096          # nodes per shard

D36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def b36(n):
    if n == 0:
        return "0"
    s = ""
    while n:
        s = D36[n % 36] + s
        n //= 36
    return s


def defold(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(ch)).lower()


G = json.load(io.open(os.path.join(WEB, "graph-web.json"), encoding="utf-8"))

# ---- decode the monolith ---------------------------------------------------
words = []
prev = b""
# prefix digits count UTF-16 code units (the browser slices UTF-16), so the
# decode must slice UTF-16 bytes too or every astral-script word corrupts
for line in G["words"].split("\n"):
    cur = prev[:D36.index(line[0]) * 2] + line[1:].encode("utf-16-le")
    words.append(cur.decode("utf-16-le"))
    prev = cur
N = len(words)

wlang = []
for run in G["wrle"].split(","):
    c = run.index(":")
    lang, num = int(run[:c], 36), int(run[c + 1:], 36)
    wlang.extend([lang] * num)
assert len(wlang) == N

kind_bits = base64.b64decode(G["kinds"])
prim_bits = base64.b64decode(G["prim"])
unc_bits = base64.b64decode(G["unc"])

DOWN = [None] * N
flat = 0
for chunk in G["adj"].split(";"):
    gt = chunk.index(">")
    p = int(chunk[:gt], 36)
    lst = []
    for part in chunk[gt + 1:].split(","):
        c = int(part, 36)
        k = (kind_bits[flat >> 2] >> ((flat & 3) * 2)) & 3
        pr = (prim_bits[flat >> 3] >> (flat & 7)) & 1
        un = (unc_bits[flat >> 3] >> (flat & 7)) & 1
        lst.append((c, k | (pr << 2) | (un << 3)))
        flat += 1
    DOWN[p] = lst

UP = collections.defaultdict(list)
for p in range(N):
    if DOWN[p]:
        for c, f in DOWN[p]:
            UP[c].append((p, f))

gids = [int(x, 36) for x in G["gids"].split(",")] if G.get("gids") else []
gtexts = G["gtexts"].split("\n") if G.get("gtexts") else []
gloss = dict(zip(gids, gtexts))

# ---- precomputed reach for bare reconstructed roots ------------------------
# extendUp picks among bare proto roots by descendant count, a 20k-capped BFS
# that would drag a hundred shards into every climb; shipping the exact count
# (same BFS, same cap, same order) lets the lazy page skip the sweep.
def is_bare_recon(i):
    w = words[i]
    return (w.endswith("-") or w.endswith("−")) and \
        "-pro" in G["codes"][wlang[i]]


REACH = {}
for i in range(N):
    if not is_bare_recon(i):
        continue
    seen = {i}
    q = [i]
    qi = 0
    while qi < len(q) and len(q) < 20000:
        node = q[qi]
        qi += 1
        if DOWN[node]:
            for c, _f in DOWN[node]:
                if c not in seen:
                    seen.add(c)
                    q.append(c)
    REACH[i] = len(q) - 1
print("bare-recon reach precomputed: {:,}".format(len(REACH)))

# ---- emit shards -----------------------------------------------------------
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

n_shards = (N + K - 1) // K
manifest = hashlib.sha1()
total = 0
for s in range(n_shards):
    lo, hi = s * K, min(N, (s + 1) * K)
    shard_words = frontcode(words[lo:hi])
    runs, cur, cnt = [], None, 0
    for i in range(lo, hi):
        if wlang[i] == cur:
            cnt += 1
        else:
            if cur is not None:
                runs.append(b36(cur) + ":" + b36(cnt))
            cur, cnt = wlang[i], 1
    if cur is not None:
        runs.append(b36(cur) + ":" + b36(cnt))
    down_parts = []
    for i in range(lo, hi):
        if DOWN[i]:
            down_parts.append(b36(i - lo) + ">" +
                              ",".join(b36(c) + "." + D36[f]
                                       for c, f in DOWN[i]))
    up_parts = []
    for i in range(lo, hi):
        ups = UP.get(i)
        if ups:
            up_parts.append(b36(i - lo) + ">" +
                            ",".join(b36(p) + "." + D36[f]
                                     for p, f in ups))
    gl_ids, gl_txt = [], []
    for i in range(lo, hi):
        g = gloss.get(i)
        if g:
            gl_ids.append(b36(i - lo))
            gl_txt.append(g)
    r_parts = []
    for i in range(lo, hi):
        if i in REACH:
            r_parts.append(b36(i - lo) + "." + b36(REACH[i]))
    shard = {"w": shard_words, "l": ",".join(runs),
             "d": ";".join(down_parts), "u": ";".join(up_parts),
             "g": ",".join(gl_ids), "gt": "\n".join(gl_txt),
             "r": ",".join(r_parts)}
    payload = gzip.compress(json.dumps(shard, ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8"),
                            compresslevel=9, mtime=0)
    manifest.update(payload)
    total += len(payload)
    io.open(os.path.join(OUT, "s{}.json.gz".format(s)), "wb").write(payload)

# ---- search buckets --------------------------------------------------------
entries = sorted(range(N), key=lambda i: (defold(words[i]), i))
BUCKET = 3000
bounds = []
n_buckets = 0
btotal = 0
for b in range(0, len(entries), BUCKET):
    ids = entries[b:b + BUCKET]
    bounds.append(defold(words[ids[0]]))
    bucket = {"w": "\n".join(words[i] for i in ids),
              "l": ",".join(b36(wlang[i]) for i in ids),
              "i": ",".join(b36(i) for i in ids),
              "d": ",".join(b36(min(1295, len(DOWN[i] or []) +
                                    len(UP.get(i) or []))) for i in ids)}
    payload = gzip.compress(json.dumps(bucket, ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8"),
                            compresslevel=9, mtime=0)
    manifest.update(payload)
    btotal += len(payload)
    io.open(os.path.join(OUT, "q{}.json.gz".format(n_buckets)),
            "wb").write(payload)
    n_buckets += 1

# ---- starters + meta -------------------------------------------------------
STARTERS = ["en:father", "en:water", "en:night", "en:star", "en:wheel",
            "la:pater", "grc:πατήρ", "sa:पितृ", "ru:вода", "hy:հայր",
            "ga:athair", "is:hjarta", "cy:mam", "sq:natë"]
keyidx = {}
for i in range(N):
    k2 = "{}:{}".format(G["codes"][wlang[i]], words[i])
    if k2 not in keyidx:
        keyidx[k2] = i
starters = [[k2, keyidx[k2]] for k2 in STARTERS if k2 in keyidx]

meta = {"v": manifest.hexdigest()[:10], "n": N, "k": K,
        "shards": n_shards, "buckets": n_buckets, "bounds": bounds,
        "codes": G["codes"], "names": G["names"], "starters": starters}
io.open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8").write(
    json.dumps(meta, ensure_ascii=False, separators=(",", ":")))

print("shards: {} ({:.1f} MB gz)   buckets: {} ({:.1f} MB gz)".format(
    n_shards, total / 1048576, n_buckets, btotal / 1048576))
print("meta: {:.0f} KB   version {}".format(
    os.path.getsize(os.path.join(OUT, "meta.json")) / 1024, meta["v"]))
