r"""Flags upscaled in-match textures that are likely to look bad, for manual review.
Nothing is changed in the pack.

Per texture (upscaled pack file vs the original from mods\original-textures):
  * invented detail: high-frequency energy the upscale added, relative to the
    original's own detail (a plain bicubic enlargement scores 1.0);
  * tone shift: how far the upscale, shrunk back to the original size, moved
    away from the original (mean colour error and contrast change);
  * terrain/ground textures (large tiling surfaces) are listed separately: any
    artefact repeats across the whole map.

Writes work\upscale-pc\review\: one side-by-side picture per flagged texture
(original enlarged | upscale, same crop, plus a 4x4 tiled view for tiling
textures) and REVIEW.md listing them worst first with the reasons.
usage: python upscale_review.py [--marked name,name]
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

GAME = r'C:\Games\Star Wars Renegade Squadron'
PACK = os.path.join(GAME, r'mods\textures')
DUMP = os.path.join(GAME, r'mods\original-textures')
WORK = r'Z:\Programming\!archived\RenegadeSquadronPC\work\upscale-pc'
OUT = os.path.join(WORK, 'review')
TERRAIN_WORDS = ('ground', 'terrain', 'snow', 'sand', 'grass', 'dirt', 'mud', 'earth', 'rock', 'gravel', 'lava', 'moss', 'soil',
                 'floor', 'tile', 'concrete', 'ice', 'ash', 'dust', 'cracked', 'arena', 'marble', 'burnt')

def lum(a): return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114

def highpass(l):
    # detail above the scale of 4 output pixels (one original texel)
    im = Image.fromarray(l.astype(np.float32), 'F')
    w, h = im.size
    low = im.resize((max(1, w // 4), max(1, h // 4)), Image.BOX).resize((w, h), Image.BILINEAR)
    return l - np.asarray(low)

def metrics(name):
    o = Image.open(os.path.join(DUMP, name + '.tga')).convert('RGBA')
    u = Image.open(os.path.join(PACK, name + '.tga')).convert('RGBA')
    oa = np.asarray(o, dtype=np.float32); ua = np.asarray(u, dtype=np.float32)
    mask = oa[..., 3] > 32
    if mask.mean() < 0.05: return None
    bic = np.asarray(o.resize(u.size, Image.BICUBIC), dtype=np.float32)
    big_mask = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize(u.size, Image.NEAREST)) > 0
    hp_u = highpass(lum(ua[..., :3])); hp_b = highpass(lum(bic[..., :3]))
    hp_o = highpass(lum(np.asarray(o.resize(u.size, Image.NEAREST), dtype=np.float32)[..., :3]))
    detail = float(hp_u[big_mask].std() / max(hp_b[big_mask].std(), 0.5))
    down = np.asarray(u.resize(o.size, Image.BOX), dtype=np.float32)
    err = float(np.abs(down[..., :3] - oa[..., :3])[mask].mean())
    c_o = float(lum(oa[..., :3])[mask].std()); c_d = float(lum(down[..., :3])[mask].std())
    contrast = c_d / max(c_o, 1.0)
    return dict(detail=round(detail, 2), error=round(err, 1), contrast=round(contrast, 2), base_contrast=round(c_o, 1), size=list(o.size))

def sheet(name, wrap):
    o = Image.open(os.path.join(DUMP, name + '.tga')).convert('RGBA')
    u = Image.open(os.path.join(PACK, name + '.tga')).convert('RGBA')
    big = o.resize(u.size, Image.BICUBIC)
    cw, ch = min(u.width, 384), min(u.height, 384)
    x0, y0 = (u.width - cw) // 2, (u.height - ch) // 2
    tiles = [('Original (enlarged)', big.crop((x0, y0, x0 + cw, y0 + ch))), ('Upscaled', u.crop((x0, y0, x0 + cw, y0 + ch)))]
    if wrap:
        # how it repeats across a surface, at roughly in-game scale
        rep = Image.new('RGBA', (u.width * 3, u.height * 3))
        for i in range(3):
            for j in range(3): rep.paste(u, (i * u.width, j * u.height))
        tiles.append(('Upscaled, tiled 3x3', rep.resize((384, 384), Image.LANCZOS)))
    w = sum(t.width for _, t in tiles) + 8 * (len(tiles) - 1)
    s = Image.new('RGB', (w, 384 + 22), (20, 20, 20)); d = ImageDraw.Draw(s); x = 0
    for label, t in tiles:
        bg = Image.new('RGBA', t.size, (90, 90, 90, 255)); bg.alpha_composite(t)
        s.paste(bg.convert('RGB'), (x, 22)); d.text((x + 4, 4), label, fill=(255, 255, 255)); x += t.width + 8
    path = os.path.join(OUT, name.replace(' ', '_') + '.png'); s.save(path); return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--marked', default='')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
    marked = [m for m in a.marked.split(',') if m]
    rows = []
    for name, rec in manifest.items():
        if rec.get('group') == 'ui' or rec.get('skipped'): continue   # in-match only
        m = metrics(name)
        if m is None: continue
        reasons = []
        terrain = bool(rec.get('wrap')) and any(w in name.lower() or w in rec.get('source', '') for w in TERRAIN_WORDS)
        # calibrated on this pack: most upscales add 1.5-3x detail and stay within a few levels of the original
        if m['detail'] >= 4.0: reasons.append('heavy invented detail (%.1fx a plain enlargement)' % m['detail'])
        elif terrain and m['detail'] >= 2.8: reasons.append('strong added detail on a tiling surface (%.1fx)' % m['detail'])
        if m['error'] >= 10 and not rec.get('single_colour'): reasons.append('colours/tones moved (avg %.0f/255 off at original size)' % m['error'])
        # contrast only means something for textures with real tonal range and their own colours
        meaningful = m['base_contrast'] >= 8 and not rec.get('single_colour')
        if not meaningful: m['contrast'] = 1.0
        if abs(m['contrast'] - 1) >= (0.2 if terrain else 0.3): reasons.append('contrast %+d%%' % round((m['contrast'] - 1) * 100))
        if terrain and reasons: reasons.append('repeats across the map')
        score = max(0, m['detail'] - 2.5) + max(0, m['error'] - 6) / 3 + abs(m['contrast'] - 1) * 4 + (1.5 if terrain else 0)
        if name in marked: reasons.insert(0, 'MARKED: Hoth terrain you flagged'); score += 100
        if reasons: rows.append((score, name, rec, m, reasons, terrain))
    rows.sort(key=lambda r: -r[0])
    lines = ['# Upscaled textures to review', '',
             'In-match textures (UI excluded) whose upscale looks likely to be poor, worst first. Nothing was changed;',
             'each entry has a side-by-side picture in this folder. To revert one, copy its file from',
             '`C:\\Games\\Star Wars Renegade Squadron\\mods\\original-textures` into `mods\\textures`.', '',
             '| # | Texture | Model | Size | Why | Picture |', '|---|---|---|---|---|---|']
    for i, (score, name, rec, m, reasons, terrain) in enumerate(rows, 1):
        pic = sheet(name, rec.get('wrap'))
        lines.append('| %d | %s | %s | %dx%d | %s | [%s](%s) |' % (i, name, rec['model'], m['size'][0], m['size'][1], '; '.join(reasons),
                                                                os.path.basename(pic), os.path.basename(pic).replace(' ', '%20')))
    open(os.path.join(OUT, 'REVIEW.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('flagged', len(rows), 'of', sum(1 for r in manifest.values() if r.get('group') != 'ui'))
    for r in rows[:25]: print('%6.2f %-40s %s' % (r[0], r[1], '; '.join(r[4])))

if __name__ == '__main__':
    main()
