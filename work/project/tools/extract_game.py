#!/usr/bin/env python3
"""Extract supplied ISO with system libarchive and pycdlib; no game downloads."""
import ctypes as C, ctypes.util, hashlib, json, sys
from pathlib import Path, PurePosixPath
root=Path('/mnt/data/renegade/game');root.mkdir(parents=True,exist_ok=True)
archive=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/Star Wars - Battlefront - Renegade Squadron (USA).7z')
iso_path=root/'disc.iso'
if not iso_path.exists():
 a=C.CDLL(ctypes.util.find_library('archive'))
 def api(n,r,*args):
  f=getattr(a,n);f.restype=r;f.argtypes=args;return f
 p=C.c_void_p
 api('archive_read_new',p);api('archive_read_support_format_all',C.c_int,p);api('archive_read_support_filter_all',C.c_int,p)
 api('archive_read_open_filename',C.c_int,p,C.c_char_p,C.c_size_t);api('archive_read_next_header',C.c_int,p,C.POINTER(p))
 api('archive_entry_pathname',C.c_char_p,p);api('archive_entry_size',C.c_longlong,p)
 api('archive_read_data',C.c_ssize_t,p,p,C.c_size_t);api('archive_error_string',C.c_char_p,p);api('archive_read_free',C.c_int,p)
 h=a.archive_read_new();a.archive_read_support_format_all(h);a.archive_read_support_filter_all(h)
 if a.archive_read_open_filename(h,str(archive).encode(),1048576)!=0:raise RuntimeError(a.archive_error_string(h))
 e=p();buf=C.create_string_buffer(1048576)
 try:
  while a.archive_read_next_header(h,C.byref(e))==0:
   n=a.archive_entry_pathname(e).decode();size=a.archive_entry_size(e);print(n,size,flush=True)
   if not n.lower().endswith('.iso'):continue
   tmp=iso_path.with_suffix('.partial');count=0
   with tmp.open('wb') as f:
    while True:
     got=a.archive_read_data(h,buf,len(buf))
     if got<0:raise RuntimeError(a.archive_error_string(h))
     if got==0:break
     f.write(buf.raw[:got]);count+=got
   if count!=size:raise RuntimeError('ISO size mismatch')
   tmp.replace(iso_path)
 finally:a.archive_read_free(h)
sys.path.insert(0,'/mnt/data/renegade/intake/pydeps');import pycdlib
iso=pycdlib.PyCdlib();iso.open(str(iso_path));records=[]
for dirname,dirs,files in iso.walk(iso_path='/'):
 for name in files:
  src=dirname.rstrip('/')+'/'+name;rel=src.lstrip('/').split(';')[0]
  if '..' in PurePosixPath(rel).parts:raise RuntimeError('unsafe path')
  dst=root/'disc'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists():iso.get_file_from_iso(str(dst),iso_path=src)
  rec=iso.get_record(iso_path=src);records.append({'path':rel,'lba':rec.extent_location(),'size':dst.stat().st_size})
iso.close();(root/'disc-files.json').write_text(json.dumps(records,indent=2))
f=root/'disc/PSP_GAME/SYSDIR/BOOT.BIN';h=hashlib.sha256(f.read_bytes()).hexdigest()
assert h=='f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68'
print('BOOT:',f.stat().st_size,h,flush=True)
