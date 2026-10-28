"""Package the tested player; reuse only allowlisted files from verified 0.9b."""
from pathlib import Path
import configparser
import hashlib
import io
import json
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / '.local/release'
previous = out / 'RenegadeSquadronPC-0.9b.zip'
assert hashlib.sha256(previous.read_bytes()).hexdigest() == '756bdab2501b8f69736eb971654d32d6a299a8406d20e68743ced51128a17a6d'
files = {}
with zipfile.ZipFile(previous) as old:
    prefix = 'RenegadeSquadronPC/'
    for name in ('msvcp140.dll', 'msvcp140_atomic_wait.dll', 'vcruntime140.dll', 'vcruntime140_1.dll',
                 'mods/files/PSP_GAME/USRDIR/GUIMENU/BFF_GUIMENU_INGAMESP.GUI',
                 'mods/files/PSP_GAME/USRDIR/GUIMENU/BFF_MAINMENU.GUI',
                 'mods/files/PSP_GAME/USRDIR/GUIMENU/BFF_OPTIONS.GUI',
                 'mods/files/PSP_GAME/USRDIR/MISC/MENU/MENU_AM.ASR'):
        files[name] = old.read(prefix + name)
    controls = old.read(prefix + 'README.txt').decode().replace('\r', '')
    files['CONTROLS-0.9b.txt'] = controls.encode()
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read_string(old.read(prefix + 'RenegadeSquadron.ini').decode())
    defaults = configparser.ConfigParser()
    defaults.optionxform = str
    defaults.read(root / 'work/rendering/vulkan.ini')
    for section in defaults:
        if section == 'DEFAULT':
            continue
        if section not in config:
            config.add_section(section)
        for key, value in defaults[section].items():
            config[section][key] = value
    ini = io.StringIO()
    config.write(ini)
    files['RenegadeSquadron.ini'] = ini.getvalue().encode()

files['RenegadeSquadron.exe'] = (root / 'work/build-perf/bin/RenegadeSquadron.exe').read_bytes()
for name in ('SDL2.dll', 'avcodec-61.dll', 'avformat-61.dll', 'avutil-59.dll', 'swresample-5.dll', 'swscale-8.dll'):
    files[name] = (root / 'work/windows-sdk/bin' / name).read_bytes()
files['README.txt'] = (root / 'docs/releases/0.9.1.md').read_bytes()
files['data/PUT PSP_GAME HERE.txt'] = b'Put an extracted PSP_GAME folder here, or put your US ULUS10292 ISO beside RenegadeSquadron.exe for automatic first-run extraction.\n'
for directory in (root / 'work/dependency-expansion010').iterdir():
    for p in directory.rglob('*'):
        if p.is_file() and p.name.lower().startswith(('license', 'copying')):
            files['licenses/' + directory.name + '/' + p.relative_to(directory).as_posix()] = p.read_bytes()
files['DEPENDENCIES.txt'] = b'SDL2 2.32.10: https://github.com/libsdl-org/SDL/releases/tag/release-2.32.10\nFFmpeg 7.1 LGPL shared build: https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-07-31-14-10\nPinned download URLs and hashes: work/restore-windows-dependencies.ps1 in the source release.\nMicrosoft Visual C++ runtime and existing PC menu overrides retained byte-for-byte from the verified v0.9b player package.\n'
manifest = [{'path': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in sorted(files.items())]
files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
archive = out / 'RenegadeSquadronPC-0.9.1.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for name, data in sorted(files.items()):
        z.writestr('RenegadeSquadronPC/' + name, data)
    z.writestr('RenegadeSquadronPC/mods/textures/', b'')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for row in manifest:
        assert hashlib.sha256(z.read('RenegadeSquadronPC/' + row['path'])).hexdigest() == row['sha256']
    z.extractall(out / 'verify-0.9.1')
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n')
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest, 'files': len(files)}, indent=2))
