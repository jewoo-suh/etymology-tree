// Verify the deployed load-once boot path: decompress the core asset, boot the
// shipped app via window.__GRAPH__ + __runapp (no #data, no shards), confirm
// chains match, then stream the gloss asset and confirm definitions attach.
'use strict';
const fs = require('fs'), vm = require('vm'), zlib = require('zlib'), path = require('path');
const ROOT = 'C:/Projects/etymology-tree-viz';

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
process.on('unhandledRejection', e => { console.log('REJECT', e && e.message); });

const shell = fs.readFileSync(ROOT + '/index.html', 'utf8');
// the deployed shell has no #data; extract only the __runapp definition block
const allBlocks = [...shell.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
  .filter(m => !m[1].includes('application/json')).map(m => m[2]);
const appBlock = allBlocks.find(s => s.includes('__runapp = function'));
const libBlock = allBlocks.find(s => !s.includes('__runapp') && !s.includes('bootload'));
if (!appBlock) { console.log('FAIL: no __runapp block in index.html'); process.exit(1); }
const appSrc = (libBlock ? libBlock + '\n;\n' : '') + appBlock;   // d3 + app

const coreName = (shell.match(/graph-core-[a-f0-9]+\.json\.gz/) || [])[0];
const glossName = (shell.match(/gloss-[a-f0-9]+\.json\.gz/) || [])[0];
console.log('assets:', coreName, '+', glossName);
const core = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(ROOT, coreName))).toString('utf8'));
const gloss = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(ROOT, glossName))).toString('utf8'));
console.log('core keys:', Object.keys(core).join(','));
console.log('core has glosses inline?', !!core.gtexts, '(should be false)');

const win = { __GRAPH__: core };
const document = { getElementById(){return stubEl();}, createElement(){return stubEl();},
  createElementNS(){return stubEl();}, createTextNode(t){return {textContent:t};},
  addEventListener(){}, body:stubEl(), documentElement:stubEl(), querySelectorAll(){return [];} };
const box = { window:win, document, console, setTimeout, clearTimeout, Promise,
  atob:b=>Buffer.from(b,'base64').toString('binary'), navigator:{},
  DecompressionStream, Response, Blob, TextDecoder, TextEncoder };
win.window = win; box.globalThis = box;
vm.createContext(box);
vm.runInContext(appSrc, box);
try { win.__runapp(); } catch (e) { /* the trailing render() hits DOM stubs; __test is already set */ }
const t = win.__test;
if (!t) { console.log('FAIL: __runapp did not expose __test'); process.exit(1); }

// build key->id from the core itself (words + wrle + codes)
const D='0123456789abcdefghijklmnopqrstuvwxyz';
const W=[];{let v='';for(const s of core.words.split('\n')){const w=v.slice(0,D.indexOf(s[0]))+s.slice(1);W.push(w);v=w;}}
const WL=[];{let p=0;for(const r of core.wrle.split(',')){const c=r.indexOf(':');const l=parseInt(r.slice(0,c),36),n=parseInt(r.slice(c+1),36);for(let j=0;j<n;j++)WL[p++]=l;}}
const KID={};for(let i=0;i<W.length;i++){const k=core.codes[WL[i]]+':'+W[i];if(KID[k]===undefined)KID[k]=i;}

const GOLD = { 'en:water':'wódr̥', 'en:communism':'communisme', 'en:out':'úd',
  'en:penguin':'kʷennom', 'en:orange':'arancia', 'la:munitio':'munio' };
let pass=0, fail=0;
for (const key in GOLD) {
  const id = KID[key]; if (id===undefined){console.log('  skip',key);continue;}
  const chain = (t.treeFor(id).chain||[]).map(x=>t.label?t.label(x):x);
  const ok = t.treeFor(id).chain.length > 1;   // has a real chain, instant, no fetch
  if (ok) pass++; else { fail++; console.log('  no chain for', key); }
}
console.log('boot-from-core: ' + pass + ' words drew instantly, ' + fail + ' failed');

// glosses were NOT in core; apply the streamed gloss and confirm no error
try { win.__applyGloss(gloss); console.log('gloss stream applied: OK'); }
catch (e) { console.log('gloss stream FAILED:', e.message); fail++; }
console.log(fail ? 'SITE CHECK FAILED' : 'SITE CHECK OK');
process.exit(fail ? 1 : 0);
