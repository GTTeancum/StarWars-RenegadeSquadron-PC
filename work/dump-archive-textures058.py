"""Decode named PSP indexed textures and mips; preserve runtime RGBA for override IDs.

Requires numpy and Pillow. No resampling or channel correction is applied here.
"""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
base=root/'work/game/disc/PSP_GAME/USRDIR'
dest=root/'work/texture-dumps058';dest.mkdir(exist_ok=True)
images=dest/'textures';images.mkdir(exist_ok=True)
report={'scope':'Original decoded runtime RGBA, not color-corrected replacements','archives':[], 'textures':[], 'failures':[]}
offset_cache={}
for area in ('ENVS','GUIMENU','GRAPHICS','MISC'):
    for path in sorted((base/area).rglob('*')):
        if not path.is_file():continue
        b=path.read_bytes()
        if b[:8]!=b'Asura   ':continue
        archive=path.relative_to(base).as_posix();archive_sha=hashlib.sha256(b).hexdigest()
        at=8;count=0
        try:
            while at+16<=len(b):
                if len(b)-at<=16 and not any(b[at:]):at=len(b);break
                size,version,flags=struct.unpack_from('<III',b,at+4)
                if size<16 or at+size>len(b):raise ValueError(f'Invalid chunk boundary at {at}')
                c=b[at:at+size];chunk_at=at;at+=size
                if c[:4]!=b'RSCF' or len(c)<32 or struct.unpack_from('<I',c,16)[0]!=2:continue
                count+=1
                try:
                    end=c.index(0,28);name=c[28:end].decode('ascii');pos=28+((end-28+4)&~3);p=c[pos:]
                    if len(p)!=struct.unpack_from('<I',c,24)[0]:raise ValueError('Payload size mismatch')
                    w,h,unknown,fmt,mipmax=struct.unpack_from('<HHHBB',p)
                    if fmt not in (4,5) or unknown or mipmax>7 or not 0<w<=4096 or not 0<h<=4096:raise ValueError('Unsupported texture header')
                    levels=[(max(1,w>>l),max(1,h>>l)) for l in range(mipmax+1)]
                    sizes=[((lw+1)//2 if fmt==4 else lw)*lh for lw,lh in levels]
                    palette_offset=8+sum(sizes);palette_bytes=64 if fmt==4 else 1024
                    if palette_offset+palette_bytes!=len(p):raise ValueError(f'Mip/palette layout mismatch: expected {palette_offset+palette_bytes}, actual {len(p)}')
                    palette=np.frombuffer(p[palette_offset:],dtype=np.uint8).reshape(-1,4)
                    level_offset=8
                    for level,((lw,lh),length) in enumerate(zip(levels,sizes)):
                        key=(lw,lh,fmt)
                        if key not in offset_cache:
                            y,x=np.indices((lh,lw));bx=x//2 if fmt==4 else x;row=(lw+1)//2 if fmt==4 else lw
                            offsets=((y//8)*((row+15)//16)+bx//16)*128+(y%8)*16+bx%16
                            offset_cache[key]=(offsets,x)
                        offsets,x=offset_cache[key]
                        if int(offsets.max())>=length:raise ValueError(f'Unsupported short swizzle layout at mip {level}: {lw}x{lh}')
                        indices=np.frombuffer(p[level_offset:level_offset+length],dtype=np.uint8)[offsets]
                        if fmt==4:indices=np.where(x%2,indices>>4,indices&15)
                        rgba=palette[indices].copy();pixels=rgba.tobytes()
                        identity='tex-v1-'+hashlib.sha256(struct.pack('<II',lw,lh)+pixels).hexdigest()
                        target=images/(identity+'.png')
                        if not target.exists():Image.fromarray(rgba).save(target)
                        report['textures'].append(dict(archive=archive,offset=chunk_at,name=name,format=fmt,mip=level,width=lw,height=lh,id=identity,payload_sha256=hashlib.sha256(p).hexdigest()))
                        level_offset+=length
                except (ValueError,IndexError,struct.error) as e:
                    report['failures'].append(dict(archive=archive,offset=chunk_at,error=str(e)))
            if any(b[at:]):raise ValueError('Nonzero archive trailer')
        except (ValueError,struct.error) as e:report['failures'].append(dict(archive=archive,error=str(e)))
        report['archives'].append(dict(archive=archive,sha256=archive_sha,texture_chunks=count))
runtime=root/'work/runs/textures057-discovery/textures/textures.jsonl'
known={json.loads(s)['id'] for s in runtime.read_text().splitlines()}
decoded={r['id'] for r in report['textures']}
report['runtime_check']={'reference':str(runtime.relative_to(root)),'reference_ids':len(known),'exact_matches':len(known&decoded),'unmatched_ids':sorted(known-decoded)}
(dest/'catalog.json').write_text(json.dumps(report,indent=2)+'\n')
summary=dict(archives=len(report['archives']),texture_chunks=sum(a['texture_chunks'] for a in report['archives']),decoded_mip_occurrences=len(report['textures']),unique_images=len(decoded),failures=report['failures'],runtime_check=report['runtime_check'])
(root/'outputs/TEXTURE-DUMPS-058-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='failures'}|{'failure_count':len(report['failures'])},indent=2))
