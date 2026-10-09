r"""Drives the installed game through its menus for verification.

Uses the controller step channel (RENEGADE_CONTROL_DIRECTORY): the game pauses
at every vblank once RENEGADE_CONTROL_START is reached, writes the presented
GPU frame, and waits for command.txt "<sequence> <until-vblank> <buttons> <lx> <ly>".
Each step here holds buttons for a few vblanks, lets the game run on, then saves
the frame as PNG. Buttons use PSP bits (cross 0x4000, circle 0x2000, square
0x8000, triangle 0x1000, start 8, select 1, up 0x10, right 0x20, down 0x40, left 0x80).

Usage: python menu_drive.py <run-name> <script.txt>
  script lines:  press <buttons> [hold]   wait <vblanks>   shot <name>   quit
"""
import json, os, shutil, subprocess, sys, time
GAME = r'C:\Games\Star Wars Renegade Squadron'
RUNS = r'Z:\Programming\!archived\RenegadeSquadronPC\work\runs'

def ppm_to_png(src, dst):
    try:
        from PIL import Image
        Image.open(src).save(dst)
        return dst
    except Exception:
        shutil.copy(src, dst[:-4] + '.ppm'); return dst[:-4] + '.ppm'

class Driver:
    def __init__(self, name, start):
        self.dir = os.path.join(RUNS, name); self.ctl = os.path.join(self.dir, 'control')
        if os.path.isdir(self.dir): shutil.rmtree(self.dir)
        os.makedirs(self.ctl)
        env = dict(os.environ)
        env.update({'RENEGADE_CONTROL_DIRECTORY': self.ctl, 'RENEGADE_CONTROL_START': str(start),
                    'PSPRECOMP_DX12_GE_READBACK': '1'})
        self.log = open(os.path.join(self.dir, 'game.log'), 'w')
        self.proc = subprocess.Popen([os.path.join(GAME, 'RenegadeSquadron.exe')], cwd=GAME, env=env, stderr=self.log, stdout=subprocess.DEVNULL)
        self.sequence = 0; self.vblank = 0; self.status = None
        self.wait_paused()
    def wait_paused(self, timeout=300):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None: raise SystemExit('game exited with %s' % self.proc.returncode)
            try:
                s = json.load(open(os.path.join(self.ctl, 'status.json')))
                if s.get('paused') and s['sequence'] == self.sequence:
                    self.status = s; self.vblank = s['vblank']; return s
            except (OSError, ValueError): pass
            time.sleep(0.05)
        raise SystemExit('timed out waiting for pause')
    def run(self, vblanks, buttons=0):
        self.sequence += 1
        with open(os.path.join(self.ctl, 'command.tmp'), 'w') as f: f.write('%d %d %d 128 128\n' % (self.sequence, self.vblank + vblanks, buttons))
        for attempt in range(200):  # the game polls the file; retry while it holds it open
            try: os.replace(os.path.join(self.ctl, 'command.tmp'), os.path.join(self.ctl, 'command.txt')); break
            except PermissionError: time.sleep(0.02)
        self.wait_paused()
    def press(self, buttons, hold=8, settle=0): self.run(hold, buttons); self.run(max(1, settle))
    def shot(self, name):
        frame = self.status.get('gpu_frame') or self.status.get('frame')
        src = os.path.join(self.ctl, frame)
        out = ppm_to_png(src, os.path.join(self.dir, '%s-v%d.png' % (name, self.vblank)))
        print('shot', out, 'gpu' if self.status.get('gpu_capture') else 'guest', 'wall=%.2f' % time.time()); return out
    # Real keyboard/mouse input through Windows (the game window must be in
    # front): key <name> holds a key for a few vblanks, mouse <dx> <dy> moves.
    VK={'esc':0x1B,'enter':0x0D,'space':0x20,'tab':0x09,'shift':0xA0,'ctrl':0xA2,'up':0x26,'down':0x28,'left':0x25,'right':0x27}
    def focus(self):
        import ctypes
        u=ctypes.windll.user32; h=u.FindWindowW(None, 'Renegade Squadron | native PSPRecomp') or u.FindWindowW(None,'Renegade Squadron')
        if not h:
            buf=[]
            def cb(hwnd,_):
                n=ctypes.create_unicode_buffer(256); u.GetWindowTextW(hwnd,n,256)
                if n.value.startswith('Renegade Squadron'): buf.append(hwnd)
                return True
            u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)(cb),0); h=buf[0] if buf else 0
        if h: u.SetForegroundWindow(h)
        return h
    def send_key(self, vk, up):
        import ctypes
        class KI(ctypes.Structure): _fields_=[('wVk',ctypes.c_ushort),('wScan',ctypes.c_ushort),('dwFlags',ctypes.c_uint),('time',ctypes.c_uint),('dwExtraInfo',ctypes.c_void_p)]
        class IN(ctypes.Structure): _fields_=[('type',ctypes.c_uint),('ki',KI),('pad',ctypes.c_ubyte*8)]
        scan=ctypes.windll.user32.MapVirtualKeyW(vk,0)
        flags=0x8|(0x2 if up else 0)|(0x1 if vk in (0x25,0x26,0x27,0x28) else 0)  # scan code, key up, extended (arrows)
        inp=IN(1,KI(0,scan,flags,0,None)); ctypes.windll.user32.SendInput(1,ctypes.byref(inp),ctypes.sizeof(inp))
    def key(self, name, hold=8, settle=60):
        vk=self.VK.get(name.lower()) or ord(name.upper()[0]); self.focus()
        self.send_key(vk,False); self.run(hold); self.send_key(vk,True); self.run(settle)
    def mouse(self, dx, dy, frames=20, buttons=0):
        import ctypes
        self.focus(); step=max(1,frames)
        for i in range(step):
            ctypes.windll.user32.mouse_event(1,int(dx/step),int(dy/step),0,0); self.run(1)
        self.run(30)
    def mouse_button(self, button=1, hold=8, settle=60):
        import ctypes
        self.focus(); down,up={1:(2,4),2:(8,16),3:(32,64)}[button]
        ctypes.windll.user32.mouse_event(down,0,0,0,0); self.run(hold); ctypes.windll.user32.mouse_event(up,0,0,0,0); self.run(settle)
    def until(self, reference, max_frames=3000, step=30, threshold=3.0, crop=None):  # real matches score below 1; the title screen scored 6 against the profile page
        # Sync point: step until the presented frame looks like the reference
        # picture (mean absolute difference on a 64x36 downsample).
        from PIL import Image, ImageChops, ImageStat
        ref=Image.open(reference).convert('RGB'); ref=(ref.crop(crop) if crop else ref).resize((64,36))
        waited=0
        while waited<=max_frames:
            frame=self.status.get('gpu_frame') or self.status.get('frame')
            cur=Image.open(os.path.join(self.ctl, frame)).convert('RGB'); cur=(cur.crop(crop) if crop else cur).resize((64,36))
            diff=sum(ImageStat.Stat(ImageChops.difference(cur,ref)).mean)/3
            if diff<threshold: print('until', os.path.basename(reference), 'matched at vblank', self.vblank, 'diff %.1f'%diff); return True
            self.run(step); waited+=step
        print('until', os.path.basename(reference), 'NOT matched by vblank', self.vblank); return False
    def pressuntil(self, buttons, reference, max_frames=3000, crop=None):
        # Taps a button every two seconds until the reference picture shows (title screens with variable timing).
        waited=0
        while waited<=max_frames:
            if self.until(reference, 0, crop=crop): return True
            self.run(8, buttons); self.run(112); waited+=120
        return False
    def text(self, chars):
        # Types into the PC text-entry box through the control channel (no window focus needed).
        self.sequence += 1
        with open(os.path.join(self.ctl, 'command.tmp'), 'w') as f: f.write(('%d %d 0 128 128 text:%s' % (self.sequence, self.vblank + 30, chars)) + chr(10))
        for attempt in range(200):
            try: os.replace(os.path.join(self.ctl, 'command.tmp'), os.path.join(self.ctl, 'command.txt')); break
            except PermissionError: time.sleep(0.02)
        self.wait_paused()
    def quit(self):
        self.sequence += 1
        with open(os.path.join(self.ctl, 'command.txt'), 'w') as f: f.write('%d 0 0 128 128\n' % self.sequence)
        try: self.proc.wait(30)
        except subprocess.TimeoutExpired: self.proc.kill()

def main():
    name, script = sys.argv[1], sys.argv[2]
    start = 300
    for line in open(script):
        if line.startswith('start '): start = int(line.split()[1])
    d = Driver(name, start)
    for line in open(script):
        parts = line.split()
        if not parts or parts[0] in ('#', 'start'): continue
        if parts[0] == 'press': d.press(int(parts[1], 0), int(parts[2]) if len(parts) > 2 else 8, int(parts[3]) if len(parts) > 3 else 60)
        elif parts[0] == 'wait': d.run(int(parts[1]))
        elif parts[0] == 'shot': d.shot(parts[1])
        elif parts[0] == 'pressuntil': d.pressuntil(int(parts[1], 0), parts[2], int(parts[3]) if len(parts) > 3 else 3000, crop=tuple(int(v) for v in parts[4:8]) if len(parts) >= 8 else None)
        elif parts[0] == 'text': d.text(parts[1])
        elif parts[0] == 'until': d.until(parts[1], int(parts[2]) if len(parts) > 2 else 3000, crop=tuple(int(v) for v in parts[3:7]) if len(parts) >= 7 else None)
        elif parts[0] == 'key': d.key(parts[1], int(parts[2]) if len(parts) > 2 else 8, int(parts[3]) if len(parts) > 3 else 60)
        elif parts[0] == 'mouse': d.mouse(int(parts[1]), int(parts[2]), int(parts[3]) if len(parts) > 3 else 20)
        elif parts[0] == 'click': d.mouse_button(int(parts[1]) if len(parts) > 1 else 1)
        elif parts[0] == 'quit': d.quit(); return
    d.quit()

if __name__ == '__main__':
    main()
