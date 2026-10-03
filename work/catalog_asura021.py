"""Read-only catalog of Renegade Asura archives; writes metadata, never payloads.

Observed RSFL offsets address the file with the RSFL chunk removed. Verify every
range against actual chunk boundaries; do not accept guessed/misaligned entries.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


def u32(data, at):
    if at < 0 or at + 4 > len(data):
        raise ValueError('Truncated uint32')
    return struct.unpack_from('<I', data, at)[0]


def cstring(data, at, end):
    stop = data.find(b'\0', at, end)
    if stop < 0 or stop - at > 4096:
        raise ValueError('Invalid resource string')
    return data[at:stop].decode('ascii'), (stop + 4) & ~3


def catalog(path):
    data = path.read_bytes()
    if data[:8] != b'Asura   ':
        raise ValueError('Unsupported archive signature')
    chunks = {}
    at = 8
    while at + 16 <= len(data):
        tag = data[at:at+4].decode('ascii')
        size, version, flags = struct.unpack_from('<III', data, at+4)
        if size < 16 or at+size > len(data):
            raise ValueError(f'Invalid chunk at {at:#x}')
        chunks[at] = dict(tag=tag, offset=at, size=size, version=version, flags=flags)
        at += size
    if data[at:] not in (b'', b'\0'*4):
        raise ValueError('Unexpected archive trailer')
    tables = [c for c in chunks.values() if c['tag'] == 'RSFL']
    if len(tables) != 1:
        raise ValueError('Expected one RSFL table')
    table = tables[0]
    table_end = table['offset'] + table['size']
    pos = table['offset'] + 16
    count = u32(data, pos)
    pos += 4
    if count > 100000:
        raise ValueError('Excessive resource count')
    resources = []
    boundaries = set(chunks) | {at}
    for _ in range(count):
        name, pos = cstring(data, pos, table_end)
        if pos+12 > table_end:
            raise ValueError('Truncated resource record')
        offset, size, flag = struct.unpack_from('<III', data, pos)
        pos += 12
        # The original offsets exclude the inserted resource-table chunk.
        start = offset + table['size'] if offset >= table['offset'] else offset
        end = start+size
        if start not in chunks or end not in boundaries or end < start:
            raise ValueError(f'Resource range not aligned: {name}')
        group = []
        cursor = start
        while cursor < end:
            chunk = chunks[cursor]
            if cursor+chunk['size'] > end:
                raise ValueError(f'Resource ends inside chunk: {name}')
            group.append(chunk)
            cursor += chunk['size']
        models = []
        for chunk in group:
            if chunk['tag'] == 'HSKN':
                model_name, _ = cstring(data, chunk['offset']+24, chunk['offset']+chunk['size'])
                models.append(dict(name=model_name, offset=chunk['offset'],
                                   size=chunk['size'], version=chunk['version'],
                                   flags=chunk['flags']))
        resources.append(dict(name=name, offset=start, size=size, flags=flag,
                              sha256=hashlib.sha256(data[start:end]).hexdigest(),
                              chunks=dict(Counter(c['tag'] for c in group)), models=models))
    if pos != table_end:
        raise ValueError('Resource table length mismatch')
    render_resources = []
    for chunk in chunks.values():
        if chunk['tag'] != 'RSCF' or chunk['size'] < 32:
            continue
        start = chunk['offset']
        kind, subtype, payload_size = struct.unpack_from('<III', data, start+16)
        if kind != 0:
            continue
        name, _ = cstring(data, start+28, start+chunk['size'])
        # Names are padded relative to the chunk, which may be unaligned globally.
        payload = start+28+((len(name)+1+3)//4)*4
        if payload+payload_size != start+chunk['size']:
            raise ValueError(f'Invalid render resource payload length: {name}')
        render_resources.append(dict(name=name, subtype=subtype, offset=start,
                                     size=chunk['size'], payload_offset=payload,
                                     payload_size=payload_size,
                                     sha256=hashlib.sha256(data[payload:payload+payload_size]).hexdigest(),
                                     leading_words=[u32(data,payload+i*4) for i in range(min(4,payload_size//4))]))
    return dict(file=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                chunks=dict(Counter(c['tag'] for c in chunks.values())),
                resource_count=count, model_count=sum(len(r['models']) for r in resources),
                resources=resources, render_resources=render_resources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('disc', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    results, failures = [], []
    for path in sorted((args.disc/'PSP_GAME'/'USRDIR').rglob('*.PSP')):
        try:
            row = catalog(path)
            row['file'] = path.relative_to(args.disc).as_posix()
            results.append(row)
        except (ValueError, KeyError, UnicodeError, struct.error) as ex:
            failures.append(dict(file=path.relative_to(args.disc).as_posix(), error=str(ex)))
    report = dict(format='renegade-asura-catalog-v1', archives=results, failures=failures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(archives=len(results), failures=failures,
                         resources=sum(r['resource_count'] for r in results),
                         models=sum(r['model_count'] for r in results))))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
