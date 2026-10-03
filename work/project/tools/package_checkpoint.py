#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,time,zipfile
r=Path('/mnt/data/renegade');profile=r/'intake/sources/PSPRecomp/profiles/renegade'
status=json.loads((r/'build-status.json').read_text()) if (r/'build-status.json').exists() else {'first_level_gameplay_verified':False,'status':'Build or diagnostics not yet completed; consult included logs.'}
readme='''# Renegade Squadron native recompilation — experimental checkpoint

This is build work toward ULUS10292 first-campaign-level gameplay, NOT a playable release and NOT evidence that that goal has been met.

The native target is Linux x86-64 for the scratch environment. No Windows binary is promised by this checkpoint. PPSSPP is not the native executable.

## Evidence

Read `build-status.json` and `logs/` for the executed stages, compiler output and any native run stop reason. A successful build, dispatch, import, or framebuffer file is not first-level gameplay. Gameplay acceptance remains false unless it has been directly tested and observed.

## Inputs

PSPRecomp commit: f6e7d415c7f447b934cc3865a31eb725f353d659
User-provided ULUS10292 BOOT.BIN SHA256:
f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68

The commercial ISO, BOOT.BIN and disc assets are deliberately excluded. The generated C++ is derived from that exact user-provided executable. Use the user's already-uploaded game archive and verified dependency intake to restore the working environment.

## Layout

- `profile/`: Renegade AOT sources and a bring-up host derived from MIT-licensed PSPRecomp services. VCS game-address overrides are not installed.
- `patches/`: generator changes and service differences against the pinned input.
- `tools/`: extraction, profile construction, generation/build, bounded runtime test and packaging helpers.
- `analysis/`: executable analysis and import reports when present.
- `logs/`: actual diagnostics; compiler failure and unresolved PSP services are not suppressed.
- `bin/`: native executable only if a build produced it; consult runtime logs before treating it as tested.

## Rebuild in a restored scratch workspace

Restore the dependency intake into `/mnt/data/renegade/intake` with its own `restore_intake.py --extract-sources`, and bootstrap the private SDK. Extract the supplied game with `tools/extract_game.py`.
Apply `patches/codegen-fixes.patch` in the pinned PSPRecomp source tree (once only), and copy `profile` to `sources/PSPRecomp/profiles/renegade`.
Configure CMake with `-DPSPRECOMP_PROFILE=renegade -DRENEGADE_SDK=/mnt/data/renegade/intake/sdk`, then build `RenegadeNative` with at most four parallel jobs on the 4 GiB scratch limit.

The tool scripts preserve their scratch paths so a subsequent scratch session can resume consistently. This is not a one-click Windows installation package.

## Remaining acceptance tests

A rendered first campaign level, movement, combat, active enemies, and mission progression must all be demonstrated in the native host. Missing HLE imports must be implemented with their actual PSP semantics, not blanket success stubs. Rendering and scheduling behavior inherited from another title still require title-specific validation.
'''
(r/'CHECKPOINT-README.md').write_text(readme)
out=Path('/mnt/data/RenegadeSquadron-Native-Checkpoint-001.zip');tmp=out.with_suffix('.partial')
entries=[]
for name in ['tools','patches','logs','analysis']:
 for f in (r/name).rglob('*'):
  if f.is_file() and f.suffix!='.pid':entries.append((f,str(f.relative_to(r))))
if profile.exists():
 for f in profile.rglob('*'):
  if f.is_file():entries.append((f,'profile/'+str(f.relative_to(profile))))
for name in ['CHECKPOINT-README.md','build-status.json','probe-status.json','finalization-status.json']:
 if (r/name).exists():entries.append((r/name,name))
binary=r/'intake/out/renegade/bin/RenegadeNative'
if binary.exists():entries.append((binary,'bin/RenegadeNative'))
probe=r/'intake/out/renegade/bin/RenegadeProbe'
if probe.exists():entries.append((probe,'bin/RenegadeProbe'))
license=r/'intake/sources/PSPRecomp/LICENSE'
if license.exists():entries.append((license,'LICENSE-PSPRecomp'))
manifest=[]
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for src,dest in entries:
  data=src.read_bytes();z.writestr(dest,data);manifest.append({'path':dest,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 z.writestr('checkpoint-manifest.json',json.dumps({'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'first_level_gameplay_verified':False,'files':manifest},indent=2))
tmp.replace(out)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 assert not any(x.endswith(('BOOT.BIN','EBOOT.BIN','.iso','.7z')) for x in z.namelist())
print(out, out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
