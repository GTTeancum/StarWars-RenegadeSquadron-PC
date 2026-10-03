"""Prepare a bounded full-vertex trace without changing gameplay input."""
from pathlib import Path
r=Path(__file__).resolve().parent.parent
s=(r/'work/capture-ground085.py').read_text().replace('085','086')
s=s.replace("env['RENEGADE_TRACE_WORLD_DRAWS']", "env['RENEGADE_TRACE_WORLD_FULL']='1'\nenv['RENEGADE_TRACE_WORLD_DRAWS']")
(r/'work/capture-ground086.py').write_text(s)
