r"""ESRGAN (RRDBNet 64nf/23nb, 4x) weights -> ONNX, with no PyTorch.

* Weights are read from .safetensors (header + raw arrays) or from a PyTorch
  .pth zip through a restricted unpickler that only rebuilds tensors and plain
  containers -- any other object in the pickle is refused, so a model file
  cannot run code here.
* The ONNX model is written directly in protobuf wire format (ModelProto with
  Conv / LeakyRelu / Concat / Mul / Add / Resize), opset 13, fp32, dynamic H/W.

usage: python esrgan_onnx.py model.pth|model.safetensors out.onnx
"""
import io, json, pickle, struct, sys, zipfile
import numpy as np

# ---------------------------------------------------------------- weights
_DTYPES = {'FloatStorage': np.float32, 'HalfStorage': np.float16, 'DoubleStorage': np.float64,
           'BFloat16Storage': None, 'LongStorage': np.int64, 'IntStorage': np.int32}

def load_safetensors(path):
    data = open(path, 'rb').read()
    n = struct.unpack_from('<Q', data, 0)[0]
    header = json.loads(data[8:8 + n])
    base = 8 + n
    kinds = {'F32': np.float32, 'F16': np.float16, 'F64': np.float64}
    out = {}
    for name, info in header.items():
        if name == '__metadata__': continue
        a, b = info['data_offsets']
        out[name] = np.frombuffer(data, kinds[info['dtype']], (b - a) // np.dtype(kinds[info['dtype']]).itemsize, base + a).reshape(info['shape']).astype(np.float32)
    return out

class _Storage:
    def __init__(self, dtype, key): self.dtype, self.key = dtype, key

def load_pth_legacy(path):
    """Pre-1.6 PyTorch file: magic, protocol and system-info pickles, the main
    pickle, the storage key list, then each storage as int64 count + raw data."""
    f = open(path, 'rb')
    import collections
    class Plain(pickle.Unpickler):
        def find_class(self, module, name):
            raise pickle.UnpicklingError('refused %s.%s in model file header' % (module, name))
    for _ in range(3): Plain(f).load()          # magic number, protocol version, sys info
    storages = {}
    rebuilds = []
    def rebuild_tensor(storage, offset, size, stride, *rest):
        holder = {}
        rebuilds.append((holder, storage, offset, tuple(size), tuple(stride)))
        return holder
    class Restricted(pickle.Unpickler):
        def find_class(self, module, name):
            if module == 'collections' and name == 'OrderedDict': return collections.OrderedDict
            if module == 'torch._utils' and name in ('_rebuild_tensor_v2', '_rebuild_tensor'): return rebuild_tensor
            if module == 'torch' and name in _DTYPES and _DTYPES[name] is not None: return name
            raise pickle.UnpicklingError('refused %s.%s in model file' % (module, name))
        def persistent_load(self, pid):
            assert pid[0] == 'storage'
            key = pid[2]
            storages.setdefault(key, _Storage(_DTYPES[pid[1]], key))
            return storages[key]
    obj = Restricted(f).load()
    keys = Plain(f).load()
    data = {}
    for key in keys:
        count = struct.unpack('<q', f.read(8))[0]
        st = storages[key]
        data[key] = np.frombuffer(f.read(count * np.dtype(st.dtype).itemsize), st.dtype)
    for holder, storage, offset, size, stride in rebuilds:
        arr = data[storage.key]
        view = np.lib.stride_tricks.as_strided(arr[offset:], shape=size, strides=tuple(x * arr.itemsize for x in stride))
        holder['__array__'] = np.array(view, dtype=np.float32, copy=True)
    def resolve(o):
        if isinstance(o, dict) and '__array__' in o and len(o) == 1: return o['__array__']
        if isinstance(o, dict): return {k: resolve(v) for k, v in o.items()}
        return o
    obj = resolve(obj)
    for wrap in ('params_ema', 'params', 'state_dict', 'model'):
        if isinstance(obj, dict) and wrap in obj and isinstance(obj[wrap], dict): obj = obj[wrap]
    return {k: v for k, v in obj.items() if isinstance(v, np.ndarray)}

def load_pth(path):
    if not zipfile.is_zipfile(path): return load_pth_legacy(path)
    z = zipfile.ZipFile(path)
    pkl = [n for n in z.namelist() if n.endswith('data.pkl')][0]
    prefix = pkl[:-len('data.pkl')]

    def rebuild_tensor(storage, offset, size, stride, *rest):
        raw = z.read(prefix + 'data/' + str(storage.key))
        arr = np.frombuffer(raw, storage.dtype)
        count = int(np.prod(size)) if size else 1
        itemsize = arr.itemsize
        view = np.lib.stride_tricks.as_strided(arr[offset:], shape=tuple(size), strides=tuple(s * itemsize for s in stride)) if size else arr[offset:offset + 1].reshape(())
        return np.array(view, dtype=np.float32, copy=True)

    class Restricted(pickle.Unpickler):
        def find_class(self, module, name):
            if module == 'collections' and name == 'OrderedDict':
                import collections; return collections.OrderedDict
            if module == 'torch._utils' and name in ('_rebuild_tensor_v2', '_rebuild_tensor'):
                return rebuild_tensor
            if module == 'torch' and name in _DTYPES and _DTYPES[name] is not None:
                return name
            raise pickle.UnpicklingError('refused %s.%s in model file' % (module, name))
        def persistent_load(self, pid):
            # ('storage', storage_type, key, location, numel)
            kind, storage_type, key = pid[0], pid[1], pid[2]
            assert kind == 'storage'
            return _Storage(_DTYPES[storage_type if isinstance(storage_type, str) else storage_type.__name__], key)

    obj = Restricted(io.BytesIO(z.read(pkl))).load()
    for wrap in ('params_ema', 'params', 'state_dict', 'model'):
        if isinstance(obj, dict) and wrap in obj and isinstance(obj[wrap], dict): obj = obj[wrap]
    return {k: v for k, v in obj.items() if isinstance(v, np.ndarray)}

def load_weights(path):
    raw = load_safetensors(path) if path.endswith('.safetensors') else load_pth(path)
    # old ESRGAN key names -> BasicSR names
    if 'model.0.weight' in raw:
        m = {}
        for k, v in raw.items():
            p = k.split('.')
            if p[1] == '0': m['conv_first.' + p[2]] = v
            elif p[1] == '1' and p[3] == '23': m['conv_body.' + p[4]] = v
            elif p[1] == '1':  # model.1.sub.i.RDBj.convk.0.weight
                m['body.%s.rdb%s.%s.%s' % (p[3], p[4][3:], p[5], p[7])] = v
            else:
                m[{'3': 'conv_up1', '6': 'conv_up2', '8': 'conv_hr', '10': 'conv_last'}[p[1]] + '.' + p[2]] = v
        raw = m
    return raw

# ---------------------------------------------------------------- protobuf writer
def _varint(n):
    out = bytearray()
    n &= (1 << 64) - 1
    while True:
        b = n & 0x7F; n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n: return bytes(out)
def _key(field, wire): return _varint((field << 3) | wire)
def f_int(field, n): return _key(field, 0) + _varint(n)
def f_bytes(field, b): return _key(field, 2) + _varint(len(b)) + b
def f_str(field, s): return f_bytes(field, s.encode())
def f_float(field, x): return _key(field, 5) + struct.pack('<f', x)

def attr_ints(name, vals): return f_str(1, name) + f_int(20, 7) + b''.join(f_int(8, v) for v in vals)
def attr_float(name, v): return f_str(1, name) + f_int(20, 1) + f_float(2, v)
def attr_int(name, v): return f_str(1, name) + f_int(20, 2) + f_int(3, v)
def attr_str(name, v): return f_str(1, name) + f_int(20, 3) + f_bytes(4, v.encode())

def node(op, ins, outs, attrs=()):
    return b''.join(f_str(1, i) for i in ins) + b''.join(f_str(2, o) for o in outs) + f_str(4, op) + b''.join(f_bytes(5, a) for a in attrs)

def tensor(name, arr):
    arr = np.ascontiguousarray(arr, dtype=np.float32)
    return b''.join(f_int(1, d) for d in arr.shape) + f_int(2, 1) + f_str(8, name) + f_bytes(9, arr.tobytes())

def value_info(name, dims):
    shape = b''.join(f_bytes(1, f_int(1, d) if isinstance(d, int) else f_str(2, d)) for d in dims)
    tt = f_int(1, 1) + f_bytes(2, shape)
    return f_str(1, name) + f_bytes(2, f_bytes(1, tt))

# ---------------------------------------------------------------- RRDBNet graph
def build(weights):
    nodes, inits = [], []
    counter = [0]
    def fresh(p):
        counter[0] += 1; return '%s_%d' % (p, counter[0])
    def conv(x, name, act):
        w, b = weights[name + '.weight'], weights[name + '.bias']
        inits.append(tensor(name + '.weight', w)); inits.append(tensor(name + '.bias', b))
        y = fresh(name)
        k = w.shape[2]
        nodes.append(node('Conv', [x, name + '.weight', name + '.bias'], [y],
                          [attr_ints('kernel_shape', [k, k]), attr_ints('pads', [k // 2] * 4), attr_ints('strides', [1, 1])]))
        if act:
            z = fresh(name + '_act')
            nodes.append(node('LeakyRelu', [y], [z], [attr_float('alpha', 0.2)])); return z
        return y
    inits.append(tensor('k_0_2', np.array([0.2], np.float32)))
    inits.append(tensor('k_scales', np.array([1, 1, 2, 2], np.float32)))
    def scaled_add(a, b):  # a*0.2 + b
        m = fresh('mul'); s = fresh('add')
        nodes.append(node('Mul', [a, 'k_0_2'], [m])); nodes.append(node('Add', [m, b], [s])); return s
    def cat(xs):
        y = fresh('cat'); nodes.append(node('Concat', xs, [y], [attr_int('axis', 1)])); return y
    def rdb(x, prefix):
        x1 = conv(x, prefix + '.conv1', True)
        x2 = conv(cat([x, x1]), prefix + '.conv2', True)
        x3 = conv(cat([x, x1, x2]), prefix + '.conv3', True)
        x4 = conv(cat([x, x1, x2, x3]), prefix + '.conv4', True)
        x5 = conv(cat([x, x1, x2, x3, x4]), prefix + '.conv5', False)
        return scaled_add(x5, x)
    def up(x):
        y = fresh('up')
        nodes.append(node('Resize', [x, '', 'k_scales'], [y],
                          [attr_str('mode', 'nearest'), attr_str('coordinate_transformation_mode', 'asymmetric'), attr_str('nearest_mode', 'floor')]))
        return y
    fea = conv('input', 'conv_first', False)
    trunk = fea
    blocks = sorted({int(k.split('.')[1]) for k in weights if k.startswith('body.')})
    for i in blocks:
        out = trunk
        for j in (1, 2, 3): out = rdb(out, 'body.%d.rdb%d' % (i, j))
        trunk = scaled_add(out, trunk)
    trunk = conv(trunk, 'conv_body', False)
    s = fresh('add'); nodes.append(node('Add', [fea, trunk], [s])); fea = s
    fea = conv(up(fea), 'conv_up1', True)
    fea = conv(up(fea), 'conv_up2', True)
    out = conv(conv(fea, 'conv_hr', True), 'conv_last', False)
    nodes.append(node('Identity', [out], ['output']))
    graph = (b''.join(f_bytes(1, n) for n in nodes) + f_str(2, 'rrdbnet') + b''.join(f_bytes(5, t) for t in inits)
             + f_bytes(11, value_info('input', [1, 3, 'h', 'w'])) + f_bytes(12, value_info('output', [1, 3, 'H', 'W'])))
    model = f_int(1, 7) + f_str(2, 'renegade-esrgan_onnx') + f_bytes(7, graph) + f_bytes(8, f_str(1, '') + f_int(2, 13))
    return model, len(blocks)

if __name__ == '__main__':
    w = load_weights(sys.argv[1])
    model, blocks = build(w)
    open(sys.argv[2], 'wb').write(model)
    print('wrote', sys.argv[2], len(model), 'bytes,', blocks, 'RRDB blocks,', len(w), 'tensors')
