// Prove the shards are a lossless re-encoding of graph-web.json: rebuild
// every field from the shard files and compare. If reconstruction is exact,
// every chain QA certifies on the monolith is certified for the shards.
'use strict';
const fs = require('fs');
const zlib = require('zlib');

const ROOT = 'C:/Projects/etymology-tree-viz';
const D = '0123456789abcdefghijklmnopqrstuvwxyz';

const G = JSON.parse(fs.readFileSync(ROOT + '/web/graph-web.json', 'utf8'));
const meta = JSON.parse(fs.readFileSync(ROOT + '/shards/meta.json', 'utf8'));

// ---- monolith ----
const WORDS = (() => {
  const p = G.words.split('\n'), o = []; let v = '';
  for (const s of p) { const w = v.slice(0, D.indexOf(s[0])) + s.slice(1); o.push(w); v = w; }
  return o;
})();
const N = WORDS.length;
const WL = [];
for (const r of G.wrle.split(',')) {
  const c = r.indexOf(':');
  const l = parseInt(r.slice(0, c), 36), n = parseInt(r.slice(c + 1), 36);
  for (let j = 0; j < n; j++) WL.push(l);
}
const kb = Buffer.from(G.kinds, 'base64'), pb = Buffer.from(G.prim, 'base64'),
      ub = Buffer.from(G.unc, 'base64');
const MONO = new Map();          // p*N+c -> flags
let flat = 0;
for (const s of G.adj.split(';')) {
  const gt = s.indexOf('>');
  const p = parseInt(s.slice(0, gt), 36);
  for (const part of s.slice(gt + 1).split(',')) {
    const c = parseInt(part, 36);
    const k = (kb[flat >> 2] >> ((flat & 3) * 2)) & 3;
    const pr = (pb[flat >> 3] >> (flat & 7)) & 1;
    const un = (ub[flat >> 3] >> (flat & 7)) & 1;
    MONO.set(p * N + c, k | (pr << 2) | (un << 3));
    flat++;
  }
}
const GLOSS = new Map();
if (G.gids) {
  const ids = G.gids.split(',').map(x => parseInt(x, 36));
  const t = G.gtexts.split('\n');
  ids.forEach((id, i) => GLOSS.set(id, t[i]));
}

// ---- shards ----
if (meta.n !== N) { console.log('FAIL: N mismatch'); process.exit(1); }
const K = meta.k;
let bad = 0;
const SDOWN = new Map(), SUP = new Map();
let wordsOK = 0, langOK = 0, glossOK = 0, glossSeen = 0;
for (let s = 0; s < meta.shards; s++) {
  const sh = JSON.parse(zlib.gunzipSync(
    fs.readFileSync(ROOT + '/shards/s' + s + '.json.gz')).toString('utf8'));
  const lo = s * K;
  let v = '';
  const local = sh.w ? sh.w.split('\n') : [];
  local.forEach((line, j) => {
    const w = v.slice(0, D.indexOf(line[0])) + line.slice(1);
    v = w;
    if (w === WORDS[lo + j]) wordsOK++; else if (bad++ < 5)
      console.log('word mismatch', lo + j, JSON.stringify(w), JSON.stringify(WORDS[lo + j]));
  });
  let pos = lo;
  for (const r of (sh.l ? sh.l.split(',') : [])) {
    const c = r.indexOf(':');
    const l = parseInt(r.slice(0, c), 36), n = parseInt(r.slice(c + 1), 36);
    for (let j = 0; j < n; j++) {
      if (WL[pos] === l) langOK++; else if (bad++ < 5)
        console.log('lang mismatch at', pos);
      pos++;
    }
  }
  for (const chunk of (sh.d ? sh.d.split(';') : [])) {
    const gt = chunk.indexOf('>');
    const p = lo + parseInt(chunk.slice(0, gt), 36);
    for (const part of chunk.slice(gt + 1).split(',')) {
      const dot = part.lastIndexOf('.');
      const c = parseInt(part.slice(0, dot), 36);
      const f = parseInt(part.slice(dot + 1), 36);
      SDOWN.set(p * N + c, f);
    }
  }
  for (const chunk of (sh.u ? sh.u.split(';') : [])) {
    const gt = chunk.indexOf('>');
    const c = lo + parseInt(chunk.slice(0, gt), 36);
    for (const part of chunk.slice(gt + 1).split(',')) {
      const dot = part.lastIndexOf('.');
      const p = parseInt(part.slice(0, dot), 36);
      const f = parseInt(part.slice(dot + 1), 36);
      SUP.set(p * N + c, f);
    }
  }
  if (sh.g) {
    const ids = sh.g.split(','), ts = sh.gt.split('\n');
    ids.forEach((x, j) => {
      glossSeen++;
      if (GLOSS.get(lo + parseInt(x, 36)) === ts[j]) glossOK++;
      else if (bad++ < 5) console.log('gloss mismatch at', lo + parseInt(x, 36));
    });
  }
}

function mapsEqual(a, b, label) {
  if (a.size !== b.size) { console.log('FAIL', label, 'size', a.size, b.size); return false; }
  for (const [k2, v2] of a) if (b.get(k2) !== v2) { console.log('FAIL', label, 'at', k2); return false; }
  return true;
}
const downEq = mapsEqual(MONO, SDOWN, 'down');
const upEq = mapsEqual(MONO, SUP, 'up');
console.log('words', wordsOK === N ? 'OK' : 'MISMATCH ' + wordsOK + '/' + N);
console.log('langs', langOK === N ? 'OK' : 'MISMATCH');
console.log('edges down', downEq ? 'OK (' + SDOWN.size + ')' : 'FAIL');
console.log('edges up  ', upEq ? 'OK (' + SUP.size + ')' : 'FAIL');
console.log('glosses', glossOK === GLOSS.size && glossSeen === GLOSS.size
  ? 'OK (' + glossOK + ')' : 'MISMATCH ' + glossOK + '/' + GLOSS.size);
const ok = wordsOK === N && langOK === N && downEq && upEq &&
           glossOK === GLOSS.size;
console.log(ok ? 'RECONSTRUCTION EXACT' : 'RECONSTRUCTION BROKEN');
process.exit(ok ? 0 : 1);
