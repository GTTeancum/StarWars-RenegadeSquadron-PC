"""Verify the identities and source bytes used by the UI review."""
import hashlib,json
from pathlib import Path
from PIL import Image
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((r/'outputs/TEXTURE-RGB-REVIEW-077.json').read_text())
assert sha(r/'outputs/SOURCE-077-combined.json')==report['candidate_file_sha256']
for item in report['sheets']:assert sha(r/item['path'])==item['sha256']
sources=set()
for d in report['decisions']:
 p=r/'work/texture-dumps058/textures'/(d['id']+'.png');im=Image.open(p).convert('RGBA')
 identity='tex-v1-'+hashlib.sha256(im.width.to_bytes(4,'little')+im.height.to_bytes(4,'little')+im.tobytes()).hexdigest();assert identity==d['id']
 for c in d['reviewed_candidates']:
  assert sha(r/c['source'])==c['sha256'];sources.add(c['source'])
result=dict(verified_original_ids=len(report['decisions']),verified_distinct_source_files=len(sources),verified_sheets=len(report['sheets']),review_sha256=sha(r/'outputs/TEXTURE-RGB-REVIEW-077.json'),no_replacements_approved=all(not d['accepted'] for d in report['decisions']))
(r/'outputs/TEXTURE-RGB-VALIDATION-077.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
