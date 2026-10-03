// Code-level checks with a minimal DOM stand-in; this is not browser visual QA.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'work/texture-catalog095/index.html'), 'utf8');
const parts = html.match(/<script id="catalogData" type="application\/json">([\s\S]*?)<\/script><script>([\s\S]*?)<\/script>/);
assert(parts, 'Embedded catalog and implementation are present');
const data = JSON.parse(parts[1]);
class Element {
  constructor(){this.children=[];this.listeners={};this.value='';this.checked=false;this.textContent='';}
  append(child){this.children.push(child);}
  replaceChildren(){this.children=[];}
  addEventListener(type, fn){this.listeners[type]=fn;}
  showModal(){this.open=true;}
  close(){this.open=false;}
  select(){this.selected=true;}
}
const elements = new Map();
const document = {getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},
                  createElement(){return new Element();}};
document.getElementById('catalogData').textContent=parts[1];
document.getElementById('base').checked=true;
const context=vm.createContext({document,navigator:{clipboard:{async writeText(){}}}});
vm.runInContext(parts[2],context,{timeout:1000});
const run=code=>vm.runInContext(code,context,{timeout:1000});
const baseCount=data.images.filter(r=>r.base_image||!r.archives.length).length;
assert.equal(run('filtered.length'),baseCount,'Default view excludes mip-only IDs');
assert.equal(elements.get('grid').children.length,Math.min(60,baseCount),'First page bounds');
elements.get('base').checked=false;run('refresh()');
assert.equal(run('filtered.length'),data.images.length,'All images available including original mips');
elements.get('runtime').checked=true;run('refresh()');
const runtimeOnly=data.images.filter(r=>!r.archives.length&&r.runtime_observed);
assert.equal(run('filtered.length'),runtimeOnly.length,'Runtime-only filter has exact scope');
elements.get('runtime').checked=false;elements.get('base').checked=true;
elements.get('archive').value='ENVS/CLASSIC/HOTH_ION_CANNON.PSP';run('refresh()');
const mapRows=data.images.filter(r=>(r.base_image||!r.archives.length)&&r.archives.includes(elements.get('archive').value));
assert.equal(run('filtered.length'),mapRows.length,'Map filter has exact provenance');
elements.get('query').value='never-a-real-texture-095';run('refresh()');
assert.equal(run('filtered.length'),0);assert.equal(elements.get('count').textContent,'No matching originals');
elements.get('query').value=mapRows[0].id;run('refresh()');
assert.equal(run('filtered.length'),1,'Exact content ID search');
run('openDetail(filtered[0])');
assert.equal(elements.get('filename').value,mapRows[0].id+'.png','Replacement filename is original canonical ID');
assert.equal(elements.get('download').download,mapRows[0].id+'.png','Download preserves canonical filename');
assert(elements.get('provenance').textContent.includes('\n'),'Detail provenance uses readable newlines');
assert(!elements.get('provenance').textContent.includes('\\n'),'No literal newline escape artifacts');
elements.get('close').listeners.click();assert(!elements.get('detail').open);
elements.get('archive').value='';elements.get('query').value='';elements.get('base').checked=false;run('refresh()');
run('page=Math.floor((filtered.length-1)/size);refresh(false)');
assert(elements.get('next').disabled,'Last page stops at image count');
assert(elements.get('grid').children.length<=60&&elements.get('grid').children.length>0);
assert.equal(new Set(data.images.map(r=>r.id)).size,data.images.length,'No duplicate identity cards');
console.log(JSON.stringify({images:data.images.length,baseView:baseCount,runtimeOnly:runtimeOnly.length,
  mapBaseImages:mapRows.length,result:'PASS',scope:'Code-level filter, pagination, provenance and filename checks; no browser rendering acceptance.'},null,2));
