"""Independent decoded-image and deployment audit of the completed fallback pack."""
import argparse, hashlib, io, json, struct
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parent.parent
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
def load(p):
    b = p.read_bytes()
    return Image.open(io.BytesIO(b + bytes(max(0, 26-len(b))))).convert('RGBA')

plan_path = root/'outputs/UPSCALER-106-plan.json'
parser=argparse.ArgumentParser();parser.add_argument('--ui2',action='store_true');args=parser.parse_args()
report_path = root/('outputs/TEXTURE-PACK-106-ui2.json' if args.ui2 else 'outputs/TEXTURE-PACK-106.json')
plan = json.loads(plan_path.read_text())
report = json.loads(report_path.read_text())
assert sha(plan_path) == report['plan_sha256']
assert report['excluded'] == plan['excluded']
rows = {r['id']: r for r in report['files']}
assert len(rows) == len(report['files']) == len(plan['rows']) == 2568
authored = {r['id']: r for r in json.loads((root/'outputs/TEXTURE-PACK-074.json').read_text())['files']}
counts = Counter(); pixels = 0; artifacts = {report_path.relative_to(root).as_posix(): sha(report_path)}
for planned in plan['rows']:
    r = rows[planned['id']]
    original, replacement = root/r['original'], root/r['replacement']
    assert sha(original) == r['original_sha256'] == planned['original_sha256']
    assert sha(replacement) == r['replacement_sha256']
    source = load(original); final = load(replacement)
    assert 'tex-v1-'+hashlib.sha256(struct.pack('<II', *source.size)+source.tobytes()).hexdigest() == r['id']
    assert replacement.stem == r['id']
    providers = [replacement.with_suffix(ext) for ext in ['.dds', '.tga', '.png'] if replacement.with_suffix(ext).exists()]
    assert providers == [replacement], f'Ambiguous providers: {providers}'
    assert list(final.size) == r['output_size']
    if r['method'] == 'preferred_authored_source':
        a = authored[r['id']]; prior = root/a['replacement']
        assert replacement.read_bytes() == prior.read_bytes() and sha(prior) == a['sha256']
        side = prior.with_suffix('.json')
        if side.exists(): assert replacement.with_suffix('.json').read_bytes() == side.read_bytes()
    else:
        assert final.size == (source.width*4, source.height*4)
        src = np.asarray(source); dst = np.asarray(final)
        assert np.array_equal(dst[:,:,3], np.repeat(np.repeat(src[:,:,3],4,0),4,1))
        if r['method'] == 'integer4x_preserve' or r.get('effective_method','').startswith('integer4x_'):
            assert np.array_equal(dst, np.repeat(np.repeat(src,4,0),4,1))
        else:
            visible = src[:,:,3] > 0
            delta = (np.asarray(final.convert('RGB').resize(source.size, Image.Resampling.BOX)).astype(float)-src[:,:,:3])[visible]
            assert np.abs(delta).mean() <= 8 and np.percentile(np.abs(delta),99) <= 40
            assert np.max(np.abs(delta.mean(0))) <= 3
            assert 0 <= r['neural_weight'] <= .5
            assert sha(root/planned['neural']) == r['neural_sha256']
    counts[r.get('effective_method',r['method'])] += 1
    pixels += final.width*final.height
    artifacts[replacement.relative_to(root).as_posix()] = sha(replacement)
assert dict(counts) == report['effective_counts']
folder = root/('work/mods-upscale106-ui2' if args.ui2 else 'work/mods-upscale106')
assert not (folder/'models').exists()
assert len(list((folder/'textures').glob('*.png'))) + len(list((folder/'textures').glob('*.tga'))) == len(rows)
receipt = dict(deployed_images=len(rows), authored_preserved=len(authored), generated_images=len(rows)-len(authored),
               exact_alpha_generated=len(rows)-len(authored), effective_counts=dict(counts), output_pixels=pixels,
               excluded_dynamic_or_zero=len(plan['excluded']), artifact_sha256=artifacts,
               scope='Every decoded image identity, source/output hash, dimensions, alpha, provider uniqueness and authored precedence verified. Numerical source reconstruction bounds are not artistic certification. Gameplay acceptance is separate.')
p = root/('outputs/UPSCALER-106-ui2-verification.json' if args.ui2 else 'outputs/UPSCALER-106-verification.json')
if p.exists(): assert json.loads(p.read_text()) == receipt
else: p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='artifact_sha256'},indent=2))
