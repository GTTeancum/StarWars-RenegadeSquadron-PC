"""Classify observed mutable source slots without guessing asset origin.

Per-run source metadata and original RGBA identities are evidence. Sharing an
address across unrelated runs, or absence from the archive index, is not proof
of animation, generated content or a particular authored source match.
"""
import csv, hashlib, json
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / 'work/texture-catalog099'
catalog_path = out / 'catalog.json'
catalog = json.loads(catalog_path.read_text())
assert not any(catalog[k] for k in ['runtime_errors', 'unsupported', 'uncatalogued_texture_archives', 'pack_errors'])
images = {r['id']: r for r in catalog['images']}
fields = ['address', 'width', 'height', 'format', 'buffer_width', 'mip_level', 'clut_address', 'swizzled']
groups, hashes = defaultdict(dict), {}
for name, expected_hash in catalog['manifest_sha256'].items():
    # Shared live manifests contain observations from several unidentifiable
    # runs, so grouping those addresses would invent continuity.
    parts = Path(name).parts
    if len(parts) < 5 or parts[:2] != ('work', 'runs'):
        continue
    path = root / name
    sha = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    assert sha == expected_hash, path
    hashes[name] = sha
    run = parts[2]
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        row = json.loads(line)
        assert row['id'] in images
        if not row.get('address'):
            continue  # zero address has no established mutable source meaning
        key = (run, *(row.get(k) for k in fields))
        groups[key].setdefault(row['id'], dict(id=row['id'], first_manifest_line=line_number,
                                              original_file=name.rsplit('/', 1)[0] + '/' + row['file']))
cases = []
for key, observations in sorted(groups.items()):
    if len(observations) < 2:
        continue
    source = dict(zip(fields, key[1:]))
    signature = json.dumps([key[0], source], sort_keys=True, separators=(',', ':'))
    case_id = 'slot-v1-' + hashlib.sha256(signature.encode()).hexdigest()[:20]
    members = []
    for row in sorted(observations.values(), key=lambda r:r['first_manifest_line']):
        image = images[row['id']]
        members.append(row | dict(status=image['status'], names=image['names'], archives=image['archives'],
                                  dimensions=[image['width'], image['height']], render_target_sample=image['render_target_sample']))
    render_target_role = all(m['render_target_sample'] for m in members)
    cases.append(dict(case_id=case_id, run=key[0], source=source, members=members,
                      role='observed_render_target_samples' if render_target_role else 'mutable_source_unknown_role',
                      proven='Distinct original RGBA identities were observed for identical source metadata in this run.',
                      unresolved='Per-draw write history and vblank timestamps were not recorded; no archived asset name established.' if render_target_role else
                                 'Texel/CLUT mutation, streaming reuse or generated/animated cause is not established. No vblank timestamps were recorded.',
                      replacement_policy='Each verified RGBA identity needs its own content filename; do not bind by this memory address.'))
member_ids = {m['id'] for c in cases for m in c['members']}
unresolved_ids = {r['id'] for r in images.values() if r['status']=='runtime_only_unresolved'}
report = dict(scope='Observed mutable decoded source configurations, not a complete dynamic texture census.',
              excluded='Shared live manifests and zero addresses. Cross-run address equality is not continuity evidence.',
              catalog_sha256=hashlib.file_digest(catalog_path.open('rb'),'sha256').hexdigest(),
              manifest_sha256=hashes, case_count=len(cases), member_ids=len(member_ids),
              render_target_ids_in_cases=sum(images[id_]['render_target_sample'] for id_ in member_ids),
              unresolved_origin_ids_in_cases=len(member_ids & unresolved_ids), cases=cases)
(root / 'outputs/TEXTURE-MUTABILITY-099.json').write_text(json.dumps(report, indent=2)+'\n')
with (out / 'mutable-sources.csv').open('w', newline='', encoding='utf-8-sig') as f:
    columns = ['case_id','run','role',*fields,'id','first_manifest_line','names','status','original_file','review']
    writer = csv.DictWriter(f,fieldnames=columns)
    writer.writeheader()
    for case in cases:
        for row in case['members']:
            writer.writerow(dict(case_id=case['case_id'],run=case['run'],**case['source'],
                                 role=case['role'],
                                 id=row['id'],first_manifest_line=row['first_manifest_line'],
                                 names=' | '.join(row['names']),status=row['status'],original_file=row['original_file'],
                                 review='Observed decoded content change; cause unresolved. Use each content ID filename.'))
print(json.dumps({k:report[k] for k in ['case_count','member_ids','render_target_ids_in_cases','unresolved_origin_ids_in_cases','scope']},indent=2))
