#!/usr/bin/env python3
"""Send real X11 mouse/key input to a single native test window on a private Xvfb.
No game memory/process injection. Window coordinates are in client pixels.
"""
import argparse,ctypes as C,ctypes.util,json,os,re,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--display',default=':95');p.add_argument('--id');p.add_argument('--log',type=Path)
p.add_argument('action',choices=['list','click','move','key','resize','focus','capture']);p.add_argument('args',nargs='*');a=p.parse_args()
env=dict(os.environ,DISPLAY=a.display)
windows=subprocess.check_output(['wmctrl','-l'],env=env,text=True)
if a.action=='list':print(windows);raise SystemExit(0)
ids=[line.split()[0] for line in windows.splitlines() if 'Renegade' in line or 'vblank ' in line]
w=a.id or (ids[0] if len(ids)==1 else None)
if not w:raise SystemExit('Specify --id for a unique Renegade window; got '+windows)
subprocess.run(['wmctrl','-ia',w],env=env,check=True);time.sleep(.08)
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.restype=C.c_void_p;x.XOpenDisplay.argtypes=[C.c_char_p];d=x.XOpenDisplay(a.display.encode())
if not d:raise SystemExit('Could not open private X display')
x.XFlush.argtypes=[C.c_void_p];x.XSync.argtypes=[C.c_void_p,C.c_int];x.XCloseDisplay.argtypes=[C.c_void_p]
x.XStringToKeysym.argtypes=[C.c_char_p];x.XStringToKeysym.restype=C.c_ulong
x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_ubyte
xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
try:
 if a.action in ['click','move']:
  if len(a.args)!=2:p.error('click/move need client x y')
  output=subprocess.check_output(['xwininfo','-id',w],env=env,text=True)
  x0=int(re.search(r'Absolute upper-left X:\s*(-?\d+)',output)[1]);y0=int(re.search(r'Absolute upper-left Y:\s*(-?\d+)',output)[1])
  xx,yy=map(int,a.args);xt.XTestFakeMotionEvent(d,-1,x0+xx,y0+yy,0)
  if a.action=='click':xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0)
 elif a.action=='key':
  if not a.args:p.error('key needs one or more X keysym names')
  codes=[x.XKeysymToKeycode(d,x.XStringToKeysym(v.encode())) for v in a.args]
  if not all(codes):p.error('unknown key')
  for code in codes:xt.XTestFakeKeyEvent(d,code,1,0)
  for code in reversed(codes):xt.XTestFakeKeyEvent(d,code,0,0)
 elif a.action=='resize':
  if len(a.args)!=2:p.error('resize needs width height')
  width,height=map(int,a.args)
  if not (480<=width<=4096 and 312<=height<=4096):p.error('invalid resize')
  subprocess.run(['wmctrl','-ir',w,'-e',f'0,-1,-1,{width},{height}'],env=env,check=True)
 elif a.action=='capture':
  if len(a.args)!=1:p.error('capture needs output PNG')
  dest=Path(a.args[0]);dest.parent.mkdir(parents=True,exist_ok=True)
  # Captures real pixels including the window-manager title bar.
  from PIL import ImageGrab
  output=subprocess.check_output(['xwininfo','-id',w],env=env,text=True)
  x0=int(re.search(r'Absolute upper-left X:\s*(-?\d+)',output)[1]);y0=int(re.search(r'Absolute upper-left Y:\s*(-?\d+)',output)[1])
  width=int(re.search(r'Width:\s*(\d+)',output)[1]);height=int(re.search(r'Height:\s*(\d+)',output)[1])
  prop=subprocess.check_output(['xprop','-id',w,'_NET_FRAME_EXTENTS'],env=env,text=True)
  m=re.search(r'=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)',prop)
  left,right,top,bottom=map(int,m.groups()) if m else (0,0,0,0)
  ImageGrab.grab(xdisplay=a.display).crop((x0-left,y0-top,x0+width+right,y0+height+bottom)).save(dest)
 elif a.action!='focus':p.error('unknown action')
 x.XSync(d,0)
finally:x.XCloseDisplay(d)
record={'unix':time.time(),'display':a.display,'window':w,'action':a.action,'args':a.args}
if a.log:
 a.log.parent.mkdir(parents=True,exist_ok=True)
 with a.log.open('a') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(record))
