from pathlib import Path
import hashlib, json, zipfile
root = Path(__file__).resolve().parents[1]
work = root / 'work'
out = root / 'outputs'
archive = out / 'RenegadeSquadron-Checkpoint-016-Instant-Action-Callback.zip'
if archive.exists():
    archive.unlink()
sha_sidecar = archive.with_suffix('.zip.sha256')
if sha_sidecar.exists():
    sha_sidecar.unlink()

files = {}
def add(arc, path):
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    if not p.exists():
        raise FileNotFoundError(f'{arc}: {p}')
    files[arc] = p

def add_if_exists(arc, path):
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    if p.exists():
        files[arc] = p

# Primary checkpoint artifacts.
for name in [
    'CHECKPOINT-016-INSTANT-ACTION-CALLBACK.md',
    'INSTANT-ACTION-016-results.json',
    'instant016a-vblank2640.png',
    'instant016b-vblank2576.png',
    'instant016c-vblank2772.png',
    'instant016c_flight-vblank2784.png',
    'instant016d-vblank2784.png',
    'instant016e-vblank2640.png',
    'instant016f-vblank2656.png',
    'instant016b-summary.json',
    'instant016c-summary.json',
    'instant016c_flight-summary.json',
    'instant016d-summary.json',
    'instant016e-summary.json',
    'instant016f-summary.json',
]:
    add_if_exists(f'outputs/{name}', out / name)

# Source and helper changes.
for rel in [
    'work/project/source/profiles/renegade/supplemental/callback_08896118.cpp',
    'work/project/source/profiles/renegade/tests/platform003.cpp',
    'work/instant016_runner.py',
    'work/write_instant016_results.py',
    'work/package016.py',
]:
    add_if_exists(rel, root / rel)

# Build and test evidence.
for rel in [
    'work/build-windows016-incremental.log',
    'work/build-windows016-incremental.exit',
    'work/test-platform016.log',
    'work/test-platform016.exit',
    'work/test-windows016.log',
    'work/test-windows016.exit',
    'work/build-windows-native/Testing/Temporary/LastTest.log',
    'work/runs/startup016/results.json',
]:
    add_if_exists(rel, root / rel)

# Runtime run evidence. Keep logs, inputs, state, and summaries without copying the huge native exe.
for run in ['instant016a', 'instant016b', 'instant016c', 'instant016c_flight', 'instant016d', 'instant016e', 'instant016f']:
    run_dir = work / 'runs' / run
    if run_dir.exists():
        for p in run_dir.rglob('*'):
            if p.is_file():
                add(f'work/runs/{run}/{p.relative_to(run_dir).as_posix()}', p)
for control in ['control-instant015a', 'control-instant015b', 'control-instant015c', 'control-instant015d', 'control-instant015e', 'control-instant015f']:
    control_dir = work / 'runs' / control
    if control_dir.exists():
        for p in control_dir.rglob('*'):
            if p.is_file() and p.suffix.lower() in {'.json', '.jsonl', '.log', '.txt'}:
                add(f'work/runs/{control}/{p.relative_to(control_dir).as_posix()}', p)

# Add a small binary fingerprint instead of the executable itself.
exe = work / 'build-windows-native' / 'bin' / 'RenegadeNative.exe'
exe_fingerprint = {
    'path': str(exe),
    'bytes': exe.stat().st_size,
    'sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
}

manifest = []
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for arc, path in sorted(files.items()):
        data = path.read_bytes()
        z.writestr(arc.replace('\\', '/'), data)
        manifest.append({'path': arc.replace('\\', '/'), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    z.writestr('binary-fingerprint.json', json.dumps(exe_fingerprint, indent=2) + '\n')
    manifest.append({'path': 'binary-fingerprint.json', 'bytes': len(json.dumps(exe_fingerprint, indent=2) + '\n'), 'sha256': hashlib.sha256((json.dumps(exe_fingerprint, indent=2) + '\n').encode()).hexdigest()})
    z.writestr('manifest.json', json.dumps({'files': manifest}, indent=2) + '\n')

with zipfile.ZipFile(archive) as z:
    bad = z.testzip()
    if bad is not None:
        raise RuntimeError(f'zip CRC failed for {bad}')
    manifest_loaded = json.loads(z.read('manifest.json'))['files']
    for row in manifest_loaded:
        if hashlib.sha256(z.read(row['path'])).hexdigest() != row['sha256']:
            raise RuntimeError(f'hash mismatch for {row["path"]}')

archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
sha_sidecar.write_text(f'{archive_hash}  {archive.name}\n')
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': archive_hash, 'payloads': len(manifest)}, indent=2))
