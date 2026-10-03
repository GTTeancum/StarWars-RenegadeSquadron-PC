"""Create an offline, paginated original-texture browser from the verified catalog."""
import hashlib, json
from pathlib import Path
from urllib.parse import quote
root = Path(__file__).resolve().parent.parent
out = root / 'work/texture-catalog099'
catalog = json.loads((out / 'catalog.json').read_text())
assert not any(catalog[k] for k in ['unsupported', 'uncatalogued_texture_archives', 'runtime_errors', 'pack_errors'])
rows = []
for row in catalog['images']:
    rows.append({k: row[k] for k in ['id', 'width', 'height', 'status', 'base_image', 'runtime_observed',
                                   'names', 'archives', 'manual_override', 'existing_pack_override']} | {
        'preview': '../../' + quote(row['preview'], safe='/'),
        'original': '../../' + quote(row['original'], safe='/'),
        'mips': sorted({r['mip'] for r in row['archive_records']}),
        'runtime_runs': sorted({r['run'] for r in row['runtime_records'] if r['run']}),
        'rgb_related_names': row['exact_rgb_related_names'], 'render_target_sample': row['render_target_sample'],
        'shared_provenance': any(r['run'] is None for r in row['runtime_records'])})
data = json.dumps(dict(counts=catalog['counts'], coverage=catalog['coverage'], images=rows), separators=(',', ':')).replace('<', '\\u003c')
html = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Renegade Squadron texture catalog</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#111921;color:#edf3f9;font:15px system-ui,sans-serif}
main{max-width:1400px;margin:auto;padding:28px}h1{font-size:28px;margin:0 0 8px}p{color:#b7c9d8;line-height:1.5}
nav,.filters,.pages{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:18px 0}
input,select,button{font:inherit;color:inherit;background:#20303e;border:1px solid #52677a;border-radius:7px;padding:9px}
input[type=search]{flex:1;min-width:260px}input[type=checkbox]{accent-color:#81d3ee}label{display:flex;align-items:center;gap:8px}
button{cursor:pointer}button:disabled{opacity:.4;cursor:default}a{color:#99e3f9}#count{margin-left:auto}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px}
.card{padding:10px;text-align:left;min-width:0;background:#1b2935;border:1px solid #354858;border-radius:9px}
.card img{width:100%;height:150px;object-fit:contain;image-rendering:pixelated;background:repeating-conic-gradient(#32404a 0 25%,#1b2731 0 50%) 0/16px 16px}
.name{font-weight:600;overflow-wrap:anywhere;margin-top:9px}.meta{color:#abc0d2;font-size:13px;line-height:1.5;margin-top:5px}
dialog{background:#1b2935;color:inherit;border:1px solid #688497;border-radius:12px;max-width:850px;width:95%;max-height:95vh;overflow:auto}
dialog::backdrop{background:#000a}#detailImage{display:block;max-width:100%;max-height:45vh;object-fit:contain;margin:14px auto;background:repeating-conic-gradient(#32404a 0 25%,#1b2731 0 50%) 0/16px 16px}
#filename{width:100%;font:12px ui-monospace,monospace}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font:13px ui-monospace,monospace}
.note{padding:12px 15px;background:#203644;border-left:3px solid #82cee4}.stats{font-weight:600;color:#dcf2ff}
</style><main>
<h1>Renegade Squadron texture catalog</h1><p class="stats" id="stats"></p>
<p class="note">Choose a map or search the original name. Base images are shown first; lower mip images remain available by unchecking the filter.
Keep your replacement's orientation and channels as authored. Place it in <b>work/mods-user/textures</b> using the content filename shown below. Changing render-target captures are hidden initially; enable their checkbox to inspect them. No automatic matches or upscales are applied.</p>
<nav><a href="textures.csv">Names and IDs (CSV)</a><a href="original-sources.csv">Your original source index</a><a href="runtime-review.csv">Runtime review queue</a><a href="mutable-sources.csv">Content variants observed during play</a><a href="catalog.json">Full provenance (JSON)</a><a href="../../TEXTURE-MATCHING.md">Matching instructions</a></nav>
<div class="filters"><input id="query" type="search" aria-label="Search textures" placeholder="Search names, map paths or content IDs">
<select id="archive" aria-label="Map or UI archive"><option value="">All maps and UI</option></select>
<label><input id="base" type="checkbox" checked>Base images only</label>
<label><input id="runtime" type="checkbox">Runtime-only originals</label><label><input id="framebuffers" type="checkbox">Include changing frame captures</label></div>
<p id="coverage"></p><div class="pages"><button id="previous">Previous</button><button id="next">Next</button><span id="count" role="status"></span></div>
<div id="grid"></div>
<dialog id="detail"><button id="close">Close</button><h2 id="detailName"></h2><img id="detailImage" alt="Original texture">
<label for="filename">Replacement filename (change the extension to DDS or TGA if needed)</label><input id="filename" readonly>
<nav><button id="copy">Copy filename</button><a id="download" download>Save original PNG</a><a id="original">Original source file</a></nav>
<pre id="provenance"></pre></dialog></main>
<script id="catalogData" type="application/json">__DATA__</script><script>
'use strict';
const data=JSON.parse(document.getElementById('catalogData').textContent);
const el=id=>document.getElementById(id);let filtered=[],page=0;const size=60;
el('stats').textContent=`${data.counts.catalog_unique_ids.toLocaleString()} original images · ${data.counts.texture_archives} decoded texture archives · ${data.counts.runtime_only_ids} runtime IDs outside the named archive catalog`;
for(const c of data.coverage){const o=document.createElement('option');o.value=c.archive;o.textContent=c.archive;el('archive').append(o)}
function refresh(reset=true){if(reset)page=0;const q=el('query').value.toLowerCase().trim(),archive=el('archive').value;
filtered=data.images.filter(r=>(!el('base').checked||r.base_image||!r.archives.length)&&(!el('runtime').checked||(!r.archives.length&&r.runtime_observed))&&(!r.render_target_sample||el('framebuffers').checked)&&(!archive||r.archives.includes(archive))&&(!q||[r.id,...r.names,...r.archives,r.status].join(' ').toLowerCase().includes(q)));
const c=data.coverage.find(c=>c.archive===archive);el('coverage').textContent=c?`${c.texture_chunks} extracted texture resources; ${c.base_ids_seen_anywhere}/${c.base_ids} base IDs seen across all runs (may be shared with other maps). ${c.successful_runs_opened.length} successful diagnostic runs opened this archive. Opens do not prove full traversal or visual acceptance.`:'Static extraction and runtime observations have separate coverage. An unnamed runtime texture is unresolved; its dynamic cause is not assumed.';
el('grid').replaceChildren();for(const r of filtered.slice(page*size,(page+1)*size)){
const card=document.createElement('button');card.className='card';card.type='button';
const img=document.createElement('img');img.src=r.preview;img.alt=r.names[0]||r.id;img.loading='lazy';card.append(img);
const name=document.createElement('div');name.className='name';name.textContent=r.names.length?r.names[0].split(/[\\/]/).pop():r.status.replaceAll('_',' ');card.append(name);
const meta=document.createElement('div');meta.className='meta';meta.textContent=`${r.width}×${r.height} · ${r.runtime_observed?'seen at runtime':'archive only'}\n${r.manual_override?'Manual replacement present':r.existing_pack_override?'Existing source074 binding':'No replacement recorded'}`;card.append(meta);
card.addEventListener('click',()=>openDetail(r));el('grid').append(card)}
el('count').textContent=filtered.length?`${page*size+1}–${Math.min((page+1)*size,filtered.length)} of ${filtered.length.toLocaleString()}`:'No matching originals';
el('previous').disabled=page===0;el('next').disabled=(page+1)*size>=filtered.length;
}
function openDetail(r){el('detailName').textContent=r.names.length?r.names[0].split(/[\\/]/).pop():r.status.replaceAll('_',' ');
el('detailImage').src=r.preview;el('filename').value=r.id+'.png';el('download').href=r.preview;el('download').download=r.id+'.png';el('original').href=r.original;
el('provenance').textContent=[`Original: ${r.width}×${r.height}`,`Identity: ${r.id}`,`Classification: ${r.status}`,`Mip levels: ${r.mips.join(', ')||'runtime/standalone'}`,'','Names:',...r.names,'','Archives:',...r.archives,'','Exact RGB relatives (alpha differs; no new binding assumed):',...r.rgb_related_names,'','Runtime runs:',...r.runtime_runs,r.shared_provenance?'Shared live dump also observed; its run cannot be attributed retrospectively.':'','',r.manual_override?`Manual replacement: ${r.manual_override.file}`:'',r.existing_pack_override?`Existing binding: ${r.existing_pack_override.file}`:'','DDS takes priority over TGA, then PNG. Restart after editing replacements.'].filter(Boolean).join('\n');el('detail').showModal();}
for(const id of ['query','archive','base','runtime','framebuffers'])el(id).addEventListener(id==='query'?'input':'change',()=>refresh());
el('previous').addEventListener('click',()=>{page--;refresh(false)});el('next').addEventListener('click',()=>{page++;refresh(false)});
el('close').addEventListener('click',()=>el('detail').close());el('copy').addEventListener('click',async()=>{el('filename').select();try{await navigator.clipboard.writeText(el('filename').value);el('copy').textContent='Copied'}catch{el('copy').textContent='Selected — press Ctrl+C'}});
refresh();
</script></html>'''.replace('__DATA__', data)
(out / 'index.html').write_text(html, encoding='utf-8')
# Artifact invariants: data is embedded, no network fetches, all image/source
# references resolve inside the repository and original identities remain intact.
for row in rows:
    for key in ['preview', 'original']:
        from urllib.parse import unquote
        p = (out / unquote(row[key])).resolve()
        assert p.is_relative_to(root) and p.is_file(), p
assert 'fetch(' not in html and len(rows) == catalog['counts']['catalog_unique_ids']
for filename in ['textures.csv','original-sources.csv','runtime-review.csv','mutable-sources.csv','catalog.json']:
    assert (out/filename).is_file(), filename
print(json.dumps({'images':len(rows), 'html_sha256':hashlib.sha256((out/'index.html').read_bytes()).hexdigest(),
                  'catalog_sha256':hashlib.sha256((out/'catalog.json').read_bytes()).hexdigest()}, indent=2))
