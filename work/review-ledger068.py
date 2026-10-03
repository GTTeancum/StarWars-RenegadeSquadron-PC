"""Separate reviewed candidate decisions from unreviewed archive base identities."""
import collections,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())
bound={f['id'] for f in json.loads((root/'outputs/TEXTURE-PACK-068.json').read_text())['files']}
history=collections.defaultdict(list)
for n in ['062','063','065','066','067','068']:
    manifest=json.loads((root/f'outputs/TEXTURE-PACK-{n}.json').read_text())
    for d in manifest['decisions']:
        history[d['id']].append(dict(checkpoint=n,**d))
scored={g['id']:g for g in json.loads((root/'work/texture-matches060/full-resolution.json').read_text())['matches']}
base=collections.defaultdict(list)
for t in catalog['textures']:
    if t['mip']==0:base[t['id']].append(t)
rows=[]
for identity,records in sorted(base.items()):
    candidates=scored.get(identity,{}).get('candidates',[])
    identical=[c for c in candidates if c['best_rgb_rmse']==0 and not c['swap_original_rb'] and c['source_width']==records[0]['width'] and c['source_height']==records[0]['height']]
    if identity in bound:status='bound_reviewed_source'
    elif history[identity]:status='reviewed_candidate_held'
    elif identical:status='same_size_rgb_copy_found_no_rgb_improvement'
    elif candidates:status='scored_candidates_not_yet_reviewed'
    else:status='no_full_resolution_candidates_recorded'
    rows.append(dict(id=identity,status=status,records=records,decision_history=history[identity],candidate_count=len(candidates),same_size_rgb_copies=identical,best_scored_candidate=candidates[0] if candidates else None))
counts=dict(collections.Counter(row['status'] for row in rows))
report=dict(scope='Disposition ledger for every archived base identity. Holding a reviewed candidate does not prove no suitable source exists elsewhere. Historical early manifests without per-ID decisions are not inferred as held.',counts=counts,base_images=rows)
(root/'outputs/TEXTURE-REVIEW-LEDGER-068.json').write_text(json.dumps(report,indent=2)+'\n')
text=['# Source-review ledger at checkpoint 068','','Every one of the 1,055 archived base identities has a status and provenance in the accompanying JSON. This separates an unsuccessful candidate review from a texture that has not yet received a recorded review.','','| Status | Base identities |','| --- | ---: |']
text += [f'| {key} | {value} |' for key,value in sorted(counts.items())]
text += ['','A held candidate is not proof that the whole supplied corpus lacks a suitable source. Same-size RGB copies provide no RGB-detail gain; alpha may differ and is not silently substituted. No source is approved based only on a similarity score.','']
(root/'outputs/TEXTURE-REVIEW-LEDGER-068.md').write_text('\n'.join(text))
print(json.dumps(counts,indent=2))
