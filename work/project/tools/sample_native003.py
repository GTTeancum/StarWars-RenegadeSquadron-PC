#!/usr/bin/env python3
"""Read-only ptrace CPU/stack sampler; no target register or memory writes."""
import ctypes,os,sys,json,time
libc=ctypes.CDLL(None,use_errno=True)
libc.ptrace.restype=ctypes.c_long
class Regs(ctypes.Structure):
 _fields_=[(x,ctypes.c_ulonglong) for x in 'r15 r14 r13 r12 rbp rbx r11 r10 r9 r8 rax rcx rdx rsi rdi orig_rax rip cs eflags rsp ss fs_base gs_base ds es fs gs'.split()]
pid=int(sys.argv[1]);rc=libc.ptrace(16,pid,None,None)
if rc==-1:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
try:
 os.waitpid(pid,0);r=Regs()
 if libc.ptrace(12,pid,None,ctypes.byref(r))==-1:raise OSError(ctypes.get_errno())
 result={'pid':pid,'registers':{n:hex(getattr(r,n)) for n,_ in r._fields_},'maps':open(f'/proc/{pid}/maps').read()}
 with open(f'/proc/{pid}/mem','rb',buffering=0) as f:
  f.seek(r.rsp);stack=f.read(2048);result['stack_qwords']=[hex(int.from_bytes(stack[i:i+8],'little')) for i in range(0,len(stack),8)]
 print(json.dumps(result,indent=2))
finally:libc.ptrace(17,pid,None,None)
