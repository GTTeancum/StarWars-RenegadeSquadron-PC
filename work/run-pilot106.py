"""Run exactly the recorded native GPU pilot; no shell interpolation."""
import json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent.parent
plan=json.loads((root/'outputs/UPSCALER-106-pilot-plan.json').read_text())
if any((root/'work/upscale106/pilot/neural').iterdir()):raise SystemExit('Pilot outputs already exist; inspect those rather than overwrite them.')
raise SystemExit(subprocess.call(plan['command'],cwd=root/'work/upscale-tools/official-20220424',stdin=subprocess.DEVNULL))
