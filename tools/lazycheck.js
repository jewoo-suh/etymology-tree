// Run the SHIPPED page script headless in both data modes and compare the
// chains it computes: shard mode (fetch backed by the local shards/ dir,
// loading lazily exactly as a browser would) against monolith mode (full
// graph inline). Any divergence means the lazy loader changes what readers
// see, and fails the build.
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const zlib = require('zlib');

const ROOT = 'C:/Projects/etymology-tree-viz';

function stubEl() {
  const el = {
    style: { setProperty() {}, width: '', display: '' },
    dataset: {}, classList: { add() {}, remove() {} },
    children: [], value: '', textContent: '', title: '',
    setAttribute() {}, getAttribute() { return null; },
    appendChild(c) { return c; }, removeChild() {}, remove() {},
    addEventListener() {}, insertBefore() {}, querySelectorAll() { return []; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 800, height: 600 }; },
    focus() {}, blur() {}, closest() { return null; },
    clientWidth: 1200, clientHeight: 800, scrollLeft: 0, scrollTop: 0,
    childNodes: [], firstChild: null, parentNode: null,
    scrollWidth: 1200, scrollHeight: 800, innerHTML: '',
    getContext() {
      return { measureText(t) { return { width: (t || '').length * 8 }; },
               font: '' };
    },
    scrollTo() {},
  };
  return el;
}

function makeSandbox(dataText, meta) {
  const dataEl = stubEl();
  dataEl.textContent = dataText || '';
  const document = {
    getElementById(id) { return id === 'data' ? dataEl : stubEl(); },
    createElement() { return stubEl(); },
    createElementNS() { return stubEl(); },
    createTextNode(t) { return { textContent: t }; },
    addEventListener() {}, removeEventListener() {},
    body: stubEl(), documentElement: stubEl(),
    querySelectorAll() { return []; },
  };
  const windowObj = { __SHARDMETA__: meta || undefined };
  const sandbox = {
    window: windowObj, document, console,
    setTimeout, clearTimeout, Promise,
    atob: (b) => Buffer.from(b, 'base64').toString('binary'),
    navigator: {},
    fetch(url) {
      const clean = String(url).split('?')[0];
      const file = path.join(ROOT, clean);
      return new Promise((res, rej) => {
        fs.readFile(file, (err, buf) => {
          if (err) return rej(new Error('missing ' + clean));
          res(new Response(buf));
        });
      });
    },
    DecompressionStream, Response, Blob, TextDecoder, TextEncoder,
  };
  windowObj.window = windowObj;
  sandbox.globalThis = sandbox;
  return sandbox;
}

function extractApp(html) {
  // every executable script block in order (the JSON data block is read via
  // the DOM stub, not executed)
  const out = [];
  for (const m of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    if (m[1].includes('application/json')) continue;
    out.push(m[2]);
  }
  return out.join('\n;\n');
}

process.on('unhandledRejection', (e) => {
  if (process.env.LAZYDEBUG) console.log('  (async boot noise:', String(e).slice(0, 120) + ')');
});
(async function main() {

  const shell = fs.readFileSync(ROOT + '/index.html', 'utf8');
  const meta = JSON.parse(fs.readFileSync(ROOT + '/shards/meta.json', 'utf8'));
  const mono = fs.readFileSync(ROOT + '/web/graph-web.json', 'utf8');
  const webPage = fs.readFileSync(ROOT + '/web/index-web.html', 'utf8');

  const lazyBox = makeSandbox('', meta);
  vm.createContext(lazyBox);
  vm.runInContext(extractApp(shell), lazyBox);
  const lazy = lazyBox.window.__test;
  if (!lazy) { console.log('FAIL: no test hook in shell'); process.exit(1); }

  const monoBox = makeSandbox(mono, null);
  vm.createContext(monoBox);
  vm.runInContext(extractApp(webPage), monoBox);
  const full = monoBox.window.__test;
  if (!full) { console.log('FAIL: no test hook in web bundle'); process.exit(1); }

  const GOLD = ['en:tooth', 'en:day', 'en:night', 'en:star', 'en:sun', 'en:eye',
    'en:hound', 'en:father', 'en:moon', 'en:water', 'en:sugar', 'en:grammar',
    'en:king', 'en:bread', 'en:book', 'en:heart', 'en:wheel', 'en:carve',
    'en:teacher', 'en:ontology', 'la:munitio', 'en:Korea', 'de:Antibabypille',
    'de:Vater', 'fr:père', 'es:agua', 'ru:вода', 'en:whisky', 'en:name',
    'en:salt', 'en:communism', 'en:bear', 'en:avocado', 'en:penguin',
    'en:robot', 'en:orange', 'en:ketchup', 'en:culture', 'en:create',
    'en:concurrent', 'en:influence', 'en:salary', 'en:alcohol', 'en:paradise',
    'en:admiral', 'en:quarantine', 'en:hazard', 'en:magazine', 'en:karaoke',
    'en:zero', 'en:cipher'];

  let pass = 0, fail = 0, shardsTouched = new Set();
  const origFetch = lazyBox.fetch;
  for (const key of GOLD) {
    const id = full.KEYIDX[key];
    if (id === undefined) { console.log('  skip', key, '(absent)'); continue; }
    const want = (full.treeFor(id).chain || []).join(',');
    await lazy.prepare(id);
    const early = (lazy.treeFor(id).chain || []).join(',');
    await lazy.drain(id);
    const got = (lazy.treeFor(id).chain || []).join(',');
    if (got === want && early === want) pass++;
    else {
      fail++;
      console.log('DIVERGED', key);
      console.log('  mono :', want);
      console.log('  early:', early);
      console.log('  lazy :', got);
    }
  }
  console.log(pass + ' identical, ' + fail + ' diverged of ' + GOLD.length);

  // random sweep: every ~33000th node, whatever script or language
  let rpass = 0, rfail = 0;
  for (let id = 17; id < meta.n; id += 33333) {
    const want = (full.treeFor(id).chain || []).join(',');
    await lazy.prepare(id);
    const early = (lazy.treeFor(id).chain || []).join(',');
    await lazy.drain(id);
    const got = (lazy.treeFor(id).chain || []).join(',');
    if (got === want && early === want) rpass++;
    else {
      rfail++;
      console.log('DIVERGED id', id);
      console.log('  mono:', want);
      console.log('  lazy:', got);
    }
  }
  console.log(rpass + ' identical, ' + rfail + ' diverged of random sweep');

  // fresh-visit cost: a brand-new context opening one word
  let bytes = 0, files = 0;
  const freshBox = makeSandbox('', meta);
  const baseFetch = freshBox.fetch;
  freshBox.fetch = function (url) {
    return baseFetch(url).then(function (r) {
      const clean = String(url).split('?')[0];
      try { bytes += fs.statSync(path.join(ROOT, clean)).size; files++; } catch (e) {}
      return r;
    });
  };
  vm.createContext(freshBox);
  vm.runInContext(extractApp(shell), freshBox);
  const fresh = freshBox.window.__test;
  await fresh.prepare(full.KEYIDX['en:father']);
  console.log('fresh visit, en:father chain ready: ' + files + ' files, ' +
              (bytes / 1048576).toFixed(2) + ' MB');
  await fresh.drain(full.KEYIDX['en:father']);
  console.log('  full tree drained: ' + files + ' files, ' +
              (bytes / 1048576).toFixed(2) + ' MB');
  let b2 = bytes, f2 = files;
  await fresh.prepare(full.KEYIDX['en:concurrent']);
  console.log('  then en:concurrent chain: +' + (files - f2) + ' files, +' +
              ((bytes - b2) / 1048576).toFixed(2) + ' MB');
  process.exit((fail + rfail) ? 1 : 0);
})().catch(function (e) {
  console.log('HARNESS ERROR:', e && e.stack || e);
  process.exit(1);
});
