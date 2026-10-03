"""Revalidate the retained original conversion intake; make no source matches."""
import csv, hashlib, json, struct
from pathlib import Path, PureWindowsPath
root = Path(__file__).resolve().parent.parent
intake = json.loads((root / 'outputs/TEXTURE-SOURCES-058.json').read_text())
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
archives, images, failures = [], [], []
for old in intake['archives']:
    archive = root / old['archive'].replace('\\', '/')
    current = sha(archive)
    row = dict(archive=archive.relative_to(root).as_posix(), sha256=current,
               bytes=archive.stat().st_size, image_count=len(old['images']))
    archives.append(row)
    if current != old['sha256'] or row['bytes'] != old['bytes']:
        failures.append(dict(archive=row['archive'], reason='Original archive changed from intake'))
    for old_image in old['images']:
        name = PureWindowsPath(old_image['path'])
        assert not name.is_absolute() and not name.drive and '..' not in name.parts
        path = root / 'work/texture-sources058' / archive.stem / Path(*name.parts)
        if not path.is_file():
            failures.append(dict(file=str(path), reason='Missing extracted original source'))
            continue
        digest = sha(path)
        if digest != old_image['sha256'] or path.stat().st_size != old_image['bytes']:
            failures.append(dict(file=str(path), reason='Extracted source changed from intake'))
        w = h = None
        if path.suffix.lower() == '.tga':
            with path.open('rb') as f:
                head = f.read(18)
            if len(head) == 18:
                w, h = struct.unpack_from('<HH', head, 12)
        images.append(dict(archive=row['archive'], file=path.relative_to(root).as_posix(),
                           name=path.name, bytes=path.stat().st_size, sha256=digest, width=w, height=h,
                           review='Not newly matched or transformed; original-source index for manual review'))
    print(f'{archive.name}: {len(old["images"])} source hashes checked', flush=True)
actual = {p.name for p in (root / 'SWBF2 PSP mod maps').glob('*.7z')}
expected = {Path(a['archive']).name for a in archives}
if actual != expected:
    failures.append(dict(reason='Conversion archive inventory changed', added=sorted(actual-expected), missing=sorted(expected-actual)))
report = dict(scope='All retained intake files rehashed against original source manifest; not match acceptance or every-image rendering validation.',
              channel_policy='Source bytes/orientation/channels unchanged. PSP runtime RGBA IDs stay uncorrected. No new red/blue swap or authored-image transform.',
              archives=archives, image_count=len(images), image_bytes=sum(r['bytes'] for r in images), failures=failures)
(root / 'outputs/TEXTURE-SOURCES-095.json').write_text(json.dumps(report, indent=2) + '\n')
dest = root / 'work/texture-catalog095'
with (dest / 'original-sources.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(images[0]))
    writer.writeheader()
    writer.writerows(images)
(dest / 'original-sources.json').write_text(json.dumps(images, indent=2) + '\n')
assert not failures, 'See source integrity failures; do not assume unchanged originals'
print(json.dumps(dict(archives=len(archives), images=len(images), bytes=report['image_bytes'], failures=failures), indent=2))
