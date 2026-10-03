"""Read-only input-table inspection of this task's paused native game; no RAM dump or writes."""
import ctypes as c,struct,json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('label');a=p.parse_args();r=Path(__file__).resolve().parent
meta=json.loads((r/'runs'/a.run/'run.json').read_text());status=json.loads((r/'runs'/('control-'+a.run)/'status.json').read_text());assert status['paused'] and meta['exit_code'] is None
k=c.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[c.c_uint32,c.c_int,c.c_uint32];k.OpenProcess.restype=c.c_void_p
k.CloseHandle.argtypes=[c.c_void_p]
k.ReadProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)];k.ReadProcessMemory.restype=c.c_int
k.QueryFullProcessImageNameW.argtypes=[c.c_void_p,c.c_uint32,c.c_wchar_p,c.POINTER(c.c_uint32)];k.QueryFullProcessImageNameW.restype=c.c_int
class MBI(c.Structure):
 _fields_=[('base',c.c_void_p),('allocation',c.c_void_p),('allocation_protect',c.c_uint32),('partition',c.c_ushort),('size',c.c_size_t),('state',c.c_uint32),('protect',c.c_uint32),('type',c.c_uint32)]
k.VirtualQueryEx.argtypes=[c.c_void_p,c.c_void_p,c.POINTER(MBI),c.c_size_t];k.VirtualQueryEx.restype=c.c_size_t
h=k.OpenProcess(0x410,False,meta['pid']);assert h,'OpenProcess read-only failed'
def read(addr,size):
 buf=c.create_string_buffer(size);got=c.c_size_t();assert k.ReadProcessMemory(h,addr,buf,size,c.byref(got)) and got.value==size,'ReadProcessMemory failed';return buf.raw
try:
 name=c.create_unicode_buffer(32768);n=c.c_uint32(len(name));assert k.QueryFullProcessImageNameW(h,0,name,c.byref(n))
 assert Path(name.value).resolve()==Path(meta['command'][0]).resolve(),'PID image mismatch'
 boot=(r/'game/disc/PSP_GAME/SYSDIR/BOOT.BIN').read_bytes();assert boot[:4]==b'\x7fELF'
 phoff=struct.unpack_from('<I',boot,28)[0];phsize,phcount=struct.unpack_from('<HH',boot,42)
 segments=[struct.unpack_from('<8I',boot,phoff+i*phsize) for i in range(phcount)]
 seg=next(s for s in segments if s[0]==1 and s[4]>256 and s[6]&1)
 _,offset,vaddr,_,size,_,_,_=seg
 # This PRX has relative segment addresses and is relocated to 0x08804000.
 if vaddr<0x08000000:vaddr+=0x08804000
 signature=boot[offset:offset+8];guest_base=0x08000000
 hostbase=None;address=0
 while address<0x00007fffffffffff:
  m=MBI()
  if not k.VirtualQueryEx(h,address,c.byref(m),c.sizeof(m)):break
  base=m.base or 0
  if m.state==0x1000 and m.protect&0xff in (4,8,0x40,0x80) and 32*1024*1024<=m.size<=96*1024*1024:
   begin=base+(vaddr-guest_base)//65536*65536
   try:b=read(begin,131072)
   except AssertionError:b=b''
   at=b.find(signature)
   if at>=0 and b[at+24:at+36]==boot[offset+24:offset+36]:hostbase=begin+at-(vaddr-guest_base);break
  address=base+m.size
 assert hostbase is not None,'Cannot identify guest RAM by original code signature'
 ram=read(hostbase,32*1024*1024)
 def u(addr):return struct.unpack_from('<I',ram,addr-guest_base)[0]
 readers=(0x08A5E34C,0x08A5EC4C,0x08A5EE14,0x08A5F128,0x08A60028,0x08A60A00)
 objects=[]
 for reader in readers:
  needle=struct.pack('<I',reader);start=0
  while True:
   pos=ram.find(needle,start)
   if pos<0:break
   start=pos+4
   if pos%4:continue
   vt=guest_base+pos-8
   if not all(u(vt+i)==0 or 0x08800000<=u(vt+i)<0x08b00000 for i in (0,4,8)):continue
   at=0;vbytes=struct.pack('<I',vt)
   while True:
    obj=ram.find(vbytes,at)
    if obj<0:break
    at=obj+4
    if obj%4 or obj+80>=len(ram):continue
    addr=guest_base+obj;maps=u(addr+8);index=u(addr+12);mp=maps+index*16
    if not (0x08800000<=mp<0x0a000000-16 and index<16):continue
    count=u(mp);values=u(mp+12)
    if not (1<=count<=64 and 0x08800000<=values<0x0a000000-count*4):continue
    numbers=list(struct.unpack_from('<'+'f'*count,ram,values-guest_base))
    objects.append(dict(object=hex(addr),vtable=hex(vt),reader=hex(reader),map=hex(mp),map_index=index,count=count,values_address=hex(values),values=numbers,binding_words={str(i):u(addr+i) for i in range(16,64,4)}))
 result=dict(run=a.run,pid=meta['pid'],executable_sha256=meta['native_binary_sha256'],status=status,method='OpenProcess QUERY_INFORMATION|VM_READ; no write rights; verified image and original-code RAM signature',objects=objects)
 out=r/'runs'/a.run/('input-inspection-'+a.label+'.json');assert not out.exists();out.write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:k.CloseHandle(h)
