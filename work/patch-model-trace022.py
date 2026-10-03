"""Compatibility entry point; the build also installs these hooks automatically."""
from pathlib import Path
import runpy
import sys
profile = Path(__file__).resolve().parent / 'project/source/profiles/renegade'
sys.argv = [str(profile / 'tools/patch_asset_hooks.py'), str(profile / 'generated'), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name='__main__')
