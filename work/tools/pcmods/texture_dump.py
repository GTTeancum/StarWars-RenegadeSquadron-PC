r"""Complete texture dump from the game disc, one image per texture name.

Every texture on the disc is an Asura RSCF resource of type 2 (PSP IDX4/IDX8,
swizzled, with mips and a palette) inside the ENVS, GUIMENU, GRAPHICS and MISC
archives; type 0 resources are models and type 3 sounds. This reads all of
them straight from the disc (no gameplay needed) and writes:

  <out>\textures\<name>.tga      full-size 32-bit image, one per texture name
  <out>\textures\<name>~2.tga    a second, different copy of the same name (if any)
  <out>\names.tsv                every runtime texture ID -> name, copy number
  <out>\index.json               name -> source path, size, levels/archives, IDs

Each level file carries its own copy of the unit, vehicle and weapon textures,
and each copy is stored at several sizes (mips). Identical copies already share
one ID; the same name can still have 2-3 slightly different copies. names.tsv
maps all of those IDs to the one name, so a single replacement image named
after the texture covers every level and every size.

names.tsv also lists a palette-independent ID (the stored pixels) and a
colour-only ID per texture: the game recolours the palettes of some textures
(unit skins) after loading; those are matched on their pixels and keep the
game's own alpha.

Images are uncompressed 32-bit TGA: Photoshop opens the alpha as an alpha
channel ("Alpha 1") rather than as transparency. On unit textures that
channel is the colour-zone map (255 keep as painted, 0 zone 1, ~128 zone 2).

Replacements: put <name>.tga (or .dds/.png) in mods\textures together with
names.tsv. <name>~2.tga overrides only the second copy. manifest.json in the
same folder can point names at other files: {"imp_inf_scout": "scout_hd.tga"}.
A file named by the full ID (tex-v1-...) still takes priority.

Usage: python texture_dump.py [--game <USRDIR>] [--out <folder>] [--install <mods\textures>]
"""
import argparse, collections, hashlib, json, os, shutil, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image

AREAS = ('ENVS', 'GUIMENU', 'GRAPHICS', 'MISC')
_offset_cache = {}

def decode_texture(p):
    """RSCF type-2 payload -> list of (width, height, rgba ndarray) per mip.
    Same layout and swizzle as Asura_PSP_TextureManagement::Load."""
    w, h, reserved, fmt, mipmax = struct.unpack_from('<HHHBB', p)
    if fmt not in (4, 5) or reserved or mipmax > 7 or not (0 < w <= 4096 and 0 < h <= 4096):
        raise ValueError('unsupported texture header fmt=%d' % fmt)
    levels = [(max(1, w >> l), max(1, h >> l)) for l in range(mipmax + 1)]
    sizes = [((lw + 1) // 2 if fmt == 4 else lw) * lh for lw, lh in levels]
    palette_offset = 8 + sum(sizes)
    if palette_offset + (64 if fmt == 4 else 1024) != len(p):
        raise ValueError('mip/palette layout mismatch')
    palette = np.frombuffer(p[palette_offset:], dtype=np.uint8).reshape(-1, 4)
    out, at = [], 8
    decode_texture.raw = []
    for (lw, lh), length in zip(levels, sizes):
        key = (lw, lh, fmt)
        if key not in _offset_cache:
            y, x = np.indices((lh, lw)); bx = x // 2 if fmt == 4 else x; row = (lw + 1) // 2 if fmt == 4 else lw
            _offset_cache[key] = (((y // 8) * ((row + 15) // 16) + bx // 16) * 128 + (y % 8) * 16 + bx % 16, x)
        offsets, x = _offset_cache[key]
        if int(offsets.max()) >= length: raise ValueError('short swizzle layout %dx%d' % (lw, lh))
        idx = np.frombuffer(p[at:at + length], dtype=np.uint8)[offsets]
        if fmt == 4: idx = np.where(x % 2, idx >> 4, idx & 15)
        out.append((lw, lh, palette[idx].copy())); decode_texture.raw.append((fmt, p[at:at + length])); at += length
    return out

def texture_id(w, h, rgba):
    # Same identity as the game's renegade::overrides::texture_id.
    return 'tex-v1-' + hashlib.sha256(struct.pack('<II', w, h) + rgba.tobytes()).hexdigest()

def index_id(w, h, fmt, raw):
    # Palette-independent identity (renegade::overrides::index_id): the stored,
    # swizzled index pixels. The game recolours unit palettes at load time, but
    # never the pixels.
    return 'tex-idx-' + hashlib.sha256(struct.pack('<IIII', w, h, fmt, 1) + raw).hexdigest()

def colour_id(w, h, rgba):
    # Colour-only identity (renegade::overrides::colour_id): the game rewrites the
    # palette alpha of some textures (unit skins) after loading, so their runtime
    # ID differs from the disc while the colours are identical.
    return 'tex-rgb-' + hashlib.sha256(struct.pack('<II', w, h) + np.ascontiguousarray(rgba[..., :3]).tobytes()).hexdigest()

def scan(game):
    """Yields (archive, offset, source name, [(w, h, rgba, id)...]) for every texture resource."""
    failures = []
    for area in AREAS:
        for path in sorted((game / area).rglob('*')):
            if not path.is_file(): continue
            with path.open('rb') as f:
                if f.read(8) != b'Asura   ': continue
            b = path.read_bytes(); archive = path.relative_to(game).as_posix(); at = 8
            while at + 16 <= len(b):
                if len(b) - at <= 16 and not any(b[at:]): break
                size = struct.unpack_from('<I', b, at + 4)[0]
                if size < 16 or at + size > len(b): failures.append((archive, at, 'bad chunk boundary')); break
                c = b[at:at + size]; chunk_at = at; at += size
                if c[:4] != b'RSCF' or len(c) < 32 or struct.unpack_from('<I', c, 16)[0] != 2: continue
                try:
                    end = c.index(0, 28); name = c[28:end].decode('latin1'); pos = 28 + ((end - 28 + 4) & ~3)
                    payload = c[pos:]
                    if len(payload) != struct.unpack_from('<I', c, 24)[0]: raise ValueError('payload size mismatch')
                    levels = decode_texture(payload)
                    mips = [(w, h, rgba, texture_id(w, h, rgba), (colour_id(w, h, rgba), index_id(w, h, fmt, raw)))
                            for (w, h, rgba), (fmt, raw) in zip(levels, decode_texture.raw)]
                    yield archive, chunk_at, name, mips
                except (ValueError, IndexError, struct.error) as e:
                    failures.append((archive, chunk_at, str(e)))
    scan.failures = failures

def short_names(source_names):
    """Lower-case file name without extension; parent folder prefixed where two paths share one."""
    B = chr(92)
    parts = {n: n.lower().replace('/', B).strip(B).split(B) for n in source_names}
    base = collections.defaultdict(list)
    for n, p in parts.items(): base[os.path.splitext(p[-1])[0]].append(n)
    out = {}
    for stem, names in base.items():
        if len(names) == 1: out[names[0]] = stem; continue
        for n in names:
            p = parts[n]; out[n] = (p[-2] + '_' if len(p) > 1 else '') + stem
        if len(set(out[n] for n in names)) < len(names):
            for i, n in enumerate(sorted(names)): out[n] = '%s_%d' % (out[n], i + 1)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=r'C:\Games\Star Wars Renegade Squadron\data\PSP_GAME\USRDIR')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[2] / 'texture-dump'))
    ap.add_argument('--install', help='mods\\textures folder to receive names.tsv')
    a = ap.parse_args()
    game, out = Path(a.game), Path(a.out)
    (out / 'textures').mkdir(parents=True, exist_ok=True)

    chunks = []          # (archive, offset, name, mips)
    for archive, offset, name, mips in scan(game):
        chunks.append((archive, offset, name, [(w, h, mid) for w, h, _, mid, _ in mips], mips[0][:4], [m[4] for m in mips]))
    print('texture resources', len(chunks), 'failures', len(scan.failures))

    # Group by source name, then by distinct full-size image (a "copy").
    by_name = collections.defaultdict(lambda: collections.defaultdict(list))
    colour_ids = {}
    for archive, offset, name, mips, top, cids in chunks:
        by_name[name.lower()][mips[0][2]].append((archive, mips, top))
        for (_, _, mid), cid in zip(mips, cids): colour_ids[mid] = cid
    shorts = short_names(by_name.keys())

    id_owner = {}        # id -> (short, copy, archives) ; an ID shared by two names goes to the more widely used one
    index = {}
    written = 0
    for name in sorted(by_name):
        copies = sorted(by_name[name].items(), key=lambda kv: (-len({r[0] for r in kv[1]}), kv[0]))
        short = shorts[name]; entry = dict(source=name, copies=[])
        for n, (top_id, recs) in enumerate(copies, 1):
            stem = short if n == 1 else '%s~%d' % (short, n)
            w, h, rgba, _ = recs[0][2]
            target = out / 'textures' / (stem + '.tga')
            if not target.exists(): Image.fromarray(rgba, 'RGBA').save(target, compression=None); written += 1
            archives = sorted({r[0] for r in recs})
            ids = sorted({mid for r in recs for (_, _, mid) in r[1]})
            entry['copies'].append(dict(file=stem + '.tga', width=w, height=h, archives=archives,
                                        sizes=sorted({(mw, mh) for r in recs for (mw, mh, _) in r[1]}, reverse=True), ids=ids))
            for mid in ids:
                prev = id_owner.get(mid)
                if prev is None or len(archives) > prev[2]: id_owner[mid] = (short, n, len(archives))
        index[short] = entry

    shared = collections.Counter()
    for short, entry in index.items():
        for c in entry['copies']:
            for mid in c['ids']:
                if id_owner[mid][0] != short: shared[mid] += 1
    with open(out / 'names.tsv', 'w', newline='\n') as f:
        f.write('# texture ID\tname\tcopy  (generated by texture_dump.py from your disc)\n')
        for mid in sorted(id_owner): f.write('%s\t%s\t%d\n' % (mid, id_owner[mid][0], id_owner[mid][1]))
        # Palette-independent and colour-only fallbacks, used when the game
        # recoloured a texture's palette after loading (unit skins).
        colour_owner = {}
        for mid, owner in id_owner.items():
            for cid in colour_ids[mid]:
                prev = colour_owner.get(cid)
                if prev is None or owner[2] > prev[2]: colour_owner[cid] = owner
        for cid in sorted(colour_owner): f.write('%s\t%s\t%d\n' % (cid, colour_owner[cid][0], colour_owner[cid][1]))
    (out / 'index.json').write_text(json.dumps(index, indent=1))
    multi = sum(1 for e in index.values() if len(e['copies']) > 1)
    summary = dict(texture_resources=len(chunks), failures=len(scan.failures), names=len(index),
                   names_with_several_copies=multi, runtime_ids=len(id_owner), images_written=written,
                   ids_shared_by_two_names=len(shared))
    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    if scan.failures: print('FAILURES:', scan.failures[:10])
    if a.install:
        dest = Path(a.install); dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / 'names.tsv', dest / 'names.tsv'); print('installed', dest / 'names.tsv')

if __name__ == '__main__':
    main()
