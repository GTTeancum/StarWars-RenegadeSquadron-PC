"""Verify archive/runtime texture identities and build a manual matching catalog.

No source-image matching, replacements, resampling, rotation or channel swaps.
Runtime previews are lossless PNG encodings of the verified original RGBA pixels.
"""
import csv, hashlib, io, json, re, struct
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent.parent
disc = root / 'work/game/disc/PSP_GAME/USRDIR'
out = root / 'work/texture-catalog101'
out.mkdir(exist_ok=True)
(out / 'previews').mkdir(exist_ok=True)
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
source_index_state = json.loads((root/'outputs/TEXTURES-100-state.json').read_text())
for filename in ['original-sources.csv', 'original-sources.json']:
    prior = root/'work/texture-catalog100'/filename
    prior_name = prior.relative_to(root).as_posix()
    assert sha(prior) == source_index_state['artifact_sha256'][prior_name]
    destination = out/filename
    if destination.exists():
        assert destination.read_bytes() == prior.read_bytes()
    else:
        destination.write_bytes(prior.read_bytes())

def load(p):
    data = p.read_bytes()
    if p.suffix.lower() == '.tga' and len(data) < 26:
        data += bytes(26 - len(data))  # in-memory footer probe padding only
    return Image.open(io.BytesIO(data)).convert('RGBA')

def identity(im):
    return 'tex-v1-' + hashlib.sha256(struct.pack('<II', *im.size) + im.tobytes()).hexdigest()

def relative(p):
    return p.relative_to(root).as_posix()

catalog_path = root / 'work/texture-dumps058/catalog.json'
archive_catalog = json.loads(catalog_path.read_text())
assert not archive_catalog['failures']
origins = defaultdict(list)
for row in archive_catalog['textures']:
    origins[row['id']].append(row)
images, rgb_index = {}, defaultdict(list)
for id_, rows in sorted(origins.items()):
    p = root / 'work/texture-dumps058/textures' / (id_ + '.png')
    im = load(p)
    assert identity(im) == id_, p
    assert all((row['width'], row['height']) == im.size for row in rows)
    images[id_] = dict(id=id_, width=im.width, height=im.height, original=relative(p),
                      original_sha256=sha(p), preview=relative(p), archive_records=rows,
                      runtime_records=[], status='archive_rgba')
    rgb_index[hashlib.sha256(struct.pack('<II', *im.size) + im.convert('RGB').tobytes()).hexdigest()].append(id_)
print(f'Archive original identities verified: {len(images)}', flush=True)

# Check every kind-2 texture chunk independently against the retained catalog,
# including zero-texture archives and trailing bytes. Unknown formats fail the
# archive audit explicitly rather than being mistaken for complete extraction.
archives, unsupported, missing_archives = [], [], []
known_archives = {a['archive']: a for a in archive_catalog['archives']}
occurrences = defaultdict(list)
for row in archive_catalog['textures']:
    occurrences[(row['archive'], row['offset'])].append(row)
inventory = []
for p in sorted(disc.rglob('*')):
    if not p.is_file():
        continue
    with p.open('rb') as f:
        head = f.read(16)
    area = p.relative_to(disc).parts[0]
    if head[:8] != b'Asura   ' and area not in {'ENVS', 'GUIMENU', 'GRAPHICS', 'MISC'}:
        continue
    name = p.relative_to(disc).as_posix()
    if head[:8] != b'Asura   ':
        inventory.append(dict(file=name, sha256=sha(p), header_hex=head.hex(),
                              status='standalone_png' if head.startswith(b'\x89PNG') else 'non_asura_resource'))
        continue
    b = p.read_bytes()
    if name not in known_archives:
        # Other sound/text archives are inventoried, not assumed to contain
        # texture payloads merely because they share the Asura container.
        expected = None
    else:
        expected = known_archives[name]
        assert hashlib.sha256(b).hexdigest() == expected['sha256'], name
    at, chunks, formats = 8, 0, Counter()
    try:
        while at + 16 <= len(b):
            if len(b) - at <= 16 and not any(b[at:]):
                at = len(b)
                break
            size = struct.unpack_from('<I', b, at + 4)[0]
            assert size >= 16 and at + size <= len(b), f'{name}: chunk boundary {at}'
            c = b[at:at + size]
            if c[:4] == b'RSCF' and len(c) >= 32 and struct.unpack_from('<I', c, 16)[0] == 2:
                chunks += 1
                end = c.index(0, 28)
                pos = 28 + ((end - 28 + 4) & ~3)
                payload = c[pos:]
                assert len(payload) >= 8
                w, h, reserved, fmt, mipmax = struct.unpack_from('<HHHBB', payload)
                formats[fmt] += 1
                rows = occurrences[(name, at)]
                if fmt not in (4, 5) or reserved or not rows:
                    unsupported.append(dict(archive=name, offset=at, format=fmt,
                                            reason='unsupported header or texture chunk absent from decoded catalog'))
                else:
                    assert {r['mip'] for r in rows} == set(range(mipmax + 1)), (name, at)
                    assert all(r['payload_sha256'] == hashlib.sha256(payload).hexdigest() for r in rows)
            at += size
        assert not any(b[at:]), f'{name}: nonzero trailer'
    except (AssertionError, ValueError, struct.error) as e:
        unsupported.append(dict(archive=name, reason=str(e)))
    if expected:
        assert expected['texture_chunks'] == chunks, name
    elif chunks:
        missing_archives.append(name)
    archives.append(dict(archive=name, sha256=hashlib.sha256(b).hexdigest(), bytes=len(b),
                         texture_chunks=chunks, texture_formats=dict(formats), decoded_catalog=expected is not None))
print(f'Asura containers audited: {len(archives)}; uncatalogued texture archives: {len(missing_archives)}', flush=True)

# Runtime provenance belongs to each private run's dump manifest. Shared live
# manifests cannot truthfully be attributed to individual runs after the fact.
run_rows, manifests = {}, []
observed_archives = defaultdict(set)
for folder in sorted((root / 'work/runs').iterdir()):
    state_path = folder / 'run.json'
    if not state_path.is_file():
        continue
    state = json.loads(state_path.read_text())
    success = state.get('state') == 'finished' and state.get('exit_code') == 0 and not state.get('timed_out')
    terminal = state.get('state') == 'finished'
    run_rows[folder.name] = dict(state=state.get('state'), exit_code=state.get('exit_code'),
                               timed_out=state.get('timed_out'), successful_terminal=success,
                               state_sha256=sha(state_path), binary_sha256=state.get('native_binary_sha256'))
    log = folder / 'native.log'
    if success and log.is_file():
        for line in log.read_text(errors='replace').splitlines():
            if '[io] raw UMD open' in line:
                m = re.search(r'[\\/]((?:ENVS|GUIMENU|GRAPHICS|MISC)[\\/][^"\r\n]+)"', line)
                if m:
                    observed_archives[m.group(1).replace('\\', '/')].add(folder.name)
    manifest = folder / 'textures/textures.jsonl'
    if terminal and manifest.is_file():
        manifests.append((manifest, folder.name, success))
live = root / 'work/texture-dumps-live/textures/textures.jsonl'
if live.is_file():
    manifests.append((live, None, None))

errors, runtime_ids, manifest_hashes = [], set(), {}
for manifest, run, success in manifests:
    manifest_hashes[relative(manifest)] = sha(manifest)
    unique_rows = set()
    for number, line in enumerate(manifest.read_text().splitlines(), 1):
        try:
            row = json.loads(line)
            id_ = row['id']
            assert re.fullmatch(r'tex-v1-[0-9a-f]{64}', id_)
            assert row['file'] == id_ + '.tga', 'Unexpected runtime filename'
            packed = json.dumps(row, sort_keys=True)
            if packed in unique_rows:
                continue
            unique_rows.add(packed)
            p = manifest.parent / row['file']
            im = load(p)
            assert identity(im) == id_, 'Runtime RGBA identity mismatch'
            assert im.size == (row['width'], row['height'])
            runtime_ids.add(id_)
            if id_ not in images:
                rgb = hashlib.sha256(struct.pack('<II', *im.size) + im.convert('RGB').tobytes()).hexdigest()
                matches = sorted(rgb_index.get(rgb, []))
                status = 'exact_archive_rgb_alpha_variant' if matches else 'runtime_only_unresolved'
                if row.get('address') == 0:
                    status = 'runtime_zero_address'
                preview = out / 'previews' / (id_ + '.png')
                if not preview.exists():
                    im.save(preview)
                assert identity(load(preview)) == id_
                # Supply missing originals to the common manual-matching folder
                # as a lossless PNG; retain original TGA and its source path.
                merged = live.parent / (id_ + '.png')
                if not merged.exists():
                    merged.write_bytes(preview.read_bytes())
                assert identity(load(merged)) == id_
                images[id_] = dict(id=id_, width=im.width, height=im.height, original=relative(p),
                                  original_sha256=sha(p), preview=relative(preview), archive_records=[],
                                  runtime_records=[], status=status, exact_rgb_archive_ids=matches)
            observation = dict(run=run, successful_terminal=success, manifest=relative(manifest),
                               provenance='per_run_manifest' if run else 'shared_live_manifest_run_unattributed', **row)
            images[id_]['runtime_records'].append(observation)
        except (AssertionError, KeyError, ValueError, OSError) as e:
            errors.append(dict(manifest=relative(manifest), line=number, reason=str(e)))
    print(f'Runtime manifest audited: {run or "shared live"} ({len(unique_rows)} distinct observations)', flush=True)

standalone = []
for p in sorted((root / 'work/game/disc').rglob('*.png')):
    im = load(p)
    id_ = identity(im)
    row = dict(file=relative(p), id=id_, sha256=sha(p), width=im.width, height=im.height)
    standalone.append(row)
    if id_ not in images:
        images[id_] = dict(id=id_, width=im.width, height=im.height, original=relative(p),
                          original_sha256=row['sha256'], preview=relative(p), archive_records=[],
                          runtime_records=[], status='standalone_disc_png')
    images[id_].setdefault('standalone_records', []).append(row)
    merged = live.parent / (id_ + '.png')
    if not merged.exists():
        im.save(merged)
    assert identity(load(merged)) == id_

pack_report = json.loads((root / 'outputs/TEXTURE-PACK-074.json').read_text())
bindings = {row['id']: row for row in pack_report['files']}
pack_errors = []
for id_, row in images.items():
    row['runtime_observed'] = bool(row['runtime_records'])
    row['base_image'] = any(r['mip'] == 0 for r in row['archive_records'])
    row['names'] = sorted({r['name'] for r in row['archive_records']})
    row['archives'] = sorted({r['archive'] for r in row['archive_records']})
    row['manual_override'] = None
    row['existing_pack_override'] = None
    for label, pack in [('manual_override', 'work/mods-user'), ('existing_pack_override', 'work/mods-textures-source074')]:
        for ext in ('.dds', '.tga', '.png'):
            path = root / pack / 'textures' / (id_ + ext)
            if path.is_file():
                row[label] = dict(file=relative(path), sha256=sha(path))
                if label == 'existing_pack_override' and id_ in bindings and sha(path) != bindings[id_]['sha256']:
                    pack_errors.append(dict(id=id_, reason='Existing pack image changed from provenance manifest'))
                break
    row['classification_scope'] = ('Exact archived RGBA/name provenance' if row['archive_records'] else
                                    'No named archive identity established; do not infer dynamic cause from absence alone')
    row['exact_rgb_related_names'] = sorted({r['name'] for match in row.get('exact_rgb_archive_ids', [])
                                            for r in origins[match]})

# Classify full-size unswizzled RGBA samples at render targets observed in
# the same run. This is a concrete framebuffer provenance category, not an
# inferred game-resource name or proof of every dynamic rendering mechanism.
render_targets, target_evidence_sha256 = defaultdict(set), {}
for run in run_rows:
    folder = root / 'work/runs' / run
    log = folder / 'native.log'
    if log.is_file():
        text = log.read_text(errors='replace')
        for m in re.finditer(r'\[frame\][^\r\n]* address=0x([0-9a-fA-F]+)', text):
            address = int(m.group(1), 16)
            if (address & 0x3f000000) == 0x04000000:
                render_targets[run].add(address & 0x001ffff0)
        if render_targets[run]: target_evidence_sha256[relative(log)] = sha(log)
    path = folder / 'render-report.jsonl'
    if path.is_file():
        for line in path.read_text().splitlines():
            frame = json.loads(line)
            for probe in frame.get('probes', []):
                render_targets[run].add(int(probe['target']) & 0x001ffff0)
            for read in frame.get('surface_reads', []):
                render_targets[run].add(int(read['target']) & 0x001ffff0)
        target_evidence_sha256[relative(path)] = sha(path)
for row in images.values():
    evidence = [o for o in row['runtime_records'] if o['run'] and
                (o.get('address', 0) & 0x3f000000) == 0x04000000 and
                (o['address'] & 0x001ffff0) in render_targets[o['run']] and
                o.get('format') == 3 and not o.get('swizzled') and
                o.get('buffer_width') == 512 and o['width'] == 512 and o['height'] == 512]
    row['render_target_records'] = evidence
    row['render_target_sample'] = bool(evidence)
    if evidence and row['status'] == 'runtime_only_unresolved':
        row['status'] = 'runtime_render_target_sample'
        row['classification_scope'] = 'Full-size unswizzled RGBA texture sample at a same-run observed render target; no archived game-resource name established.'

coverage = []
for a in archive_catalog['archives']:
    ids = sorted({r['id'] for r in archive_catalog['textures'] if r['archive'] == a['archive']})
    base_ids = sorted({r['id'] for r in archive_catalog['textures'] if r['archive'] == a['archive'] and r['mip'] == 0})
    coverage.append(dict(archive=a['archive'], texture_chunks=a['texture_chunks'], unique_ids=len(ids),
                         base_ids=len(base_ids), base_ids_seen_anywhere=sum(images[i]['runtime_observed'] for i in base_ids),
                         successful_runs_opened=sorted(observed_archives.get(a['archive'], []))))

rows = sorted(images.values(), key=lambda r: r['id'])
counts = dict(archive_containers=len(archives), texture_archives=len(archive_catalog['archives']),
              archive_texture_chunks=sum(a['texture_chunks'] for a in archive_catalog['archives']),
              archived_mip_occurrences=len(archive_catalog['textures']), archived_unique_ids=len(origins),
              runtime_unique_ids=len(runtime_ids), catalog_unique_ids=len(rows), standalone_pngs=len(standalone),
              runtime_only_ids=len(runtime_ids - origins.keys()), runtime_manifests=len(manifests),
              status_counts=dict(Counter(r['status'] for r in rows)),
              env_archives_opened=sum(bool(c['successful_runs_opened']) for c in coverage if c['archive'].startswith('ENVS/')))
runtime_formats = Counter()
for id_ in runtime_ids:
    for fmt in {r['format'] for r in images[id_]['runtime_records']}:
        runtime_formats[fmt] += 1
counts['runtime_formats_unique_ids'] = dict(runtime_formats)
counts['render_target_sample_ids'] = sum(r['render_target_sample'] for r in rows)
report = dict(scope='Verified static archive extraction plus encountered runtime originals; shared content IDs seen anywhere do not prove a particular map was visited, and opens do not prove visual/traversal coverage.',
              policy='Manual matching only. No transforms, source matching, new bindings or upscaling. Original hash uses LE width/height followed by runtime RGBA.',
              counts=counts, archives=archives, non_asura_resources=inventory, coverage=coverage,
              unsupported=unsupported, uncatalogued_texture_archives=missing_archives,
              runtime_errors=errors, pack_errors=pack_errors, runs=run_rows,
              manifest_sha256=manifest_hashes, render_target_evidence_sha256=target_evidence_sha256, archive_catalog_sha256=sha(catalog_path), images=rows)
(out / 'catalog.json').write_text(json.dumps(report, indent=2) + '\n')
with (out / 'textures.csv').open('w', newline='', encoding='utf-8-sig') as f:
    fields = ['id', 'width', 'height', 'status', 'base_image', 'runtime_observed', 'names', 'archives', 'original', 'original_sha256']
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        flat = {k: row[k] for k in fields}
        flat['names'] = ' | '.join(flat['names'])
        flat['archives'] = ' | '.join(flat['archives'])
        writer.writerow(flat)
(root / 'outputs/TEXTURE-CATALOG-101.json').write_text(json.dumps({k: v for k, v in report.items() if k != 'images'}, indent=2) + '\n')
unresolved = [r for r in rows if r['status'] in {'runtime_only_unresolved', 'runtime_zero_address', 'exact_archive_rgb_alpha_variant', 'runtime_render_target_sample'}]
with (out / 'runtime-review.csv').open('w', newline='', encoding='utf-8-sig') as f:
    fields = ['id', 'width', 'height', 'status', 'original', 'original_sha256', 'exact_rgb_related_names', 'review']
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in unresolved:
        writer.writerow({k: r[k] for k in fields if k != 'review'} | {
            'exact_rgb_related_names': ' | '.join(r['exact_rgb_related_names']),
            'review': 'Observed render-target sample; changing content retained. No new override accepted.' if r['render_target_sample'] else 'Unresolved origin; no new override accepted. Dynamic cause not established.'})
lines = ['# Texture coverage — checkpoint 101', '',
         f"{counts['texture_archives']} texture archives: {counts['archive_texture_chunks']} resource chunks, "
         f"{counts['archived_mip_occurrences']} mip occurrences, {counts['archived_unique_ids']} archived content IDs.",
         f"Consolidated catalog: {counts['catalog_unique_ids']} IDs, including {counts['runtime_only_ids']} runtime IDs outside exact named RGBA provenance.", '',
         'Runtime observations are collected from retained dump manifests. An archive open is not full traversal or visual acceptance.', '',
         '| Archive | Base IDs | IDs seen anywhere (shared) | Successful runs opened |', '| --- | ---: | ---: | ---: |']
lines += [f"| {c['archive']} | {c['base_ids']} | {c['base_ids_seen_anywhere']} | {len(c['successful_runs_opened'])} |" for c in coverage]
lines += ['', 'Static parser rejects unknown texture headers instead of silently dropping them. ' +
          ('No such cases were found in this inventory.' if not unsupported else f'{len(unsupported)} cases require review; see JSON.'),
          f"{counts['status_counts'].get('runtime_only_unresolved',0)} runtime-only textures remain origin-unresolved; "
          f"{counts['status_counts'].get('exact_archive_rgb_alpha_variant',0)} have exact dimensions/RGB matching archived originals with different alpha, "
          f"and {counts['status_counts'].get('runtime_zero_address',0)} is a zero-address texture.",
          f"{counts['render_target_sample_ids']} originals are unswizzled RGBA samples at same-run observed render targets. They remain available but are excluded from the default manual image view. No asset names or full dynamic census are inferred.",
          'No new authored matches, transforms, replacements or upscales were generated. Shared live manifest records cannot be attributed to individual runs after the fact.', '']
(root / 'outputs/TEXTURE-COVERAGE-101.md').write_text('\n'.join(lines))
assert not unsupported and not missing_archives and not errors and not pack_errors, 'See explicit catalog errors; coverage is not complete'
print(json.dumps(counts, indent=2), flush=True)
