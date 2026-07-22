// Crypto-random word sampler for QA rounds: uniform over web-build nodes
// that have at least one parent (a chain exists to check), excluding
// everything in the ledger. Prints lang:word keys and appends them to the
// ledger so no round repeats a word.
'use strict';
const fs = require('fs');
const crypto = require('crypto');

const ROOT = 'C:/Projects/etymology-tree-viz';
const LEDGER = ROOT + '/tools/checked_words.txt';
const N_PICK = parseInt(process.argv[2] || '20', 10);

const D = '0123456789abcdefghijklmnopqrstuvwxyz';
const G = JSON.parse(fs.readFileSync(ROOT + '/web/graph-web.json', 'utf8'));
const WORDS = (() => {
  const p = G.words.split('\n'), o = []; let v = '';
  for (const s of p) { const w = v.slice(0, D.indexOf(s[0])) + s.slice(1); o.push(w); v = w; }
  return o;
})();
const N = WORDS.length;
const WL = [];
{
  let pos = 0;
  for (const r of G.wrle.split(',')) {
    const c = r.indexOf(':');
    const l = parseInt(r.slice(0, c), 36), n = parseInt(r.slice(c + 1), 36);
    for (let j = 0; j < n; j++) WL[pos++] = l;
  }
}
const hasUp = new Uint8Array(N);
for (const s of G.adj.split(';')) {
  const gt = s.indexOf('>');
  for (const part of s.slice(gt + 1).split(',')) hasUp[parseInt(part, 36)] = 1;
}

const ledger = new Set(
  fs.existsSync(LEDGER)
    ? fs.readFileSync(LEDGER, 'utf8').split('\n').map(x => x.trim()).filter(Boolean)
    : []);

const picked = [];
let guard = 0;
while (picked.length < N_PICK && guard++ < 500000) {
  const i = crypto.randomInt(N);
  if (!hasUp[i]) continue;
  const key = G.codes[WL[i]] + ':' + WORDS[i];
  if (ledger.has(key)) continue;
  ledger.add(key);
  picked.push(key);
}
fs.appendFileSync(LEDGER, picked.join('\n') + '\n');
console.log(picked.join('\n'));
