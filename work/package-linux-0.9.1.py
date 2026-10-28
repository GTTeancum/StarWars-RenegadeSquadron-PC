"""Run under Linux from the repository; package allowlisted runtime files only."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / '.local/release'
stage = out / 'linux-0.9.1-stage/RenegadeSquadronPC-Linux'
stage.mkdir(parents=True, exist_ok=False)
sdk = root / '.local/linux-deps/sdk/usr'
def copy(source, name):
    dest = stage / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return dest
exe = copy(root / '.local/build-linux/bin/RenegadeSquadron', 'RenegadeSquadron')
exe.chmod(0o755)
# Remove the machine-specific build RUNPATH; the launcher uses bundled libraries.
remove = out / 'linux-remove-rpath.cmake'
remove.write_text(f'file(RPATH_REMOVE FILE "{exe}")\n')
subprocess.run(['cmake', '-P', str(remove)], check=True)
for source, name in [
    ('lib/x86_64-linux-gnu/sdl2-compat/libSDL2-2.0.so.0', 'lib/libSDL2-2.0.so.0'),
    ('lib/x86_64-linux-gnu/libSDL3.so.0', 'lib/libSDL3.so.0'),
    ('lib/x86_64-linux-gnu/libXss.so.1', 'lib/libXss.so.1')]:
    copy(sdk / source, name)
for package in ['libsdl2-compat', 'libsdl3-0', 'libxss1']:
    copy(sdk / 'share/doc' / package / 'copyright', f'licenses/{package}.txt')
previous = out / 'RenegadeSquadronPC-0.9.1.zip'
assert hashlib.sha256(previous.read_bytes()).hexdigest() == '6f7d040267d6bdda6850173cfc24cdca85258541995dd2c8d943694535bffd7e'
with zipfile.ZipFile(previous) as z:
    for name in ['RenegadeSquadron.ini', 'CONTROLS-0.9b.txt',
                 'mods/files/PSP_GAME/USRDIR/GUIMENU/BFF_GUIMENU_INGAMESP.GUI',
                 'mods/files/PSP_GAME/USRDIR/GUIMENU/BFF_MAINMENU.GUI',
                 'mods/files/PSP_GAME/USRDIR/GUIMENU/BFF_OPTIONS.GUI',
                 'mods/files/PSP_GAME/USRDIR/MISC/MENU/MENU_AM.ASR']:
        dest = stage / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(z.read('RenegadeSquadronPC/' + name))
copy(root / 'docs/releases/0.9.1-linux.md', 'README.md')
launcher = stage / 'Play-RenegadeSquadron.sh'
launcher.write_text('''#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")"
mkdir -p .local/tmp .local/cache
export TMPDIR="$PWD/.local/tmp" XDG_CACHE_HOME="$PWD/.local/cache"
export LD_LIBRARY_PATH="$PWD/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
ulimit -s 16384
exec ./RenegadeSquadron "$@"
''')
launcher.chmod(0o755)
(stage / 'data').mkdir(exist_ok=True)
(stage / 'mods/textures').mkdir(parents=True, exist_ok=True)
manifest = [{'path': p.relative_to(stage).as_posix(), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(stage.rglob('*')) if p.is_file()]
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
archive = out / 'RenegadeSquadronPC-0.9.1-linux-ubuntu26.04-x86_64.tar.gz'
def attributes(info):
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    info.mode = 0o755 if info.isdir() or info.name.endswith(('RenegadeSquadron', '.sh')) else 0o644
    return info
with tarfile.open(archive, 'w:gz') as t:
    t.add(stage, arcname=stage.name, filter=attributes)
with tarfile.open(archive) as t:
    for row in manifest:
        assert hashlib.sha256(t.extractfile(stage.name + '/' + row['path']).read()).hexdigest() == row['sha256']
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_name(archive.name + '.sha256').write_text(f'{digest}  {archive.name}\n')
print(json.dumps({'file': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest}, indent=2))
