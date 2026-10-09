r"""Builds the Xbox button-glyph replacement for the game's PSP button atlas.

The game draws every on-screen button prompt from one 128x128 atlas
(GRAPHICS\PSPBUTTONS.ASR, texture id tex-v1-8f8e...). Its TTXT table names 29
regions. This writes a 512x512 override with the matching Xbox glyph in each
region, cut from buttonAtlas.png in the repository root. Icon regions that are
not buttons (yellow objective arrow, sabre, command post, skull...) keep the
original pixels, upscaled.

Mapping: PSP cross/circle/square/triangle -> A/B/X/Y, L/R -> LB/RB,
start/select -> Menu/View, analog -> left stick, d-pad -> d-pad. One
deliberate exception for PC mode: the small d-pad-up tile only ever appears in
"Press <> to change equipment / Use / Enter" prompts, and the PC layout puts
that on X, so that tile shows X.
"""
import struct, sys, os
from PIL import Image

REPO = r'Z:\Programming\!archived\RenegadeSquadronPC'
GAME = r'C:\Games\Star Wars Renegade Squadron\data\PSP_GAME\USRDIR'
ATLAS_ID = 'tex-v1-8f8ec0dadcd9cedf2611d3a2a10d05d656502109752f6461229d9f302348f7b2'
ORIGINAL = os.path.join(REPO, r'work\texture-dumps-live\textures', ATLAS_ID + '.png')
SIZE = 512

def regions():
    b = open(os.path.join(GAME, r'GRAPHICS\PSPBUTTONS.ASR'), 'rb').read()
    j = b.find(b'TTXT'); size = struct.unpack_from('<I', b, j + 4)[0]; end = j + size; p = j + 20
    printable = lambda c: 0x20 <= c < 0x7f
    items = []
    while p < end:
        q = p
        while q < end and b[q] != 0: q += 1
        name = b[p:q].decode('latin1'); q += 1
        while q % 4: q += 1
        fl = []
        while q + 4 <= end and not (printable(b[q]) and printable(b[q + 1]) and printable(b[q + 2])):
            fl.append(struct.unpack_from('<f', b, q)[0]); q += 4
        items.append((name, fl)); p = q
    # the four floats before each name are that region's u0 v0 u1 v1
    return {items[k + 1][0].replace('.tga', ''): items[k][1][:4] for k in range(len(items) - 1)}

def xbox_cells():
    im = Image.open(os.path.join(REPO, 'buttonAtlas.png')).convert('RGBA')
    small = {}
    for row, (y0, y1) in enumerate(((11, 37), (41, 67))):
        for i in range(14):
            x0 = 1 + 24 * i
            small[row * 14 + i] = im.crop((x0 - 1, y0, x0 + 24, y1))
    big = {'B': im.crop((8, 73, 66, 131)), 'X': im.crop((68, 73, 126, 131)),
           'A': im.crop((128, 73, 186, 131)), 'Y': im.crop((188, 73, 246, 131))}
    return small, big

def trim(img):
    bbox = img.getchannel('A').point(lambda a: 255 if a > 24 else 0).getbbox()
    return img.crop(bbox) if bbox else img

def main():
    out_paths = sys.argv[1:] or [os.path.join(REPO, r'work\mods-pc\textures', ATLAS_ID + '.png')]
    reg = regions()
    small, big = xbox_cells()
    original = Image.open(ORIGINAL).convert('RGBA')
    glyph = {
        'analog': small[11], 'analog_Small': small[11],
        'big_circle': big['B'], 'big_square': big['X'], 'big_triangle': big['Y'], 'big_x': big['A'],
        'button_circle': small[0], 'button_square': small[1], 'button_triangle': small[3], 'button_x': small[2],
        'd_pad': small[10], 'd_pad_up': small[13], 'd_pad_dn': small[20], 'd_pad_lf': small[23], 'd_pad_rt': small[17],
        'd_pad_dn_Small': small[20], 'd_pad_lf_Small': small[23], 'd_pad_rt_Small': small[17],
        'd_pad_up_Small': small[1],   # PC layout: change equipment / use is on X
        'button_l1': small[7], 'button_r1': small[6], 'button_select': small[5], 'button_start': small[4],
    }
    atlas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    for name, (u0, v0, u1, v1) in reg.items():
        x0, y0, x1, y1 = round(u0 * SIZE), round(v0 * SIZE), round(u1 * SIZE), round(v1 * SIZE)
        w, h = x1 - x0, y1 - y0
        if name in glyph:
            g = trim(glyph[name])
            # the PSP art filled about 85% of its tile; match that
            scale = min(w * 0.86 / g.width, h * 0.86 / g.height)
            g = g.resize((max(1, round(g.width * scale)), max(1, round(g.height * scale))), Image.LANCZOS)
            atlas.alpha_composite(g, (x0 + (w - g.width) // 2, y0 + (h - g.height) // 2))
        else:
            src = original.crop((round(u0 * 128), round(v0 * 128), round(u1 * 128), round(v1 * 128)))
            atlas.alpha_composite(src.resize((w, h), Image.LANCZOS), (x0, y0))
    for path in out_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        atlas.save(path)
        print('wrote', path)

if __name__ == '__main__':
    main()
