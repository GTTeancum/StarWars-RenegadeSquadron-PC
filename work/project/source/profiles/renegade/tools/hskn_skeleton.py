"""Read verified HSKN v8 skeleton metadata without extracting game geometry.

Layout follows original loader 08826794: 08826894 parents, 088268AC poses,
08826A94 named parts, 088269AC slot IDs. Unsupported variants fail explicitly.
"""
import math
import struct


def parse_skeleton(data):
    if len(data) < 24 or data[:4] != b'HSKN':
        raise ValueError('Expected HSKN header')
    size, version, flags, extras, count = struct.unpack_from('<5I', data, 4)
    if size != len(data) or size > 128 * 1024 * 1024:
        raise ValueError('Invalid HSKN size')
    if version != 8 or flags & ~9 or not flags & 1:
        raise ValueError('Only named HSKN v8 flags 1/9 are verified')
    if not 0 < count <= 4096 or extras > 4096:
        raise ValueError('Invalid HSKN count')
    pos = 24

    def take(size):
        nonlocal pos
        if size < 0 or pos + size > len(data):
            raise ValueError('Truncated HSKN field')
        result = data[pos:pos+size]
        pos += size
        return result

    def string():
        nonlocal pos
        end = data.find(b'\0', pos, min(len(data), pos+513))
        if end < 0:
            raise ValueError('Invalid HSKN string')
        length = end-pos
        raw = take((length+4) & ~3)
        if any(v < 32 or v > 126 for v in raw[:length]):
            raise ValueError('Non-ASCII HSKN name')
        return raw[:length].decode('ascii')

    name = string()
    take(extras*72)  # Original loader 08826B80 skips these records.
    parents = struct.unpack('<' + str(count) + 'I', take(count*4))
    poses = list(struct.iter_unpack('<7f', take(count*28)))
    bones = []
    for i, pose in enumerate(poses):
        if parents[i] > i or (i and parents[i] == i):
            raise ValueError('Invalid or non-topological HSKN parent')
        if not all(math.isfinite(v) for v in pose):
            raise ValueError('Nonfinite HSKN pose')
        if abs(sum(v*v for v in pose[3:])-1) > 0.01:
            raise ValueError('Invalid HSKN quaternion')
        bone_name = string()
        geometry_size, = struct.unpack('<I', take(4))
        take(geometry_size)
        bones.append(dict(slot=i, name=bone_name, parent=parents[i],
                          translation=list(pose[:3]), rotation_xyzw=list(pose[3:]),
                          geometry_bytes=geometry_size))
    ids = struct.unpack('<' + str(count) + 'I', take(count*4))
    if pos != len(data):
        raise ValueError('Unexpected HSKN trailer')
    for bone, identity in zip(bones, ids):
        bone['slot_id'] = identity
        x, y, z, w = bone['rotation_xyzw']
        rotation = [1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w),
                    2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w),
                    2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y)]
        translation = bone['translation'][:]
        if bone['slot']:
            parent = bones[bone['parent']]
            pr = parent['bind_rotation_columns']
            translation = [sum(pr[k*3+i]*translation[k] for k in range(3))+
                           parent['bind_translation'][i] for i in range(3)]
            rotation = [sum(pr[k*3+i]*rotation[j*3+k] for k in range(3))
                        for j in range(3) for i in range(3)]
        bone['bind_rotation_columns'] = rotation
        bone['bind_translation'] = translation
    return dict(name=name, version=version, flags=flags, bones=bones)


def extract_skeleton(archive, model_name):
    """Find one named skeleton in a complete, boundary-validated Asura archive."""
    if archive[:8] != b'Asura   ':
        raise ValueError('Expected Asura archive')
    pos = 8
    found = []
    while pos + 16 <= len(archive):
        size, = struct.unpack_from('<I', archive, pos+4)
        if size < 16 or pos+size > len(archive):
            raise ValueError('Invalid Asura chunk boundary')
        if archive[pos:pos+4] == b'HSKN':
            chunk = archive[pos:pos+size]
            end = chunk.find(b'\0', 24, 537)
            if end >= 0 and chunk[24:end] == model_name.encode('ascii'):
                found.append(parse_skeleton(chunk))
        pos += size
    if archive[pos:] not in (b'', b'\0'*4):
        raise ValueError('Unexpected Asura trailer')
    if len(found) != 1:
        raise ValueError('Expected exactly one matching HSKN model')
    return found[0]


if __name__ == '__main__':
    import argparse
    import hashlib
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('model_name')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = args.archive.read_bytes()
    result = extract_skeleton(data, args.model_name)
    result['source_sha256'] = hashlib.sha256(data).hexdigest()
    result['source_archive'] = str(args.archive.resolve())
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
