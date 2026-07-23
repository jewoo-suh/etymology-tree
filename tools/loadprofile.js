// Measure cold-open cost per word: sequential fetch WAVES (round-trips),
// total shards, and bytes. Reuses the shipped shell script headless with a
// fetch that resolves on a macrotask, so wave structure is observable.
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const ROOT = 'C:/Projects/etymology-tree-viz';

function stubEl() {
  const el = { style:{setProperty(){},}, dataset:{}, classList:{add(){},remove(){}},
    children:[], childNodes:[], value:'', textContent:'', title:'', firstChild:null,
    setAttribute(){}, getAttribute(){return null;}, appendChild(c){return c;},
    removeChild(){}, remove(){}, addEventListener(){}, insertBefore(){},
    querySelectorAll(){return [];}, getBoundingClientRect(){return {left:0,top:0,width:800,height:600};},
    focus(){}, blur(){}, closest(){return null;}, clientWidth:1200, clientHeight:800,
    scrollLeft:0, scrollTop:0, scrollWidth:1200, scrollHeight:800, innerHTML:'',
    getContext(){return {measureText(t){return {width:(t||'').length*8};}, font:''};}, scrollTo(){} };
  return el;
}
let bytes = 0, files = 0, inFlight = 0, waves = 0;
function makeSandbox(meta) {
  const document = { getElementById(){return stubEl();}, createElement(){return stubEl();},
    createElementNS(){return stubEl();}, createTextNode(t){return {textContent:t};},
    addEventListener(){}, body:stubEl(), documentElement:stubEl(), querySelectorAll(){return [];} };
  const win = { __SHARDMETA__: meta };
  const sb = { window:win, document, console, setTimeout, clearTimeout, Promise,
    atob:(b)=>Buffer.from(b,'base64').toString('binary'), navigator:{},
    DecompressionStream, Response, Blob, TextDecoder, TextEncoder,
    fetch(url){
      const clean = String(url).split('?')[0];
      if (inFlight === 0) waves++;
      inFlight++;
      return new Promise((res,rej)=>{
        fs.readFile(path.join(ROOT, clean),(err,buf)=>{
          setTimeout(()=>{
            inFlight--;
            if (err) return rej(new Error('missing '+clean));
            try { bytes += fs.statSync(path.join(ROOT, clean)).size; files++; } catch(e){}
            res(new Response(buf));
          },0);
        });
      });
    } };
  win.window = win; sb.globalThis = sb; return sb;
}
function extractApp(html){
  const out=[];
  for (const m of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g))
    if (!m[1].includes('application/json')) out.push(m[2]);
  return out.join('\n;\n');
}
process.on('unhandledRejection',()=>{});
(async function(){
  const shell = fs.readFileSync(ROOT+'/index.html','utf8');
  const meta = JSON.parse(fs.readFileSync(ROOT+'/shards/meta.json','utf8'));
  const words = fs.readFileSync(ROOT+'/tools/checked_words.txt','utf8').split('\n').map(x=>x.trim()).filter(Boolean);
  // sample every Nth checked word plus the starters
  const sample = [];
  for (let i=0;i<words.length && sample.length<30;i+=Math.ceil(words.length/30)) sample.push(words[i]);
  // key -> id map straight from the graph (client learns these via search)
  const D='0123456789abcdefghijklmnopqrstuvwxyz';
  const G=JSON.parse(fs.readFileSync(ROOT+'/web/graph-web.json','utf8'));
  const W=[];{let v='';for(const s of G.words.split('\n')){const w=v.slice(0,D.indexOf(s[0]))+s.slice(1);W.push(w);v=w;}}
  const WL=[];{let p=0;for(const r of G.wrle.split(',')){const c=r.indexOf(':');const l=parseInt(r.slice(0,c),36),n=parseInt(r.slice(c+1),36);for(let j=0;j<n;j++)WL[p++]=l;}}
  const KID={};for(let i=0;i<W.length;i++){const k=G.codes[WL[i]]+':'+W[i];if(KID[k]===undefined)KID[k]=i;}
  const appSrc = extractApp(shell);
  const rows = [];
  for (const key of sample) {
    const id = KID[key];
    if (id === undefined) continue;
    const box = makeSandbox(meta);        // FRESH cold context per word
    vm.createContext(box); vm.runInContext(appSrc, box);
    const t = box.window.__test;
    bytes=0; files=0; waves=0; inFlight=0;
    await t.prepare(id);          // chain-ready (what the user waits for)
    rows.push({ key, waves, files, kb: Math.round(bytes/1024) });
  }
  rows.sort((a,b)=>b.waves-a.waves);
  console.log('word'.padEnd(22),'waves','files',' KB   (chain-ready cost)');
  for (const r of rows) console.log(r.key.padEnd(22), String(r.waves).padStart(3), String(r.files).padStart(5), String(r.kb).padStart(5));
  const avg = a => (a.reduce((s,r)=>s+r,0)/a.length).toFixed(1);
  console.log('--- median waves', rows.map(r=>r.waves).sort((a,b)=>a-b)[rows.length>>1],
    '| avg waves', avg(rows.map(r=>r.waves)), '| avg files', avg(rows.map(r=>r.files)), '| avg KB', avg(rows.map(r=>r.kb)));
})();
