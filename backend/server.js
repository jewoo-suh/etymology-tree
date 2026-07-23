// Etymology backend prototype.
//
// Holds the whole graph in RAM and runs the SHIPPED client algorithms in a VM
// (zero reimplementation, same QA-verified logic). Per request it computes one
// word's display server-side and returns a few KB of render-ready JSON, so the
// browser fetches one small response per word -- instant, tiny first load.
//
//   node --max-old-space-size=4096 backend/server.js [port]
//
// Then open http://localhost:8787/ . The GitHub Pages site is untouched.
'use strict';
const fs = require('fs');
const vm = require('vm');
const http = require('http');
const path = require('path');
const zlib = require('zlib');

const ROOT = path.join(__dirname, '..');
const PORT = parseInt(process.argv[2] || '8787', 10);

// a bad request must never take the whole server down
process.on('uncaughtException', function (e) { console.error('uncaught:', e && e.message); });
process.on('unhandledRejection', function (e) { console.error('rejection:', e && e.message); });

function stubEl() {
  const el = { style:{setProperty(){}}, dataset:{}, classList:{add(){},remove(){}},
    children:[], childNodes:[], value:'', textContent:'', title:'', firstChild:null,
    setAttribute(){}, getAttribute(){return null;}, appendChild(c){return c;},
    removeChild(){}, remove(){}, addEventListener(){}, insertBefore(){},
    querySelectorAll(){return [];}, getBoundingClientRect(){return {left:0,top:0,width:800,height:600};},
    focus(){}, blur(){}, closest(){return null;}, clientWidth:1200, clientHeight:800,
    scrollLeft:0, scrollTop:0, scrollWidth:1200, scrollHeight:800, innerHTML:'',
    getContext(){return {measureText(t){return {width:(t||'').length*8};}, font:''};}, scrollTo(){} };
  return el;
}

console.log('loading graph into memory...');
const t0 = Date.now();
const shell = fs.readFileSync(path.join(ROOT, 'web', 'template.html'), 'utf8');
const lib = fs.readFileSync(path.join(ROOT, 'web', 'vendor', 'd3-hierarchy.min.js'), 'utf8');
const graph = JSON.parse(fs.readFileSync(path.join(ROOT, 'web', 'graph-web.json'), 'utf8'));

// extract the app script block (the __runapp definition) from the template
const appBlock = [...shell.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
  .map(m => ({ attr: m[1], code: m[2] }))
  .find(b => !b.attr.includes('application/json') && b.code.includes('__runapp = function'));
if (!appBlock) { console.error('could not find app block in template'); process.exit(1); }

const win = { __GRAPH__: graph };
const document = { getElementById(){return stubEl();}, createElement(){return stubEl();},
  createElementNS(){return stubEl();}, createTextNode(t){return {textContent:t};},
  addEventListener(){}, body:stubEl(), documentElement:stubEl(), querySelectorAll(){return [];} };
const box = { window:win, document, console, setTimeout, clearTimeout, Promise,
  atob:b=>Buffer.from(b,'base64').toString('binary'), navigator:{},
  DecompressionStream, Response, Blob, TextDecoder, TextEncoder };
win.window = win; box.globalThis = box;
vm.createContext(box);
vm.runInContext(lib + '\n;\n' + appBlock.code, box);
try { win.__runapp(); } catch (e) { /* trailing render() hits DOM stubs; API is set */ }

if (!win.__apiTree) { console.error('app did not expose __apiTree'); process.exit(1); }
console.log('ready in ' + ((Date.now() - t0) / 1000).toFixed(1) + 's; ' +
  graph.words.split('\n').length.toLocaleString() + ' nodes. http://localhost:' + PORT + '/');

function send(res, code, body, type, gzOK) {
  var buf = Buffer.isBuffer(body) ? body : Buffer.from(body);
  var head = { 'Content-Type': type, 'Access-Control-Allow-Origin': '*',
               'Cache-Control': 'public, max-age=3600' };
  if (gzOK && buf.length > 1024) { buf = zlib.gzipSync(buf); head['Content-Encoding'] = 'gzip'; }
  head['Content-Length'] = buf.length;
  res.writeHead(code, head); res.end(buf);
}

const server = http.createServer(function (req, res) {
  try {
    const u = new URL(req.url, 'http://x');
    const accGz = /\bgzip\b/.test(req.headers['accept-encoding'] || '');
    if (u.pathname === '/api/search') {
      const q = u.searchParams.get('q') || '';
      return send(res, 200, JSON.stringify(win.__apiSearch(q)), 'application/json', accGz);
    }
    if (u.pathname === '/api/tree') {
      let id = u.searchParams.get('id');
      id = id != null ? parseInt(id, 10) : win.__apiKey(u.searchParams.get('w') || '');
      if (id == null || id < 0) return send(res, 404, '{"error":"not found"}', 'application/json', false);
      return send(res, 200, JSON.stringify(win.__apiTree(id)), 'application/json', accGz);
    }
    if (u.pathname === '/' || u.pathname === '/index.html') {
      return send(res, 200, fs.readFileSync(path.join(__dirname, 'app.html')), 'text/html; charset=utf-8', accGz);
    }
    if (u.pathname === '/d3.js') {
      return send(res, 200, lib, 'text/javascript; charset=utf-8', accGz);
    }
    send(res, 404, 'not found', 'text/plain', false);
  } catch (e) {
    send(res, 500, JSON.stringify({ error: String(e && e.message || e) }), 'application/json', false);
  }
});
server.listen(PORT);
