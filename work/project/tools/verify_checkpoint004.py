#!/usr/bin/env python3
"""Stream-verify a checkpoint ZIP; optionally extract into a new directory.
Checks names, duplicate members, record sizes, SHA-256, and ZIP CRC. Never
executes a program or downloads data. Requires Python 3.11+.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, stat, tempfile, zipfile
from pathlib import Path, PurePosixPath

def safe_name(name: str) -> None:
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '\\' in name or ':' in name or '..' in p.parts or p.as_posix() != name:
        raise ValueError(f'Unsafe checkpoint path: {name!r}')

def process(archive: Path, output: Path | None = None) -> int:
    destination = output.resolve() if output is not None else None
    if destination is not None and destination.exists():
        raise ValueError('Extraction destination must not already exist')
    temporary: Path | None = None
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='.renegade-verify-', dir=destination.parent))
    try:
        with zipfile.ZipFile(archive) as z:
            members = z.infolist()
            names = [i.filename for i in members]
            if len(names) > 10000 or len(set(names)) != len(names):
                raise ValueError('Too many or duplicate ZIP members')
            for i in members:
                safe_name(i.filename)
                if i.is_dir() or stat.S_ISLNK(i.external_attr >> 16):
                    raise ValueError('Directory and link entries are not supported')
            info = z.getinfo('manifest.json')
            if info.file_size > 8 * 1024 * 1024:
                raise ValueError('Manifest exceeds bound')
            raw = z.read(info)
            m = json.loads(raw)
            if m.get('format') != 'renegade-native-checkpoint-v4':
                raise ValueError('Unknown checkpoint format')
            records = m['files']
            if not records or len({f['path'] for f in records}) != len(records):
                raise ValueError('Empty or duplicate manifest records')
            if set(names) != {'manifest.json', *(f['path'] for f in records)}:
                raise ValueError('ZIP and manifest members differ')
            if sum(f['size'] for f in records) > 2 * 1024 ** 3:
                raise ValueError('Uncompressed checkpoint exceeds 2 GiB')
            for f in records:
                safe_name(f['path']); i = z.getinfo(f['path'])
                if f['size'] < 0 or i.file_size != f['size']:
                    raise ValueError('Member size mismatch: ' + f['path'])
                h = hashlib.sha256(); count = 0
                target = temporary / f['path'] if temporary is not None else None
                if target is not None:
                    target.parent.mkdir(parents=True, exist_ok=True)
                out = target.open('xb') if target is not None else None
                try:
                    with z.open(i) as stream:
                        while chunk := stream.read(1024 * 1024):
                            h.update(chunk); count += len(chunk)
                            if out is not None: out.write(chunk)
                finally:
                    if out is not None: out.close()
                if count != f['size'] or h.hexdigest() != f['sha256']:
                    raise ValueError('Member digest mismatch: ' + f['path'])
                if target is not None:
                    os.chmod(target, 0o755 if f.get('executable', False) else 0o644)
            if temporary is not None:
                (temporary / 'manifest.json').write_bytes(raw)
                temporary.rename(destination); temporary = None
            return len(records)
    finally:
        if temporary is not None: shutil.rmtree(temporary)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('--extract',type=Path)
    a=p.parse_args()
    try: print(f'Verified {process(a.archive,a.extract)} checkpoint payloads (SHA-256 and ZIP CRC).')
    except (ValueError,KeyError,OSError,zipfile.BadZipFile) as e: p.exit(2,f'Checkpoint rejected: {e}\n')
