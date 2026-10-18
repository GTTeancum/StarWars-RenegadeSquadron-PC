r"""Drives the installed game through its menus for verification.

Uses the controller step channel (RENEGADE_CONTROL_DIRECTORY): the game pauses
at every vblank once RENEGADE_CONTROL_START is reached, writes the presented
GPU frame, and waits for command.txt "<sequence> <until-vblank> <buttons> <lx> <ly>".
Each step here holds buttons for a few vblanks, lets the game run on, then saves
the frame as PNG. Buttons use PSP bits (cross 0x4000, circle 0x2000, square
0x8000, triangle 0x1000, start 8, select 1, up 0x10, right 0x20, down 0x40, left 0x80).

Usage: python menu_drive.py <run-name> <script.txt>
  script lines:  press <buttons> [hold]   wait <vblanks>   shot <name>   quit
                 key <name> [hold] [settle]   mouse <dx> <dy> [frames]   cursor <x> <y> [settle]
                 click [button] [hold] [settle]   drag <x0> <y0> <x1> <y1> [steps]
                 until <ref.png> [max] [x0 y0 x1 y1]   waituntil <vblank>
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
                    'PSPRECOMP_DX12_GE_READBACK': '1',
                    # headless and silent: no window, no sound device
                    'PSPRECOMP_WINDOW': '0', 'PSPRECOMP_AUDIO': '0', 'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy'})
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
        vblanks = max(1, vblanks)  # the game rejects zero-length steps
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
    # Keyboard/mouse through the control channel (headless): key <name> holds an
    # SDL key for a few vblanks, mouse <dx> <dy> [frames] moves the mouse.
    KEYS={'esc':'Escape','enter':'Return','space':'Space','tab':'Tab','shift':'Left_Shift','ctrl':'Left_Ctrl','up':'Up','down':'Down','left':'Left','right':'Right','backspace':'Backspace'}
    def command(self, vblanks, buttons=0, extra=''):
        vblanks = max(1, vblanks)
        self.sequence += 1
        line='%d %d %d 128 128%s' % (self.sequence, self.vblank + vblanks, buttons, (' '+extra) if extra else '')
        with open(os.path.join(self.ctl, 'command.tmp'), 'w') as f: f.write(line + chr(10))
        for attempt in range(200):
            try: os.replace(os.path.join(self.ctl, 'command.tmp'), os.path.join(self.ctl, 'command.txt')); break
            except PermissionError: time.sleep(0.02)
        self.wait_paused()
    def key(self, name, hold=8, settle=60):
        # several keys held together with '+', e.g. key w+shift
        keys = '+'.join(self.KEYS.get(k.lower(), k.upper() if len(k) == 1 else k) for k in name.split('+'))
        self.command(hold, 0, 'key:' + keys); self.run(settle)
    def mouse(self, dx, dy, frames=20, buttons=0):
        step=max(1,frames)
        for i in range(step): self.command(1, 0, 'mouse:%d,%d' % (int(dx/step), int(dy/step)))
        self.run(30)
    def cursor(self, x, y, settle=30):
        # Places the menu cursor (PSP 480x272 screen coordinates) and lets the hover settle.
        self.command(1, 0, 'cursor:%g,%g' % (x, y)); self.run(settle)
    def mouse_button(self, button=1, hold=8, settle=60):
        # Presses a mouse button (1 left, 2 middle, 3 right) for a few vblanks, then releases it.
        self.command(hold, 0, 'click:%d' % button); self.command(1, 0, 'click:0'); self.run(settle)
    def drag(self, x0, y0, x1, y1, steps=8, settle=30):
        # Left-button drag from one cursor position to another (sliders).
        self.cursor(x0, y0, 10); self.command(3, 0, 'click:1')
        for i in range(1, steps + 1):
            t = i / steps; self.command(3, 0, 'cursor:%g,%g' % (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        self.command(1, 0, 'click:0'); self.run(settle)
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
    def keyuntil(self, name, reference, max_frames=3000, crop=None):
        # Taps a keyboard key every two seconds until the reference picture shows.
        waited=0
        while waited<=max_frames:
            if self.until(reference, 0, crop=crop): return True
            self.key(name, 8, 112); waited+=120
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
        elif parts[0] == 'waituntil': d.run(max(1, int(parts[1]) - d.vblank))  # reach a fixed vblank (RAM dump triggers)
        elif parts[0] == 'shot': d.shot(parts[1])
        elif parts[0] == 'pressuntil': d.pressuntil(int(parts[1], 0), parts[2], int(parts[3]) if len(parts) > 3 else 3000, crop=tuple(int(v) for v in parts[4:8]) if len(parts) >= 8 else None)
        elif parts[0] == 'text': d.text(parts[1])
        elif parts[0] == 'keyuntil': d.keyuntil(parts[1], parts[2], int(parts[3]) if len(parts) > 3 else 3000, crop=tuple(int(v) for v in parts[4:8]) if len(parts) >= 8 else None)
        elif parts[0] == 'until': d.until(parts[1], int(parts[2]) if len(parts) > 2 else 3000, crop=tuple(int(v) for v in parts[3:7]) if len(parts) >= 7 else None)
        elif parts[0] == 'key': d.key(parts[1], int(parts[2]) if len(parts) > 2 else 8, int(parts[3]) if len(parts) > 3 else 60)
        elif parts[0] == 'mouse': d.mouse(int(parts[1]), int(parts[2]), int(parts[3]) if len(parts) > 3 else 20)
        elif parts[0] == 'click': d.mouse_button(int(parts[1]) if len(parts) > 1 else 1, int(parts[2]) if len(parts) > 2 else 8, int(parts[3]) if len(parts) > 3 else 60)
        elif parts[0] == 'cursor': d.cursor(float(parts[1]), float(parts[2]), int(parts[3]) if len(parts) > 3 else 30)
        elif parts[0] == 'mousepattern':
            # mousepattern <dx,dx,...> <repeats>: one mouse step per vblank (uneven polling, e.g. 0,16)
            seq = [int(v) for v in parts[1].split(',')]
            for i in range(int(parts[2]) * len(seq)): d.command(1, 0, 'mouse:%d,0' % seq[i % len(seq)])
            d.run(30)
        elif parts[0] == 'clickuntil':
            # clickuntil <ref> [max]: left click every two seconds until the reference picture shows
            waited = 0; limit = int(parts[2]) if len(parts) > 2 else 3000
            while waited <= limit and not d.until(parts[1], 0):
                d.mouse_button(1, 8, 112); waited += 120
        elif parts[0] == 'wheel':
            # wheel <notches> [settle]: positive = up
            d.command(1, 0, 'wheel:%d' % int(parts[1])); d.run(int(parts[2]) if len(parts) > 2 else 30)
        elif parts[0] == 'drag': d.drag(*[float(v) for v in parts[1:5]], int(parts[5]) if len(parts) > 5 else 8)
        elif parts[0] == 'quit': d.quit(); return
    d.quit()

if __name__ == '__main__':
    main()
