"""Create a verified source-only snapshot from Git's tracked/unignored file set."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
out=root/'outputs/SOURCE-061.zip'
if out.exists():raise SystemExit('Snapshot already exists; use a new checkpoint number.')
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
paths=sorted({Path(n).as_posix() for n in names if n and (root/n).is_file()})
for name in paths:
    p=Path(name)
    assert not p.is_absolute() and '..' not in p.parts
    assert not name.startswith(('work/game/','work/runs/','work/windows-sdk/','work/mods-','work/reference-'))
    assert p.suffix.lower() not in {'.iso','.7z','.zip','.msh','.tga','.dds','.png','.exe','.dll','.lib','.wav'},name
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest={name:sha((root/name).read_bytes()) for name in paths}
with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in paths:z.write(root/name,name)
    z.writestr('SNAPSHOT-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    assert all(sha(z.read(name))==digest for name,digest in manifest.items())
build_inputs=[root/'work/build-windows-native/CMakeCache.txt',root/'work/configure-windows.cmd',root/'work/build-windows.cmd',root/'work/build-tools/cmake/data/bin/cmake.exe',root/'work/build-tools/bin/ninja.exe',Path('C:/Program Files/Microsoft Visual Studio/18/Community/VC/Tools/MSVC/14.44.35207/bin/HostX64/x64/cl.exe')]
build_inputs+=list((root/'work/windows-sdk').rglob('*'))
report={'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'python':sys.version,'snapshot':out.name,'file_count':len(paths),'archive_sha256':sha(out.read_bytes()),'verified_every_entry':True,'source_sha256':manifest,'build_input_sha256':{str(p):sha(p.read_bytes()) for p in build_inputs if p.is_file()},'excluded':'Game disc, proprietary test assets, reference clone, dependencies, binaries and native run payloads; dependency/build identities recorded separately. Local source snapshot, not a fresh-machine build test.'}
(root/'outputs/SOURCE-061-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','build_input_sha256']},indent=2))
