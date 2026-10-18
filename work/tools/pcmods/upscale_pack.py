r"""AI 4x upscale of every texture in the installed pack that is still the game's
original picture, written back into the pack as 32-bit TGA by name.

Models (chosen by the user from side-by-side samples, ONNX via esrgan_onnx.py,
run on the GPU through onnxruntime-directml in work\upscale-pc\venv):
  * 4x Nomos8kSC  -- UI (menus, load screens, fonts, HUD, minimaps) and characters
  * 4x UltraSharp -- scenery, vehicles, weapons, and anything not listed above

Processing:
  * load-screen halves are upscaled separately (they are not continuous across
    their shared edge, so joining them made a visible line);
  * images are padded before inference (wrap-around for tiling textures,
    mirrored otherwise) and cropped after; big images run in overlapping tiles;
  * alpha: colour-zone masks / a few exact levels replicated exactly; cutouts
    upscaled by the same model and re-thresholded; soft alpha (fonts, glows)
    upscaled by the same model with its peak level restored;
  * the PC button glyphs (pspbuttons, button_*, d_pad_*) are skipped, and files
    that differ from the dump (an upscale or a modder's edit) are never touched.

usage: work\upscale-pc\venv\Scripts\python.exe upscale_pack.py [--only a,b] [--group ui|characters|other] [--pilot] [--limit N]
Resumable: finished textures are recorded in work\upscale-pc\manifest.json.
"""
import argparse, json, os, re, sys, time
import numpy as np
from PIL import Image
import onnxruntime as ort

GAME = r'C:\Games\Star Wars Renegade Squadron'
PACK = os.path.join(GAME, r'mods\textures')
DUMP = os.path.join(GAME, r'mods\original-textures')
WORK = r'Z:\Programming\!archived\RenegadeSquadronPC\work\upscale-pc'
MODELS = {'nomos': os.path.join(WORK, r'models\4xNomos8kSC.onnx'), 'ultrasharp': os.path.join(WORK, r'models\4x-UltraSharp.onnx')}
SCALE, PAD, TILE, OVERLAP = 4, 8, 192, 16
# The load-screen halves are not continuous across their shared edge (the game
# lays them out apart), so joining them smeared that edge into a visible line.
JOIN_HALVES = False

def same_image(a_path, b_path):
    a, b = Image.open(a_path).convert('RGBA'), Image.open(b_path).convert('RGBA')
    return a.size == b.size and np.array_equal(np.asarray(a), np.asarray(b))

def sources():
    out = {}
    for name, rec in json.load(open(os.path.join(DUMP, 'index.json'))).items():
        for copy in rec.get('copies', []): out[copy['file'][:-4]] = rec.get('source', '').lower().replace(chr(92), '/')
    return out

def group_of(source):
    parts = [p for p in source.split('/') if p]
    top = parts[1] if len(parts) > 2 else ''
    if top in ('frontend', 'gui', 'fonts', 'characters'): return 'characters' if top == 'characters' else 'ui'
    leaf = parts[-1] if parts else ''
    if len(parts) == 2 and (leaf.endswith('_map.asr') or leaf.startswith('hud') or leaf.startswith('sniper')): return 'ui'
    return 'other'

def skipped(name):
    return name == 'pspbuttons' or name.startswith('button_') or name.startswith('d_pad_')

def candidates():
    out = []
    for f in sorted(os.listdir(DUMP)):
        if not f.lower().endswith('.tga'): continue
        name = f[:-4]
        if skipped(name): continue
        pack = os.path.join(PACK, f)
        if os.path.exists(pack) and not same_image(pack, os.path.join(DUMP, f)): continue
        out.append(name)
    return out

def tileable(rgb):
    a = rgb.astype(np.float32)
    if a.shape[0] < 8 or a.shape[1] < 8: return False
    inner_x = np.abs(np.diff(a, axis=1)).mean() + 1.0
    inner_y = np.abs(np.diff(a, axis=0)).mean() + 1.0
    return np.abs(a[:, 0] - a[:, -1]).mean() <= 1.6 * inner_x and np.abs(a[0] - a[-1]).mean() <= 1.6 * inner_y

def alpha_kind(alpha):
    values = np.unique(alpha)
    if values.size == 1 and values[0] == 255: return 'opaque'
    if values.size <= 2 and set(values.tolist()) <= {0, 255}: return 'cutout'
    if values.size <= 4: return 'zones'
    return 'soft'

class Upscaler:
    def __init__(self):
        self.sessions = {}
        so = ort.SessionOptions(); so.log_severity_level = 3
        self.so = so
    def session(self, key):
        # one model on the GPU at a time (the integrated GPU's memory is small)
        if key not in self.sessions:
            self.sessions.clear()
            self.sessions[key] = ort.InferenceSession(MODELS[key], self.so, providers=['DmlExecutionProvider', 'CPUExecutionProvider'])
        return self.sessions[key]
    def run(self, key, rgb):
        """(H,W,3) float 0..1, already padded -> (4H,4W,3), tiled with cross-fades."""
        sess = self.session(key)
        h, w, _ = rgb.shape
        if h <= TILE and w <= TILE:
            return sess.run(None, {'input': np.ascontiguousarray(rgb.transpose(2, 0, 1)[None])})[0][0].transpose(1, 2, 0)
        out = np.zeros((h * SCALE, w * SCALE, 3), np.float32); wsum = np.zeros((h * SCALE, w * SCALE, 1), np.float32)
        step = TILE - OVERLAP
        ys = sorted({min(y, h - TILE) for y in range(0, h, step)}) if h > TILE else [0]
        xs = sorted({min(x, w - TILE) for x in range(0, w, step)}) if w > TILE else [0]
        for y0 in ys:
            for x0 in xs:
                part = rgb[y0:y0 + TILE, x0:x0 + TILE]
                y = sess.run(None, {'input': np.ascontiguousarray(part.transpose(2, 0, 1)[None])})[0][0].transpose(1, 2, 0)
                th, tw = y.shape[:2]
                ry = np.minimum(np.arange(th) + 1, np.arange(th)[::-1] + 1)
                rx = np.minimum(np.arange(tw) + 1, np.arange(tw)[::-1] + 1)
                m = np.minimum(np.minimum(ry[:, None], OVERLAP * SCALE), np.minimum(rx[None, :], OVERLAP * SCALE)).astype(np.float32)[:, :, None]
                out[y0 * SCALE:y0 * SCALE + th, x0 * SCALE:x0 * SCALE + tw] += y * m
                wsum[y0 * SCALE:y0 * SCALE + th, x0 * SCALE:x0 * SCALE + tw] += m
        return out / np.maximum(wsum, 1e-6)

def upscale_image(up, key, rgba):
    """RGBA uint8 -> 4x RGBA uint8."""
    h, w = rgba.shape[:2]
    rgb8, alpha8 = rgba[:, :, :3], rgba[:, :, 3]
    wrap = bool(tileable(rgb8))
    p = min(PAD, max(1, min(w, h) // 2 - 1))
    mode = 'wrap' if wrap else 'reflect'
    def model(img):
        padded = np.pad(img, ((p, p), (p, p), (0, 0)), mode=mode)
        return np.clip(up.run(key, padded), 0, 1)[p * SCALE:(p + h) * SCALE, p * SCALE:(p + w) * SCALE]
    kind = alpha_kind(alpha8)
    visible = rgb8[alpha8 >= 32].astype(np.float32)
    single_colour = False
    if kind != 'opaque' and visible.shape[0] >= 16:
        # nearly every clearly visible pixel the same colour (a few stray dark texels allowed)
        close = np.abs(visible - np.median(visible, axis=0)).max(axis=1) <= 12
        single_colour = close.mean() >= 0.99
        visible = visible[close]
    if single_colour:
        # one colour drawn through its alpha (font pages, glyph sprites): only the
        # shape is upscaled, the colour stays exact (no dimming or fringes)
        rgb = np.broadcast_to(np.median(visible, axis=0) / 255, (h * SCALE, w * SCALE, 3)).copy()
    else:
        rgb = model(rgb8.astype(np.float32) / 255)
    if kind == 'opaque':
        alpha = np.full((h * SCALE, w * SCALE), 255, np.uint8)
    elif kind == 'zones':
        alpha = np.repeat(np.repeat(alpha8, SCALE, axis=0), SCALE, axis=1)
    else:
        a = model(np.repeat(alpha8[:, :, None].astype(np.float32) / 255, 3, axis=2)).mean(axis=2)
        if kind == 'cutout':
            alpha = np.where(a >= 0.5, 255, 0).astype(np.uint8)
        else:
            # keep the source's peak opacity (the model tends to dim thin bright strokes)
            src_peak = alpha8.max() / 255.0
            if src_peak < 0.75:
                # faint glows / light beams: the models flatten low-level masks, so
                # the transparency follows the original smoothly instead
                a = np.asarray(Image.fromarray(alpha8.astype(np.float32) / 255, 'F').resize((w * SCALE, h * SCALE), Image.BICUBIC))
            else:
                peak = np.percentile(a[a > 0.05], 99.5) if (a > 0.05).any() else 1.0
                if peak > 0.2 and peak < src_peak: a = a * (src_peak / peak)
            if single_colour and src_peak >= 0.75:   # glyphs (solid shapes), not faint glows
                # glyph shapes: solid interiors and clean anti-aliased edges (the
                # model reads the mask as a photo and shades it); a smooth levels
                # curve around the edge keeps a 1-2 pixel soft rim at 4x
                t = np.clip((a - 0.22) / (0.62 - 0.22), 0, 1)
                a = t * t * (3 - 2 * t) * src_peak
            alpha = np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)
    return np.dstack([np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8), alpha]), dict(wrap=wrap, pad=p, alpha=kind, single_colour=bool(single_colour))

def save_tga(arr, path):
    tmp = path + '.tmp.tga'
    Image.fromarray(arr, 'RGBA').save(tmp, compression=None)
    os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--group', default='', help='ui, characters or other')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--pilot', action='store_true', help='write to the pilot folder in the work area, leave the pack alone')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    out_dir = os.path.join(WORK, 'pilot') if a.pilot else PACK
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(WORK, 'manifest.json')
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    src = sources()
    names = [n for n in (a.only.split(',') if a.only else candidates()) if n and (a.pilot or n not in manifest)]
    if a.group: names = [n for n in names if group_of(src.get(n, '')) == a.group]
    # model groups together (one model loaded at a time), UI first
    order = {'ui': 0, 'characters': 1, 'other': 2}
    names.sort(key=lambda n: (order[group_of(src.get(n, ''))], n))
    if a.limit: names = names[:a.limit]
    counts = {g: sum(group_of(src.get(n, '')) == g for n in names) for g in order}
    print('to upscale:', len(names), counts, 'already done:', len(manifest), flush=True)
    if a.dry_run: return
    up = Upscaler(); t0 = time.time(); done = 0
    pending = list(names); finished = set()
    while pending:
        name = pending.pop(0)
        if name in finished: continue
        group = group_of(src.get(name, ''))
        key = 'nomos' if group in ('ui', 'characters') else 'ultrasharp'
        t1 = time.time()
        # left/right halves of one picture: upscale joined
        m = re.match(r'(.*)_(left|right)$', name)
        partner = (m.group(1) + ('_right' if m.group(2) == 'left' else '_left')) if m else None
        group_names = [name]
        if JOIN_HALVES and partner and partner in pending:
            left, right = (name, partner) if m.group(2) == 'left' else (partner, name)
            L = np.asarray(Image.open(os.path.join(DUMP, left + '.tga')).convert('RGBA'))
            R = np.asarray(Image.open(os.path.join(DUMP, right + '.tga')).convert('RGBA'))
            if L.shape == R.shape:
                big, info = upscale_image(up, key, np.concatenate([L, R], axis=1))
                half = big.shape[1] // 2
                results = {left: big[:, :half], right: big[:, half:]}
                info['joined'] = [left, right]
                pending.remove(partner); group_names = [left, right]
            else:
                partner = None
        if not partner or len(group_names) == 1:
            rgba = np.asarray(Image.open(os.path.join(DUMP, name + '.tga')).convert('RGBA'))
            big, info = upscale_image(up, key, rgba)
            results = {name: big}
        for n, arr in results.items():
            target = os.path.join(out_dir, n + '.tga')
            record = dict(info, model=key, group=group, source=src.get(n, ''), output=[arr.shape[1], arr.shape[0]], seconds=round(time.time() - t1, 1))
            if not a.pilot and os.path.exists(target) and not same_image(target, os.path.join(DUMP, n + '.tga')):
                record['skipped'] = 'pack file changed during the run'
            else:
                save_tga(np.ascontiguousarray(arr), target)
            finished.add(n); done += 1
            if not a.pilot: manifest[n] = record
        if not a.pilot and (done % 10 < len(results) or not pending):
            json.dump(manifest, open(manifest_path + '.tmp', 'w'), indent=1); os.replace(manifest_path + '.tmp', manifest_path)
        el = time.time() - t0
        print('%d/%d %s [%s %s] %.1fs (~%.0f min left)' % (done, len(names), '+'.join(results), group, key, time.time() - t1,
                                                       el / done * (len(names) - done) / 60), flush=True)
    if not a.pilot:
        json.dump(manifest, open(manifest_path + '.tmp', 'w'), indent=1); os.replace(manifest_path + '.tmp', manifest_path)
    print('finished', done, 'in %.1f min' % ((time.time() - t0) / 60), flush=True)

if __name__ == '__main__':
    main()
