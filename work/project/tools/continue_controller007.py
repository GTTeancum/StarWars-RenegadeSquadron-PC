#!/usr/bin/env python3
"""Continue a paused native process with recorded PSP controller inputs only."""
import argparse,json,time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("control",type=Path);p.add_argument("commands",type=Path)
p.add_argument("--start",type=int,required=True);p.add_argument("--end",type=int,required=True)
p.add_argument("--wait",type=float,default=600)
a=p.parse_args();deadline=time.monotonic()+a.wait
def status():
 try:return json.loads((a.control/"status.json").read_text())
 except (OSError,json.JSONDecodeError):return None
while True:
 s=status()
 if s and s["paused"] and s["vblank"]==a.start:break
 if time.monotonic()>deadline:raise RuntimeError("Initial controller endpoint not reached")
 time.sleep(.1)
records=[]
for line in a.commands.read_text().splitlines():
 _,start,end,buttons,x,y=map(int,line.split())
 if start>=a.start and end>0 and end<=a.end:records.append((start,end,buttons,x,y))
at=a.start
for start,end,buttons,x,y in records:
 if start!=at:raise RuntimeError("Recorded input intervals are not contiguous")
 s=status()
 if not s or not s["paused"] or s["vblank"]!=start:raise RuntimeError("Native state does not match recorded boundary")
 seq=s["sequence"]+1;tmp=a.control/"command.new"
 tmp.write_text(f"{seq} {end} {buttons} {x} {y}\n");tmp.replace(a.control/"command.txt")
 while True:
  s=status()
  if s and s["sequence"]==seq and s["paused"] and s["vblank"]==end:break
  if time.monotonic()>deadline:raise RuntimeError("Controller continuation timed out")
  time.sleep(.1)
 print(json.dumps({"from":start,"until":end,"buttons":buttons,"x":x,"y":y}),flush=True)
 at=end
if at!=a.end:raise RuntimeError("Continuation did not reach requested final endpoint")
print(json.dumps({"finished":True,"vblank":at,"guest_state_injection":False}),flush=True)
