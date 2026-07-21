#!/usr/bin/env node
// Gold-standard QA for etymology chains. Run against any build:
//
//   node tools/qa.js web/graph-web.json
//
// Each test names steps a chain MUST contain and steps or gloss fragments it
// must NEVER contain. The forbidden lists encode every failure class found by
// auditing: wrong-lexeme bridges (star via "steer", sun via sin, eye via egg,
// day via dough, hound via hand, moon via lamentation, Korea via cabbage or
// Persephone), derivational padding (tothen, nighten, sugren, faderen), and
// sibling-relation gluing (grammar via glamour). A regression on any of these
// classes fails the run, so it cannot ship silently again.
'use strict';
const fs = require('fs');

const GRAPH = process.argv[2] || 'web/graph-web.json';

// ---- gold tests -----------------------------------------------------------
// must: every entry must appear in the chain (alternatives with |)
// banL: labels that must not appear (exact, defolded)
// banG: fragments that must not appear in any step's label or gloss
const TESTS = [
  { w: 'en:tooth', must: ['h₃dónts', 'tanþs', 'toþ'], banL: ['tothen'], banG: ['teethe'] },
  { w: 'en:day', must: ['dagaz'], banL: ['dag', 'daig'], banG: ['dough', 'childermasse'] },
  { w: 'en:night', must: ['nókʷts', 'niht'], banL: ['nighten', 'nahtāną'], banG: ['become night'] },
  { w: 'en:star', must: ['steorra'], banL: ['ster', 'stæger', 'staigraz'], banG: ['stair', 'steer'] },
  { w: 'en:sun', must: ['sunn'], banL: ['senn', 'synn', 'sunjō'], banG: ['transgression'] },
  { w: 'en:eye', must: ['aug'], banL: ['ieg', 'æg', 'ei', 'ajją'], banG: ['egg', 'island'] },
  { w: 'en:hound', must: ['hundaz'], banL: ['honde', 'hond'], banG: [] },
  { w: 'en:father', must: ['ph₂tḗr', 'fæder'], banL: ['faderen', 'fæderen', 'athair', 'ayr'], banG: [] },
  { w: 'en:moon', must: ['mēnô', 'mona'], banL: ['mainaz'], banG: ['lament', 'damaging'] },
  { w: 'en:water', must: ['wódr̥', 'wæter'], banL: [], banG: [] },
  { w: 'en:sugar', must: ['çucre|sucre'], banL: ['sugren'], banG: ['steer'] },
  { w: 'en:grammar', must: ['grammatica'], banL: ['glamour', 'glam', 'glēam'], banG: [] },
  { w: 'en:king', must: ['cyning'], banL: ['cennan', 'kenin'], banG: ['make known'] },
  { w: 'en:bread', must: [], banL: ['braidaz', 'brad'], banG: ['broad', 'roasted'] },
  { w: 'en:book', must: ['bōk|boc'], banL: [], banG: [] },
  { w: 'en:heart', must: ['hert|heort'], banL: ['heorot', 'herutaz'], banG: ['deer', 'stag'] },
  { w: 'en:wheel', must: ['kʷékʷlos|hwēol|hweol'], banL: ['whelen'], banG: [] },
  { w: 'en:carve', must: ['kerbaną'], banL: [], banG: [] },
  { w: 'en:teacher', must: ['teach'], banL: [], banG: [] },
  { w: 'en:ontology', must: ['ontologia'], banL: [], banG: [] },
  { w: 'la:munitio', must: ['munio', 'moene'], banL: [], banG: [] },
  { w: 'en:Korea', must: [], banL: ['kool', 'κόρη'], banG: ['cabbage', 'persephone', 'maiden'] },
  { w: 'de:Antibabypille', must: ['pille|baby'], banL: [], banG: [] },
  { w: 'de:Vater', must: ['fadēr'], banL: [], banG: [] },
  { w: 'fr:père', must: ['pater'], banL: [], banG: [] },
  { w: 'es:agua', must: ['aqua'], banL: [], banG: [] },
  { w: 'ru:вода', must: ['voda'], banL: [], banG: [] },
  { w: 'en:whisky', must: ['uisge|uisce'], banL: [], banG: [] },
  { w: 'en:name', must: ['h₁nómn̥|nama'], banL: [], banG: [] },
  { w: 'en:salt', must: ['salt'], banL: [], banG: [] },
  { w: 'en:communism', must: ['communisme', 'communis'], banL: [], banG: [] },
  { w: 'en:bear', must: ['bera'], banL: [], banG: ['pierce'] },
  { w: 'en:avocado', must: ['ahuacatl'], banL: ['ahuat', 'ahuacat'], banG: ['oak', 'acorn'] },
  { w: 'en:penguin', must: ['kʷennom'], banL: [], banG: [] },
  { w: 'en:robot', must: ['robota'], banL: [], banG: [] },
  { w: 'en:orange', must: ['نارنج'], banL: [], banG: [] },
  { w: 'en:ketchup', must: ['膎汁'], banL: [], banG: [] },
  { w: 'en:culture', must: ['cultura', 'colo'], banL: [], banG: [] },
  { w: 'en:create', must: ['creo'], banL: [], banG: [] },
  { w: 'en:concurrent', must: ['concurrens|concurrēns'], banL: [], banG: [] },
  { w: 'en:influence', must: ['influentia'], banL: [], banG: [] },
  { w: 'en:salary', must: ['salarium|salārium'], banL: [], banG: [] },
  { w: 'en:alcohol', must: ['guḫlum|كحل'], banL: [], banG: [] },
  { w: 'en:paradise', must: ['παράδεισος'], banL: [], banG: [] },
  { w: 'en:admiral', must: ['أمير|امير'], banL: [], banG: [] },
  { w: 'en:quarantine', must: ['quadraginta|quadrāgintā'], banL: ['quarentena'], banG: [] },
  { w: 'en:hazard', must: ['زهر'], banL: [], banG: [] },
  { w: 'en:magazine', must: ['مخزن|مَخْزَن'], banL: [], banG: [] },
  { w: 'en:karaoke', must: ['オーケストラ|orchestra'], banL: [], banG: [] },
  { w: 'en:zero', must: ['शून्य|صفر'], banL: [], banG: [] },
  { w: 'en:cipher', must: ['صفر|cifra'], banL: [], banG: [] },
];

// ---- decode (mirrors the page exactly) -------------------------------------
const G = JSON.parse(fs.readFileSync(GRAPH, 'utf8'));
const D = '0123456789abcdefghijklmnopqrstuvwxyz';
const WORDS = (() => {
  const p = G.words.split('\n'), o = new Array(p.length);
  let v = '';
  for (let i = 0; i < p.length; i++) {
    const s = p[i];
    const w = v.slice(0, D.indexOf(s[0])) + s.slice(1);
    o[i] = w; v = w;
  }
  return o;
})();
const N = WORDS.length, CODES = G.codes;
const WLANG = new Uint16Array(N);
{
  let pos = 0;
  for (const s of G.wrle.split(',')) {
    const c = s.indexOf(':');
    const l = parseInt(s.slice(0, c), 36), n = parseInt(s.slice(c + 1), 36);
    for (let j = 0; j < n; j++) WLANG[pos++] = l;
  }
}
const GLOSS = {};
{
  const ids = G.gids ? G.gids.split(',').map(x => parseInt(x, 36)) : [];
  const t = G.gtexts ? G.gtexts.split('\n') : [];
  for (let i = 0; i < ids.length; i++) GLOSS[ids[i]] = t[i];
}
const DOWN = new Array(N), DOWNK = new Array(N), UP = new Array(N), UPK = new Array(N);
const PRIM = new Set();
const PRIMPAR = new Array(N);
{
  const bin = Buffer.from(G.kinds, 'base64');
  const pb = G.prim ? Buffer.from(G.prim, 'base64') : null;
  let flat = 0;
  for (const s of G.adj.split(';')) {
    const gt = s.indexOf('>');
    const p = parseInt(s.slice(0, gt), 36);
    const parts = s.slice(gt + 1).split(',');
    const arr = [], ka = [];
    for (let j = 0; j < parts.length; j++) {
      const c = parseInt(parts[j], 36);
      const k = (bin[flat >> 2] >> ((flat & 3) * 2)) & 3;
      arr.push(c); ka.push(k);
      (UP[c] || (UP[c] = [])).push(p);
      (UPK[c] || (UPK[c] = [])).push(k);
      if (pb && (pb[flat >> 3] >> (flat & 7)) & 1) {
        PRIM.add(p * N + c);
        (PRIMPAR[c] || (PRIMPAR[c] = [])).push(p);
      }
      flat++;
    }
    DOWN[p] = arr; DOWNK[p] = ka;
  }
}
const code = id => CODES[WLANG[id]];
const isRecon = id => code(id).indexOf('-pro') > -1;
const isBare = id => WORDS[id].endsWith('-') || WORDS[id].endsWith('−');
const isAffix = id => {
  const w = WORDS[id];
  if (!w) return false;
  const a = w.charAt(0), z = w.charAt(w.length - 1);
  if (a === '-' || a === '−') return true;
  return (z === '-' || z === '−') && !isRecon(id);
};
const lbl = id => (isRecon(id) ? '*' : '') + WORDS[id];
const KEY = {};
const ALLIDS = {};
for (let i = 0; i < N; i++) {
  const k = code(i) + ':' + WORDS[i];
  if (KEY[k] === undefined) KEY[k] = i;
  (ALLIDS[k] = ALLIDS[k] || []).push(i);
}

// ---- the page's climb ------------------------------------------------------
const rc = {};
function reachCount(id) {
  if (rc[id] !== undefined) return rc[id];
  const seen = { [id]: 1 }, q = [id];
  let i = 0;
  while (i < q.length && q.length < 20000) {
    for (const c of (DOWN[q[i]] || [])) if (!seen[c]) { seen[c] = 1; q.push(c); }
    i++;
  }
  return (rc[id] = q.length - 1);
}
function ancestorsVia(id, allow) {
  const parentOf = {}, depth = { [id]: 0 }, q = [id];
  for (let i = 0; i < q.length; i++) {
    const cur = q[i], ps = UP[cur] || [], ks = UPK[cur] || [];
    for (let j = 0; j < ps.length; j++) {
      if (!allow[ks[j]]) continue;
      const p = ps[j];
      if (isAffix(p) || depth[p] !== undefined || !primOK(p, cur, ks[j])) continue;
      depth[p] = depth[cur] + 1; parentOf[p] = cur; q.push(p);
    }
  }
  return { parentOf, depth };
}
function bestRoute(root, id, allow, inSet) {
  const memo = {}, onS = {};
  function best(cur) {
    if (cur === id) return { cost: 0, route: [id] };
    if (memo[cur] !== undefined) return memo[cur];
    if (onS[cur]) return null;
    onS[cur] = 1;
    const ks = DOWN[cur] || [], kk = DOWNK[cur] || [];
    let f = null;
    for (let i = 0; i < ks.length; i++) {
      const c = ks[i];
      if (!allow[kk[i]] || inSet[c] === undefined || isAffix(c) ||
          !primOK(cur, c, kk[i])) continue;
      const s2 = best(c);
      if (!s2) continue;
      const cost = s2.cost + (kk[i] === 3 ? 1 : kk[i] === 2 ? 2 : 0) +
        (code(cur) === code(c) ? 1 : 0);
      if (!f || cost < f.cost ||
          (cost === f.cost && s2.route.length + 1 > f.route.length))
        f = { cost, route: [cur].concat(s2.route) };
    }
    delete onS[cur];
    memo[cur] = f;
    return memo[cur];
  }
  const got = best(root);
  return got ? got.route : null;
}
function topmost(cands, allow) {
  if (cands.length < 2) return cands[0];
  const score = {};
  cands.forEach(c => score[c] = 0);
  for (const b of cands) {
    const seen = { [b]: 1 }, q = [b];
    for (let i = 0; i < q.length && q.length < 4000; i++) {
      const cur = q[i], ps = UP[cur] || [], ks = UPK[cur] || [];
      for (let j = 0; j < ps.length; j++) {
        if (!allow[ks[j]]) continue;
        const p = ps[j];
        if (isAffix(p) || seen[p] || !primOK(p, cur, ks[j])) continue;
        seen[p] = 1; q.push(p);
        if (score[p] !== undefined) score[p]++;
      }
    }
  }
  let b0 = cands[0];
  for (const c of cands) if (score[c] > score[b0]) b0 = c;
  return b0;
}
function extendUp(route) {
  const seen = {};
  route.forEach(x => seen[x] = 1);
  for (let s = 0; s < 6; s++) {
    const top = route[0], ps = UP[top] || [];
    let best = -1, bn = -1;
    for (const p of ps) {
      if (seen[p] || isAffix(p) || !isRecon(p) || !isBare(p) ||
          !primOK(p, top, kindNum(p, top))) continue;
      const n = reachCount(p);
      if (n > bn) { bn = n; best = p; }
    }
    if (best < 0) break;
    seen[best] = 1; route.unshift(best);
  }
  return route;
}
function passWith(id, allow, allowBare) {
  const r = ancestorsVia(id, allow);
  const cands = [];
  for (let k in r.depth) {
    k = +k;
    if (k !== id && isRecon(k) && (allowBare || !isBare(k))) cands.push(k);
  }
  if (!cands.length) return null;
  const root = topmost(cands, allow);
  let route = bestRoute(root, id, allow, r.depth);
  if (!route) {
    route = [];
    let cur = root;
    while (cur !== id) { route.push(cur); cur = r.parentOf[cur]; }
    route.push(id);
  }
  return { root, route };
}
const WAVES = [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 0, 1], [1, 1, 1, 1]];
function climbWaves(id) {
  for (const w of WAVES) {
    const g = passWith(id, w, false);
    if (g) { g.route = extendUp(g.route); return g; }
  }
  const b = passWith(id, [1, 1, 1, 1], true);
  if (b) { b.route = extendUp(b.route); return b; }
  const r = ancestorsVia(id, [1, 1, 1, 1]);
  let best = -1, bd = -1;
  for (let k in r.depth) {
    k = +k;
    if (k !== id && r.depth[k] > bd) { bd = r.depth[k]; best = k; }
  }
  if (best < 0) return null;
  const route = [];
  let cur = best;
  while (cur !== id) { route.push(cur); cur = r.parentOf[cur]; }
  route.push(id);
  return { root: best, route };
}
/* Where a word's own page names its parent, exploration may only enter it
   that way: es:aguacate cites Classical Nahuatl ahuacatl, and a stray
   descendants edge from Pipil ahuacat (ahuat "oak" + -cat on its own page)
   must not carry the climb into the oak lineage. */
function primOK(par, child, k) {
  const pp = PRIMPAR[child];
  if (!pp) return true;
  if (pp.indexOf(par) > -1) return true;
  // a dead-end primary releases the other parents -- lineage ones only,
  // never formation parts (kind 3)
  if (pp.some(x => (UP[x] || []).length)) return false;
  return k !== 3 || code(par) !== code(child);
}
function kindNum(p, c) {
  const a = DOWN[p] || [], k = DOWNK[p] || [];
  for (let i = 0; i < a.length; i++) if (a[i] === c) return k[i];
  return 0;
}
function pageChain(id) {
  const route = [id], seen = { [id]: 1 };
  let cur = id;
  for (let step = 0; step < 30; step++) {
    const ps = UP[cur] || [];
    let next = -1;
    for (const q of ps) {
      if (!PRIM.has(q * N + cur) || seen[q] || isAffix(q)) continue;
      next = q;
      break;
    }
    if (next < 0) break;
    seen[next] = 1; route.unshift(next); cur = next;
  }
  return route;
}
// ---- the page's tree build + path overwrite --------------------------------
// The chain a user actually reads is the drawn tree's lit path, which can
// differ from climb(): transitive reduction shapes the tree, and the chain bar
// is rewritten to match the drawing. QA must judge the displayed route --
// testing climb() alone is how *whelen slipped through while the logic looked
// clean.
const caches = [{}, {}];
function reachSet(id, limit, wr) {
  const c = caches[wr ? 1 : 0];
  if (c[id]) return c[id];
  const seen = { [id]: 1 }, q = [id];
  let i = 0;
  while (i < q.length && q.length < limit) {
    const ks = DOWN[q[i]] || [], kk = DOWNK[q[i]] || [];
    i++;
    for (let j = 0; j < ks.length; j++) {
      if (kk[j] === 2 && !wr) continue;
      const x = ks[j];
      if (!seen[x]) { seen[x] = 1; q.push(x); }
    }
  }
  c[id] = seen;
  return seen;
}
function directChildren(id, chainSet) {
  const ks = DOWN[id] || [], kk = DOWNK[id] || [], out = [];
  for (let i = 0; i < ks.length; i++) {
    if (isAffix(ks[i])) continue;
    out.push([ks[i], kk[i]]);
  }
  if (out.length < 3) return out;
  const sets = out.map(e => reachSet(e[0], 2500, true));
  const keep = [];
  for (let a = 0; a < out.length; a++) {
    if (chainSet.has(id * N + out[a][0])) { keep.push(out[a]); continue; }
    let sh = false;
    for (let b = 0; b < out.length && !sh; b++)
      if (a !== b && sets[b][out[a][0]]) sh = true;
    if (!sh) keep.push(out[a]);
  }
  return keep.length ? keep : out;
}
function buildTree(rootId, route) {
  let budget = 5000;
  const onStack = {};
  const chainSet = new Set();
  for (let ci = 0; ci + 1 < route.length; ci++)
    chainSet.add(route[ci] * N + route[ci + 1]);
  function rec(id, depth, parentOn) {
    budget--;
    const on = parentOn && depth < route.length && route[depth] === id;
    const out = { id, path: on, children: [] };
    if (depth >= 12) return out;
    onStack[id] = 1;
    for (const [c] of directChildren(id, chainSet)) {
      if (onStack[c]) continue;
      const cOn = on && depth + 1 < route.length && route[depth + 1] === c;
      if (budget <= 0 && !cOn) continue;
      out.children.push(rec(c, depth + 1, on));
    }
    delete onStack[id];
    return out;
  }
  return rec(rootId, 0, true);
}
function pathInTree(tree, id, want) {
  let best = null, bestScore = -1;
  (function walk(n, trail) {
    const t = trail.concat([n]);
    if (n.id === id) {
      let score = 0;
      for (const x of t) if (want[x.id]) score++;
      if (score > bestScore || (score === bestScore && best && t.length < best.length)) {
        bestScore = score;
        best = t;
      }
      return;
    }
    for (const ch of n.children) walk(ch, t);
  })(tree, []);
  return best;
}
function displayedRoute(id) {
  const c = climb(id);
  if (!c) return [id];
  let route = c.route;
  const tree = buildTree(route[0], route);
  const want = {};
  route.forEach(x => want[x] = 1);
  const drawn = pathInTree(tree, id, want);
  if (drawn) route = drawn.map(nd => nd.id);
  return route;
}

function climb(id) {
  let walk = pageChain(id);
  if (walk.length > 1) {
    const ext = climbWaves(walk[0]);
    if (ext && ext.route.length > 1) walk = ext.route.slice(0, -1).concat(walk);
    else {
      let rescued = false;
      for (let i = 1; i < walk.length && i <= 4 && !rescued; i++) {
        const e2 = climbWaves(walk[i]);
        if (e2 && e2.route.length > i + 1 &&
            kindNum(e2.route[e2.route.length - 2], walk[i]) !== 2) {
          walk = e2.route.slice(0, -1).concat(walk.slice(i));
          rescued = true;
        }
      }
      if (!rescued) walk = extendUp(walk);
    }
    return { root: walk[0], route: walk };
  }
  return climbWaves(id);
}

// ---- run --------------------------------------------------------------------
const defold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
function judge(t, route) {
  const labels = route.map(x => defold(lbl(x)).replace(/^\*/, ''));
  const exact = route.map(x => defold(lbl(x)));
  const texts = route.map(x => defold(lbl(x)) + ' ' + defold(GLOSS[x] || ''));
  const probs = [];
  for (const m of t.must) {
    const alts = m.split('|').map(a => defold(a).replace(/^\*/, ''));
    if (!labels.some(L => alts.some(a => L.includes(a))))
      probs.push('missing required "' + m + '"');
  }
  for (const b of t.banL) {
    const bb = defold(b);
    if (exact.some(L => L === bb))
      probs.push('contains forbidden step "' + b + '"');
  }
  for (const b of t.banG) {
    const bb = defold(b);
    if (texts.some(T => T.includes(bb)))
      probs.push('touches forbidden lexeme "' + b + '"');
  }
  return probs;
}
let pass = 0, fail = 0;
const failures = [];
for (const t of TESTS) {
  const ids = ALLIDS[t.w] || [];
  const id = ids[0];
  if (id === undefined) {
    // budget slices may lack a word entirely; that is a capacity limit, not a
    // falsehood, and only counts as failure without --allow-absent
    if (process.argv.includes('--allow-absent')) {
      console.log('  skip ' + t.w + ' (absent from this slice)');
    } else {
      failures.push(t.w + ': ABSENT from build');
      fail++;
    }
    continue;
  }
  /* Homographs: the intended sense may sit at any position, and slice
     builds can even reorder them. A test passes if any sense's displayed
     chain satisfies it, and the reported chain is the best attempt. */
  let route = null, probsBest = null;
  for (const cand of ids) {
    const r2 = displayedRoute(cand);
    const pr = judge(t, r2);
    if (!pr.length) { route = r2; probsBest = pr; break; }
    if (!probsBest || pr.length < probsBest.length) { route = r2; probsBest = pr; }
  }
  // must-matching strips the asterisk (a required 'dagaz' may arrive as
  // *dagaz); exact bans keep it, so banning attested "dag" (the dough entry)
  // does not also ban the legitimate proto *dag
  const probs = probsBest;
  if (probs.length) {
    fail++;
    failures.push(t.w + ': ' + probs.join('; ') + '\n      chain: ' +
      route.map(x => lbl(x)).join(' → '));
  } else {
    pass++;
  }
}
console.log('QA against ' + GRAPH);
console.log('  ' + pass + ' passed, ' + fail + ' failed of ' + TESTS.length);
for (const f of failures) console.log('  FAIL ' + f);
process.exit(fail ? 1 : 0);
