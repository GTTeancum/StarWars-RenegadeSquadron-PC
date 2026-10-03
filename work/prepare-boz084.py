"""Resolve shared converted-map materials without modifying supplied sources."""
import hashlib,json,shutil
from pathlib import Path
r=Path(__file__).resolve().parent.parent
raw=r/'work/map-conversions084/data_BOZ/Worlds/BOZ'
target=r/'work/map-resolved084/BOZ'
assert not target.exists(), 'Preserve existing resolved staging; inspect before reuse.'
shutil.copytree(raw,target)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
copied=[]
for name,source in [
 ('yav_prop_fern1.tga','work/texture-sources058/data_PYV FINAL/data_PYV/Worlds/PYV/MSH/yav_prop_fern1.tga'),
 ('end_prop_foliage_1.tga','work/texture-sources058/data_EN3 FINAL/data_EN3/Worlds/EN3/MSH/end_prop_foliage_1.tga')]:
 src=r/source;dst=target/'msh'/name
 assert not dst.exists()
 shutil.copy2(src,dst);assert sha(src)==sha(dst)
 copied.append(dict(source=source,destination=dst.relative_to(r).as_posix(),sha256=sha(dst)))
verified={p.relative_to(raw).as_posix():sha(p) for p in raw.rglob('*') if p.is_file()}
assert all(sha(target/name)==value for name,value in verified.items())
(r/'outputs/BOZ-RESOLVED-084.json').write_text(json.dumps(dict(original=raw.relative_to(r).as_posix(),resolved=target.relative_to(r).as_posix(),unchanged_original_files=verified,shared_materials=copied,image_operations=[],note='Endor EN2 PC and EN3 foliage copies are byte-identical; EN3 copy selected.'),indent=2)+'\n')
for old,new in [('analyze-world083.py','analyze-world084.py'),('align-triangles083.py','align-triangles084.py'),('stage-world083.py','stage-world084.py'),('report-ground083.py','report-ground084.py')]:
 text=(r/'work'/old).read_text().replace('083','084').replace('korriban','boz').replace('CONVERTED-KOR','CONVERTED-BOZ')
 (r/'work'/new).write_text(text)
