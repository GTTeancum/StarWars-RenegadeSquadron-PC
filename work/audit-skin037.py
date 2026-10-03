"""Load a real weighted MSH, explicit mapping and diffuse image as one unit.

Identity corrections are loader fixtures, NOT a playable retarget mapping.
Only copies under the local ignored work/mods-skin037-io directory are changed.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parent.parent
exe = root / 'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'
env = os.environ.copy()
env['PATH'] = str(root / 'work/windows-sdk/bin') + os.pathsep + env.get('PATH', '')
source = Path('Z:/Modding/SWBF2_Modtools/assets/sides/cis/msh')
model_source = source / 'cis_inf_bdroid_low1.msh'
texture_source = source / 'PC/cis_inf_battledroid.tga'
destination = root / 'work/mods-skin037-io'
destination.mkdir(exist_ok=True)
model = destination / model_source.name
texture = destination / texture_source.name
shutil.copyfile(model_source, model)
shutil.copyfile(texture_source, texture)
metadata = subprocess.run([str(exe), '--skeleton', str(model)], env=env,
                          capture_output=True, text=True, check=True)
nodes = json.loads(metadata.stdout)['nodes']
mapping = destination / 'identity.bindings'
matrix = '1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'
mapping.write_text('RS_SKIN_BINDINGS 1\n' + str(len(nodes)) + '\n' +
                   ''.join(f'{n["index"]} {i} {matrix}\n' for i, n in enumerate(nodes)))
results = []

def run(label):
    result = subprocess.run([str(exe), '--skin-load', str(model), str(mapping)],
                            env=env, capture_output=True, text=True)
    results.append(dict(case=label, exit_code=result.returncode,
                        stdout=result.stdout, stderr=result.stderr))
    return result

valid = run('real weighted model and TGA')
assert valid.returncode == 0, valid.stderr
summary = json.loads(valid.stdout)
assert summary['vertices'] == 1446 and summary['textured_segments'] == summary['segments'] > 0
# A corrupt preferred DDS must reject the candidate instead of changing material
# selection silently. The original TGA and model remain intact.
preferred = texture.with_suffix('.dds')
assert not preferred.exists(), 'Unexpected local DDS; refusing to overwrite'
try:
    preferred.write_bytes(b'broken DDS test')
    invalid = run('corrupt preferred DDS rejects complete skin')
    assert invalid.returncode == 1 and invalid.stderr
finally:
    preferred.unlink(missing_ok=True)
restored = run('TGA load after corrupt test copy removed')
assert restored.returncode == 0 and restored.stdout == valid.stdout
paths = [model_source, texture_source, model, texture, mapping, exe, Path(__file__),
         root / 'work/build-windows-native/bin/RenegadeNative.exe']
report = dict(scope='Loader and identity-pose deformation only; no game retargeting or animated rendering.',
              results=results,
              hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root / 'outputs/SKIN-037-real-asset.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(results, indent=2))
