r"""Hashed menu text (HTXT chunks, Asura_Chunk_HashedLocalisedText version 1/2)
and plain text tables (LTXT, Asura_Chunk_LocalText version 4) in Renegade's
.ASR text files. Formats follow the engine's Process() readers in
work\asura-reference\AvP_Branches\E3\Asura\Independent\ChunkSystem.

Menu strings live in MISC\MENU\MENU_<lang>.ASR as one HTXT page ("Menu",
0x0033155F); each entry is (hash of the text ID, UTF-16 string). HUD/game
strings live in TEXT\STDTEXT.ASR as LTXT tables indexed by number.
"""
import struct, sys, os
from asura_gui import asura_hash

class AsrFile:
    def __init__(self, data):
        self.header = bytes(data[:8]); self.chunks = []
        p = 8
        while p + 16 <= len(data):
            tag = data[p:p + 4].decode('latin1'); size, version, flags = struct.unpack_from('<III', data, p + 4)
            if size < 16: break
            self.chunks.append([tag, version, flags, bytes(data[p + 16:p + size])]); p += size
        self.trailer = bytes(data[p:])
    def encode(self):
        out = bytearray(self.header)
        for tag, version, flags, payload in self.chunks:
            out += tag.encode('latin1') + struct.pack('<III', 16 + len(payload), version, flags) + payload
        return bytes(out) + self.trailer

def utf16(s):
    return s.encode('utf-16le')

class HashedText:
    """One HTXT chunk: count, page id, string bytes, entries, page name, text ids."""
    def __init__(self, version, flags, payload):
        self.version, self.flags = version, flags
        r = 0
        count = struct.unpack_from('<i', payload, r)[0]; r += 4
        if version >= 1:
            self.page_id, size_for_strings = struct.unpack_from('<II', payload, r); r += 8
        else:
            self.page_id = asura_hash('Cutscene')
        self.entries = []   # [hash, text, raw utf-16 bytes or None once edited]
        for _ in range(count):
            h, n = struct.unpack_from('<Ii', payload, r); r += 8
            raw = payload[r:r + n * 2]; r += n * 2
            self.entries.append([h, raw.decode('utf-16le').rstrip('\0'), raw])
        self.page_name = None; self.ids = None
        if version >= 2:
            end = payload.index(b'\0', r); self.page_name = payload[r:end].decode('latin1'); r = end + 1
            while r % 4: r += 1
        if version >= 1:
            size_ids = struct.unpack_from('<I', payload, r)[0]; r += 4
            self.ids = payload[r:r + size_ids].split(b'\0')[:count]; r += size_ids
        self.rest = payload[r:]
    def encode(self):
        blobs = [(h, raw if raw is not None else utf16(s + '\0')) for h, s, raw in self.entries]
        strings = b''.join(struct.pack('<Ii', h, len(b) // 2) + b for h, b in blobs)
        size_for_strings = sum(len(b) for h, b in blobs)
        out = struct.pack('<i', len(self.entries))
        if self.version >= 1: out += struct.pack('<II', self.page_id, size_for_strings)
        out += strings
        if self.version >= 2:
            name = self.page_name.encode('latin1') + b'\0'; name += b'\0' * (-len(name) % 4); out += name
        if self.version >= 1:
            ids = b''.join(i + b'\0' for i in self.ids)
            out += struct.pack('<I', len(ids)) + ids
        return out + self.rest
    def find(self, text_id):
        h = asura_hash(text_id)
        for e in self.entries:
            if e[0] == h: return e[1]
        return None
    def set(self, text_id, text):
        """Adds or replaces the string for a text ID (menus look it up by hash)."""
        h = asura_hash(text_id)
        for e in self.entries:
            if e[0] == h: e[1] = text; e[2] = None; return
        self.entries.append([h, text, None])
        if self.ids is not None: self.ids.append(text_id.encode('latin1'))

class LocalText:
    """One LTXT chunk (version 4): language, then numbered strings."""
    def __init__(self, version, flags, payload):
        # the chunk struct carries NumEntries, then (version 4) the language number
        self.version, self.flags = version, flags
        r = 0
        count = struct.unpack_from('<i', payload, r)[0]; r += 4
        self.language = struct.unpack_from('<i', payload, r)[0]; r += 4
        self.strings = []   # [text, raw bytes or None once edited]
        for _ in range(count):
            n = struct.unpack_from('<i', payload, r)[0]; r += 4
            raw = payload[r:r + n * 2]; r += n * 2
            self.strings.append([raw.decode('utf-16le').rstrip('\0'), raw])
        self.rest = payload[r:]
    def encode(self):
        out = struct.pack('<ii', len(self.strings), self.language)
        for s, raw in self.strings:
            b = raw if raw is not None else utf16(s + '\0')
            out += struct.pack('<i', len(b) // 2) + b
        return out + self.rest
    def set(self, index, text):
        self.strings[index] = [text, None]

def load_menu_text(path):
    f = AsrFile(open(path, 'rb').read())
    pages = [(i, HashedText(c[1], c[2], c[3])) for i, c in enumerate(f.chunks) if c[0] == 'HTXT']
    return f, pages

def save_menu_text(f, pages, path):
    for i, page in pages: f.chunks[i][3] = page.encode()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(f.encode())

if __name__ == '__main__':
    path = sys.argv[2]
    data = open(path, 'rb').read()
    f = AsrFile(data)
    if sys.argv[1] == 'roundtrip':
        for c in f.chunks:
            if c[0] == 'HTXT': c[3] = HashedText(c[1], c[2], c[3]).encode()
            if c[0] == 'LTXT': c[3] = LocalText(c[1], c[2], c[3]).encode()
        print(os.path.basename(path), 'byte-exact' if f.encode() == data else 'MISMATCH')
    elif sys.argv[1] == 'find':
        for c in f.chunks:
            if c[0] == 'HTXT':
                t = HashedText(c[1], c[2], c[3])
                for h, s, raw in t.entries:
                    if sys.argv[3].lower() in s.lower(): print('%08X %r' % (h, s))
    elif sys.argv[1] == 'ids':
        for c in f.chunks:
            if c[0] == 'HTXT':
                t = HashedText(c[1], c[2], c[3])
                for (h, s, raw), i in zip(t.entries, t.ids or []): print('%08X %-40s %r' % (h, i.decode('latin1'), s[:60]))
