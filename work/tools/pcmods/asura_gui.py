r"""Reader/writer for Asura GUIMenu page chunks (UIMP) in Renegade's .GUI files.

The layout follows the engine's own ReadFromChunkStream functions
(work\asura-reference\AvP_Branches\E3\Asura\Independent\GUIMenu\*.cpp,
Asura_Chunk_Stream.cpp for the primitive encodings). Every object is kept as an
ordered dict of the exact fields read, so writing a parsed page back produces
the original bytes; `roundtrip_check` proves that for every page in a file.

Objects that the reference does not cover (Renegade's project-specific widget
types 3000+ and the carousel) raise Unsupported; files/pages containing them
are left untouched by the editing tools.
"""
import struct, sys, os, io

NULL_STRING = 0x00FFFF00  # Asura_String::NULL_STRING_CHUNK

def asura_hash(text):
    """Asura_GetHashID: lower-case, backslash -> slash, h = h*31 + c."""
    h = 0
    for c in text:
        if 'A' <= c <= 'Z': c = c.lower()
        if c == '\\': c = '/'
        h = ((h << 5) - h + ord(c)) & 0xFFFFFFFF
    return h

class Unsupported(Exception):
    pass

# ---------------------------------------------------------------- stream

class Reader:
    def __init__(self, data, pos=0):
        self.d = data; self.p = pos
    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v
    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v
    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v
    def u16(self):
        v = struct.unpack_from('<H', self.d, self.p)[0]; self.p += 2; return v
    def u8(self):
        v = self.d[self.p]; self.p += 1; return v
    def boolean(self):
        return self.u8() != 0
    def raw(self, n):
        v = self.d[self.p:self.p + n]; self.p += n; return bytes(v)
    def string(self):
        # ReadString: 4-byte groups until a NUL; NULL_STRING_CHUNK marks a null string
        if struct.unpack_from('<I', self.d, self.p)[0] == NULL_STRING:
            self.p += 4; return None
        start = self.p
        while True:
            chunk = self.d[self.p:self.p + 4]; self.p += 4
            if b'\0' in chunk: break
        raw = bytes(self.d[start:self.p])
        return raw[:raw.index(b'\0')].decode('latin1')

class Writer:
    def __init__(self):
        self.b = bytearray()
    def u32(self, v): self.b += struct.pack('<I', v & 0xFFFFFFFF)
    def i32(self, v): self.b += struct.pack('<i', v)
    def f32(self, v): self.b += struct.pack('<f', v) if not isinstance(v, bytes) else v
    def u16(self, v): self.b += struct.pack('<H', v)
    def u8(self, v): self.b += struct.pack('<B', v)
    def boolean(self, v): self.u8(1 if v else 0)
    def raw(self, v): self.b += v
    def string(self, s):
        if s is None:
            self.u32(NULL_STRING); return
        raw = s.encode('latin1') + b'\0'
        raw += b'\0' * (-len(raw) % 4)
        self.b += raw

# floats are kept as raw bytes to round-trip NaN/denormal payloads exactly
def rf(r): return r.raw(4)
def wf(w, v): w.raw(v if isinstance(v, bytes) else struct.pack('<f', v))
def fval(b): return struct.unpack('<f', b)[0] if isinstance(b, bytes) else b
def fbytes(v): return struct.pack('<f', v)

# ---------------------------------------------------------------- shared records

def read_console_cmd(r):
    return {'version': r.u32(), 'name': r.string(), 'args': r.string()}
def write_console_cmd(w, c):
    w.u32(c['version']); w.string(c['name']); w.string(c['args'])

def read_console_var(r):
    return {'version': r.u32(), 'name': r.string()}
def write_console_var(w, v):
    w.u32(v['version']); w.string(v['name'])

def read_condition_var(r):
    c = {'version': r.u32(), 'var': read_console_var(r)}
    if c['version'] >= 1: c['cmd'] = read_console_cmd(r)
    c['value'] = r.string(); c['condition'] = r.u32()
    return c
def write_condition_var(w, c):
    w.u32(c['version']); write_console_var(w, c['var'])
    if c['version'] >= 1: write_console_cmd(w, c['cmd'])
    w.string(c['value']); w.u32(c['condition'])

def read_condition_manager(r):
    m = {'version': r.u32(), 'operator': r.u32()}
    n = r.u32(); m['vars'] = [read_condition_var(r) for _ in range(n)]
    return m
def write_condition_manager(w, m):
    w.u32(m['version']); w.u32(m['operator']); w.u32(len(m['vars']))
    for v in m['vars']: write_condition_var(w, v)

def read_command_manager(r):
    m = {'version': r.u32()}
    n = r.u32(); m['actions'] = []
    for _ in range(n):
        a = {'button': r.u32()}
        if m['version'] >= 1: a['flags'] = r.u32()
        a['cmd'] = read_console_cmd(r); m['actions'].append(a)
    return m
def write_command_manager(w, m):
    w.u32(m['version']); w.u32(len(m['actions']))
    for a in m['actions']:
        w.u32(a['button'])
        if m['version'] >= 1: w.u32(a['flags'])
        write_console_cmd(w, a['cmd'])

def read_modifier(r):
    m = {'version': r.u32()}
    if m['version'] >= 1: m['conditions'] = read_condition_manager(r)
    m['state'] = r.u32(); m['modify_type'] = r.u32(); m['data_type'] = r.u32()
    t = m['data_type']
    if t == 1: m['data'] = r.u32()
    elif t == 2: m['data'] = r.i32()
    elif t == 3: m['data'] = rf(r)
    elif t == 4: m['data'] = [rf(r) for _ in range(4)]
    elif t == 5:
        m['data'] = [rf(r), rf(r)]
        if m['version'] < 2: m['data'].append(rf(r))
    elif t == 6:
        n = r.u32(); m['data'] = [r.u16() for _ in range(n)]
    elif t == 7:
        n = r.u32(); m['data'] = r.raw(n)
    elif t == 8: m['data'] = [rf(r) for _ in range(4)]
    elif t == 9: m['data'] = r.string()
    elif t == 0: m['data'] = None
    else: raise Unsupported('modifier data type %d' % t)
    return m
def write_modifier(w, m):
    w.u32(m['version'])
    if m['version'] >= 1: write_condition_manager(w, m['conditions'])
    w.u32(m['state']); w.u32(m['modify_type']); w.u32(m['data_type'])
    t = m['data_type']; d = m['data']
    if t == 1: w.u32(d)
    elif t == 2: w.i32(d)
    elif t == 3: wf(w, d)
    elif t in (4, 8):
        for v in d: wf(w, v)
    elif t == 5:
        for v in d: wf(w, v)
    elif t == 6:
        w.u32(len(d))
        for v in d: w.u16(v)
    elif t == 7:
        w.u32(len(d)); w.raw(d)
    elif t == 9: w.string(d)

def read_animator(r):
    a = {'version': r.u32(), 'sequence': r.string()}
    if a['version'] >= 2:
        a['start_conditions'] = read_condition_manager(r); a['start_active'] = r.boolean()
    a['speed'] = rf(r)
    if a['version'] >= 1: a['tools_flags'] = r.u32()
    if a['version'] >= 3: a['delay'] = rf(r)
    if a['version'] >= 4: a['initialise_to_end'] = r.boolean()
    return a
def write_animator(w, a):
    w.u32(a['version']); w.string(a['sequence'])
    if a['version'] >= 2:
        write_condition_manager(w, a['start_conditions']); w.boolean(a['start_active'])
    wf(w, a['speed'])
    if a['version'] >= 1: w.u32(a['tools_flags'])
    if a['version'] >= 3: wf(w, a['delay'])
    if a['version'] >= 4: w.boolean(a['initialise_to_end'])

def read_special_effects(r):
    return {'version': r.u32(), 'delay': rf(r), 'teletype': r.boolean(), 'chars_per_second': r.u32(),
            'alpha_fade': rf(r), 'teletype_dir': r.u32(), 'decrypt': r.boolean(), 'decrypt_change': rf(r),
            'decrypt_time': rf(r), 'cursor': r.boolean(), 'cursor_flash': rf(r), 'cursor_stop': rf(r)}
def write_special_effects(w, e):
    w.u32(e['version']); wf(w, e['delay']); w.boolean(e['teletype']); w.u32(e['chars_per_second'])
    wf(w, e['alpha_fade']); w.u32(e['teletype_dir']); w.boolean(e['decrypt']); wf(w, e['decrypt_change'])
    wf(w, e['decrypt_time']); w.boolean(e['cursor']); wf(w, e['cursor_flash']); wf(w, e['cursor_stop'])

# ---------------------------------------------------------------- root / bases

T_MENUPAGE = 1
T_IMAGE, T_TEXT, T_PATH, T_ANIMATION, T_STATUSTEXT, T_FMV = 1001, 1002, 1003, 1004, 1005, 1006
T_BUTTON, T_CHECKBOX, T_SLIDER, T_TEXTBOX, T_TEXTLISTBOX, T_GROUP, T_ANIMIMAGE, T_PROGRESSBAR, T_NUMERIC, T_LISTBOX, T_LISTBOXENTRY, T_CAROUSEL = range(2001, 2013)
TYPE_NAMES = {T_MENUPAGE: 'MenuPage', T_IMAGE: 'Image', T_TEXT: 'Text', T_PATH: 'Path', T_ANIMATION: 'Animation',
              T_STATUSTEXT: 'StatusText', T_FMV: 'FMV', T_BUTTON: 'Button', T_CHECKBOX: 'CheckBox', T_SLIDER: 'Slider',
              T_TEXTBOX: 'TextBox', T_TEXTLISTBOX: 'TextListBox', T_GROUP: 'Group', T_ANIMIMAGE: 'AnimatingImage',
              T_PROGRESSBAR: 'ProgressBar', T_NUMERIC: 'Numeric', T_LISTBOX: 'ListBox', T_LISTBOXENTRY: 'ListBoxEntry'}

def read_root(r, o):
    v = o['root_version'] = r.u32()
    if v > 20: raise Unsupported('root version %d' % v)
    o['name'] = r.string()
    o['colour'] = [rf(r) for _ in range(4)]
    if v >= 20: o['bounds'] = [rf(r) for _ in range(4)]          # MinX MaxX MinY MaxY
    else: o['old_pos'] = [rf(r), rf(r), rf(r)]
    o['hash'] = r.u32(); o['flags'] = r.u32()
    if v == 0:
        o['display_conditions'] = [(r.i32(), r.u32())]
    else:
        n = r.u32(); o['display_conditions'] = [(r.i32(), r.u32()) for _ in range(n)]
    o['translucency'] = r.u32()
    if 2 <= v < 9: o['inheritance'] = (r.u32(), r.u32())
    if v >= 3: o['style_child_editable'] = r.u32(); o['tools_flags'] = r.u32()
    if v >= 4: o['style_hash'] = r.u32(); o['style_use_local'] = r.u32()
    if v >= 5:
        if v >= 10: o['condition_manager'] = read_condition_manager(r)
        else: o['single_condition'] = read_condition_var(r)
    if v >= 6:
        n = r.u32() if v <= 17 else r.u8()
        o['modifiers'] = [read_modifier(r) for _ in range(n)]
    if v >= 8:
        n = r.u32() if v <= 17 else r.u8()
        o['animators'] = [read_animator(r) for _ in range(n)]
        if v == 12: o['comment12'] = (r.string(), r.string())
        if v >= 13:
            n = r.u32(); o['comments'] = [(r.u32(), r.string(), r.string(), r.string()) for _ in range(n)]
        if v == 14: o['anchor14'] = (r.u32(), r.u32())
        if v >= 15:
            o['pos_mode'] = (r.u32(), r.u32()); o['pos_origin'] = [rf(r), rf(r)]

def write_root(w, o):
    v = o['root_version']; w.u32(v); w.string(o['name'])
    for c in o['colour']: wf(w, c)
    if v >= 20:
        for b in o['bounds']: wf(w, b)
    else:
        for b in o['old_pos']: wf(w, b)
    w.u32(o['hash']); w.u32(o['flags'])
    if v == 0:
        t, c = o['display_conditions'][0]; w.i32(t); w.u32(c)
    else:
        w.u32(len(o['display_conditions']))
        for t, c in o['display_conditions']: w.i32(t); w.u32(c)
    w.u32(o['translucency'])
    if 2 <= v < 9: w.u32(o['inheritance'][0]); w.u32(o['inheritance'][1])
    if v >= 3: w.u32(o['style_child_editable']); w.u32(o['tools_flags'])
    if v >= 4: w.u32(o['style_hash']); w.u32(o['style_use_local'])
    if v >= 5:
        if v >= 10: write_condition_manager(w, o['condition_manager'])
        else: write_condition_var(w, o['single_condition'])
    if v >= 6:
        (w.u32 if v <= 17 else w.u8)(len(o['modifiers']))
        for m in o['modifiers']: write_modifier(w, m)
    if v >= 8:
        (w.u32 if v <= 17 else w.u8)(len(o['animators']))
        for a in o['animators']: write_animator(w, a)
        if v == 12: w.string(o['comment12'][0]); w.string(o['comment12'][1])
        if v >= 13:
            w.u32(len(o['comments']))
            for cv, a, b, c in o['comments']: w.u32(cv); w.string(a); w.string(b); w.string(c)
        if v == 14: w.u32(o['anchor14'][0]); w.u32(o['anchor14'][1])
        if v >= 15:
            w.u32(o['pos_mode'][0]); w.u32(o['pos_mode'][1]); wf(w, o['pos_origin'][0]); wf(w, o['pos_origin'][1])

def read_element_base(r, o):
    read_root(r, o)
    v = o['element_version'] = r.u32()
    if v > 4: raise Unsupported('element base version %d' % v)
    if v < 4: o['element_dims'] = [rf(r), rf(r)]
    if 1 <= v < 3: o['element_scaling'] = (r.u32(), rf(r), rf(r))
def write_element_base(w, o):
    write_root(w, o); v = o['element_version']; w.u32(v)
    if v < 4: wf(w, o['element_dims'][0]); wf(w, o['element_dims'][1])
    if 1 <= v < 3: w.u32(o['element_scaling'][0]); wf(w, o['element_scaling'][1]); wf(w, o['element_scaling'][2])

def read_widget_base(r, o):
    read_root(r, o)
    v = o['widget_version'] = r.u32()
    if v > 3: raise Unsupported('widget base version %d' % v)
    o['nav'] = [r.u32() for _ in range(4)]
    if v >= 2: o['roll_in'] = read_console_cmd(r); o['roll_out'] = read_console_cmd(r)
    if v >= 1: o['selectable'] = r.boolean()
    if v >= 3: o['always_selectable'] = r.boolean()
def write_widget_base(w, o):
    write_root(w, o); v = o['widget_version']; w.u32(v)
    for h in o['nav']: w.u32(h)
    if v >= 2: write_console_cmd(w, o['roll_in']); write_console_cmd(w, o['roll_out'])
    if v >= 1: w.boolean(o['selectable'])
    if v >= 3: w.boolean(o['always_selectable'])

def read_children(r):
    n = r.u32()
    return [read_object(r) for _ in range(n)]
def write_children(w, children):
    w.u32(len(children))
    for c in children: write_object(w, c)

# ---------------------------------------------------------------- objects

def read_object(r):
    version = r.u32(); typ = r.u32()
    o = {'type': typ, 'version': version}
    f = READERS.get(typ)
    if f is None: raise Unsupported('object type %d' % typ)
    f(r, o, version)
    return o

def write_object(w, o):
    w.u32(o['version']); w.u32(o['type'])
    WRITERS[o['type']](w, o, o['version'])

def read_menupage(r, o, v):
    read_root(r, o)
    if v < 8: o['page_dims'] = [rf(r), rf(r)]
    o['children'] = read_children(r)
    o['startup_widget'] = r.u32()
    if v >= 1: o['filename'] = r.string()
    if 2 <= v <= 6: o['platform'] = r.i32()
    if v >= 3:
        o['on_init'] = read_console_cmd(r); o['on_deinit'] = read_console_cmd(r)
        if v >= 6: o['on_update'] = read_console_cmd(r)
    if v >= 4: o['page_flags'] = r.u32()
    if v >= 10: o['virtual_size'] = [rf(r), rf(r)]
def write_menupage(w, o, v):
    write_root(w, o)
    if v < 8: wf(w, o['page_dims'][0]); wf(w, o['page_dims'][1])
    write_children(w, o['children']); w.u32(o['startup_widget'])
    if v >= 1: w.string(o['filename'])
    if 2 <= v <= 6: w.i32(o['platform'])
    if v >= 3:
        write_console_cmd(w, o['on_init']); write_console_cmd(w, o['on_deinit'])
        if v >= 6: write_console_cmd(w, o['on_update'])
    if v >= 4: w.u32(o['page_flags'])
    if v >= 10: wf(w, o['virtual_size'][0]); wf(w, o['virtual_size'][1])

def read_image(r, o, v):
    read_element_base(r, o)
    o['uv'] = [rf(r) for _ in range(4)]; o['texture_hash'] = r.u32(); o['texture'] = r.string()
    if v >= 1: o['tile_hash'] = r.u32(); o['tile'] = r.string()
    if v >= 2: o['rotation'] = rf(r)
    o['children'] = read_children(r)
def write_image(w, o, v):
    write_element_base(w, o)
    for x in o['uv']: wf(w, x)
    w.u32(o['texture_hash']); w.string(o['texture'])
    if v >= 1: w.u32(o['tile_hash']); w.string(o['tile'])
    if v >= 2: wf(w, o['rotation'])
    write_children(w, o['children'])

def read_text(r, o, v):
    read_element_base(r, o)
    if v < 6:
        if v < 4: o['literal'] = r.string()
        else:
            n = r.u32(); o['literal_utf16'] = [r.u16() for _ in range(n)]
    if v >= 6: o['text_page'] = r.u32()
    if v >= 2: o['text_id'] = r.u32()
    if v >= 8: o['font_hash'] = r.u32()
    else: o['font'] = r.string()
    if v >= 1: o['font_scale'] = rf(r)
    if v >= 3: o['render_flags'] = r.u32()
    if v >= 5: o['scroll_rate'] = rf(r)
    if v >= 7: o['line_spacing'] = rf(r)
    if v >= 10: o['offset'] = [rf(r), rf(r)]
    o['children'] = read_children(r)
    if v >= 11:
        o['special_effects_enabled'] = r.boolean()
        if o['special_effects_enabled']: o['special_effects'] = read_special_effects(r)
def write_text(w, o, v):
    write_element_base(w, o)
    if v < 6:
        if v < 4: w.string(o['literal'])
        else:
            w.u32(len(o['literal_utf16']))
            for c in o['literal_utf16']: w.u16(c)
    if v >= 6: w.u32(o['text_page'])
    if v >= 2: w.u32(o['text_id'])
    if v >= 8: w.u32(o['font_hash'])
    else: w.string(o['font'])
    if v >= 1: wf(w, o['font_scale'])
    if v >= 3: w.u32(o['render_flags'])
    if v >= 5: wf(w, o['scroll_rate'])
    if v >= 7: wf(w, o['line_spacing'])
    if v >= 10: wf(w, o['offset'][0]); wf(w, o['offset'][1])
    write_children(w, o['children'])
    if v >= 11:
        w.boolean(o['special_effects_enabled'])
        if o['special_effects_enabled']: write_special_effects(w, o['special_effects'])

def read_statustext(r, o, v):
    read_element_base(r, o)
    if v >= 2: o['font_hash'] = r.u32()
    else: o['font'] = r.string()
    o['font_scale'] = rf(r); o['render_flags'] = r.u32(); o['console_var'] = read_console_var(r)
    n = r.u32(); o['entries'] = []
    for _ in range(n):
        e = {'compare': r.u32(), 'threshold': r.i32()}
        if v >= 1: e['text_page'] = r.u32()
        e['text_id'] = r.u32(); e['colour'] = [rf(r) for _ in range(4)]; o['entries'].append(e)
    o['children'] = read_children(r)
    if v >= 3:
        o['special_effects_enabled'] = r.boolean()
        if o['special_effects_enabled']: o['special_effects'] = read_special_effects(r)
def write_statustext(w, o, v):
    write_element_base(w, o)
    if v >= 2: w.u32(o['font_hash'])
    else: w.string(o['font'])
    wf(w, o['font_scale']); w.u32(o['render_flags']); write_console_var(w, o['console_var'])
    w.u32(len(o['entries']))
    for e in o['entries']:
        w.u32(e['compare']); w.i32(e['threshold'])
        if v >= 1: w.u32(e['text_page'])
        w.u32(e['text_id'])
        for c in e['colour']: wf(w, c)
    write_children(w, o['children'])
    if v >= 3:
        w.boolean(o['special_effects_enabled'])
        if o['special_effects_enabled']: write_special_effects(w, o['special_effects'])

def read_path(r, o, v):
    # version 0 paths store Asura_Vector_3 samples, later ones Asura_Vector_2
    read_element_base(r, o)
    dims = 3 if v == 0 else 2
    g = {'version': r.u32()}
    if g['version'] < 10002: raise Unsupported('old graph')
    g['flags'] = r.u32()
    if not g['flags'] & 1: raise Unsupported('spline graph data')
    n = r.u32(); g['samples'] = [tuple(rf(r) for _ in range(dims)) for _ in range(n)]
    o['graph'] = g
    o['children'] = read_children(r)
def write_path(w, o, v):
    write_element_base(w, o); g = o['graph']
    w.u32(g['version']); w.u32(g['flags']); w.u32(len(g['samples']))
    for s in g['samples']:
        for x in s: wf(w, x)
    write_children(w, o['children'])

def read_animation(r, o, v):
    read_element_base(r, o)
    if v == 0:
        o['skin'] = r.u32()
        if o['skin'] != 0: o['anim'] = r.u32(); o['anim_flags'] = r.u32()
    else:
        o['skin'] = r.u32(); o['anim'] = r.u32(); o['anim_flags'] = r.u32()
    o['fov'] = rf(r); o['zoom'] = rf(r)
    o['camera_offset'] = [rf(r) for _ in range(3)]; o['render_orient'] = [rf(r) for _ in range(3)]
    if v >= 5: o['skin_offset'] = [rf(r) for _ in range(3)]; o['camera_orient'] = [rf(r) for _ in range(3)]
    if v >= 2: o['rotation_speed'] = [rf(r) for _ in range(3)]
    if v >= 3: o['export_data'] = r.boolean()
    if v >= 4: o['vertical_fov'] = r.boolean(); o['stretch'] = r.boolean()
    o['children'] = read_children(r)
def write_animation(w, o, v):
    write_element_base(w, o)
    if v == 0:
        w.u32(o['skin'])
        if o['skin'] != 0: w.u32(o['anim']); w.u32(o['anim_flags'])
    else:
        w.u32(o['skin']); w.u32(o['anim']); w.u32(o['anim_flags'])
    wf(w, o['fov']); wf(w, o['zoom'])
    for x in o['camera_offset']: wf(w, x)
    for x in o['render_orient']: wf(w, x)
    if v >= 5:
        for x in o['skin_offset']: wf(w, x)
        for x in o['camera_orient']: wf(w, x)
    if v >= 2:
        for x in o['rotation_speed']: wf(w, x)
    if v >= 3: w.boolean(o['export_data'])
    if v >= 4: w.boolean(o['vertical_fov']); w.boolean(o['stretch'])
    write_children(w, o['children'])

def read_fmv(r, o, v):
    read_element_base(r, o)
    o['uv'] = [rf(r) for _ in range(4)]; o['texture_hash'] = r.u32(); o['texture'] = r.string()
    o['rotation'] = rf(r); o['fmv'] = r.string(); o['soundtrack'] = r.u32()
    o['play_sound'] = r.boolean(); o['loop'] = r.boolean()
    o['children'] = read_children(r)
def write_fmv(w, o, v):
    write_element_base(w, o)
    for x in o['uv']: wf(w, x)
    w.u32(o['texture_hash']); w.string(o['texture']); wf(w, o['rotation']); w.string(o['fmv'])
    w.u32(o['soundtrack']); w.boolean(o['play_sound']); w.boolean(o['loop'])
    write_children(w, o['children'])

def read_button(r, o, v):
    read_widget_base(r, o)
    o['children'] = read_children(r)
    o['link_to'] = r.u32(); o['button_flags'] = r.u32()
    if v == 1: o['command'] = read_console_cmd(r)
    if v >= 2: o['commands'] = read_command_manager(r)
    if v >= 3: o['min_time_active'] = rf(r); o['autoclick_time'] = rf(r)
def write_button(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    w.u32(o['link_to']); w.u32(o['button_flags'])
    if v == 1: write_console_cmd(w, o['command'])
    if v >= 2: write_command_manager(w, o['commands'])
    if v >= 3: wf(w, o['min_time_active']); wf(w, o['autoclick_time'])

def read_checkbox(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    if v >= 1: o['console_var'] = read_console_var(r)
    if v >= 2: o['checkbox_flags'] = r.u32()
def write_checkbox(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    if v >= 1: write_console_var(w, o['console_var'])
    if v >= 2: w.u32(o['checkbox_flags'])

def read_slider(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    o['path_hash'] = r.u32()
    if v in (1, 2):
        o['step'] = rf(r); o['audio_hash'] = r.u32(); o['slider_flags'] = r.u32()
        if v == 2: o['console_var'] = read_console_var(r)
    elif v == 3:
        o['steps'] = r.u32(); o['audio_hash'] = r.u32(); o['slider_flags'] = r.u32(); o['console_var'] = read_console_var(r)
    elif v != 0: raise Unsupported('slider version %d' % v)
def write_slider(w, o, v):
    write_widget_base(w, o); write_children(w, o['children']); w.u32(o['path_hash'])
    if v in (1, 2):
        wf(w, o['step']); w.u32(o['audio_hash']); w.u32(o['slider_flags'])
        if v == 2: write_console_var(w, o['console_var'])
    elif v == 3:
        w.u32(o['steps']); w.u32(o['audio_hash']); w.u32(o['slider_flags']); write_console_var(w, o['console_var'])

def read_textbox(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    o['active_text'] = r.u32()
    if v >= 1: o['max_chars'] = r.u32()
    if v >= 3: o['password'] = r.boolean()
    if v >= 4: o['allow_blank'] = r.boolean()
    if v >= 2: o['console_var'] = read_console_var(r)
def write_textbox(w, o, v):
    write_widget_base(w, o); write_children(w, o['children']); w.u32(o['active_text'])
    if v >= 1: w.u32(o['max_chars'])
    if v >= 3: w.boolean(o['password'])
    if v >= 4: w.boolean(o['allow_blank'])
    if v >= 2: write_console_var(w, o['console_var'])

def read_textlistbox(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    if v < 10: o['dims'] = [rf(r), rf(r)]
    o['max_allowed'] = r.u32(); o['max_displayed'] = r.u32(); o['font'] = r.string()
    if v >= 7: o['font_scale'] = rf(r)
    if v >= 1: o['render_flags'] = r.u32()
    if v >= 2: o['commands'] = read_command_manager(r)
    if v >= 3: o['population'] = read_console_cmd(r)
    if v >= 4:
        o['dec_hash'] = r.u32(); o['inc_hash'] = r.u32(); o['flash_colour'] = [rf(r) for _ in range(4)]; o['flash_timer'] = rf(r)
    if v >= 5: o['repeat_delays'] = [rf(r), rf(r)]
    if v >= 6: o['text_scroll_rate'] = rf(r)
    if v >= 8: o['init_var'] = read_console_var(r)
    if v >= 9: o['scrollbar_hash'] = r.u32()
def write_textlistbox(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    if v < 10: wf(w, o['dims'][0]); wf(w, o['dims'][1])
    w.u32(o['max_allowed']); w.u32(o['max_displayed']); w.string(o['font'])
    if v >= 7: wf(w, o['font_scale'])
    if v >= 1: w.u32(o['render_flags'])
    if v >= 2: write_command_manager(w, o['commands'])
    if v >= 3: write_console_cmd(w, o['population'])
    if v >= 4:
        w.u32(o['dec_hash']); w.u32(o['inc_hash'])
        for c in o['flash_colour']: wf(w, c)
        wf(w, o['flash_timer'])
    if v >= 5: wf(w, o['repeat_delays'][0]); wf(w, o['repeat_delays'][1])
    if v >= 6: wf(w, o['text_scroll_rate'])
    if v >= 8: write_console_var(w, o['init_var'])
    if v >= 9: w.u32(o['scrollbar_hash'])

def read_group(r, o, v):
    read_widget_base(r, o)
    if v >= 1: o['linked'] = r.u32()
    o['children'] = read_children(r)
def write_group(w, o, v):
    write_widget_base(w, o)
    if v >= 1: w.u32(o['linked'])
    write_children(w, o['children'])

def read_animimage(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    n = r.u32(); o['frames'] = []
    for _ in range(n):
        o['frames'].append({'texture_hash': r.u32(), 'texture': r.string(), 'rect': [rf(r) for _ in range(4)], 'uv': [rf(r) for _ in range(4)]})
    n = r.u32(); o['sequences'] = []
    for _ in range(n):
        s = {'fps': rf(r), 'max_frames': r.u16()}; k = r.u16(); s['frames'] = [r.u32() for _ in range(k)]; o['sequences'].append(s)
def write_animimage(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    w.u32(len(o['frames']))
    for f in o['frames']:
        w.u32(f['texture_hash']); w.string(f['texture'])
        for x in f['rect']: wf(w, x)
        for x in f['uv']: wf(w, x)
    w.u32(len(o['sequences']))
    for s in o['sequences']:
        wf(w, s['fps']); w.u16(s['max_frames']); w.u16(len(s['frames']))
        for f in s['frames']: w.u32(f)

def read_progressbar(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    o['maximum'] = rf(r); o['minimum'] = rf(r); o['step'] = rf(r)
    if v > 0: o['console_var'] = read_console_var(r)
    o['overlays'] = [(r.u32(), r.u32(), r.u32()) for _ in range(4)]
def write_progressbar(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    wf(w, o['maximum']); wf(w, o['minimum']); wf(w, o['step'])
    if v > 0: write_console_var(w, o['console_var'])
    for a, b, c in o['overlays']: w.u32(a); w.u32(b); w.u32(c)

def read_numeric(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    o['maximum'] = rf(r); o['minimum'] = rf(r); o['step'] = rf(r)
    o['flash_colour'] = [rf(r) for _ in range(4)]; o['flash_timer'] = rf(r)
    o['display_as_int'] = r.u32(); o['precision'] = r.u32()
    o['dec_hash'] = r.u32(); o['inc_hash'] = r.u32(); o['feedback_hash'] = r.u32()
    if v >= 1: o['console_var'] = read_console_var(r)
    if v >= 2: o['repeat_delays'] = [rf(r), rf(r)]
    if v >= 3: o['numeric_flags'] = r.u32()
def write_numeric(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    wf(w, o['maximum']); wf(w, o['minimum']); wf(w, o['step'])
    for c in o['flash_colour']: wf(w, c)
    wf(w, o['flash_timer']); w.u32(o['display_as_int']); w.u32(o['precision'])
    w.u32(o['dec_hash']); w.u32(o['inc_hash']); w.u32(o['feedback_hash'])
    if v >= 1: write_console_var(w, o['console_var'])
    if v >= 2: wf(w, o['repeat_delays'][0]); wf(w, o['repeat_delays'][1])
    if v >= 3: w.u32(o['numeric_flags'])

def read_listboxentry(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
def write_listboxentry(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])

def read_listbox(r, o, v):
    read_widget_base(r, o); o['children'] = read_children(r)
    if v < 6: o['dims'] = [rf(r), rf(r)]
    o['max_allowed'] = r.u32(); o['max_displayed'] = r.u32()
    o['commands'] = read_command_manager(r)
    tv = r.u32(); tt = r.u32()
    if tt != T_LISTBOXENTRY: raise Unsupported('list box template type %d' % tt)
    t = {'type': tt, 'version': tv}; read_listboxentry(r, t, tv); o['template'] = t
    if v < 11: raise Unsupported('list box version %d' % v)
    n = r.u32()
    o['population'] = [(r.u32(), read_console_cmd(r)) for _ in range(n)]
    o['visibility'] = [(r.u32(), read_console_cmd(r)) for _ in range(n)]
def write_listbox(w, o, v):
    write_widget_base(w, o); write_children(w, o['children'])
    if v < 6: wf(w, o['dims'][0]); wf(w, o['dims'][1])
    w.u32(o['max_allowed']); w.u32(o['max_displayed']); write_command_manager(w, o['commands'])
    write_object(w, o['template'])
    w.u32(len(o['population']))
    for h, c in o['population']: w.u32(h); write_console_cmd(w, c)
    for h, c in o['visibility']: w.u32(h); write_console_cmd(w, c)

READERS = {T_MENUPAGE: read_menupage, T_IMAGE: read_image, T_TEXT: read_text, T_PATH: read_path,
           T_ANIMATION: read_animation, T_STATUSTEXT: read_statustext, T_FMV: read_fmv, T_BUTTON: read_button,
           T_CHECKBOX: read_checkbox, T_SLIDER: read_slider, T_TEXTBOX: read_textbox, T_TEXTLISTBOX: read_textlistbox,
           T_GROUP: read_group, T_ANIMIMAGE: read_animimage, T_PROGRESSBAR: read_progressbar, T_NUMERIC: read_numeric,
           T_LISTBOX: read_listbox, T_LISTBOXENTRY: read_listboxentry}
WRITERS = {T_MENUPAGE: write_menupage, T_IMAGE: write_image, T_TEXT: write_text, T_PATH: write_path,
           T_ANIMATION: write_animation, T_STATUSTEXT: write_statustext, T_FMV: write_fmv, T_BUTTON: write_button,
           T_CHECKBOX: write_checkbox, T_SLIDER: write_slider, T_TEXTBOX: write_textbox, T_TEXTLISTBOX: write_textlistbox,
           T_GROUP: write_group, T_ANIMIMAGE: write_animimage, T_PROGRESSBAR: write_progressbar, T_NUMERIC: write_numeric,
           T_LISTBOX: write_listbox, T_LISTBOXENTRY: write_listboxentry}

# ---------------------------------------------------------------- files

class Chunk:
    def __init__(self, tag, version, flags, payload):
        self.tag, self.version, self.flags, self.payload = tag, version, flags, payload
        self.page = None       # parsed page for UIMP chunks
        self.error = None
    def encode(self):
        body = self.payload if self.page is None else encode_page(self.page)
        return self.tag.encode('latin1') + struct.pack('<III', 16 + len(body), self.version, self.flags) + body

def encode_page(page):
    w = Writer()
    w.u32(page['chunk_version']); w.u32(T_MENUPAGE)
    write_menupage(w, page, page['version'])
    return bytes(w.b)

def parse_page(payload):
    r = Reader(payload)
    chunk_version = r.u32(); typ = r.u32()
    if typ != T_MENUPAGE: raise Unsupported('UIMP object type %d' % typ)
    page = {'type': typ, 'version': chunk_version, 'chunk_version': chunk_version}
    read_menupage(r, page, chunk_version)
    if r.p != len(payload):
        raise Unsupported('page %s: %d trailing bytes' % (page.get('name'), len(payload) - r.p))
    return page

class GuiFile:
    def __init__(self, data):
        self.header = bytes(data[:8])
        self.chunks = []
        p = 8
        while p + 16 <= len(data):
            tag = data[p:p + 4].decode('latin1'); size, version, flags = struct.unpack_from('<III', data, p + 4)
            payload = bytes(data[p + 16:p + size])
            c = Chunk(tag, version, flags, payload)
            if tag == 'UIMP':
                try: c.page = parse_page(payload)
                except Unsupported as e: c.error = str(e)
            self.chunks.append(c); p += size
        self.trailer = bytes(data[p:])
    def encode(self):
        return self.header + b''.join(c.encode() for c in self.chunks) + self.trailer
    def pages(self):
        return [c.page for c in self.chunks if c.page is not None]
    def page(self, name):
        for c in self.chunks:
            if c.page is not None and c.page['name'] == name: return c.page
        raise KeyError(name)

def walk(obj):
    yield obj
    for c in obj.get('children', []):
        yield from walk(c)
    if 'template' in obj: yield from walk(obj['template'])

def find(page, name):
    for o in walk(page):
        if o.get('name') == name: return o
    raise KeyError(name)

def roundtrip_check(path):
    data = open(path, 'rb').read()
    g = GuiFile(data)
    out = g.encode()
    ok = out == data
    report = ['%s: %s, %d chunks, %d pages parsed' % (os.path.basename(path), 'byte-exact' if ok else 'MISMATCH', len(g.chunks), len(g.pages()))]
    for c in g.chunks:
        if c.tag == 'UIMP' and c.error: report.append('   unparsed page: ' + c.error)
    if not ok:
        for i, c in enumerate(g.chunks):
            if c.page is not None and c.encode() != c.tag.encode('latin1') + struct.pack('<III', 16 + len(c.payload), c.version, c.flags) + c.payload:
                report.append('   chunk %d page %s re-encodes differently' % (i, c.page['name']))
    return ok, report

if __name__ == '__main__':
    if sys.argv[1] == 'roundtrip':
        allok = True
        for p in sys.argv[2:]:
            ok, rep = roundtrip_check(p); allok &= ok; print('\n'.join(rep))
        sys.exit(0 if allok else 1)
    if sys.argv[1] == 'dump':
        g = GuiFile(open(sys.argv[2], 'rb').read())
        for page in g.pages():
            print('== page', page['name'], 'startup=%08X' % page['startup_widget'], 'flags=%08X' % page.get('page_flags', 0),
                  'init=%s deinit=%s' % (page.get('on_init', {}).get('name'), page.get('on_deinit', {}).get('name')))
            def show(o, depth):
                extra = ''
                if o['type'] == T_BUTTON:
                    cmds = ['%s %s' % (a['cmd']['name'], a['cmd']['args']) for a in o.get('commands', {}).get('actions', [])]
                    extra = 'link=%08X flags=%X cmds=%s' % (o['link_to'], o['button_flags'], cmds)
                elif o['type'] == T_TEXT: extra = 'page=%08X id=%08X font=%08X scale=%s' % (o.get('text_page', 0), o.get('text_id', 0), o.get('font_hash', 0), fval(o['font_scale']))
                elif o['type'] in (T_SLIDER, T_CHECKBOX, T_NUMERIC, T_TEXTBOX, T_PROGRESSBAR, T_STATUSTEXT): extra = 'var=%s' % o.get('console_var', {}).get('name')
                elif o['type'] == T_IMAGE: extra = 'tex=%s' % o['texture']
                b = [fval(x) for x in o['bounds']] if 'bounds' in o else None
                print('  ' * depth + '%-14s %-32s hash=%08X flags=%08X bounds=%s %s' % (TYPE_NAMES.get(o['type'], o['type']), o['name'], o['hash'], o['flags'], b and [round(x, 1) for x in b], extra))
                for c in o.get('children', []): show(c, depth + 1)
            for c in page['children']: show(c, 1)
