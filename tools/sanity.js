// Structural sanity check on the whole graph, aggregate not word-by-word.
// Walks every PRIMARY (displayed-chain) lineage edge and counts red flags that
// signal whole classes of error, with the worst examples per class:
//
//   1. cycles            a node that is its own ancestor (chains must be a DAG)
//   2. multi-primary     a node with >1 primary parent (page-walk must be one)
//   3. affix-ancestor    an affix used as a lineage parent (barred by design)
//   4. age inversion     inheritance/derivation flowing young -> old
//   5. semantic break    same-stage inh with zero gloss overlap (homograph tell)
//   6. merge magnets     nodes with the most incoming edges (over-merge tells)
//
//   node --max-old-space-size=6000 tools/sanity.js
'use strict';
const fs = require('fs');
const ROOT = 'C:/Projects/etymology-tree-viz';
const D = '0123456789abcdefghijklmnopqrstuvwxyz';
const G = JSON.parse(fs.readFileSync(ROOT + '/web/graph-web.json', 'utf8'));

const WORDS = (() => { const p = G.words.split('\n'), o = []; let v = '';
  for (const s of p) { const w = v.slice(0, D.indexOf(s[0])) + s.slice(1); o.push(w); v = w; } return o; })();
const N = WORDS.length, CODES = G.codes;
const WL = new Int32Array(N);
{ let pos = 0; for (const r of G.wrle.split(',')) { const c = r.indexOf(':');
  const l = parseInt(r.slice(0, c), 36), n = parseInt(r.slice(c + 1), 36);
  for (let j = 0; j < n; j++) WL[pos++] = l; } }
const GL = {};
{ const ids = G.gids ? G.gids.split(',').map(x => parseInt(x, 36)) : [];
  const t = G.gtexts ? G.gtexts.split('\n') : [];
  for (let i = 0; i < ids.length; i++) GL[ids[i]] = t[i]; }
// decode adjacency + kinds + primary bit
const DOWN = new Array(N), DOWNK = new Array(N), UPcount = new Int32Array(N);
const PRIMPARENT = new Int32Array(N).fill(-1);   // one primary parent per child
const primMulti = [];
const KN = ['inh', 'bor', 'root', 'd/f'];
{ const kb = Buffer.from(G.kinds, 'base64'), pb = G.prim ? Buffer.from(G.prim, 'base64') : null;
  let flat = 0;
  for (const s of G.adj.split(';')) { const gt = s.indexOf('>'); const p = parseInt(s.slice(0, gt), 36);
    const parts = s.slice(gt + 1).split(','), arr = [], ka = [];
    for (const part of parts) { const c = parseInt(part, 36);
      const k = (kb[flat >> 2] >> ((flat & 3) * 2)) & 3;
      arr.push(c); ka.push(k); UPcount[c]++;
      if (pb && (pb[flat >> 3] >> (flat & 7)) & 1) {
        if (PRIMPARENT[c] === -1) PRIMPARENT[c] = p; else primMulti.push(c);
      }
      flat++; }
    DOWN[p] = arr; DOWNK[p] = ka; } }

const code = i => CODES[WL[i]];
const lbl = i => (code(i).indexOf('-pro') > -1 ? '*' : '') + WORDS[i];
const key = i => code(i) + ':' + WORDS[i];
function kindOf(p, c){ const a = DOWN[p]||[], k = DOWNK[p]||[]; for (let j=0;j<a.length;j++) if (a[j]===c) return k[j]; return -1; }
const STOP = new Set(('the of and to a in is was be as it or an for with from by on at that this he she they we you i are were being been has have had not no more most very can will would there their his her its our your my one two three four five'.split(' ')));
function toks(g){ const o=new Set(); (g||'').toLowerCase().replace(/[^\p{L}]+/gu,' ').split(' ').forEach(w=>{if(w.length>2&&!STOP.has(w))o.add(w);}); return o; }
function script(w){ for (const ch of (w||'')) { const o=ch.codePointAt(0); if(o>64) return o>>8; } return 0; }
const isAffix = i => { const w=WORDS[i]; if(!w) return false; const a=w[0],z=w[w.length-1];
  if(a==='-'||a==='−') return true; return (z==='-'||z==='−') && code(i).indexOf('-pro')<0; };

// coarse language age tiers: 0 proto, 1 ancient, 2 medieval, 3 modern/unknown
const ANCIENT = new Set('la grc sa ang got non sga owl goh osx odt ofs orv cu xcl peo ae hit egy akk arc hbo ltc och ojp xlc xpr pal-old xhc phn xum osc xve xlu xbc sog otk oui txb txh xto xpg gmy grc-koi grc-dor grc-att grk-pro'.split(' '));
const MEDIEVAL = new Set('enm fro frm gmh gml dum pro odt gkm pal fa-cls ota zlw-ocs zlw-opl osp roa-opt gmq-oda mga owl-mid sga-mid la-med la-lat la-eme la-vul la-ecc xno frk goh gml odt'.split(' '));
function age(i){ const c=code(i); if(c.indexOf('-pro')>-1) return 0; if(ANCIENT.has(c)) return 1; if(MEDIEVAL.has(c)) return 2; return 3; }

// ---- walk primaries ----
let cycles=[], ageInv=[], semBreak=[], affixAnc=[];
const seenCycle = new Uint8Array(N);
for (let c=0;c<N;c++){
  const p = PRIMPARENT[c];
  if (p===-1) continue;
  if (isAffix(p) && code(p).indexOf('-pro')<0) affixAnc.push([p,c]);
  const k = kindOf(p,c);
  // age inversion: inheritance/derivation (0,3) must flow older->younger
  if ((k===0||k===3)) { const ap=age(p), ac=age(c); if (ap>ac) ageInv.push([p,c,ap,ac]); }
  // semantic break: inheritance within one language stage, both glossed, same
  // script, zero content overlap -> classic homograph mis-pick
  if (k===0){ const gp=GL[p], gc=GL[c];
    if (gp&&gc&&script(WORDS[p])===script(WORDS[c])){
      const tp=toks(gp), tc=toks(gc); let ov=0; tp.forEach(x=>{if(tc.has(x))ov++;});
      const wp=WORDS[p].replace(/[-−]/g,''), wc=WORDS[c].replace(/[-−]/g,'');
      const sharePfx = wp.slice(0,4)===wc.slice(0,4);
      if (ov===0 && tp.size>0 && tc.size>0 && !sharePfx) semBreak.push([p,c]);
    } }
}
// cycle detection over primary chains
for (let c=0;c<N;c++){
  if (seenCycle[c]) continue;
  const path=[]; const onpath=new Set(); let x=c, steps=0;
  while (x!==-1 && steps++<80){
    if (onpath.has(x)){ cycles.push(x); break; }
    onpath.add(x); path.push(x); x=PRIMPARENT[x];
  }
  path.forEach(n=>seenCycle[n]=1);
}
// merge magnets: highest incoming degree
const magnets=[]; for (let i=0;i<N;i++) if(UPcount[i]>=40) magnets.push([i,UPcount[i]]);
magnets.sort((a,b)=>b[1]-a[1]);

const nPrim = PRIMPARENT.reduce((s,p)=>s+(p!==-1?1:0),0);
function show(list, fmt, n){ list.slice(0,n||12).forEach(fmt); }
console.log('=== GRAPH SANITY (over ' + nPrim.toLocaleString() + ' primary lineage edges, ' + N.toLocaleString() + ' nodes) ===\n');

console.log('1. CYCLES (node is its own ancestor):        ' + cycles.length);
show(cycles.slice(0,6), c=>console.log('     '+key(c)));

console.log('\n2. MULTI-PRIMARY (>1 page-walk parent):       ' + primMulti.length);
show([...new Set(primMulti)].slice(0,6), c=>console.log('     '+key(c)));

console.log('\n3. AFFIX-AS-ANCESTOR (barred by design):      ' + affixAnc.length);
show(affixAnc, e=>console.log('     '+lbl(e[0])+'  ->  '+key(e[1])));

console.log('\n4. AGE INVERSIONS (inh/der young -> old):     ' + ageInv.length +
  '   (' + (ageInv.length/nPrim*100).toFixed(3) + '% of primaries)');
const TIER=['proto','ancient','medieval','modern'];
show(ageInv.sort((a,b)=>(b[2]-b[3])-(a[2]-a[3])), e=>console.log('     '+KN[kindOf(e[0],e[1])].padEnd(4)+' '+lbl(e[0])+' ('+TIER[e[2]]+') -> '+key(e[1])+' ('+TIER[e[3]]+')'));

console.log('\n5. SEMANTIC BREAKS (same-script inh, 0 gloss overlap, diff prefix): ' + semBreak.length +
  '   (' + (semBreak.length/nPrim*100).toFixed(3) + '%)');
show(semBreak, e=>console.log('     '+lbl(e[0])+' "'+(GL[e[0]]||'').slice(0,26)+'" -> '+key(e[1])+' "'+(GL[e[1]]||'').slice(0,26)+'"'));

console.log('\n6. MERGE MAGNETS (incoming degree >=40, top 15):');
show(magnets, e=>console.log('     '+String(e[1]).padStart(5)+'  '+key(e[0])+'  "'+(GL[e[0]]||'').slice(0,30)+'"'), 15);
