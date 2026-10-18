r"""CPU runner for the Real-ESRGAN family ncnn models (.param/.bin), in NumPy.

The ncnn Vulkan builds cannot allocate GPU memory on this machine's Radeon 780M
driver, so the same published models run here on the CPU: the .param graph
(Convolution with optional leaky ReLU, Split, Concat, Eltwise sum with
coefficients, BinaryOp add, nearest Interp) is executed layer by layer with the
weights read from .bin in ncnn's storage order (per convolution: a 4-byte tag,
fp32 or fp16 weights [out, in, kh, kw], then fp32 bias).

    net = Net(param_path, bin_path)
    out = net.run(rgb_float32)   # (H, W, 3) in 0..1 -> (4H, 4W, 3)
"""
import numpy as np

class Net:
    def __init__(self, param_path, bin_path):
        lines = open(param_path).read().split('\n')
        assert lines[0].strip() == '7767517'
        self.layers = []
        blob = open(bin_path, 'rb').read()
        pos = 0
        for line in lines[2:]:
            parts = line.split()
            if not parts: continue
            kind, name = parts[0], parts[1]
            nin, nout = int(parts[2]), int(parts[3])
            ins = parts[4:4 + nin]; outs = parts[4 + nin:4 + nin + nout]
            params = {}
            for kv in parts[4 + nin + nout:]:
                k, v = kv.split('=', 1)
                k = int(k)
                if k <= -23300:  # array: -233xx=count,v1,v2...
                    vals = v.split(',')
                    params[-(k + 23300)] = [float(x) for x in vals[1:]]
                else:
                    params[k] = float(v) if ('.' in v or 'e' in v) else int(v)
            layer = dict(kind=kind, name=name, ins=ins, outs=outs, p=params)
            if kind == 'Convolution':
                o, k = params[0], params.get(1, 1)
                size = params[6]
                tag = int.from_bytes(blob[pos:pos + 4], 'little'); pos += 4
                if tag == 0x01306B47:
                    w = np.frombuffer(blob, np.float16, size, pos).astype(np.float32); pos += size * 2
                    pos += (-pos) % 4
                elif tag == 0:
                    w = np.frombuffer(blob, np.float32, size, pos).copy(); pos += size * 4
                else:
                    raise ValueError('unsupported weight tag %x in %s' % (tag, name))
                c = size // (o * k * k)
                layer['w'] = w.reshape(o, c * k * k)
                layer['k'] = k
                if params.get(5, 0):
                    layer['b'] = np.frombuffer(blob, np.float32, o, pos).copy(); pos += o * 4
                else:
                    layer['b'] = np.zeros(o, np.float32)
            self.layers.append(layer)
        assert pos == len(blob), 'weights not fully consumed (%d of %d)' % (pos, len(blob))
        # last use of each blob, to free intermediates early
        self.last = {}
        for i, l in enumerate(self.layers):
            for b in l['ins']: self.last[b] = i

    @staticmethod
    def conv(x, w, b, k):
        c, h, wd = x.shape
        if k == 1:
            cols = x.reshape(c, h * wd)
        else:
            p = k // 2
            xp = np.pad(x, ((0, 0), (p, p), (p, p)))
            win = np.lib.stride_tricks.sliding_window_view(xp, (k, k), axis=(1, 2))  # c,h,w,k,k
            cols = np.ascontiguousarray(win.transpose(0, 3, 4, 1, 2)).reshape(c * k * k, h * wd)
        out = w @ cols
        out += b[:, None]
        return out.reshape(-1, h, wd)

    def run(self, rgb):
        blobs = {}
        x = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32)
        for i, l in enumerate(self.layers):
            kind = l['kind']
            if kind == 'Input':
                blobs[l['outs'][0]] = x
                continue
            ins = [blobs[b] for b in l['ins']]
            if kind == 'Convolution':
                y = self.conv(ins[0], l['w'], l['b'], l['k'])
                if l['p'].get(9, 0) == 2:  # leaky relu
                    slope = l['p'].get(10, [0.0])[0]
                    np.maximum(y, y * slope, out=y)
                elif l['p'].get(9, 0) == 1:
                    np.maximum(y, 0, out=y)
                outs = [y]
            elif kind == 'Split':
                outs = [ins[0]] * len(l['outs'])
            elif kind == 'Concat':
                outs = [np.concatenate(ins, axis=0)]
            elif kind == 'Eltwise':
                coeffs = l['p'].get(1, [1.0] * len(ins))
                y = ins[0] * coeffs[0]
                for t, c in zip(ins[1:], coeffs[1:]): y = y + t * c
                outs = [y]
            elif kind == 'BinaryOp':
                assert l['p'].get(0, 0) == 0, 'only add'
                outs = [ins[0] + ins[1]]
            elif kind == 'Interp':
                assert l['p'].get(0, 1) == 1, 'only nearest'
                s = int(round(l['p'].get(1, 2.0)))
                outs = [np.repeat(np.repeat(ins[0], s, axis=1), s, axis=2)]
            else:
                raise ValueError('unsupported layer ' + kind)
            for b, v in zip(l['outs'], outs): blobs[b] = v
            for b in l['ins']:
                if self.last.get(b) == i and b in blobs: del blobs[b]
        out = blobs['output']
        return np.clip(out.transpose(1, 2, 0), 0.0, 1.0)

def upscale(net, rgb, tile=96, overlap=12):
    """Tiled run (bounded memory); tiles overlap and are cross-faded."""
    h, w, _ = rgb.shape
    s = 4
    out = np.zeros((h * s, w * s, 3), np.float32)
    weight = np.zeros((h * s, w * s, 1), np.float32)
    step = tile - overlap
    ys = list(range(0, max(1, h - overlap), step)) or [0]
    xs = list(range(0, max(1, w - overlap), step)) or [0]
    for y0 in ys:
        for x0 in xs:
            y1, x1 = min(h, y0 + tile), min(w, x0 + tile)
            ya, xa = max(0, y1 - tile), max(0, x1 - tile)
            part = net.run(rgb[ya:y1, xa:x1])
            th, tw = (y1 - ya) * s, (x1 - xa) * s
            ramp_y = np.minimum(np.arange(th) + 1, np.arange(th)[::-1] + 1).astype(np.float32)
            ramp_x = np.minimum(np.arange(tw) + 1, np.arange(tw)[::-1] + 1).astype(np.float32)
            m = np.minimum(np.minimum(ramp_y[:, None], overlap * s), np.minimum(ramp_x[None, :], overlap * s))[:, :, None]
            out[ya * s:y1 * s, xa * s:x1 * s] += part * m
            weight[ya * s:y1 * s, xa * s:x1 * s] += m
    return out / np.maximum(weight, 1e-6)
